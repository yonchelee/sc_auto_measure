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

# Column indices for clarity.
COL_NAME = 0
COL_TOP = 1
COL_BOTTOM = 2
COL_THICK_PX = 3
COL_THICK_MM = 4
NUMERIC_COLUMNS = (COL_TOP, COL_BOTTOM, COL_THICK_PX, COL_THICK_MM)


class MeasurementTable(QTableWidget):
    """Excel-style table.

    The ``Layer`` (name) column is text-editable.  All four numeric columns —
    Top (px), Bottom (px), Thickness (px) and Thickness (mm) — are also
    user-editable; edits emit :pyattr:`valueEdited` and the parent window is
    expected to update the underlying :class:`Layer` and re-render the table
    so the dependent fields stay consistent.
    """

    layerRenamed = pyqtSignal(int, str)
    # row, column index, parsed float value
    valueEdited = pyqtSignal(int, int, float)
    # row, column index — emitted when the user typed something that wasn't
    # a valid number; the parent should re-render the table to revert.
    valueEditFailed = pyqtSignal(int, int)

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
        self.setItem(row, COL_NAME, name_item)

        values = [
            (COL_TOP, f"{layer.y_top_px:.2f}"),
            (COL_BOTTOM, f"{layer.y_bottom_px:.2f}"),
            (COL_THICK_PX, f"{layer.thickness_px:.2f}"),
            (COL_THICK_MM, f"{layer.thickness_mm:.4f}"),
        ]
        for col, text in values:
            item = QTableWidgetItem(text)
            item.setFlags(
                Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsEditable
            )
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.setItem(row, col, item)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._updating:
            return
        col = item.column()
        row = item.row()
        if col == COL_NAME:
            self.layerRenamed.emit(row, item.text())
            return
        if col in NUMERIC_COLUMNS:
            try:
                value = float(item.text().strip())
            except ValueError:
                self.valueEditFailed.emit(row, col)
                return
            self.valueEdited.emit(row, col, value)

    def clear_layers(self) -> None:
        self._updating = True
        try:
            self.setRowCount(0)
        finally:
            self._updating = False
