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
