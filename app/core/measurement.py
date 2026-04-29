"""Data classes for a measurement session."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class Layer:
    """A single detected stack layer along the measurement line."""

    name: str
    y_top_px: float
    y_bottom_px: float
    thickness_px: float
    thickness_mm: float = 0.0

    def recompute(self, mm_per_pixel: Optional[float]) -> None:
        self.thickness_px = abs(self.y_bottom_px - self.y_top_px)
        if mm_per_pixel is not None:
            self.thickness_mm = self.thickness_px * mm_per_pixel
        else:
            self.thickness_mm = 0.0

    # ------------------------------------------------------------------
    # Manual editing helpers — keep all four numeric fields consistent
    # whenever one of them is changed by the user from the table.
    # ------------------------------------------------------------------

    def set_top_px(self, value: float, mm_per_pixel: Optional[float]) -> None:
        """Update ``y_top_px`` and refresh thickness fields."""
        self.y_top_px = float(value)
        self.recompute(mm_per_pixel)

    def set_bottom_px(self, value: float, mm_per_pixel: Optional[float]) -> None:
        """Update ``y_bottom_px`` and refresh thickness fields."""
        self.y_bottom_px = float(value)
        self.recompute(mm_per_pixel)

    def set_thickness_px(
        self, value: float, mm_per_pixel: Optional[float]
    ) -> None:
        """Set thickness in pixels by moving the bottom edge.

        ``y_top_px`` is left untouched, ``y_bottom_px`` is recomputed so that
        ``|bottom - top| == value``.  The new bottom keeps the same direction
        (above/below the top) as before.
        """
        value = float(value)
        if value < 0:
            raise ValueError("thickness must be >= 0")
        sign = 1.0 if self.y_bottom_px >= self.y_top_px else -1.0
        self.y_bottom_px = self.y_top_px + sign * value
        self.recompute(mm_per_pixel)

    def set_thickness_mm(
        self, value: float, mm_per_pixel: Optional[float]
    ) -> None:
        """Set thickness in millimetres.

        Requires a calibrated ``mm_per_pixel`` so we can back-compute the new
        pixel thickness; otherwise raises :class:`ValueError`.
        """
        value = float(value)
        if value < 0:
            raise ValueError("thickness must be >= 0")
        if mm_per_pixel is None or mm_per_pixel <= 0:
            raise ValueError(
                "mm/pixel ratio is not calibrated; cannot edit mm value"
            )
        new_thickness_px = value / mm_per_pixel
        self.set_thickness_px(new_thickness_px, mm_per_pixel)


@dataclass
class Measurement:
    """All layers extracted from the currently loaded image."""

    image_path: Optional[Path] = None
    layers: List[Layer] = field(default_factory=list)
    mm_per_pixel: Optional[float] = None

    def clear(self) -> None:
        self.layers.clear()

    def replace_layers(self, layers: List[Layer]) -> None:
        self.layers = list(layers)
        self.recompute_all()

    def recompute_all(self) -> None:
        for layer in self.layers:
            layer.recompute(self.mm_per_pixel)
