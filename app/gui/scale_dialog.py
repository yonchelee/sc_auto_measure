"""Dialog that asks the user for the real length of the reference line."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
)


class ScaleDialog(QDialog):
    """Modal dialog returning a real-world length in millimetres."""

    def __init__(self, pixel_distance: float, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("기준선 실제 길이 입력")
        self._pixel_distance = pixel_distance

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        info = QLabel(
            f"클릭한 두 점의 픽셀 거리: <b>{pixel_distance:.2f} px</b><br>"
            "이 거리가 실제로 몇 mm 인지 입력하세요."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        form = QFormLayout()
        self._spin = QDoubleSpinBox(self)
        self._spin.setDecimals(3)
        self._spin.setRange(0.001, 10000.0)
        self._spin.setSingleStep(0.1)
        self._spin.setValue(10.0)
        self._spin.setSuffix(" mm")
        form.addRow("실제 길이:", self._spin)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def real_mm(self) -> float:
        return float(self._spin.value())

    @property
    def pixel_distance(self) -> float:
        return self._pixel_distance
