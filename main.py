"""Application entry point."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from app.gui.main_window import MainWindow
from app.gui.style import apply_app_style


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("NX Section Layer Thickness Analyzer")
    apply_app_style(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
