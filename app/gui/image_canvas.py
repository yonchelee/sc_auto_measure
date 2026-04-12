"""Interactive image canvas: drag&drop, scale/measure-line clicks, overlays."""

from __future__ import annotations

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
)
from PyQt6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
)

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
        self.setBackgroundBrush(QBrush(QColor(40, 40, 40)))

        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._image_bgr: Optional[np.ndarray] = None
        self._image_path: Optional[Path] = None

        self._mode: CanvasMode = CanvasMode.IDLE
        self._pending_point: Optional[QPointF] = None

        # Overlay items, kept so we can clear/redraw.
        self._scale_line_items: list = []
        self._measure_line_items: list = []
        self._boundary_items: list = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def image_bgr(self) -> Optional[np.ndarray]:
        return self._image_bgr

    @property
    def image_path(self) -> Optional[Path]:
        return self._image_path

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

    def draw_scale_line(self, p1: QPointF, p2: QPointF) -> None:
        for it in self._scale_line_items:
            self._scene.removeItem(it)
        self._scale_line_items.clear()
        pen = QPen(QColor(80, 160, 255), 2)
        pen.setCosmetic(True)
        line = self._scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), pen)
        self._scale_line_items.append(line)
        for pt in (p1, p2):
            ell = self._scene.addEllipse(pt.x() - 3, pt.y() - 3, 6, 6, pen)
            self._scale_line_items.append(ell)

    def draw_measure_line(self, p1: QPointF, p2: QPointF) -> None:
        for it in self._measure_line_items:
            self._scene.removeItem(it)
        self._measure_line_items.clear()
        pen = QPen(QColor(80, 220, 120), 2)
        pen.setCosmetic(True)
        line = self._scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), pen)
        self._measure_line_items.append(line)

    def draw_boundaries(self, points: List[QPointF], line_width: int = 40) -> None:
        """Draw short horizontal tick marks at each detected boundary."""
        for it in self._boundary_items:
            self._scene.removeItem(it)
        self._boundary_items.clear()
        pen = QPen(QColor(255, 80, 80), 2)
        pen.setCosmetic(True)
        for idx, pt in enumerate(points):
            x, y = pt.x(), pt.y()
            tick = self._scene.addLine(
                x - line_width / 2, y, x + line_width / 2, y, pen
            )
            self._boundary_items.append(tick)
            text = self._scene.addSimpleText(f"b{idx}")
            text.setBrush(QBrush(QColor(255, 80, 80)))
            text.setPos(x + line_width / 2 + 4, y - 8)
            self._boundary_items.append(text)

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
        self._pixmap_item = self._scene.addPixmap(pix)
        self._scene.setSceneRect(0, 0, w, h)
        self.resetTransform()
        self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
