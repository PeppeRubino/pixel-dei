# --------------------------------------------------------
# File: src/rendering/arcade_renderer.py
# Integrated macOS-style renderer with full-canvas world map
# --------------------------------------------------------

import os
import math
import arcade
from PIL import Image
import numpy as np

from ui.input import Button
from commands.mouse_input import MouseInputHandler


DEFAULT_BG = arcade.color.BLACK


def _hex_to_rgb(hexstr: str):
    s = hexstr.lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    return tuple(int(s[i:i+2], 16) for i in (0, 2, 4))


# --------------------------------------------------------
# MAIN WINDOW
# --------------------------------------------------------

class ArcadeRenderer(arcade.Window):

    def __init__(self, world, pixel_manager, window_size=(1200, 800), tile_size=4):
        super().__init__(
            window_size[0],
            window_size[1],
            "Evolutive Simulator",
            resizable=True,
            antialiasing=True
        )

        self.world = world
        self.pixels = pixel_manager
        self.tile_size = tile_size

        # --- CAMERA SYSTEM ---
        self.scale = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0

        self.dragging = False
        self.drag_start_mouse = (0, 0)
        self.drag_threshold = 4

        self.paused = False
        self.selected_pixel = None
        self.selected_biome = None

        # --- BUTTONS (Mac floating) ---
        self.btn_start = Button(20, self.height - 44, 110, 26, "▶︎ / ❚❚")
        self.btn_reset = Button(140, self.height - 44, 90, 26, "Reset")

        self._prepare_biome_texture()

        self.input = MouseInputHandler(self)

        arcade.schedule(self._update, 1/60)

    # --------------------------------------------------------
    # MAP TEXTURE
    # --------------------------------------------------------

    def _prepare_biome_texture(self):
        img_arr = self.world.color_map()
        pil = Image.fromarray(img_arr, mode="RGB")

        os.makedirs("data/cache", exist_ok=True)
        path = os.path.join("data", "cache", "biome_preview.png")
        pil.save(path)

        self.bg_texture = arcade.load_texture(path)

    # --------------------------------------------------------
    # UPDATE LOOP
    # --------------------------------------------------------

    def _update(self, delta_time):
        if not self.paused:
            self.pixels.step(delta_time, self.world, getattr(self.world, "resource_grid", None))

    # --------------------------------------------------------
    # CAMERA CLAMP
    # --------------------------------------------------------

    def _clamp_offsets(self):
        view_w = self.world.size[0] / self.scale
        view_h = self.world.size[1] / self.scale

        self.offset_x = max(0, min(self.offset_x, self.world.size[0] - view_w))
        self.offset_y = max(0, min(self.offset_y, self.world.size[1] - view_h))

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    def on_draw(self):
        arcade.start_render()
        arcade.set_background_color(DEFAULT_BG)

        # ------------------------
        # FULL-CANVAS MAP (NO DIV EFFECT)
        # ------------------------

        vw = self.width / self.scale
        vh = self.height / self.scale

        tx1 = self.offset_x / self.world.size[0]
        ty1 = self.offset_y / self.world.size[1]
        tx2 = (self.offset_x + vw) / self.world.size[0]
        ty2 = (self.offset_y + vh) / self.world.size[1]

        arcade.draw_lrwh_rectangle_textured(
            0, 0,
            self.width,
            self.height,
            self.bg_texture,
            tex_coords=(tx1, ty1, tx2, ty2)
        )

        # ------------------------
        # PIXELS OVERLAY
        # ------------------------

        for i in range(self.pixels.count):
            if not self.pixels.alive[i]:
                continue

            x = self.pixels.positions[i, 0]
            y = self.pixels.positions[i, 1]

            sx = (x - self.offset_x) * self.scale
            sy = (y - self.offset_y) * self.scale

            if not (0 <= sx <= self.width and 0 <= sy <= self.height):
                continue

            energy = self.pixels.energies[i]
            r = max(2.0, 3.5 * self.scale)

            color = _hex_to_rgb("#00FFAA") if energy > 0.5 else _hex_to_rgb("#FF9900")
            arcade.draw_circle_filled(sx, sy, r, color)

            if self.selected_pixel == i:
                arcade.draw_circle_outline(sx, sy, r + 4, arcade.color.CYAN, 2)

        # ------------------------
        # MAC-STYLE FLOATING UI
        # ------------------------

        self._draw_glass_panel(16, self.height - 72, 270, 60)
        self._draw_glass_panel(20, 20, 420, 120)

        # Buttons
        self.btn_start.rect = (30, self.height - 54, 110, 28)
        self.btn_reset.rect = (150, self.height - 54, 90, 28)
        self._draw_button(self.btn_start)
        self._draw_button(self.btn_reset)

        # Info Panels
        self._draw_info()

    # --------------------------------------------------------
    # MAC-STYLE GLASS PANEL
    # --------------------------------------------------------

    def _draw_glass_panel(self, x, y, w, h):
        arcade.draw_rectangle_filled(
            x + w / 2,
            y + h / 2,
            w, h,
            (40, 40, 40, 190)
        )
        arcade.draw_rectangle_outline(
            x + w / 2,
            y + h / 2,
            w, h,
            arcade.color.WHITE_SMOKE,
            1.2
        )

    def _draw_button(self, btn):
        x, y, w, h = btn.rect
        arcade.draw_rectangle_filled(x + w / 2, y + h / 2, w, h, (90, 90, 90))
        arcade.draw_text(btn.label, x + 10, y + 6, arcade.color.WHITE, 14)

    # --------------------------------------------------------
    # INFO UI
    # --------------------------------------------------------

    def _draw_info(self):
        world_info = {
            "size": f"{self.world.size[0]} x {self.world.size[1]}",
            "pixels": str(self.pixels.count),
            "alive": str(np.sum(self.pixels.alive))
        }

        self._draw_text_block(30, 100, "World", world_info)

        if self.selected_pixel is not None:
            px = self.pixels.get_pixel_info(self.selected_pixel)
            self._draw_text_block(220, 100, "Pixel", px)

    def _draw_text_block(self, x, y, title, data):
        arcade.draw_text(title, x, y + 70, arcade.color.CYAN, 12, bold=True)
        yy = y + 52
        for k, v in data.items():
            arcade.draw_text(f"{k}: {v}", x, yy, arcade.color.WHITE_SMOKE, 11)
            yy -= 16

    # --------------------------------------------------------
    # INPUT DELEGATION
    # --------------------------------------------------------

    def on_mouse_press(self, x, y, button, modifiers):
        self.input.on_mouse_press(x, y, button, modifiers)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        self.input.on_mouse_drag(x, y, dx, dy, buttons, modifiers)

    def on_mouse_release(self, x, y, button, modifiers):
        self.input.on_mouse_release(x, y, button, modifiers)

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        self.scale *= 1.1 ** scroll_y
        self.scale = max(0.2, min(6.0, self.scale))
        self._clamp_offsets()

    def on_key_press(self, symbol, modifiers):
        if symbol == arcade.key.SPACE:
            self.paused = not self.paused

    def run(self):
        arcade.run()
