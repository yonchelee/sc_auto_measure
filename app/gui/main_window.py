"""Main window wiring the canvas, measurement table and actions together."""

from __future__ import annotations

from pathlib import Path
from typing import List

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..core import edge_detector, excel_exporter
from ..core.measurement import Layer, Measurement
from ..core.scale_calibrator import ScaleCalibrator
from .image_canvas import CanvasMode, ImageCanvas
from .measurement_table import MeasurementTable
from .scale_dialog import ScaleDialog


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("NX Section Layer Thickness Analyzer")
        self.resize(1280, 820)

        self._calibrator = ScaleCalibrator()
        self._measurement = Measurement()

        self._canvas = ImageCanvas(self)
        self._table = MeasurementTable(self)

        self._build_ui()
        self._build_menu()
        self._connect_signals()
        self._update_status_labels()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(self._canvas)

        right = QWidget(self)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel("Measurements")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_layout.addWidget(title)

        right_layout.addWidget(self._table, 1)

        self._scale_label = QLabel("mm/pixel: n/a")
        self._mode_label = QLabel("모드: 탐색")
        right_layout.addWidget(self._scale_label)
        right_layout.addWidget(self._mode_label)

        button_row1 = QHBoxLayout()
        self._btn_scale = QPushButton("기준선 설정")
        self._btn_measure = QPushButton("측정선 그리기")
        button_row1.addWidget(self._btn_scale)
        button_row1.addWidget(self._btn_measure)
        right_layout.addLayout(button_row1)

        button_row2 = QHBoxLayout()
        self._btn_clear = QPushButton("초기화")
        self._btn_delete_row = QPushButton("선택 행 삭제")
        button_row2.addWidget(self._btn_delete_row)
        button_row2.addWidget(self._btn_clear)
        right_layout.addLayout(button_row2)

        self._btn_export = QPushButton("Excel로 내보내기")
        right_layout.addWidget(self._btn_export)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        self.setCentralWidget(splitter)

        self.statusBar().showMessage("이미지를 드래그하거나 파일을 여세요.")

    def _build_menu(self) -> None:
        menu = self.menuBar()
        file_menu = menu.addMenu("파일")

        open_act = QAction("이미지 열기…", self)
        open_act.setShortcut("Ctrl+O")
        open_act.triggered.connect(self._open_image_dialog)
        file_menu.addAction(open_act)

        save_act = QAction("Excel로 저장…", self)
        save_act.setShortcut("Ctrl+S")
        save_act.triggered.connect(self._export_dialog)
        file_menu.addAction(save_act)

        file_menu.addSeparator()
        quit_act = QAction("종료", self)
        quit_act.setShortcut("Ctrl+Q")
        quit_act.triggered.connect(self.close)
        file_menu.addAction(quit_act)

    def _connect_signals(self) -> None:
        self._canvas.statusMessage.connect(self.statusBar().showMessage)
        self._canvas.statusMessage.connect(self._mode_label.setText)
        self._canvas.imageLoaded.connect(self._on_image_loaded)
        self._canvas.scaleLineReady.connect(self._on_scale_line_ready)
        self._canvas.measureLineReady.connect(self._on_measure_line_ready)

        self._btn_scale.clicked.connect(
            lambda: self._canvas.set_mode(CanvasMode.SET_SCALE)
        )
        self._btn_measure.clicked.connect(self._start_measure_mode)
        self._btn_clear.clicked.connect(self._clear_measurements)
        self._btn_delete_row.clicked.connect(self._delete_selected_row)
        self._btn_export.clicked.connect(self._export_dialog)

        self._table.layerRenamed.connect(self._on_layer_renamed)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_image_loaded(self, path: Path) -> None:
        self._measurement = Measurement(
            image_path=Path(path),
            layers=[],
            mm_per_pixel=self._calibrator.mm_per_pixel,
        )
        self._table.clear_layers()
        self._update_status_labels()

    def _on_scale_line_ready(self, p1: QPointF, p2: QPointF) -> None:
        pixel_distance = (
            (p2.x() - p1.x()) ** 2 + (p2.y() - p1.y()) ** 2
        ) ** 0.5
        if pixel_distance <= 0:
            QMessageBox.warning(self, "오류", "두 점의 거리가 0입니다.")
            return
        dialog = ScaleDialog(pixel_distance, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        real_mm = dialog.real_mm()
        try:
            self._calibrator.set_reference(
                (p1.x(), p1.y()), (p2.x(), p2.y()), real_mm
            )
        except ValueError as err:
            QMessageBox.warning(self, "오류", str(err))
            return
        self._measurement.mm_per_pixel = self._calibrator.mm_per_pixel
        self._measurement.recompute_all()
        self._table.set_layers(self._measurement.layers)
        self._update_status_labels()

    def _start_measure_mode(self) -> None:
        if self._canvas.image_bgr is None:
            QMessageBox.information(self, "안내", "먼저 이미지를 불러오세요.")
            return
        if not self._calibrator.is_calibrated:
            reply = QMessageBox.question(
                self,
                "스케일 미설정",
                "기준선이 설정되지 않았습니다. 계속하시겠습니까?\n"
                "(mm 단위 값이 0으로 표시됩니다)",
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self._canvas.set_mode(CanvasMode.DRAW_MEASURE_LINE)

    def _on_measure_line_ready(self, p1: QPointF, p2: QPointF) -> None:
        image = self._canvas.image_bgr
        if image is None:
            return
        layers: List[Layer] = edge_detector.detect_layers(
            image, (p1.x(), p1.y()), (p2.x(), p2.y())
        )
        if not layers:
            QMessageBox.information(
                self,
                "검출 실패",
                "레이어를 찾지 못했습니다. 측정선 위치를 조정해 보세요.",
            )
            return
        self._measurement.replace_layers(layers)
        self._table.set_layers(self._measurement.layers)
        self._draw_boundary_overlays(p1, p2)
        self._update_status_labels()

    def _draw_boundary_overlays(self, p1: QPointF, p2: QPointF) -> None:
        points = []
        for layer in self._measurement.layers:
            points.append(QPointF(p1.x(), layer.y_top_px))
        if self._measurement.layers:
            last = self._measurement.layers[-1]
            points.append(QPointF(p1.x(), last.y_bottom_px))
        self._canvas.draw_boundaries(points)

    def _on_layer_renamed(self, row: int, new_name: str) -> None:
        if 0 <= row < len(self._measurement.layers):
            self._measurement.layers[row].name = new_name

    def _clear_measurements(self) -> None:
        self._measurement.clear()
        self._table.clear_layers()
        self._canvas.draw_boundaries([])

    def _delete_selected_row(self) -> None:
        rows = sorted({idx.row() for idx in self._table.selectedIndexes()}, reverse=True)
        for row in rows:
            if 0 <= row < len(self._measurement.layers):
                del self._measurement.layers[row]
        # Rename remaining layers sequentially.
        for i, layer in enumerate(self._measurement.layers, start=1):
            layer.name = f"Layer {i}"
        self._table.set_layers(self._measurement.layers)

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def _open_image_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "이미지 열기",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)",
        )
        if path:
            self._canvas.load_image(Path(path))

    def _export_dialog(self) -> None:
        if not self._measurement.layers:
            QMessageBox.information(self, "안내", "내보낼 데이터가 없습니다.")
            return
        default_name = "measurements.xlsx"
        if self._measurement.image_path is not None:
            default_name = self._measurement.image_path.stem + "_measurements.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Excel로 저장",
            default_name,
            "Excel Workbook (*.xlsx)",
        )
        if not path:
            return
        out = Path(path)
        if out.suffix.lower() != ".xlsx":
            out = out.with_suffix(".xlsx")
        try:
            excel_exporter.export(
                out, self._measurement, self._measurement.image_path
            )
        except Exception as err:  # pragma: no cover - user feedback path
            QMessageBox.critical(self, "저장 실패", str(err))
            return
        self.statusBar().showMessage(f"저장 완료: {out}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _update_status_labels(self) -> None:
        if self._calibrator.is_calibrated:
            self._scale_label.setText(
                f"mm/pixel: {self._calibrator.mm_per_pixel:.5f}"
            )
        else:
            self._scale_label.setText("mm/pixel: n/a (기준선 미설정)")
