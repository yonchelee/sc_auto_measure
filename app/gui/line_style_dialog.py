"""Dialog for editing the visual style of canvas overlay lines."""

from __future__ import annotations

from dataclasses import replace
from typing import Optional, Tuple

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..core.line_style import ArrowShape, CanvasStyle, LineStyle

_ARROW_LABELS = [
    ("없음", ArrowShape.NONE),
    ("화살표", ArrowShape.ARROW),
    ("점", ArrowShape.DOT),
    ("사선", ArrowShape.DASH),
]


class _ColorButton(QPushButton):
    """Small button that shows the current color and opens a picker on click."""

    def __init__(self, initial: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(80)
        self._color = QColor(initial)
        self._refresh()
        self.clicked.connect(self._pick)

    def color_hex(self) -> str:
        return self._color.name()

    def set_color_hex(self, value: str) -> None:
        c = QColor(value)
        if c.isValid():
            self._color = c
            self._refresh()

    def _refresh(self) -> None:
        self.setText(self._color.name())
        # Choose readable text color based on luminance.
        lum = (
            0.299 * self._color.red()
            + 0.587 * self._color.green()
            + 0.114 * self._color.blue()
        )
        text = "#000000" if lum > 140 else "#FFFFFF"
        self.setStyleSheet(
            f"background-color: {self._color.name()}; color: {text};"
            " padding: 4px;"
        )

    def _pick(self) -> None:
        chosen = QColorDialog.getColor(self._color, self, "색상 선택")
        if chosen.isValid():
            self._color = chosen
            self._refresh()


class _LineStyleGroup(QGroupBox):
    """Group with color / width / arrow controls for a single LineStyle."""

    def __init__(
        self,
        title: str,
        line_style: LineStyle,
        *,
        with_arrow: bool = True,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(title, parent)
        form = QFormLayout(self)

        self._color_btn = _ColorButton(line_style.color, self)
        form.addRow("색상", self._color_btn)

        self._width_spin = QSpinBox(self)
        self._width_spin.setRange(1, 20)
        self._width_spin.setValue(int(line_style.width))
        form.addRow("두께 (px)", self._width_spin)

        self._arrow_combo: Optional[QComboBox] = None
        if with_arrow:
            self._arrow_combo = QComboBox(self)
            for label, shape in _ARROW_LABELS:
                self._arrow_combo.addItem(label, shape)
            idx = next(
                (
                    i
                    for i, (_, s) in enumerate(_ARROW_LABELS)
                    if s == line_style.arrow
                ),
                0,
            )
            self._arrow_combo.setCurrentIndex(idx)
            form.addRow("화살표", self._arrow_combo)

    def to_line_style(self, base: LineStyle) -> LineStyle:
        arrow = base.arrow
        if self._arrow_combo is not None:
            arrow = self._arrow_combo.currentData()
        return replace(
            base,
            color=self._color_btn.color_hex(),
            width=int(self._width_spin.value()),
            arrow=arrow,
        )


class LineStyleDialog(QDialog):
    """Edit colors, widths, arrow shape and (optionally) line position."""

    def __init__(
        self,
        style: CanvasStyle,
        measure_endpoints: Optional[Tuple[QPointF, QPointF]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("선 스타일 편집")
        self._style = style

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self._scale_group = _LineStyleGroup(
            "기준선 (Scale)", style.scale, with_arrow=True, parent=self
        )
        self._measure_group = _LineStyleGroup(
            "측정선 (Measure)", style.measure, with_arrow=True, parent=self
        )
        self._boundary_group = _LineStyleGroup(
            "경계 표시 (Boundary)",
            style.boundary,
            with_arrow=False,
            parent=self,
        )
        layout.addWidget(self._scale_group)
        layout.addWidget(self._measure_group)
        layout.addWidget(self._boundary_group)

        # Position editing for the measure line endpoints.
        self._pos_group: Optional[QGroupBox] = None
        self._pos_spins: list[QDoubleSpinBox] = []
        if measure_endpoints is not None:
            self._pos_group = QGroupBox("측정선 위치 (px)", self)
            form = QFormLayout(self._pos_group)
            form.setSpacing(10)
            form.setContentsMargins(8, 8, 8, 8)
            p1, p2 = measure_endpoints
            for label, value in (
                ("시작 X", p1.x()),
                ("시작 Y", p1.y()),
                ("끝 X", p2.x()),
                ("끝 Y", p2.y()),
            ):
                spin = QDoubleSpinBox(self._pos_group)
                spin.setRange(-100000.0, 100000.0)
                spin.setDecimals(2)
                spin.setSingleStep(1.0)
                spin.setValue(float(value))
                form.addRow(label, spin)
                self._pos_spins.append(spin)
            layout.addWidget(self._pos_group)
            note = QLabel(
                "위치 변경 시 측정선이 새 좌표로 이동합니다.\n"
                "기존 레이어 측정값은 유지되며 다시 검출하려면\n"
                "측정선 그리기를 다시 실행하세요."
            )
            note.setProperty("role", "caption")
            note.setStyleSheet("color: #6E6E73; font-size: 12px;")
            layout.addWidget(note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def result_style(self) -> CanvasStyle:
        return CanvasStyle(
            scale=self._scale_group.to_line_style(self._style.scale),
            measure=self._measure_group.to_line_style(self._style.measure),
            boundary=self._boundary_group.to_line_style(self._style.boundary),
        )

    def result_endpoints(self) -> Optional[Tuple[QPointF, QPointF]]:
        if not self._pos_spins:
            return None
        return (
            QPointF(self._pos_spins[0].value(), self._pos_spins[1].value()),
            QPointF(self._pos_spins[2].value(), self._pos_spins[3].value()),
        )
