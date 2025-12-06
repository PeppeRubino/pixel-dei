# --------------------------------------------------------
# File: src/gui/layout.py
#
# Layout helpers for the single-window GUI.
# Provides panel rectangles for:
#   - top world-info bar
#   - left pixel-info panel
#   - bottom controls bar
#   - central map area
# --------------------------------------------------------

from typing import Tuple

Rect = Tuple[float, float, float, float]


def compute_main_layout(
    window_width: int,
    window_height: int,
    padding: int = 16,
    top_height: int = 64,
    bottom_height: int = 80,
    right_width: int = 280,
) -> Tuple[Rect, Rect, Rect, Rect]:
    """
    Returns (world_rect, side_rect, bottom_rect, map_rect).
    Rect format is (x, y, w, h).

    Layout:
      - world_rect: full-width top bar with controls / overlay
      - side_rect: right sidebar with global + selected-pixel info + evolution log
      - bottom_rect: full-width bottom strip for graphs / metrics
      - map_rect: central area for the world map
    """
    full_w, full_h = window_width, window_height

    # Top control bar
    top_y = full_h - top_height - padding
    world_rect = (padding, top_y, full_w - 2 * padding, top_height)

    # Bottom row: graphs / metrics panel
    bottom_y = padding
    bottom_rect = (padding, bottom_y, full_w - 2 * padding, bottom_height)

    # Right sidebar between top and bottom
    side_x = full_w - right_width - padding
    side_y = bottom_y + bottom_height + padding
    side_top = top_y - padding
    side_h = max(1, side_top - side_y)
    side_rect = (side_x, side_y, right_width, side_h)

    # Central map area: left of sidebar, between top and bottom
    map_x = padding
    map_y = side_y
    map_w = max(1, side_x - padding - map_x)
    map_h = side_h
    map_rect = (map_x, map_y, map_w, map_h)

    return world_rect, side_rect, bottom_rect, map_rect


def rect_contains(rect: Rect, x: float, y: float) -> bool:
    rx, ry, rw, rh = rect
    return rx <= x <= rx + rw and ry <= y <= ry + rh
