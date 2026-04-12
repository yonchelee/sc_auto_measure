"""Generate a synthetic NX-style section screenshot for testing.

Run:
    python examples/generate_sample.py

Outputs:
    examples/sample_section.png   (800 x 520 PNG)

The image contains five stacked layers of known pixel thicknesses and a
10 mm scale bar (100 px) so the app can be end-to-end validated.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


# Layer (name, pixel thickness, BGR fill colour)
LAYERS = [
    ("Top Coat",      20, (230, 230, 230)),
    ("Adhesive",      15, (120, 180, 240)),
    ("Core Metal",    60, (170, 170, 170)),
    ("Insulator",     30, (110, 200, 140)),
    ("Base",          45, ( 90,  90,  90)),
]

WIDTH = 800
MARGIN_TOP = 60
MARGIN_BOTTOM = 280
STACK_X = 220
STACK_W = 360

SCALE_BAR_PX = 100   # 100 px == 10 mm  -> 0.1 mm/px


def draw_scale_bar(img: np.ndarray) -> None:
    """Draw a 100 px = 10 mm scale bar in the bottom-left corner."""
    h, w = img.shape[:2]
    x0, y0 = 60, h - 40
    x1 = x0 + SCALE_BAR_PX
    black = (0, 0, 0)
    cv2.line(img, (x0, y0), (x1, y0), black, 2)
    cv2.line(img, (x0, y0 - 8), (x0, y0 + 8), black, 2)
    cv2.line(img, (x1, y0 - 8), (x1, y0 + 8), black, 2)
    cv2.putText(
        img,
        "10 mm",
        (x0 + 20, y0 - 14),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        black,
        1,
        cv2.LINE_AA,
    )


def draw_title(img: np.ndarray) -> None:
    cv2.putText(
        img,
        "NX Section - Sample Stack (for testing)",
        (40, 36),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 0, 0),
        1,
        cv2.LINE_AA,
    )


def draw_stack(img: np.ndarray) -> list[tuple[str, int, int]]:
    """Draw the layered stack, return [(name, y_top, y_bottom), ...]."""
    y = MARGIN_TOP
    out: list[tuple[str, int, int]] = []
    for name, thickness, colour in LAYERS:
        cv2.rectangle(
            img,
            (STACK_X, y),
            (STACK_X + STACK_W, y + thickness),
            colour,
            thickness=-1,
        )
        # Dark boundary for strong Canny edge.
        cv2.rectangle(
            img,
            (STACK_X, y),
            (STACK_X + STACK_W, y + thickness),
            (40, 40, 40),
            thickness=1,
        )
        # Label to the right of the stack.
        cv2.putText(
            img,
            f"{name}  ({thickness} px)",
            (STACK_X + STACK_W + 16, y + thickness // 2 + 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            1,
            cv2.LINE_AA,
        )
        out.append((name, y, y + thickness))
        y += thickness
    return out


def main() -> Path:
    total_stack_h = sum(h for _, h, _ in LAYERS)
    height = MARGIN_TOP + total_stack_h + MARGIN_BOTTOM

    img = np.full((height, WIDTH, 3), 255, dtype=np.uint8)
    draw_title(img)
    layers = draw_stack(img)
    draw_scale_bar(img)

    # Legend at the bottom: expected mm values given the 10 mm / 100 px bar.
    mm_per_px = 10.0 / SCALE_BAR_PX
    legend_y = MARGIN_TOP + total_stack_h + 40
    cv2.putText(
        img,
        f"Scale: 100 px = 10 mm  ->  {mm_per_px:.3f} mm/px",
        (60, legend_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 0, 0),
        1,
        cv2.LINE_AA,
    )
    for i, (name, y_top, y_bot) in enumerate(layers):
        thickness_px = y_bot - y_top
        mm = thickness_px * mm_per_px
        cv2.putText(
            img,
            f"Expected Layer {i + 1} ({name}): {thickness_px} px = {mm:.2f} mm",
            (60, legend_y + 24 + i * 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (60, 60, 60),
            1,
            cv2.LINE_AA,
        )

    out_path = Path(__file__).resolve().parent / "sample_section.png"
    cv2.imwrite(str(out_path), img)
    print(f"Wrote {out_path}")
    return out_path


if __name__ == "__main__":
    main()
