# -------------------------------------------------
# src/pixel/identity.py
"""
Semantic, emergent naming for evolving units.

Names are compressed descriptions of:
  - base ontological status (FluxUnit / FunctionalLineage / Species)
  - dominant metabolism
  - energetic strategy
  - structural / motility state

Name format (parts may be omitted if not yet emerse):

    [BASE] - [METABOLISM] - [ENERGY] - [STRUCTURE]
"""
from typing import Dict, Tuple

import numpy as np


def _compute_metabolic_signals(manager, idx: int) -> Tuple[float, float, float]:
    """Return (metabolic_stress, energy_deficit_signal, homeostasis_error)."""
    e = float(manager.energies[idx])
    avg = float(getattr(manager, "_energy_avg", np.array([e]))[idx])
    var = float(getattr(manager, "_energy_var", np.array([0.0]))[idx])
    energy_deficit_signal = max(0.0, 0.5 - e)
    homeostasis_error = var
    metabolic_stress = energy_deficit_signal + homeostasis_error
    return metabolic_stress, energy_deficit_signal, homeostasis_error


def _base_tag(manager, idx: int) -> str:
    """Ontological base: FluxUnit / FunctionalLineage / Species."""
    if not hasattr(manager, "birth_time"):
        return "FluxUnit"
    age = float(manager.time) - float(manager.birth_time[idx])
    metabolic_stress, _, _ = _compute_metabolic_signals(manager, idx)
    if age < 200.0:
        return "FluxUnit"
    if metabolic_stress < 0.05:
        return "FunctionalLineage"
    return "Species"


def _metabolism_tag(env_inputs: Dict[str, float]) -> Tuple[str, str]:
    """Derive metabolism tag + human-readable descriptor from dominant environmental channel."""
    if not env_inputs:
        return "", ""

    light = float(env_inputs.get("LIGHT", 0.0))
    organics = float(env_inputs.get("ORGANIC_SOUP", 0.0))
    redox = float(env_inputs.get("H2S", 0.0)) + float(env_inputs.get("FE2", 0.0))

    vals = np.array([light, organics, redox], dtype=float)
    labels = ["Phototrophic", "Heterotrophic", "Chemotrophic"]
    trait_desc = [
        "Photosynthetic conversion",
        "Organic-matter energy conversion",
        "Redox gradient conversion",
    ]

    total = float(vals.sum())
    if total <= 1e-6:
        return "", ""

    order = np.argsort(vals)[::-1]
    top, second = order[0], order[1]
    v_top, v_second = vals[top], vals[second]

    # if several channels comparable, consider mixotroph
    if v_second > 0.5 * v_top and v_second > 0.1:
        return "Mixotrophic", "Multiple concurrent energy pathways"

    return labels[top], trait_desc[top]


def _energy_strategy_tag(manager, idx: int) -> str:
    """Efficient / Volatile / Frugal / Accumulator / Balanced."""
    e = float(manager.energies[idx])
    avg = float(getattr(manager, "_energy_avg", np.array([e]))[idx])
    var = float(getattr(manager, "_energy_var", np.array([0.0]))[idx])

    if var < 0.005 and avg > 0.7:
        return "Efficient"
    if avg < 0.3:
        return "Frugal"
    if var > 0.05:
        return "Volatile"
    if avg > 0.85:
        return "Accumulator"
    return ""


def _structure_tag(metabolic_stress: float, energy: float) -> str:
    """Very primitive structural / motility tag derived from dynamics."""
    if energy >= 0.4 and metabolic_stress < 0.02:
        return "Sessile"
    if energy >= 0.4 and metabolic_stress >= 0.02:
        return "Motile"
    return ""


def describe_identity(manager, world, idx: int) -> Dict[str, str]:
    """
    Build a semantic identity description for a given pixel index.

    Returns a dict with keys such as:
      - Identity
      - Lineage age
      - Dominant metabolism / trait
      - Emergent structure
      - metabolic_stress, homeostasis_error, energy_deficit_signal
    """
    if idx < 0 or idx >= manager.count or not manager.alive[idx]:
        return {}

    # base ontological tag
    base = _base_tag(manager, idx)

    # environment around the pixel (for metabolism inference)
    try:
        x = int(round(float(manager.positions[idx, 0])))
        y = int(round(float(manager.positions[idx, 1])))
        get_env = getattr(world, "get_environment_inputs", None)
        env_inputs = get_env(x, y, float(manager.time)) if callable(get_env) else {}
    except Exception:
        env_inputs = {}

    metab_tag, metab_desc = _metabolism_tag(env_inputs)

    # energetic strategy and stress
    metabolic_stress, energy_deficit_signal, homeostasis_error = _compute_metabolic_signals(manager, idx)
    energy_tag = _energy_strategy_tag(manager, idx)

    # structural tag
    e = float(manager.energies[idx])
    struct_tag = _structure_tag(metabolic_stress, e)

    parts = [base]
    if metab_tag:
        parts.append(metab_tag)
    if energy_tag:
        parts.append(energy_tag)
    if struct_tag:
        parts.append(struct_tag)
    identity = " - ".join(parts)

    # lineage age in ticks
    if hasattr(manager, "birth_time"):
        age_ticks = max(0.0, float(manager.time) - float(manager.birth_time[idx]))
    else:
        age_ticks = 0.0

    info: Dict[str, str] = {}
    info["Identity"] = identity
    info["Lineage age"] = f"{age_ticks:.0f} ticks"

    if metab_tag:
        info["Dominant metabolism"] = metab_tag
    if metab_desc:
        info["Dominant trait"] = metab_desc
    if struct_tag:
        info["Emergent structure"] = struct_tag

    # expose internal signals for debug / deep reading
    info["metabolic_stress"] = f"{metabolic_stress:.3f}"
    info["homeostasis_error"] = f"{homeostasis_error:.3f}"
    info["energy_deficit_signal"] = f"{energy_deficit_signal:.3f}"

    return info

