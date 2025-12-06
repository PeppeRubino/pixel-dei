"""
Top bar mixin for the DearPyGui app.

Responsabilità:
  - barra di controllo in alto (play/pause/step/speed/time/save)
  - formattazione del tempo simulato
  - callback per i pulsanti
"""
from __future__ import annotations

from typing import TYPE_CHECKING
import os
import datetime as _dt

import dearpygui.dearpygui as dpg

from .dpg_constants import WINDOW_W, TOP_H

if TYPE_CHECKING:  # pragma: no cover - solo per type hints
    from .dpg_app import DPGApp


class TopBarMixin:
    """Metodi legati alla barra superiore e alla gestione del tempo."""

    sim: "Simulation"  # attribute provided by DPGApp

    # --------------------------- build ---------------------------

    def _build_top_bar(self: "DPGApp") -> None:
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
            dpg.add_same_line()
            dpg.add_button(label="Save", callback=self._on_save)

    # ------------------------- callbacks -------------------------

    def _on_play(self, sender, app_data):
        self.sim.paused = False

    def _on_pause(self, sender, app_data):
        self.sim.paused = True

    def _on_step(self, sender, app_data):
        if self.sim.paused:
            self.sim.step(self.sim.base_dt)

    def _on_speed_change(self, sender, app_data):
        try:
            self.sim.speed = float(app_data)
        except Exception:
            pass

    def _on_save(self, sender, app_data):
        """Save a snapshot di World + PixelManager in data/snapshots/."""
        try:
            ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "snapshots"))
            os.makedirs(base_dir, exist_ok=True)
            world_path = os.path.join(base_dir, f"world_{ts}.npz")
            pixels_path = os.path.join(base_dir, f"pixels_{ts}.npz")
            world = getattr(self, "world", None)
            pm = getattr(self, "pm", None)
            if hasattr(world, "save_snapshot"):
                world.save_snapshot(world_path)
            if hasattr(pm, "save"):
                pm.save(pixels_path)
            print(f"[dpg] Saved snapshot to {world_path} and {pixels_path}")
        except Exception as e:
            print("[dpg] Error while saving snapshot:", e)

    # ----------------------- time helpers ------------------------

    def _format_sim_time(self) -> str:
        """Return calendar-like time (month/year) from Simulation.time.

        Convenzione: 1.0 unità di Simulation.time ≈ 1 mese.
        """
        total_months = int(self.sim.time)
        year = total_months // 12 + 1
        month = total_months % 12 + 1
        return f"Month {month:02d} / Year {year:04d}"

