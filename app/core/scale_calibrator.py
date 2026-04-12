"""Pixel <-> millimetre conversion state."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple

Point = Tuple[float, float]


@dataclass
class ScaleCalibrator:
    """Holds the current reference line and derived mm/pixel ratio."""

    p1: Optional[Point] = None
    p2: Optional[Point] = None
    real_mm: Optional[float] = None
    mm_per_pixel: Optional[float] = None

    @property
    def is_calibrated(self) -> bool:
        return self.mm_per_pixel is not None and self.mm_per_pixel > 0

    def set_reference(self, p1: Point, p2: Point, real_mm: float) -> float:
        """Set two screen points and the real distance between them (mm)."""
        if real_mm <= 0:
            raise ValueError("real_mm must be positive")
        pixel_distance = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if pixel_distance <= 0:
            raise ValueError("Reference line has zero length")
        self.p1 = p1
        self.p2 = p2
        self.real_mm = real_mm
        self.mm_per_pixel = real_mm / pixel_distance
        return self.mm_per_pixel

    def reset(self) -> None:
        self.p1 = None
        self.p2 = None
        self.real_mm = None
        self.mm_per_pixel = None

    def to_mm(self, pixels: float) -> float:
        if not self.is_calibrated:
            return 0.0
        return pixels * float(self.mm_per_pixel)
