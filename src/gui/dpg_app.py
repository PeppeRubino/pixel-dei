"""
DearPyGui-based GUI for the Evolutive Simulator.

Single-window layout:
  - Top bar: play/pause, step, speed slider
  - Left: world map (dynamic texture) + pixel overlay
  - Right: global state, selected pixel info, population plot, evolution log

Pyglet is not used here for windowing; we only use the existing
Simulation/World/PixelManager logic and render via DearPyGui.
"""
from typing import Deque, List, Tuple, Optional
from collections import deque
import time

import numpy as np

from simulation.core import Simulation

try:
    import dearpygui.dearpygui as dpg  # type: ignore
except ImportError as e:  # pragma: no cover - runtime guard
    raise RuntimeError(
        "DearPyGui is not installed. Please run `pip install dearpygui` inside your venv."
    ) from e


WINDOW_W, WINDOW_H = 1200, 880
TOP_H = 50
WORLD_W = 820
GUI_W = WINDOW_W - WORLD_W


class DPGApp:
    def __init__(self, sim: Simulation):
        self.sim = sim
        self.world = sim.world
        self.pm = sim.pixels
        self.texture_w = self.world.size[0]
        self.texture_h = self.world.size[1]

        # camera / view window in world coordinates
        w, h = self.world.size
        self.view_x0 = 0.0
        self.view_y0 = 0.0
        self.view_x1 = float(max(1, w - 1))
        self.view_y1 = float(max(1, h - 1))
        self._is_panning = False
        self._last_pan_pos: Optional[Tuple[float, float]] = None

        # histories for plots
        self.pop_history: Deque[float] = deque(maxlen=200)
        self.energy_history: Deque[float] = deque(maxlen=200)
        self.stress_history: Deque[float] = deque(maxlen=200)
        self.evo_log: Deque[str] = deque(maxlen=6)

        self.last_alive: Optional[int] = None
        self.avg_energy: float = 0.0
        self.avg_stress: float = 0.0

        self.selected_pixel: Optional[int] = None

        self._last_time = time.time()

    # -------------------------------------------------
    # TEXTURE HELPERS
    # -------------------------------------------------

    def _world_color_map_rgba(self) -> List[float]:
        """Return current world biome map as flattened RGBA floats in [0,1]."""
        img = self.world.color_map()  # (h, w, 3) uint8
        h, w, _ = img.shape
        self.texture_w, self.texture_h = w, h
        rgb = img.astype("float32") / 255.0
        alpha = np.ones((h, w, 1), dtype="float32")
        rgba = np.concatenate([rgb, alpha], axis=2)
        return rgba.flatten().tolist()

    # -------------------------------------------------
    # UI BUILD
    # -------------------------------------------------

    def build(self):
        dpg.create_context()
        dpg.create_viewport(title="Evolutive Simulator", width=WINDOW_W, height=WINDOW_H)

        # texture registry
        with dpg.texture_registry(show=False):
            dpg.add_dynamic_texture(
                self.texture_w,
                self.texture_h,
                self._world_color_map_rgba(),
                tag="world_texture",
            )

        # top bar
        with dpg.window(
            tag="top_bar",
            pos=(0, 0),
            width=WINDOW_W,
            height=TOP_H,
            no_move=True,
            no_resize=True,
            no_title_bar=True,
        ):
            dpg.add_button(label="▶ Play", tag="btn_play", callback=self._on_play)
            dpg.add_same_line()
            dpg.add_button(label="⏸ Pause", tag="btn_pause", callback=self._on_pause)
            dpg.add_same_line()
            dpg.add_button(label="⏭ Step", callback=self._on_step)
            dpg.add_same_line()
            dpg.add_slider_float(
                label="Speed",
                min_value=0.1,
                max_value=8.0,
                default_value=self.sim.speed,
                width=200,
                callback=self._on_speed_change,
            )
            dpg.add_same_line()
            dpg.add_text("", tag="txt_time")

        # world area (drawlist so we can overlay pixels)
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

        # right panel
        with dpg.window(
            tag="right_panel",
            pos=(WORLD_W, TOP_H),
            width=GUI_W,
            height=WINDOW_H - TOP_H,
            no_move=True,
            no_resize=True,
            no_title_bar=True,
        ):
            dpg.add_text("GLOBAL STATE")
            dpg.add_separator()
            dpg.add_text("", tag="txt_population")
            dpg.add_text("", tag="txt_o2")
            dpg.add_text("", tag="txt_co2")
            dpg.add_text("", tag="txt_energy_mean")
            dpg.add_text("", tag="txt_stress_mean")

            dpg.add_spacer(height=8)
            dpg.add_separator()
            dpg.add_text("SELECTED PIXEL")
            dpg.add_separator()
            dpg.add_text("", tag="txt_identity")
            dpg.add_text("", tag="txt_pixel_age")
            dpg.add_text("", tag="txt_pixel_energy")
            dpg.add_text("", tag="txt_pixel_organics")
            dpg.add_text("", tag="txt_pixel_membrane")
            dpg.add_text("", tag="txt_pixel_stress")

            dpg.add_spacer(height=8)
            dpg.add_separator()
            dpg.add_text("POPULATION TREND")

            with dpg.plot(label="Population", height=180, width=GUI_W - 40, tag="plot_population"):
                dpg.add_plot_legend()
                dpg.add_plot_axis(dpg.mvXAxis, tag="axis_x")
                with dpg.plot_axis(dpg.mvYAxis, tag="axis_y"):
                    dpg.add_line_series([], [], label="Population", tag="series_population")

            dpg.add_spacer(height=8)
            dpg.add_separator()
            dpg.add_text("EVENT LOG")
            dpg.add_input_text(
                multiline=True,
                readonly=True,
                height=140,
                width=GUI_W - 40,
                tag="txt_event_log",
            )

        # mouse click handler for selecting pixels on the world
        with dpg.handler_registry():
            dpg.add_mouse_click_handler(callback=self._on_mouse_click)
            # optional zoom / pan handlers (if DearPyGui version supports them)
            try:
                dpg.add_mouse_wheel_handler(callback=self._on_mouse_wheel)
            except Exception:
                pass
            try:
                dpg.add_mouse_drag_handler(button=0, callback=self._on_mouse_drag)
            except Exception:
                pass

        dpg.setup_dearpygui()
        dpg.show_viewport()

    # -------------------------------------------------
    # CALLBACKS
    # -------------------------------------------------

    def _on_play(self, sender, app_data):
        self.sim.paused = False

    def _on_pause(self, sender, app_data):
        self.sim.paused = True

    def _on_step(self, sender, app_data):
        # single step when paused
        if self.sim.paused:
            self.sim.step(self.sim.base_dt)

    def _on_speed_change(self, sender, app_data):
        try:
            self.sim.speed = float(app_data)
        except Exception:
            pass

    def _on_mouse_click(self, sender, app_data):
        # DearPyGui versions differ: app_data can be
        # - int (button)
        # - list/tuple [button, x, y]
        # - dict {"button": ..., "pos": (..., ...)}
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
        # only react to left button
        if button != 0:
            return
        mx, my = dpg.get_mouse_pos()
        # allow a generous vertical range; safety if coordinate origin differs
        if not (0 <= mx <= WORLD_W):
            return

        world_w, world_h = self.world.size
        local_x = mx
        local_y = my - TOP_H
        # map from screen -> current view window
        vx0, vx1 = self.view_x0, self.view_x1
        vy0, vy1 = self.view_y0, self.view_y1
        vw = max(1e-6, vx1 - vx0)
        vh = max(1e-6, vy1 - vy0)
        wx = vx0 + (local_x / max(1.0, WORLD_W)) * vw
        # y is flipped (screen 0 at top, world 0 at top)
        wy = vy0 + (1.0 - (local_y / max(1.0, WINDOW_H - TOP_H))) * vh

        # find nearest pixel
        best = None
        bestd = 6.0
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
        if best is not None:
            try:
                print(f"[dpg] Selected pixel index={best}")
            except Exception:
                pass

    def _on_mouse_wheel(self, sender, app_data):
        # zoom around center of view; app_data is typically the vertical scroll amount
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
        # clamp zoom levels
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
        # drag to pan the view when the cursor is over the world area
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

        # convert screen delta to world delta based on current view size
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

    def _on_frame(self):
        now = time.time()
        dt = now - self._last_time
        self._last_time = now

        # advance simulation
        self.sim.step(dt)

        # update world texture only if biomes changed
        if getattr(self.world, "_biome_dirty", False):
            dpg.set_value("world_texture", self._world_color_map_rgba())
            setattr(self.world, "_biome_dirty", False)

        # update stats
        self._update_stats()
        self._update_world_drawlist()
        self._update_sidebar()

    # -------------------------------------------------
    # PER-FRAME UPDATES
    # -------------------------------------------------

    def _update_stats(self):
        if self.pm.count > 0:
            alive_mask = self.pm.alive[: self.pm.count]
            alive = int(np.sum(alive_mask))
        else:
            alive_mask = None
            alive = 0

        if alive > 0 and alive_mask is not None:
            energies = self.pm.energies[: self.pm.count][alive_mask]
            avg_e = float(np.mean(energies))
            var_e = float(np.var(energies))
        else:
            avg_e = 0.0
            var_e = 0.0

        energy_deficit = max(0.0, 0.5 - avg_e)
        stress = energy_deficit + var_e

        self.avg_energy = avg_e
        self.avg_stress = stress
        self.pop_history.append(alive)
        self.energy_history.append(avg_e)
        self.stress_history.append(stress)

        # evolution log
        if self.last_alive is None:
            self.last_alive = alive
        else:
            if alive == 0 and self.last_alive > 0:
                self.evo_log.appendleft("Population extinct")
            elif alive > self.last_alive:
                delta = alive - self.last_alive
                self.evo_log.appendleft(f"{delta} new cells")
            elif alive < self.last_alive:
                self.evo_log.appendleft("Population bottleneck")
            self.last_alive = alive

    def _update_world_drawlist(self):
        # clear drawlist and redraw world + pixels
        dpg.delete_item("world_drawlist", children_only=True)
        # determine which part of the texture to show based on current view
        world_w, world_h = self.world.size
        vx0, vx1 = self.view_x0, self.view_x1
        vy0, vy1 = self.view_y0, self.view_y1
        vw = max(1e-6, vx1 - vx0)
        vh = max(1e-6, vy1 - vy0)
        # uv coordinates are normalized [0,1]
        u0 = float(vx0) / max(1.0, world_w - 1)
        u1 = float(vx1) / max(1.0, world_w - 1)
        # DearPyGui textures are typically bottom-left origin; our world.y=0 at top,
        # so we flip the v coordinates.
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

        for i in range(self.pm.count):
            if not self.pm.alive[i]:
                continue
            x = float(self.pm.positions[i, 0])
            y = float(self.pm.positions[i, 1])
            # skip pixels outside current view
            if not (vx0 <= x <= vx1 and vy0 <= y <= vy1):
                continue
            sx = (x - vx0) / vw * WORLD_W
            sy = (1.0 - (y - vy0) / vh) * h_screen
            e = float(self.pm.energies[i])
            col = (0, 255, 200, 255) if e > 0.5 else (255, 120, 0, 255)
            dpg.draw_circle(center=(sx, sy), radius=3.0, color=col, fill=col, parent="world_drawlist")

    def _update_sidebar(self):
        # time + global
        dpg.set_value("txt_time", f"t={self.sim.time:.1f}")
        alive = self.last_alive if self.last_alive is not None else 0
        dpg.set_value("txt_population", f"Population: {alive}")
        dpg.set_value("txt_o2", f"O₂: {self.world.global_o2:.3f}")
        dpg.set_value("txt_co2", f"CO₂: {self.world.global_co2:.5f}")
        dpg.set_value("txt_energy_mean", f"Average energy: {self.avg_energy:.2f}")
        dpg.set_value("txt_stress_mean", f"Average stress: {self.avg_stress:.3f}")

        # plot
        if len(self.pop_history) >= 2:
            xs = list(range(len(self.pop_history)))
            ys = list(self.pop_history)
            dpg.set_value("series_population", [xs, ys])

        # selected pixel
        if self.selected_pixel is not None and 0 <= self.selected_pixel < self.pm.count:
            idx = self.selected_pixel
            try:
                from pixel.identity import describe_identity
                import pixel.metabolism as metab

                id_info = describe_identity(self.pm, self.world, idx)
                dpg.set_value("txt_identity", id_info.get("Identity", ""))
                dpg.set_value("txt_pixel_age", id_info.get("Lineage age", ""))

                stocks = getattr(self.pm, "internal_resources", None)
                if stocks is not None:
                    s = stocks[idx]
                    energy = float(s[metab.IDX_ENERGY])
                    organics = float(s[metab.IDX_ORGANICS])
                    membrane = float(s[metab.IDX_MEMBRANE])
                    dpg.set_value("txt_pixel_energy", f"Energy: {energy:.2f}")
                    dpg.set_value("txt_pixel_organics", f"Organics: {organics:.2f}")
                    dpg.set_value("txt_pixel_membrane", f"Membrane: {membrane:.2f}")
                else:
                    dpg.set_value("txt_pixel_energy", "")
                    dpg.set_value("txt_pixel_organics", "")
                    dpg.set_value("txt_pixel_membrane", "")

                ms = id_info.get("metabolic_stress")
                if ms is not None:
                    dpg.set_value("txt_pixel_stress", f"Stress: {ms}")
                else:
                    dpg.set_value("txt_pixel_stress", "")
            except Exception:
                dpg.set_value("txt_identity", "")
                dpg.set_value("txt_pixel_age", "")
                dpg.set_value("txt_pixel_energy", "")
                dpg.set_value("txt_pixel_organics", "")
                dpg.set_value("txt_pixel_membrane", "")
                dpg.set_value("txt_pixel_stress", "")
        else:
            dpg.set_value("txt_identity", "")
            dpg.set_value("txt_pixel_age", "")
            dpg.set_value("txt_pixel_energy", "")
            dpg.set_value("txt_pixel_organics", "")
            dpg.set_value("txt_pixel_membrane", "")
            dpg.set_value("txt_pixel_stress", "")

        # evolution log text
        log_lines = "\n".join(list(self.evo_log))
        dpg.set_value("txt_event_log", log_lines)


def run_dpg_app(sim: Simulation):
    app = DPGApp(sim)
    app.build()
    # manual main loop so we can run simulation each frame
    while dpg.is_dearpygui_running():
        app._on_frame()
        dpg.render_dearpygui_frame()
    dpg.destroy_context()
