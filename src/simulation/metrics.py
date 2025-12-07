# --------------------------------------------------------
# File: src/simulation/metrics.py
#
# Lightweight metrics recorder for the Evolutive Simulator.
#
# Goal: collect just enough aggregated data to answer the
# research questions in research_questions.md, without
# overloading the main simulation loop.
# --------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import os
import csv
import uuid
import math
from datetime import datetime


@dataclass
class RunRecorder:
    """
    Collects coarse-grained metrics over the course of a run.

    It is intentionally light:
      - samples every `sample_every` Simulation.step() calls
      - stores only aggregated values, not per-cell state
      - writes a single CSV at the end of the run
    """

    out_dir: str = os.path.join("data", "metrics")
    label: str = ""
    seed: int = 0
    # unique identifier for this run (for cross-file tracking)
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    # optional extra metadata (global params, code version, etc.)
    meta: Dict[str, Any] = field(default_factory=dict)
    # sampling control: at most one row per simulated year, but callers
    # can still require a minimum step interval via sample_every.
    sample_every: int = 1

    step_count: int = 0
    last_year_sampled: int = 0  # calendar year label last written (0 = none)
    rows: List[Dict[str, Any]] = field(default_factory=list)

    def update(self, sim: "Simulation", eff_dt: float) -> None:
        """
        Sample metrics from the current simulation state.
        """
        self.step_count += 1
        # opzionale: vincolo minimo in step fra due campioni
        if self.step_count % max(1, self.sample_every) != 0:
            return

        # convenzione globale: 1.0 unità di sim.time ≃ 1 mese
        total_months = float(sim.time)
        calendar_year = int(total_months // 12) + 1
        # registriamo al massimo un campione per anno di calendario
        if calendar_year == self.last_year_sampled:
            return
        self.last_year_sampled = calendar_year

        world = sim.world
        pm = sim.pixels

        # ---------- population & energy ----------
        if pm.count > 0:
            alive_mask = pm.alive[: pm.count]
            alive = int(alive_mask.sum())
        else:
            alive_mask = None
            alive = 0

        if alive > 0 and alive_mask is not None:
            energies = pm.energies[: pm.count][alive_mask]
            avg_energy = float(energies.mean())
            var_energy = float(energies.var())
        else:
            avg_energy = 0.0
            var_energy = 0.0

        # ---------- traits / diversity ----------
        trait_diversity = 0
        avg_traits_per_cell = 0.0
        traits_list = getattr(pm, "traits", None)
        if traits_list is not None and alive > 0:
            sigs = set()
            total_traits = 0
            for i in range(pm.count):
                if not pm.alive[i]:
                    continue
                if i >= len(traits_list):
                    continue
                try:
                    tset = set(traits_list[i])
                except Exception:
                    tset = set()
                sigs.add(tuple(sorted(tset)))
                total_traits += len(tset)
            trait_diversity = len(sigs)
            if alive > 0:
                avg_traits_per_cell = total_traits / float(alive)

        # ---------- information order ----------
        mean_info_order = 0.0
        if getattr(pm, "internal_resources", None) is not None:
            try:
                import pixel.metabolism as metab  # local import to avoid hard dependency at module import

                stocks = pm.internal_resources[: pm.count]
                if alive_mask is not None:
                    stocks = stocks[alive_mask]
                if stocks.size > 0:
                    info_vals = stocks[:, metab.IDX_INFO]
                    mean_info_order = float(info_vals.mean())
            except Exception:
                mean_info_order = 0.0

        # ---------- global environment ----------
        global_o2 = float(getattr(world, "global_o2", 0.0))
        global_co2 = float(getattr(world, "global_co2", 0.0))

        row = {
            # tempo grezzo della simulazione
            "tick": int(self.step_count),
            "time": total_months,  # mesi simulati totali
            "year": calendar_year,  # anno di calendario (uguale alla GUI)
            "population": alive,
            "avg_energy": avg_energy,
            "var_energy": var_energy,
            "trait_diversity": trait_diversity,
            "avg_traits_per_cell": avg_traits_per_cell,
            "mean_info_order": mean_info_order,
            "global_o2": global_o2,
            "global_co2": global_co2,
        }
        self.rows.append(row)

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    def save(self) -> Optional[str]:
        """
        Write collected rows to a CSV file.
        Returns the path if something was written, else None.
        """
        if not self.rows:
            return None

        os.makedirs(self.out_dir, exist_ok=True)

        # basic filename: metrics_{label or 'run'}_{nrows}.csv
        base_label = self.label or "run"
        fname = f"metrics_{base_label}_{self.run_id[:8]}_{len(self.rows)}.csv"
        path = os.path.join(self.out_dir, fname)

        # embed seed/run_id into each row so the CSV is self-describing
        for row in self.rows:
            row.setdefault("seed", self.seed)
            row.setdefault("run_id", self.run_id)

        fieldnames = list(self.rows[0].keys())

        with open(path, "w", newline="", encoding="utf-8") as f:
            # metadata header as comment lines (scientific-archive friendly)
            dt_str = datetime.utcnow().isoformat(timespec="seconds") + "Z"
            f.write(f"# datetime={dt_str}\n")
            f.write(f"# run_id={self.run_id}\n")
            f.write(f"# seed={self.seed}\n")
            if self.label:
                f.write(f"# label={self.label}\n")
            for k, v in (self.meta or {}).items():
                f.write(f"# {k}={v}\n")

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in self.rows:
                writer.writerow(row)

        print(f"[metrics] Saved {len(self.rows)} samples to {path}")
        return path
