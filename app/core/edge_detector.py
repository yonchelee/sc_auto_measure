"""OpenCV-based layer detection along a user-drawn measurement line."""

from __future__ import annotations

from typing import List, Sequence, Tuple

import cv2
import numpy as np

from .measurement import Layer

Point = Tuple[float, float]


def _auto_canny_thresholds(gray: np.ndarray, sigma: float = 0.33) -> Tuple[int, int]:
    median = float(np.median(gray))
    lower = int(max(0, (1.0 - sigma) * median))
    upper = int(min(255, (1.0 + sigma) * median))
    if upper <= lower:
        upper = lower + 1
    return lower, upper


def compute_edge_map(image_bgr: np.ndarray) -> np.ndarray:
    """Return a binary edge map from a BGR image."""
    if image_bgr is None or image_bgr.size == 0:
        raise ValueError("image_bgr is empty")
    if image_bgr.ndim == 3:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    else:
        gray = image_bgr
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    low, high = _auto_canny_thresholds(blurred)
    return cv2.Canny(blurred, low, high)


def _sample_along_line(
    edge_map: np.ndarray, p1: Point, p2: Point
) -> Tuple[np.ndarray, np.ndarray]:
    """Sample edge values along the line, return (t-values, edge-hits)."""
    x1, y1 = p1
    x2, y2 = p2
    length = int(round(max(abs(x2 - x1), abs(y2 - y1)))) + 1
    length = max(length, 2)
    xs = np.linspace(x1, x2, length)
    ys = np.linspace(y1, y2, length)
    h, w = edge_map.shape[:2]
    xi = np.clip(np.round(xs).astype(int), 0, w - 1)
    yi = np.clip(np.round(ys).astype(int), 0, h - 1)
    samples = edge_map[yi, xi]
    return np.arange(length, dtype=float), samples


def _find_boundaries(
    t_values: np.ndarray, samples: np.ndarray, merge_gap: int = 2
) -> List[float]:
    """Return t-values (position along sampled line) of merged edge boundaries."""
    hits = np.where(samples > 0)[0]
    if hits.size == 0:
        return []
    groups: List[List[int]] = [[int(hits[0])]]
    for idx in hits[1:]:
        if idx - groups[-1][-1] <= merge_gap:
            groups[-1].append(int(idx))
        else:
            groups.append([int(idx)])
    return [float(np.mean(g)) for g in groups]


def detect_layers(
    image_bgr: np.ndarray,
    p1: Point,
    p2: Point,
    *,
    min_thickness_px: float = 2.0,
    merge_gap: int = 2,
) -> List[Layer]:
    """Detect stack layers along the line p1->p2 on ``image_bgr``.

    The returned layers have ``thickness_mm == 0`` — the caller should apply
    :meth:`Measurement.recompute_all` after assigning ``mm_per_pixel``.
    """
    edge_map = compute_edge_map(image_bgr)
    t_values, samples = _sample_along_line(edge_map, p1, p2)
    if samples.size == 0:
        return []

    boundaries_t = _find_boundaries(t_values, samples, merge_gap=merge_gap)
    if len(boundaries_t) < 2:
        return []

    # Convert back to y-pixel positions (projecting t onto the line).
    x1, y1 = p1
    x2, y2 = p2
    total = float(t_values[-1]) if t_values[-1] > 0 else 1.0

    def t_to_y(t: float) -> float:
        return y1 + (y2 - y1) * (t / total)

    layers: List[Layer] = []
    for i in range(len(boundaries_t) - 1):
        y_top = t_to_y(boundaries_t[i])
        y_bot = t_to_y(boundaries_t[i + 1])
        thickness_px = abs(y_bot - y_top)
        # If the measurement line is mostly horizontal, fall back to the
        # parametric length rather than y-difference.
        if abs(y2 - y1) < abs(x2 - x1):
            thickness_px = abs(boundaries_t[i + 1] - boundaries_t[i])
        if thickness_px < min_thickness_px:
            continue
        layers.append(
            Layer(
                name=f"Layer {len(layers) + 1}",
                y_top_px=float(y_top),
                y_bottom_px=float(y_bot),
                thickness_px=float(thickness_px),
                thickness_mm=0.0,
            )
        )
    return layers


def layers_from_boundaries(
    boundaries: Sequence[float], *, min_thickness_px: float = 2.0
) -> List[Layer]:
    """Rebuild layers from a sorted list of y-pixel boundaries (manual edit)."""
    sorted_b = sorted(float(b) for b in boundaries)
    layers: List[Layer] = []
    for i in range(len(sorted_b) - 1):
        thickness = sorted_b[i + 1] - sorted_b[i]
        if thickness < min_thickness_px:
            continue
        layers.append(
            Layer(
                name=f"Layer {len(layers) + 1}",
                y_top_px=sorted_b[i],
                y_bottom_px=sorted_b[i + 1],
                thickness_px=thickness,
                thickness_mm=0.0,
            )
        )
    return layers
