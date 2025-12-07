"""
Right-side panel mixin for the DearPyGui app.

Responsabilità:
  - stato globale (popolazione, gas, energia media, stress)
  - dettagli del pixel selezionato
  - log evolutivo + riepilogo in basso
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import dearpygui.dearpygui as dpg

from .dpg_constants import WINDOW_H, WORLD_W, GUI_W, TOP_H

if TYPE_CHECKING:  # pragma: no cover
    from .dpg_app import DPGApp


class SidebarMixin:
    last_alive: int
    max_alive: int
    in_bottleneck: bool
    avg_energy: float
    avg_stress: float
    trait_diversity: int
    avg_traits_per_cell: float
    pop_history: "deque"
    evo_log: "deque"

    # ------------------------------ build ----------------------------

    def _build_sidebar(self: "DPGApp") -> None:
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
            dpg.add_text("POPULATION / TRAITS")

            with dpg.plot(label="Population / Traits", height=180, width=GUI_W - 40, tag="plot_population"):
                dpg.add_plot_legend()
                dpg.add_plot_axis(dpg.mvXAxis, tag="axis_x")
                with dpg.plot_axis(dpg.mvYAxis, tag="axis_y"):
                    dpg.add_line_series([], [], label="Population", tag="series_population")
                    dpg.add_line_series([], [], label="Avg traits per cell", tag="series_traits")

            dpg.add_spacer(height=8)
            dpg.add_separator()
            dpg.add_text("EVOLUTION SUMMARY + LOG")
            dpg.add_input_text(
                multiline=True,
                readonly=True,
                height=140,
                width=GUI_W - 40,
                tag="txt_event_log",
            )

    # ---------------------------- stats ------------------------------

    def _update_stats(self: "DPGApp") -> None:
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

        # trait diversity / media tratti per cellula (solo vive)
        self.trait_diversity = 0
        self.avg_traits_per_cell = 0.0
        traits_list = getattr(self.pm, "traits", None)
        if traits_list is not None and alive > 0:
            sigs = set()
            total_traits = 0
            for i in range(self.pm.count):
                if not self.pm.alive[i]:
                    continue
                if i >= len(traits_list):
                    continue
                try:
                    tset = set(traits_list[i])
                except Exception:
                    tset = set()
                sigs.add(tuple(sorted(tset)))
                total_traits += len(tset)
            self.trait_diversity = len(sigs)
            if alive > 0:
                self.avg_traits_per_cell = total_traits / float(alive)

        # evolution log basato sui cambi di popolazione,
        # ma con un concetto di "bottleneck" meno rumoroso:
        # - tiene traccia del massimo storico
        # - segnala bottleneck solo quando si scende sotto una
        #   frazione significativa del massimo e solo una volta per episodio.
        if getattr(self, "last_alive", None) is None:
            self.last_alive = alive
            self.max_alive = alive
            self.in_bottleneck = False
        else:
            # aggiorna massimo storico
            self.max_alive = max(getattr(self, "max_alive", 0), alive)

            if alive == 0 and self.last_alive > 0:
                self.evo_log.appendleft("Population extinct")
                self.in_bottleneck = False
            elif alive > self.last_alive:
                delta = alive - self.last_alive
                if delta > 0:
                    self.evo_log.appendleft(f"{delta} new cells")
                # uscita da un eventuale bottleneck
                if getattr(self, "max_alive", 0) > 0 and alive > 0.3 * self.max_alive:
                    self.in_bottleneck = False
            elif alive < self.last_alive:
                # calcola frazione rispetto al massimo storico
                if getattr(self, "max_alive", 0) > 0:
                    frac = alive / float(self.max_alive)
                else:
                    frac = 1.0
                # considera "bottleneck" solo se la popolazione Þ scesa
                # sotto il 20% del massimo e non Þ giÖ in bottleneck
                if 0 < alive < self.last_alive and frac < 0.2 and not getattr(self, "in_bottleneck", False):
                    self.evo_log.appendleft("Population bottleneck")
                    self.in_bottleneck = True
            self.last_alive = alive

        # "Notizie" evolutive rare (prima divisione, primi tratti, ecc.)

        # baseline / flag iniziali per le notizie
        if not hasattr(self, "initial_population"):
            self.initial_population = alive
        if not hasattr(self, "news_first_division"):
            self.news_first_division = False
        if not hasattr(self, "news_first_photosynthesis"):
            self.news_first_photosynthesis = False
        if not hasattr(self, "news_first_motility"):
            self.news_first_motility = False
        if not hasattr(self, "news_first_o2_rise"):
            self.news_first_o2_rise = False
        if not hasattr(self, "news_first_organic_soil"):
            self.news_first_organic_soil = False
        if not hasattr(self, "o2_baseline"):
            self.o2_baseline = float(self.world.global_o2)

        # 1) Prima divisione riuscita: popolazione supera il valore iniziale
        if (
            not self.news_first_division
            and getattr(self, "initial_population", 0) > 0
            and alive > self.initial_population
        ):
            self.evo_log.appendleft(f"{self._format_sim_time()} | First division observed")
            self.news_first_division = True

        # 2) Primo tratto fotosintetico
        if not self.news_first_photosynthesis and traits_list is not None and alive > 0:
            try:
                found_photo = False
                for i in range(self.pm.count):
                    if not self.pm.alive[i]:
                        continue
                    try:
                        tset = set(self.pm.traits[i])
                    except Exception:
                        tset = set()
                    if "photosynthesis" in tset:
                        found_photo = True
                        break
                if found_photo:
                    self.evo_log.appendleft(f"{self._format_sim_time()} | First photosynthetic trait")
                    self.news_first_photosynthesis = True
            except Exception:
                pass

        # 3) Prima motilita attiva (cilia/flagella/fins/legs/wings)
        if not self.news_first_motility and traits_list is not None and alive > 0:
            motile_traits = ("cilia", "flagella", "fins", "legs", "wings")
            try:
                found_motile = False
                for i in range(self.pm.count):
                    if not self.pm.alive[i]:
                        continue
                    try:
                        tset = set(self.pm.traits[i])
                    except Exception:
                        tset = set()
                    if any(t in tset for t in motile_traits):
                        found_motile = True
                        break
                if found_motile:
                    self.evo_log.appendleft(f"{self._format_sim_time()} | First active motility trait")
                    self.news_first_motility = True
            except Exception:
                pass

        # 4) Primo aumento significativo di O2 globale
        if (
            not self.news_first_o2_rise
            and float(self.world.global_o2) > self.o2_baseline + 0.005
        ):
            self.evo_log.appendleft(f"{self._format_sim_time()} | Atmospheric O2 rise detected")
            self.news_first_o2_rise = True

        # 5) Primo accumulo rilevante di suolo organico
        org_layer = getattr(self.world, "organic_layer", None)
        if org_layer is not None and not self.news_first_organic_soil:
            try:
                mean_org = float(np.mean(org_layer))
                if mean_org > 0.02:
                    self.evo_log.appendleft(f"{self._format_sim_time()} | First organic soil formation")
                    self.news_first_organic_soil = True
            except Exception:
                pass

    # --------------------------- sidebar UI --------------------------

    def _update_sidebar(self: "DPGApp") -> None:
        # time + global
        alive = self.last_alive if self.last_alive is not None else 0
        dpg.set_value("txt_time", self._format_sim_time())
        dpg.set_value("txt_population", f"Population: {alive}")
        dpg.set_value("txt_o2", f"O₂: {self.world.global_o2:.3f}")
        dpg.set_value("txt_co2", f"CO₂: {self.world.global_co2:.5f}")
        dpg.set_value("txt_energy_mean", f"Average energy: {self.avg_energy:.2f}")
        dpg.set_value("txt_stress_mean", f"Average stress: {self.avg_stress:.3f}")

        # plot popolazione
        if len(self.pop_history) >= 2:
            xs = list(range(len(self.pop_history)))
            ys = list(self.pop_history)
            dpg.set_value("series_population", [xs, ys])
            # linea secondaria: tratti medi per cellula (normalizzati per renderli visibili)
            trait_series = []
            # per semplicità, usiamo lo stesso xs e accumuliamo la storia dei tratti
            if not hasattr(self, "_traits_history"):
                self._traits_history = []
            self._traits_history.append(self.avg_traits_per_cell)
            trait_series = list(self._traits_history[-len(xs) :])
            dpg.set_value("series_traits", [xs[: len(trait_series)], trait_series])

        # pixel selezionato
        if self.selected_pixel is not None and 0 <= self.selected_pixel < self.pm.count:
            idx = self.selected_pixel
            try:
                from pixel.identity import describe_identity
                import pixel.metabolism as metab

                id_info = {}
                try:
                    id_info = describe_identity(self.pm, self.world, idx) or {}
                except Exception as e:
                    print("[dpg] describe_identity error:", e)

                dpg.set_value("txt_identity", id_info.get("Identity", f"Pixel {idx}"))
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
                    dpg.set_value("txt_pixel_energy", f"Energy: {float(self.pm.energies[idx]):.2f}")
                    dpg.set_value("txt_pixel_organics", "")
                    dpg.set_value("txt_pixel_membrane", "")

                ms = id_info.get("metabolic_stress")
                if ms is not None:
                    dpg.set_value("txt_pixel_stress", f"Stress: {ms}")
                else:
                    dpg.set_value("txt_pixel_stress", "")
            except Exception as e:
                print("[dpg] sidebar pixel error:", e)
                dpg.set_value("txt_identity", f"Pixel {idx}")
                dpg.set_value("txt_pixel_age", "")
                dpg.set_value("txt_pixel_energy", f"Energy: {float(self.pm.energies[idx]):.2f}")
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

        # riepilogo + log
        summary_lines = [
            f"Time: {self._format_sim_time()}",
            f"Population: {alive} (max {getattr(self, 'max_alive', alive)})",
            f"Trait clusters: {self.trait_diversity}  |  Avg traits/cell: {self.avg_traits_per_cell:.1f}",
            f"O2: {self.world.global_o2:.3f}   CO2: {self.world.global_co2:.5f}",
        ]
        summary = "\n".join(summary_lines)
        log_lines = "\n".join(list(self.evo_log))
        full_text = summary + ("\n\n" + log_lines if log_lines else "")
        dpg.set_value("txt_event_log", full_text)
