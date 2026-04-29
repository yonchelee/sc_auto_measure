"""Apple Minimalism design system for the desktop app.

Tokens here are the single source of truth for colors, typography, spacing
and the Qt stylesheet (QSS).  They were chosen to evoke macOS / Apple's
minimalist aesthetic: generous negative space, hairline borders, bold
headlines, monochrome palette with a single subtle accent.
"""

from __future__ import annotations

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

# Color palette — light mode first.
COLORS = {
    "bg":          "#FFFFFF",  # primary background
    "surface":     "#F5F5F7",  # panels, alt rows  (Apple subtle gray)
    "surface_2":   "#FAFAFA",  # very subtle surface
    "border":      "#E5E5EA",  # 1 px hairline divider
    "text":        "#1D1D1F",  # primary text
    "text_muted":  "#6E6E73",  # secondary / caption
    "accent":      "#0071E3",  # Apple system blue (focus rings)
    "danger":      "#D70015",  # boundary / error — desaturated red
    "primary_bg":  "#1D1D1F",  # near-black for primary buttons
    "primary_fg":  "#FFFFFF",
    "hover_bg":    "#EFEFF1",  # subtle hover background
}

# Typography sizes (pt).
FONT_FAMILY_TEXT = "-apple-system, 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif"
FONT_FAMILY_DISPLAY = "-apple-system, 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"
FONT_FAMILY_MONO = "'SF Mono', Menlo, Consolas, monospace"

# Spacing scale.
S = {
    "xs":  4,
    "sm":  8,
    "md":  12,
    "lg":  16,
    "xl":  24,
    "xxl": 32,
}

# Corner radii.
R = {
    "sm": 6,
    "md": 8,
    "lg": 12,
}

# ---------------------------------------------------------------------------
# Stylesheet
# ---------------------------------------------------------------------------


def stylesheet() -> str:
    c = COLORS
    return f"""
    /* ---------- Application baseline ---------- */
    QWidget {{
        background-color: {c['bg']};
        color: {c['text']};
        font-family: {FONT_FAMILY_TEXT};
        font-size: 13px;
    }}

    QMainWindow, QDialog {{
        background-color: {c['bg']};
    }}

    QStatusBar {{
        background-color: {c['surface_2']};
        color: {c['text_muted']};
        border-top: 1px solid {c['border']};
        padding: 4px 12px;
        font-size: 12px;
    }}

    /* ---------- Menu bar ---------- */
    QMenuBar {{
        background-color: {c['bg']};
        border-bottom: 1px solid {c['border']};
        padding: 2px 8px;
        font-size: 13px;
    }}
    QMenuBar::item {{
        padding: 6px 12px;
        background: transparent;
        border-radius: {R['sm']}px;
    }}
    QMenuBar::item:selected {{
        background-color: {c['hover_bg']};
    }}
    QMenu {{
        background-color: {c['bg']};
        border: 1px solid {c['border']};
        border-radius: {R['md']}px;
        padding: 6px;
    }}
    QMenu::item {{
        padding: 6px 16px;
        border-radius: {R['sm']}px;
    }}
    QMenu::item:selected {{
        background-color: {c['hover_bg']};
    }}

    /* ---------- Splitter / dividers ---------- */
    QSplitter::handle {{
        background-color: {c['border']};
    }}
    QSplitter::handle:horizontal {{
        width: 1px;
    }}
    QSplitter::handle:vertical {{
        height: 1px;
    }}

    /* ---------- Labels ---------- */
    QLabel {{
        background: transparent;
        color: {c['text']};
    }}
    QLabel[role="title"] {{
        font-family: {FONT_FAMILY_DISPLAY};
        font-size: 18px;
        font-weight: 700;
        color: {c['text']};
        padding: 4px 0px;
    }}
    QLabel[role="caption"] {{
        color: {c['text_muted']};
        font-size: 12px;
    }}

    /* ---------- Buttons ---------- */
    QPushButton {{
        background-color: {c['bg']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: {R['md']}px;
        padding: 8px 14px;
        font-size: 13px;
        font-weight: 500;
        min-height: 18px;
    }}
    QPushButton:hover {{
        background-color: {c['hover_bg']};
    }}
    QPushButton:pressed {{
        background-color: {c['surface']};
    }}
    QPushButton:disabled {{
        color: {c['text_muted']};
        background-color: {c['surface_2']};
    }}
    QPushButton[role="primary"] {{
        background-color: {c['primary_bg']};
        color: {c['primary_fg']};
        border: 1px solid {c['primary_bg']};
    }}
    QPushButton[role="primary"]:hover {{
        background-color: #2C2C2E;
    }}
    QPushButton[role="primary"]:pressed {{
        background-color: #000000;
    }}
    QPushButton[role="danger"] {{
        background-color: {c['bg']};
        color: {c['danger']};
        border: 1px solid {c['border']};
    }}
    QPushButton[role="danger"]:hover {{
        background-color: #FFF2F2;
    }}

    /* ---------- Inputs ---------- */
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background-color: {c['bg']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: {R['sm']}px;
        padding: 6px 10px;
        selection-background-color: {c['accent']};
        selection-color: {c['primary_fg']};
        min-height: 18px;
    }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
        border: 1px solid {c['text']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background: {c['bg']};
        border: 1px solid {c['border']};
        border-radius: {R['md']}px;
        padding: 4px;
        selection-background-color: {c['hover_bg']};
        selection-color: {c['text']};
    }}

    /* ---------- Group boxes ---------- */
    QGroupBox {{
        background-color: {c['surface_2']};
        border: 1px solid {c['border']};
        border-radius: {R['md']}px;
        margin-top: 18px;
        padding: 12px 12px 8px 12px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        left: 8px;
        color: {c['text']};
        font-size: 13px;
    }}

    /* ---------- Table ---------- */
    QTableWidget {{
        background-color: {c['bg']};
        alternate-background-color: {c['surface_2']};
        gridline-color: {c['border']};
        border: 1px solid {c['border']};
        border-radius: {R['md']}px;
        font-family: {FONT_FAMILY_MONO};
        font-size: 12px;
    }}
    QTableWidget::item {{
        padding: 6px 8px;
        border: none;
    }}
    QTableWidget::item:selected {{
        background-color: {c['hover_bg']};
        color: {c['text']};
    }}
    QHeaderView::section {{
        background-color: {c['surface']};
        color: {c['text_muted']};
        padding: 8px 10px;
        border: none;
        border-right: 1px solid {c['border']};
        border-bottom: 1px solid {c['border']};
        font-family: {FONT_FAMILY_TEXT};
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    QHeaderView::section:last {{
        border-right: none;
    }}

    /* ---------- Scrollbars ---------- */
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {c['border']};
        border-radius: 4px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c['text_muted']};
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        margin: 4px;
    }}
    QScrollBar::handle:horizontal {{
        background: {c['border']};
        border-radius: 4px;
        min-width: 24px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {c['text_muted']};
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        height: 0; width: 0; background: transparent;
    }}
    QScrollBar::add-page, QScrollBar::sub-page {{
        background: transparent;
    }}

    /* ---------- Dialog button box ---------- */
    QDialogButtonBox QPushButton {{
        min-width: 88px;
    }}
    """


# ---------------------------------------------------------------------------
# Helpers used by the app to apply the design system.
# ---------------------------------------------------------------------------


def apply_app_style(app: QApplication) -> None:
    """Apply the global font + stylesheet to a QApplication."""
    # Pick the best available system font.
    families = set(QFontDatabase.families())
    preferred = [
        "SF Pro Text",
        "SF Pro",
        "Helvetica Neue",
        "Helvetica",
        "Arial",
    ]
    family = next((f for f in preferred if f in families), app.font().family())
    font = QFont(family, 13)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)
    app.setStyleSheet(stylesheet())


def title_label_style() -> str:
    """Return the inline style for a section title label."""
    return (
        f"font-family: {FONT_FAMILY_DISPLAY};"
        f"font-size: 20px;"
        f"font-weight: 700;"
        f"color: {COLORS['text']};"
        f"padding: 4px 0px;"
    )


def caption_label_style() -> str:
    return (
        f"font-family: {FONT_FAMILY_TEXT};"
        f"font-size: 12px;"
        f"color: {COLORS['text_muted']};"
    )
