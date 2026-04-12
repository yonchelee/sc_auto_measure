"""QTableWidget wrapper displaying the list of measured layers."""

from __future__ import annotations

from typing import List

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

from ..core.measurement import Layer

COLUMN_HEADERS = [
    "Layer",
    "Top (px)",
    "Bottom (px)",
    "Thickness (px)",
    "Thickness (mm)",
]


class MeasurementTable(QTableWidget):
    """Excel-style table. Only the ``Layer`` column is user-editable."""

    layerRenamed = pyqtSignal(int, str)

    def __init__(self, parent=None) -> None:
        super().__init__(0, len(COLUMN_HEADERS), parent)
        self.setHorizontalHeaderLabels(COLUMN_HEADERS)
        self.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(self.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        self._updating = False
        self.itemChanged.connect(self._on_item_changed)

    def set_layers(self, layers: List[Layer]) -> None:
        self._updating = True
        try:
            self.setRowCount(len(layers))
            for row, layer in enumerate(layers):
                self._populate_row(row, layer)
        finally:
            self._updating = False

    def _populate_row(self, row: int, layer: Layer) -> None:
        name_item = QTableWidgetItem(layer.name)
        name_item.setFlags(
            Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsEditable
        )
        self.setItem(row, 0, name_item)

        values = [
            f"{layer.y_top_px:.2f}",
            f"{layer.y_bottom_px:.2f}",
            f"{layer.thickness_px:.2f}",
            f"{layer.thickness_mm:.4f}",
        ]
        for col, text in enumerate(values, start=1):
            item = QTableWidgetItem(text)
            item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.setItem(row, col, item)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._updating or item.column() != 0:
            return
        self.layerRenamed.emit(item.row(), item.text())

    def clear_layers(self) -> None:
        self._updating = True
        try:
            self.setRowCount(0)
        finally:
            self._updating = False
