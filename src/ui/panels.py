# --------------------------------------------------------
# File: src/ui/panels.py
"""
Simple UI panels drawing helpers.
Not using an external UI library; builds on arcade draw primitives.
"""
import arcade
from typing import Dict


def draw_top_panel(window_width: int, height: int = 120):
    # background
    arcade.draw_lrtb_rectangle_filled(0, window_width, height, 0, arcade.color.DARK_SLATE_GRAY)


def draw_bottom_panel(window_width: int, window_height: int, height: int = 120):
    arcade.draw_lrtb_rectangle_filled(0, window_width, window_height, window_height - height, arcade.color.DARK_SLATE_GRAY)


def draw_info_block(x: float, y: float, w: float, h: float, title: str, data: Dict[str, str]):
    arcade.draw_lrtb_rectangle_filled(x, x + w, y + h, y, arcade.color.LIGHT_GRAY)
    arcade.draw_rectangle_outline(x + w / 2.0, y + h / 2.0, w, h, arcade.color.BLACK)
    arcade.draw_text(title, x + 8, y + h - 22, arcade.color.BLACK, 14, bold=True)
    oy = y + h - 44
    for k, v in data.items():
        arcade.draw_text(f"{k}: {v}", x + 10, oy, arcade.color.BLACK, 12)
        oy -= 18
