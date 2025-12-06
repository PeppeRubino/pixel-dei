"""
Pyglet-based renderer for the Evolutive Simulator.

Single-window view with:
  - central 2D world map (biomes + pixels)
  - top world-info bar
  - left pixel-info panel
  - bottom control bar (Play/Pause, Reset, Speed)

DearPyGui integration is optional and lives in a separate viewport.
"""
from typing import Optional, Tuple, List

import numpy as np
import pyglet
from pyglet import shapes
from collections import deque

from simulation.core import Simulation
from gui.layout import compute_main_layout, rect_contains
from ui.input import Button


class WorldWindow(pyglet.window.Window):
    def __init__(self, sim: Simulation, width: int = 1200, height: int = 800):
        super().__init__(width=width, height=height, caption="Evolutive Simulator (Pyglet)")
        self.sim = sim

        # camera / viewport state (world coordinates)
        self.scale = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0

        self.dragging = False
        self.drag_start = (0.0, 0.0)
        self.drag_start_offset = (0.0, 0.0)

        self.selected_pixel: Optional[int] = None

        # remember initial pixel count for reset
        self._initial_pixels = int(self.sim.pixels.count)

        # UI layout rects (updated each frame)
        self._world_rect: Tuple[float, float, float, float] = (0, 0, 0, 0)
        self._pixel_rect: Tuple[float, float, float, float] = (0, 0, 0, 0)
        self._bottom_rect: Tuple[float, float, float, float] = (0, 0, 0, 0)
        self._map_rect: Tuple[float, float, float, float] = (0, 0, 0, 0)

        # UI buttons in bottom bar
        self.btn_play = Button(0, 0, 0, 0, "Pause" if not self.sim.paused else "Play")
        self.btn_reset = Button(0, 0, 0, 0, "Reset")
        self.btn_speed = Button(0, 0, 0, 0, f"Speed {self.sim.speed:.1f}x")
        self._speed_cycle: List[float] = [0.5, 1.0, 2.0, 4.0, 8.0]

        # aggregated stats and histories for bottom graphs / global state
        self._last_alive: Optional[int] = None
        self._avg_energy: float = 0.0
        self._avg_stress: float = 0.0
        self._pop_history = deque(maxlen=200)
        self._energy_history = deque(maxlen=200)
        self._stress_history = deque(maxlen=200)
        self._evo_log = deque(maxlen=6)

        # biome texture (rebuilt when world marks it dirty)
        self._biome_texture = None
        self._rebuild_biome_texture()

        # schedule simulation updates; render is driven by pyglet's event loop
        pyglet.clock.schedule_interval(self._update_simulation, 1.0 / 60.0)

        # DearPyGui integration is currently disabled to keep a single OS window.
        # Hooks are left in place for future in-window overlays if desired.
        self._dpg = None

    # -------------------------------------------------
    # BIOME TEXTURE
    # -------------------------------------------------

    def _rebuild_biome_texture(self):
        world = self.sim.world
        img = world.color_map()  # (h, w, 3) uint8
        h, w, _ = img.shape
        # Pyglet expects bottom-left origin; our array is row 0 at top,
        # so flip vertically.
        img_flipped = np.flipud(img)
        data = img_flipped.tobytes()
        self._biome_texture = pyglet.image.ImageData(w, h, "RGB", data, pitch=w * 3)

    # -------------------------------------------------
    # SIMULATION UPDATE
    # -------------------------------------------------

    def _update_simulation(self, dt: float):
        # step simulation according to internal speed/paused flags
        self.sim.step(dt)

        # if world biomes have been marked dirty by environment,
        # rebuild texture
        if getattr(self.sim.world, "_biome_dirty", False):
            try:
                self._rebuild_biome_texture()
            except Exception:
                pass
            setattr(self.sim.world, "_biome_dirty", False)

        # update global stats and histories for plots / sidebar
        pm = self.sim.pixels
        if pm.count > 0:
            alive_mask = pm.alive[: pm.count]
            alive = int(np.sum(alive_mask))
        else:
            alive_mask = None
            alive = 0

        if alive > 0 and alive_mask is not None:
            energies = pm.energies[: pm.count][alive_mask]
            avg_e = float(np.mean(energies))
            var_e = float(np.var(energies))
        else:
            avg_e = 0.0
            var_e = 0.0

        energy_deficit = max(0.0, 0.5 - avg_e)
        stress = energy_deficit + var_e

        self._avg_energy = avg_e
        self._avg_stress = stress
        self._pop_history.append(alive)
        self._energy_history.append(avg_e)
        self._stress_history.append(stress)

        # simple evolution log based on population changes
        if self._last_alive is None:
            self._last_alive = alive
        else:
            if alive == 0 and self._last_alive > 0:
                self._evo_log.appendleft("Population extinct")
            elif alive > self._last_alive:
                delta = alive - self._last_alive
                self._evo_log.appendleft(f"{delta} new cells")
            elif alive < self._last_alive:
                self._evo_log.appendleft("Population bottleneck")
            self._last_alive = alive

    # -------------------------------------------------
    # DRAW
    # -------------------------------------------------

    def on_draw(self):
        self.clear()
        world = self.sim.world
        pixels = self.sim.pixels

        world_w, world_h = world.size

        # layout panels
        self._world_rect, self._pixel_rect, self._bottom_rect, self._map_rect = compute_main_layout(
            self.width, self.height
        )
        map_x, map_y, map_w, map_h = self._map_rect

        # clamp camera to map area
        self._clamp_camera()

        # draw biome texture into map_rect based on camera viewport
        if self._biome_texture is not None:
            self._draw_biome_layer(world_w, world_h, map_x, map_y, map_w, map_h)

        # draw pixels overlay in map_rect
        if pixels is not None:
            batch = pyglet.graphics.Batch()
            for i in range(pixels.count):
                if not pixels.alive[i]:
                    continue
                x = float(pixels.positions[i, 0])
                y = float(pixels.positions[i, 1])
                sx = map_x + (x - self.offset_x) * self.scale
                sy = map_y + (y - self.offset_y) * self.scale
                if sx < map_x or sx > map_x + map_w or sy < map_y or sy > map_y + map_h:
                    continue
                e = float(pixels.energies[i])
                r = max(1.5, 2.5 * self.scale)
                color = (0, 255, 160) if e > 0.5 else (255, 153, 0)
                shapes.Circle(sx, sy, r, color=color, batch=batch)
            batch.draw()

        # draw translucent panels (top, left, bottom)
        self._draw_panels()

        wx, wy, ww, wh = self._world_rect
        # overlay text for overlay selection and time
        overlay_txt = "Overlay: Biomes"
        time_txt = f"t={self.sim.time:.1f}"
        pyglet.text.Label(
            overlay_txt,
            x=wx + ww - 200,
            y=wy + wh - 22,
            font_size=11,
            color=(230, 230, 235, 255),
        ).draw()
        pyglet.text.Label(
            time_txt,
            x=wx + ww - 80,
            y=wy + wh - 22,
            font_size=11,
            color=(230, 230, 235, 255),
        ).draw()

        # right sidebar: global state + selected pixel + evolution log
        sx, sy, sw, sh = self._pixel_rect
        header_color = (230, 230, 235, 255)
        text_color = (200, 220, 230, 255)

        # Global State
        y = sy + sh - 20
        pyglet.text.Label("Global State", x=sx + 10, y=y, font_size=12, bold=True, color=header_color).draw()
        y -= 18
        alive = self._last_alive if self._last_alive is not None else 0
        pyglet.text.Label(f"Population: {alive}", x=sx + 10, y=y, font_size=10, color=text_color).draw()
        y -= 16
        pyglet.text.Label(
            f"O₂: {self.sim.world.global_o2:.3f}", x=sx + 10, y=y, font_size=10, color=text_color, 
        ).draw()
        y -= 16
        pyglet.text.Label(
            f"CO₂: {self.sim.world.global_co2:.5f}",
            x=sx + 10,
            y=y,
            font_size=10,
            color=text_color,
        ).draw()
        y -= 16
        pyglet.text.Label(
            f"Average energy: {self._avg_energy:.2f}",
            x=sx + 10,
            y=y,
            font_size=10,
            color=text_color,
        ).draw()
        y -= 16
        pyglet.text.Label(
            f"Average stress: {self._avg_stress:.3f}",
            x=sx + 10,
            y=y,
            font_size=10,
            color=text_color,
        ).draw()

        # Selected Pixel
        y -= 24
        pyglet.text.Label("Selected Pixel", x=sx + 10, y=y, font_size=12, bold=True, color=header_color).draw()
        y -= 18
        if self.selected_pixel is not None and 0 <= self.selected_pixel < pixels.count:
            idx = self.selected_pixel
            try:
                from pixel.identity import describe_identity
                import pixel.metabolism as metab

                id_info = describe_identity(pixels, world, idx)
                # identity line
                ident = id_info.get("Identity", "")
                if ident:
                    pyglet.text.Label(ident, x=sx + 10, y=y, font_size=10, color=text_color).draw()
                    y -= 16
                # lineage
                if "Lineage age" in id_info:
                    pyglet.text.Label(
                        f"Age: {id_info['Lineage age']}", x=sx + 10, y=y, font_size=10, color=text_color
                    ).draw()
                    y -= 16

                # internal resources (no minerals)
                stocks = getattr(pixels, "internal_resources", None)
                if stocks is not None:
                    s = stocks[idx]
                    energy = float(s[metab.IDX_ENERGY])
                    organics = float(s[metab.IDX_ORGANICS])
                    membrane = float(s[metab.IDX_MEMBRANE])
                    pyglet.text.Label(
                        f"Energy: {energy:.2f}",
                        x=sx + 10,
                        y=y,
                        font_size=10,
                        color=text_color,
                    ).draw()
                    y -= 16
                    pyglet.text.Label(
                        f"Organics: {organics:.2f}",
                        x=sx + 10,
                        y=y,
                        font_size=10,
                        color=text_color,
                    ).draw()
                    y -= 16
                    pyglet.text.Label(
                        f"Membrane: {membrane:.2f}",
                        x=sx + 10,
                        y=y,
                        font_size=10,
                        color=text_color,
                    ).draw()
                    y -= 16

                # stress from id_info
                ms = id_info.get("metabolic_stress")
                if ms is not None:
                    pyglet.text.Label(f"Stress: {ms}", x=sx + 10, y=y, font_size=10, color=text_color).draw()
                    y -= 16
            except Exception:
                pass

        # Evolution Log
        y = sy + 24
        pyglet.text.Label("Evolution Log", x=sx + 10, y=y, font_size=12, bold=True, color=header_color).draw()
        y -= 18
        for entry in list(self._evo_log):
            pyglet.text.Label(entry, x=sx + 10, y=y, font_size=10, color=text_color).draw()
            y -= 14

        # bottom bar metrics + buttons
        self._draw_bottom_metrics()
        self._draw_buttons()

    # -------------------------------------------------
    # CAMERA / MAP HELPERS
    # -------------------------------------------------

    def _clamp_camera(self):
        """Clamp scale and offsets so the world stays within the map viewport."""
        world_w, world_h = self.sim.world.size
        _, _, _, map_rect = compute_main_layout(self.width, self.height)
        _, _, map_w, map_h = map_rect

        if world_w <= 0 or world_h <= 0 or map_w <= 0 or map_h <= 0:
            return

        # minimum scale so whole world fits into map_rect
        min_scale = min(map_w / world_w, map_h / world_h)
        if self.scale < min_scale:
            self.scale = min_scale

        view_w = min(world_w, max(1.0, map_w / self.scale))
        view_h = min(world_h, max(1.0, map_h / self.scale))

        max_off_x = max(0.0, world_w - view_w)
        max_off_y = max(0.0, world_h - view_h)
        self.offset_x = max(0.0, min(self.offset_x, max_off_x))
        self.offset_y = max(0.0, min(self.offset_y, max_off_y))

    def _draw_biome_layer(self, world_w, world_h, map_x, map_y, map_w, map_h):
        """Draw the biome texture using a simple scale/offset transform.

        This mirrors the older Arcade behaviour: the whole world texture is
        scaled by `scale` and translated by `offset_x/offset_y`, then drawn
        under the map_rect area. This is less strict than a true cropped
        viewport, but makes zoom/pan behaviour intuitive and robust.
        """
        tex = self._biome_texture
        if tex is None:
            return

        tex_w, tex_h = tex.width, tex.height
        draw_w = tex_w * self.scale
        draw_h = tex_h * self.scale

        # offset_x/offset_y are world coordinates; convert to pixels
        # and anchor the texture so that (0,0) of world appears at
        # (map_x, map_y) when offset is zero.
        origin_x = map_x - self.offset_x * self.scale
        origin_y = map_y - self.offset_y * self.scale

        tex.blit(origin_x, origin_y, width=draw_w, height=draw_h)

    def _draw_panels(self):
        """Draw translucent panels for world info, pixel info, and bottom controls."""
        panels = [self._world_rect, self._pixel_rect, self._bottom_rect]
        batch = pyglet.graphics.Batch()
        fill = (40, 40, 45)
        border_color = (180, 190, 210)
        for rx, ry, rw, rh in panels:
            shapes.Rectangle(rx, ry, rw, rh, color=fill, batch=batch)
            shapes.BorderedRectangle(rx, ry, rw, rh, border=1, color=fill, border_color=border_color, batch=batch)
        batch.draw()

    def _draw_buttons(self):
        """Draw bottom-bar buttons."""
        wx, wy, ww, wh = self._world_rect
        # layout: play, reset, speed in the top bar
        self.btn_play.rect = (wx + 20, wy + 12, 90, 28)
        self.btn_reset.rect = (wx + 120, wy + 12, 90, 28)
        self.btn_speed.rect = (wx + 220, wy + 12, 110, 28)

        batch = pyglet.graphics.Batch()
        for btn in (self.btn_play, self.btn_reset, self.btn_speed):
            x, y, w, h = btn.rect
            shapes.Rectangle(x, y, w, h, color=(90, 90, 95), batch=batch)
        batch.draw()

        for btn in (self.btn_play, self.btn_reset, self.btn_speed):
            x, y, w, h = btn.rect
            pyglet.text.Label(
                btn.label,
                x=x + 10,
                y=y + 8,
                font_size=11,
                color=(255, 255, 255, 255),
            )

    def _draw_bottom_metrics(self):
        """Draw simple sparkline-style graphs for population, energy, stress."""
        bx, by, bw, bh = self._bottom_rect
        # three equal sub-panels
        panel_w = bw / 3.0
        panel_h = bh
        histories = [
            ("Population", self._pop_history),
            ("Avg energy", self._energy_history),
            ("Avg stress", self._stress_history),
        ]

        for idx, (label, hist) in enumerate(histories):
            px = bx + idx * panel_w
            py = by
            # background
            shapes.Rectangle(px, py, panel_w, panel_h, color=(30, 30, 35)).draw()

            # label
            pyglet.text.Label(
                label,
                x=px + 8,
                y=py + panel_h - 18,
                font_size=10,
                color=(210, 210, 220, 255),
            )

            # sparkline
            if len(hist) >= 2:
                vals = np.array(hist, dtype=float)
                vmin = float(vals.min())
                vmax = float(vals.max())
                if vmax - vmin < 1e-6:
                    vmax = vmin + 1.0
                # inset for plot area
                gx = px + 8
                gy = py + 8
                gw = panel_w - 16
                gh = panel_h - 28
                n = len(vals)
                step_x = gw / max(1, n - 1)
                pts = []
                for i, v in enumerate(vals):
                    x = gx + i * step_x
                    y = gy + (v - vmin) / (vmax - vmin) * gh
                    pts.append((x, y))
                # draw line segments
                for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
                    shapes.Line(x0, y0, x1, y1, width=1, color=(240, 220, 120)).draw()

    # -------------------------------------------------
    # INPUT
    # -------------------------------------------------

    def on_mouse_press(self, x, y, button, modifiers):
        if button != pyglet.window.mouse.LEFT:
            return

        # bottom buttons
        if self.btn_play.contains(x, y):
            self.sim.paused = not self.sim.paused
            self.btn_play.label = "Play" if self.sim.paused else "Pause"
            return
        if self.btn_reset.contains(x, y):
            # respawn initial pixels
            self.sim.pixels.count = 0
            self.sim.pixels.spawn_random(self.sim.world, self.sim.resource_grid, n=self._initial_pixels)
            return
        if self.btn_speed.contains(x, y):
            cur = self.sim.speed
            if cur not in self._speed_cycle:
                new = 1.0
            else:
                new = self._speed_cycle[(self._speed_cycle.index(cur) + 1) % len(self._speed_cycle)]
            self.sim.speed = new
            self.btn_speed.label = f"Speed {new:.1f}x"
            return

        # click in map area: start drag + selection
        if rect_contains(self._map_rect, x, y):
            self.dragging = True
            self.drag_start = (x, y)
            self.drag_start_offset = (self.offset_x, self.offset_y)

            mx, my, mw, mh = self._map_rect
            local_x = x - mx
            local_y = y - my
            wx = self.offset_x + local_x / max(1e-6, self.scale)
            wy = self.offset_y + local_y / max(1e-6, self.scale)

            best = None
            bestd = 3.0
            for i in range(self.sim.pixels.count):
                if not self.sim.pixels.alive[i]:
                    continue
                dx = float(self.sim.pixels.positions[i, 0]) - wx
                dy = float(self.sim.pixels.positions[i, 1]) - wy
                d = (dx * dx + dy * dy) ** 0.5
                if d < bestd:
                    bestd = d
                    best = i
            self.selected_pixel = best

    def on_mouse_release(self, x, y, button, modifiers):
        if button == pyglet.window.mouse.LEFT:
            self.dragging = False

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if not (self.dragging and (buttons & pyglet.window.mouse.LEFT)):
            return
        if not rect_contains(self._map_rect, x, y):
            return
        # pan: convert screen delta to world delta
        self.offset_x = self.drag_start_offset[0] - dx / max(1e-6, self.scale)
        self.offset_y = self.drag_start_offset[1] - dy / max(1e-6, self.scale)

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        # zoom only over the map area
        if not rect_contains(self._map_rect, x, y):
            return
        # zoom around mouse position
        zoom_step = 1.1
        factor = zoom_step ** scroll_y
        old_scale = self.scale
        new_scale = max(0.1, min(8.0, old_scale * factor))
        if abs(new_scale - old_scale) < 1e-6:
            return
        mx, my, mw, mh = self._map_rect
        local_x = x - mx
        local_y = y - my
        wx = self.offset_x + local_x / max(1e-6, old_scale)
        wy = self.offset_y + local_y / max(1e-6, old_scale)
        self.scale = new_scale
        self.offset_x = wx - local_x / max(1e-6, self.scale)
        self.offset_y = wy - local_y / max(1e-6, self.scale)

    def on_key_press(self, symbol, modifiers):
        if symbol == pyglet.window.key.SPACE:
            self.sim.paused = not self.sim.paused
            self.btn_play.label = "Play" if self.sim.paused else "Pause"
        elif symbol == pyglet.window.key.PLUS or symbol == pyglet.window.key.EQUAL:
            self.sim.speed = min(8.0, self.sim.speed * 2.0)
            self.btn_speed.label = f"Speed {self.sim.speed:.1f}x"
        elif symbol == pyglet.window.key.MINUS:
            self.sim.speed = max(0.25, self.sim.speed / 2.0)
            self.btn_speed.label = f"Speed {self.sim.speed:.1f}x"


def run_pyglet_app(sim: Simulation):
    """Entry point used by main.py when --ui pyglet."""
    window = WorldWindow(sim)
    pyglet.app.run()

