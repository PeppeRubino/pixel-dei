"""
World view mixin for the DearPyGui app.

Responsabilità:
  - texture dei biomi
  - area di disegno centrale con mappa + pixel
  - gestione camera (zoom/pan)
  - selezione pixel con il mouse
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Tuple, Set

import numpy as np
import dearpygui.dearpygui as dpg

from .dpg_constants import WINDOW_W, WINDOW_H, TOP_H, WORLD_W

if TYPE_CHECKING:  # pragma: no cover
    from .dpg_app import DPGApp


class WorldViewMixin:
    world: object
    pm: object
    view_x0: float
    view_y0: float
    view_x1: float
    view_y1: float

    # ---------------------------- texture ----------------------------

    def _world_color_map_rgba(self: "DPGApp") -> List[float]:
        """Return current world biome map as flattened RGBA floats in [0,1]."""
        img = self.world.color_map()  # (h, w, 3) uint8
        h, w, _ = img.shape
        self.texture_w, self.texture_h = w, h
        rgb = img.astype("float32") / 255.0
        alpha = np.ones((h, w, 1), dtype="float32")
        rgba = np.concatenate([rgb, alpha], axis=2)
        return rgba.flatten().tolist()

    # ------------------------------ build ----------------------------

    def _build_world_window(self: "DPGApp") -> None:
        with dpg.window(
            tag="world_window",
            pos=(0, TOP_H),
            width=WORLD_W,
            height=WINDOW_H - TOP_H,
            no_move=True,
            no_resize=True,
            no_title_bar=True,
        ):
            with dpg.drawlist(width=WORLD_W, height=WINDOW_H - TOP_H, tag="world_drawlist"):
                dpg.draw_image(
                    "world_texture",
                    pmin=(0, 0),
                    pmax=(WORLD_W, WINDOW_H - TOP_H),
                    uv_min=(0, 0),
                    uv_max=(1, 1),
                )

    # --------------------------- input handlers ----------------------

    def _on_mouse_click(self, sender, app_data):
        # DearPyGui versions differ: app_data can be int, list, dict...
        if isinstance(app_data, int):
            button = int(app_data)
        elif isinstance(app_data, (list, tuple)) and len(app_data) >= 1:
            try:
                button = int(app_data[0])
            except Exception:
                button = 0
        elif isinstance(app_data, dict):
            try:
                button = int(app_data.get("button", 0))
            except Exception:
                button = 0
        else:
            button = 0
        if button != 0:
            return

        mx, my = dpg.get_mouse_pos()
        if not (0 <= mx <= WORLD_W):
            return

        world_w, world_h = self.world.size
        local_x = mx
        local_y = my - TOP_H
        vx0, vx1 = self.view_x0, self.view_x1
        vy0, vy1 = self.view_y0, self.view_y1
        vw = max(1e-6, vx1 - vx0)
        vh = max(1e-6, vy1 - vy0)
        wx = vx0 + (local_x / max(1.0, WORLD_W)) * vw
        wy = vy0 + (1.0 - (local_y / max(1.0, WINDOW_H - TOP_H))) * vh

        best = None
        bestd = 1e9
        for i in range(self.pm.count):
            if not self.pm.alive[i]:
                continue
            px = float(self.pm.positions[i, 0])
            py = float(self.pm.positions[i, 1])
            dx = px - wx
            dy = py - wy
            d = (dx * dx + dy * dy) ** 0.5
            if d < bestd:
                bestd = d
                best = i
        self.selected_pixel = best

    def _on_mouse_wheel(self, sender, app_data):
        try:
            delta = float(app_data)
        except Exception:
            return
        if delta == 0.0:
            return
        zoom_factor = 0.1 * (1.0 if delta > 0 else -1.0)
        vx0, vx1 = self.view_x0, self.view_x1
        vy0, vy1 = self.view_y0, self.view_y1
        cx = 0.5 * (vx0 + vx1)
        cy = 0.5 * (vy0 + vy1)
        w = (vx1 - vx0) * (1.0 - zoom_factor)
        h = (vy1 - vy0) * (1.0 - zoom_factor)
        world_w, world_h = self.world.size
        min_w = world_w * 0.1
        min_h = world_h * 0.1
        max_w = float(world_w)
        max_h = float(world_h)
        w = float(min(max(w, min_w), max_w))
        h = float(min(max(h, min_h), max_h))
        self.view_x0 = max(0.0, cx - w * 0.5)
        self.view_x1 = min(float(world_w - 1), cx + w * 0.5)
        self.view_y0 = max(0.0, cy - h * 0.5)
        self.view_y1 = min(float(world_h - 1), cy + h * 0.5)

    def _on_mouse_drag(self, sender, app_data):
        mx, my = dpg.get_mouse_pos()
        if not (0 <= mx <= WORLD_W and TOP_H <= my <= WINDOW_H):
            self._last_pan_pos = None
            return
        if self._last_pan_pos is None:
            self._last_pan_pos = (mx, my)
            return
        lx, ly = self._last_pan_pos
        dx_screen = mx - lx
        dy_screen = my - ly
        self._last_pan_pos = (mx, my)

        vx0, vx1 = self.view_x0, self.view_x1
        vy0, vy1 = self.view_y0, self.view_y1
        vw = max(1e-6, vx1 - vx0)
        vh = max(1e-6, vy1 - vy0)
        dx_world = -dx_screen / max(1.0, WORLD_W) * vw
        dy_world = dy_screen / max(1.0, WINDOW_H - TOP_H) * vh

        world_w, world_h = self.world.size
        max_x0 = max(0.0, float(world_w - 1) - vw)
        max_y0 = max(0.0, float(world_h - 1) - vh)
        self.view_x0 = min(max(0.0, vx0 + dx_world), max_x0)
        self.view_x1 = self.view_x0 + vw
        self.view_y0 = min(max(0.0, vy0 + dy_world), max_y0)
        self.view_y1 = self.view_y0 + vh

    # -------------------------- draw loop ---------------------------

    def _update_world_drawlist(self: "DPGApp") -> None:
        dpg.delete_item("world_drawlist", children_only=True)

        world_w, world_h = self.world.size
        vx0, vx1 = self.view_x0, self.view_x1
        vy0, vy1 = self.view_y0, self.view_y1
        vw = max(1e-6, vx1 - vx0)
        vh = max(1e-6, vy1 - vy0)

        u0 = float(vx0) / max(1.0, world_w - 1)
        u1 = float(vx1) / max(1.0, world_w - 1)
        v0 = float(vy0) / max(1.0, world_h - 1)
        v1 = float(vy1) / max(1.0, world_h - 1)
        uv_min = (u0, 1.0 - v1)
        uv_max = (u1, 1.0 - v0)

        dpg.draw_image(
            "world_texture",
            pmin=(0, 0),
            pmax=(WORLD_W, WINDOW_H - TOP_H),
            uv_min=uv_min,
            uv_max=uv_max,
            parent="world_drawlist",
        )

        h_screen = WINDOW_H - TOP_H
        traits_list = getattr(self.pm, "traits", None)

        for i in range(self.pm.count):
            if not self.pm.alive[i]:
                continue
            x = float(self.pm.positions[i, 0])
            y = float(self.pm.positions[i, 1])
            if not (vx0 <= x <= vx1 and vy0 <= y <= vy1):
                continue
            sx = (x - vx0) / vw * WORLD_W
            sy = (1.0 - (y - vy0) / vh) * h_screen
            e = float(self.pm.energies[i])

            tset: Set[str] = set()
            if traits_list is not None and i < len(traits_list):
                try:
                    tset = set(traits_list[i])
                except Exception:
                    tset = set()

            if not tset:
                base_r, base_g, base_b = 80, 210, 255
            else:
                sig = "".join(sorted(tset))
                h = sum(ord(c) for c in sig)
                base_r = 80 + (h * 37) % 150
                base_g = 80 + (h * 57) % 150
                base_b = 80 + (h * 97) % 150

            factor = 0.4 + 0.6 * max(0.0, min(1.0, e))
            r = int(base_r * factor)
            g = int(base_g * factor)
            b = int(base_b * factor)
            col = (r, g, b, 255)

            dpg.draw_circle(center=(sx, sy), radius=3.0, color=col, fill=col, parent="world_drawlist")

