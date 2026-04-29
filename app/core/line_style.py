"""Configurable visual style for lines drawn on the canvas."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ArrowShape(str, Enum):
    """Shape used to decorate the endpoints of the measurement line."""

    NONE = "none"
    ARROW = "arrow"
    DOT = "dot"
    DASH = "dash"


@dataclass
class LineStyle:
    """Color + thickness + arrowhead settings for a single line type."""

    # ARGB-style hex string, e.g. ``"#50A0FF"``.  Stored as a string so it
    # can be round-tripped through Qt and JSON without depending on QColor.
    color: str = "#50A0FF"
    width: int = 2
    arrow: ArrowShape = ArrowShape.NONE


@dataclass
class CanvasStyle:
    """Style settings for every kind of overlay drawn on the canvas."""

    scale: LineStyle = None  # type: ignore[assignment]
    measure: LineStyle = None  # type: ignore[assignment]
    boundary: LineStyle = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.scale is None:
            self.scale = LineStyle(color="#50A0FF", width=2, arrow=ArrowShape.NONE)
        if self.measure is None:
            self.measure = LineStyle(
                color="#50DC78", width=2, arrow=ArrowShape.ARROW
            )
        if self.boundary is None:
            self.boundary = LineStyle(
                color="#FF5050", width=2, arrow=ArrowShape.NONE
            )
