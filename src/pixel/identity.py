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
from typing import Dict, Tuple, Set

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


def _base_tag(manager, idx: int, traits: Set[str]) -> str:
    """Ontological base: FluxUnit / FunctionalLineage / Species.

    Tutte le unità iniziali, senza tratti, sono semplicemente FluxUnit.
    FunctionalLineage/Species emergono solo con età e stabilità.
    """
    if not traits:
        return "FluxUnit"
    if not hasattr(manager, "birth_time"):
        return "FluxUnit"
    age = float(manager.time) - float(manager.birth_time[idx])
    metabolic_stress, _, _ = _compute_metabolic_signals(manager, idx)
    if age < 500.0:
        return "FluxUnit"
    if metabolic_stress < 0.05:
        return "FunctionalLineage"
    return "Species"


def _metabolism_tag(traits: Set[str]) -> Tuple[str, str]:
    """Derive metabolism tag + description from active traits, not solo ambiente."""
    if not traits:
        return "", ""

    if "photosynthesis" in traits or "chloroplasts" in traits:
        return "Phototrophic", "Photosynthetic conversion"
    if "chemosynthesis" in traits:
        return "Chemotrophic", "Redox gradient conversion"
    if any(t in traits for t in ("herbivore", "carnivore", "omnivore", "detritivore", "filter_feeding", "parasitic")):
        return "Heterotrophic", "Organic-matter energy conversion"
    return "", ""


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


def _structure_tag(traits: Set[str]) -> str:
    """Structural / motility tag derived primarily from traits."""
    if not traits:
        return ""
    if any(t in traits for t in ("roots", "stationary")):
        return "Sessile"
    if any(t in traits for t in ("cilia", "flagella", "fins", "legs", "wings", "tube_feet", "muscle")):
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

    # active traits decoded elsewhere (PixelManager.traits)
    traits = set()
    if hasattr(manager, "traits") and idx < len(manager.traits):
        try:
            traits = set(manager.traits[idx])
        except Exception:
            traits = set()

    # base ontological tag
    base = _base_tag(manager, idx, traits)

    # metabolism / structure derived dai tratti, non solo dall'ambiente
    metab_tag, metab_desc = _metabolism_tag(traits)

    # energetic strategy e stress (solo se linea già un po' stabilizzata)
    metabolic_stress, energy_deficit_signal, homeostasis_error = _compute_metabolic_signals(manager, idx)
    energy_tag = ""
    if traits:
        energy_tag = _energy_strategy_tag(manager, idx)

    struct_tag = _structure_tag(traits)

    parts = [base]
    if metab_tag:
        parts.append(metab_tag)
    if energy_tag:
        parts.append(energy_tag)
    if struct_tag:
        parts.append(struct_tag)
    identity = " - ".join([p for p in parts if p])

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
