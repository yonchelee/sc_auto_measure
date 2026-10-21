"""Interactive image canvas: drag&drop, scale/measure-line clicks, overlays."""

from __future__ import annotations

import math
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QPen,
    QPixmap,
    QPolygonF,
)
from PyQt6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
)

from ..core.line_style import ArrowShape, CanvasStyle, LineStyle

Point = Tuple[float, float]

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


class CanvasMode(Enum):
    IDLE = auto()
    SET_SCALE = auto()
    DRAW_MEASURE_LINE = auto()


class ImageCanvas(QGraphicsView):
    """Displays a NX section screenshot and captures user input."""

    imageLoaded = pyqtSignal(Path)
    scaleLineReady = pyqtSignal(QPointF, QPointF)
    measureLineReady = pyqtSignal(QPointF, QPointF)
    statusMessage = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(self.renderHints())
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setAcceptDrops(True)
        self.setMinimumWidth(600)
        self.setBackgroundBrush(QBrush(QColor("#F5F5F7")))

        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._image_bgr: Optional[np.ndarray] = None
        self._image_path: Optional[Path] = None

        self._mode: CanvasMode = CanvasMode.IDLE
        self._pending_point: Optional[QPointF] = None

        # Overlay items, kept so we can clear/redraw.
        self._scale_line_items: list = []
        self._measure_line_items: list = []
        self._boundary_items: list = []

        # Remember last drawn endpoints so we can redraw with new styles.
        self._scale_p1: Optional[QPointF] = None
        self._scale_p2: Optional[QPointF] = None
        self._measure_p1: Optional[QPointF] = None
        self._measure_p2: Optional[QPointF] = None
        self._boundary_points: List[QPointF] = []

        # Visual style.
        self._style: CanvasStyle = CanvasStyle()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def image_bgr(self) -> Optional[np.ndarray]:
        return self._image_bgr

    @property
    def image_path(self) -> Optional[Path]:
        return self._image_path

    @property
    def style(self) -> CanvasStyle:
        return self._style

    @property
    def measure_endpoints(self) -> Optional[Tuple[QPointF, QPointF]]:
        if self._measure_p1 is None or self._measure_p2 is None:
            return None
        return (QPointF(self._measure_p1), QPointF(self._measure_p2))

    def set_style(self, style: CanvasStyle) -> None:
        self._style = style
        self._redraw_all_overlays()

    def set_measure_endpoints(self, p1: QPointF, p2: QPointF) -> None:
        """Update the measurement line position without re-detecting layers."""
        self.draw_measure_line(p1, p2)

    def set_mode(self, mode: CanvasMode) -> None:
        self._mode = mode
        self._pending_point = None
        if mode is CanvasMode.IDLE:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.statusMessage.emit("모드: 탐색")
        else:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.CrossCursor)
            label = {
                CanvasMode.SET_SCALE: "모드: 기준선 설정 (두 점 클릭)",
                CanvasMode.DRAW_MEASURE_LINE: "모드: 측정선 (두 점 클릭)",
            }[mode]
            self.statusMessage.emit(label)

    def load_image(self, path: Path) -> bool:
        path = Path(path)
        if not path.exists():
            self.statusMessage.emit(f"파일 없음: {path}")
            return False
        data = np.fromfile(str(path), dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if img is None:
            self.statusMessage.emit(f"이미지 디코드 실패: {path.name}")
            return False
        self._image_bgr = img
        self._image_path = path
        self._display_pixmap(img)
        self.clear_overlays()
        self.imageLoaded.emit(path)
        self.statusMessage.emit(f"이미지 로드: {path.name}")
        return True

    def clear_overlays(self) -> None:
        for items in (
            self._scale_line_items,
            self._measure_line_items,
            self._boundary_items,
        ):
            for it in items:
                self._scene.removeItem(it)
            items.clear()
        self._scale_p1 = self._scale_p2 = None
        self._measure_p1 = self._measure_p2 = None
        self._boundary_points = []

    def draw_scale_line(self, p1: QPointF, p2: QPointF) -> None:
        self._scale_p1 = QPointF(p1)
        self._scale_p2 = QPointF(p2)
        self._render_scale_line()

    def draw_measure_line(self, p1: QPointF, p2: QPointF) -> None:
        self._measure_p1 = QPointF(p1)
        self._measure_p2 = QPointF(p2)
        self._render_measure_line()

    def draw_boundaries(self, points: List[QPointF], line_width: int = 40) -> None:
        """Draw short horizontal tick marks at each detected boundary."""
        self._boundary_points = [QPointF(p) for p in points]
        self._boundary_tick_width = line_width
        self._render_boundaries()

    # ------------------------------------------------------------------
    # Rendering helpers (re-callable so style updates take effect)
    # ------------------------------------------------------------------

    def _redraw_all_overlays(self) -> None:
        self._render_scale_line()
        self._render_measure_line()
        self._render_boundaries()

    def _make_pen(self, line_style: LineStyle) -> QPen:
        color = QColor(line_style.color)
        if not color.isValid():
            color = QColor(255, 255, 255)
        pen = QPen(color, max(1, int(line_style.width)))
        pen.setCosmetic(True)
        return pen

    def _render_scale_line(self) -> None:
        for it in self._scale_line_items:
            self._scene.removeItem(it)
        self._scale_line_items.clear()
        if self._scale_p1 is None or self._scale_p2 is None:
            return
        pen = self._make_pen(self._style.scale)
        p1, p2 = self._scale_p1, self._scale_p2
        line = self._scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), pen)
        self._scale_line_items.append(line)
        for pt in (p1, p2):
            ell = self._scene.addEllipse(pt.x() - 3, pt.y() - 3, 6, 6, pen)
            self._scale_line_items.append(ell)
        # End decorations for the scale line if requested.
        self._draw_endpoint_decorations(
            self._scale_line_items, p1, p2, self._style.scale
        )

    def _render_measure_line(self) -> None:
        for it in self._measure_line_items:
            self._scene.removeItem(it)
        self._measure_line_items.clear()
        if self._measure_p1 is None or self._measure_p2 is None:
            return
        pen = self._make_pen(self._style.measure)
        p1, p2 = self._measure_p1, self._measure_p2
        line = self._scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), pen)
        self._measure_line_items.append(line)
        self._draw_endpoint_decorations(
            self._measure_line_items, p1, p2, self._style.measure
        )

    def _render_boundaries(self) -> None:
        for it in self._boundary_items:
            self._scene.removeItem(it)
        self._boundary_items.clear()
        if not self._boundary_points:
            return
        pen = self._make_pen(self._style.boundary)
        color = QColor(self._style.boundary.color)
        if not color.isValid():
            color = QColor(255, 80, 80)
        line_width = getattr(self, "_boundary_tick_width", 40)
        for idx, pt in enumerate(self._boundary_points):
            x, y = pt.x(), pt.y()
            tick = self._scene.addLine(
                x - line_width / 2, y, x + line_width / 2, y, pen
            )
            self._boundary_items.append(tick)
            text = self._scene.addSimpleText(f"b{idx}")
            text.setBrush(QBrush(color))
            text.setPos(x + line_width / 2 + 4, y - 8)
            self._boundary_items.append(text)

    def _draw_endpoint_decorations(
        self,
        bucket: list,
        p1: QPointF,
        p2: QPointF,
        line_style: LineStyle,
    ) -> None:
        """Draw shape decorations (arrow/dot/dash) at line endpoints."""
        shape = line_style.arrow
        if shape is ArrowShape.NONE:
            return
        color = QColor(line_style.color)
        if not color.isValid():
            color = QColor(255, 255, 255)
        pen = QPen(color, max(1, int(line_style.width)))
        pen.setCosmetic(True)
        brush = QBrush(color)
        size = max(6, int(line_style.width) * 4)

        for tip, opp in ((p1, p2), (p2, p1)):
            self._draw_single_endpoint(
                bucket, tip, opp, shape, pen, brush, size
            )

    def _draw_single_endpoint(
        self,
        bucket: list,
        tip: QPointF,
        opp: QPointF,
        shape: ArrowShape,
        pen: QPen,
        brush: QBrush,
        size: int,
    ) -> None:
        if shape is ArrowShape.DOT:
            r = size / 2
            ell = self._scene.addEllipse(
                tip.x() - r, tip.y() - r, size, size, pen, brush
            )
            bucket.append(ell)
            return

        # Direction from tip back toward the opposite endpoint.
        dx = opp.x() - tip.x()
        dy = opp.y() - tip.y()
        length = math.hypot(dx, dy)
        if length == 0:
            return
        ux, uy = dx / length, dy / length

        if shape is ArrowShape.ARROW:
            # Triangle pointing away from `opp`.
            base_x = tip.x() + ux * size
            base_y = tip.y() + uy * size
            # Perpendicular vector.
            px, py = -uy, ux
            half = size / 2
            poly = QPolygonF(
                [
                    tip,
                    QPointF(base_x + px * half, base_y + py * half),
                    QPointF(base_x - px * half, base_y - py * half),
                ]
            )
            item = self._scene.addPolygon(poly, pen, brush)
            bucket.append(item)
        elif shape is ArrowShape.DASH:
            # Short perpendicular dash crossing the tip.
            px, py = -uy, ux
            half = size / 2
            line = self._scene.addLine(
                tip.x() - px * half,
                tip.y() - py * half,
                tip.x() + px * half,
                tip.y() + py * half,
                pen,
            )
            bucket.append(line)

    # ------------------------------------------------------------------
    # Drag & drop
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event) -> None:
        if self._has_image_url(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if self._has_image_url(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.suffix.lower() in _IMAGE_EXTENSIONS:
                self.load_image(path)
                event.acceptProposedAction()
                return
        event.ignore()

    @staticmethod
    def _has_image_url(event) -> bool:
        if not event.mimeData().hasUrls():
            return False
        for url in event.mimeData().urls():
            if Path(url.toLocalFile()).suffix.lower() in _IMAGE_EXTENSIONS:
                return True
        return False

    # ------------------------------------------------------------------
    # Mouse handling
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if self._mode is CanvasMode.IDLE or self._pixmap_item is None:
            super().mousePressEvent(event)
            return
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        scene_pt = self.mapToScene(event.pos())
        if self._pending_point is None:
            self._pending_point = scene_pt
            self.statusMessage.emit("두 번째 점을 클릭하세요.")
            return

        p1 = self._pending_point
        p2 = scene_pt
        self._pending_point = None

        if self._mode is CanvasMode.SET_SCALE:
            self.draw_scale_line(p1, p2)
            self.scaleLineReady.emit(p1, p2)
        elif self._mode is CanvasMode.DRAW_MEASURE_LINE:
            # Snap to vertical unless Shift is held.
            if not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                p2 = QPointF(p1.x(), p2.y())
            self.draw_measure_line(p1, p2)
            self.measureLineReady.emit(p1, p2)

        self.set_mode(CanvasMode.IDLE)

    def wheelEvent(self, event) -> None:
        if self._pixmap_item is None:
            return
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.scale(factor, factor)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _display_pixmap(self, image_bgr: np.ndarray) -> None:
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
        pix = QPixmap.fromImage(qimg)
        self._scene.clear()
        self._scale_line_items.clear()
        self._measure_line_items.clear()
        self._boundary_items.clear()
        self._scale_p1 = self._scale_p2 = None
        self._measure_p1 = self._measure_p2 = None
        self._boundary_points = []
        self._pixmap_item = self._scene.addPixmap(pix)
        self._scene.setSceneRect(0, 0, w, h)
        self.resetTransform()
        self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
