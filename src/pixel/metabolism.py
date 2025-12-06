

# -------------------------------------------------
# src/pixel/metabolism.py
"""
Metabolism module

Implements a simple but extensible scheme:
  - internal resources per cell (stocks)
  - environmental channels per biome
  - genome as linear operators env -> internal fluxes

PixelManager passes itself so we can read/write per-pixel state.
"""
from typing import Dict, Sequence
import numpy as np

# Internal resource channels
INTERNAL_RESOURCES = ["ENERGY", "ORGANICS", "MINERALS", "MEMBRANE", "INFO_ORDER"]
IDX_ENERGY = 0
IDX_ORGANICS = 1
IDX_MINERALS = 2
IDX_MEMBRANE = 3
IDX_INFO = 4


def init_internal_state(n: int) -> np.ndarray:
    """Initialize internal stocks for n pixels: shape (n, len(INTERNAL_RESOURCES))."""
    stocks = np.zeros((n, len(INTERNAL_RESOURCES)), dtype=np.float32)
    stocks[:, IDX_ENERGY] = 1.0
    stocks[:, IDX_ORGANICS] = 0.5
    stocks[:, IDX_MINERALS] = 0.5
    stocks[:, IDX_MEMBRANE] = 0.3
    stocks[:, IDX_INFO] = 0.1
    return stocks


def _coeff_matrix_from_genome(genome_data: Sequence[float], n_env: int) -> np.ndarray:
    """Interpret flat genome vector as matrix [n_internal x n_env] of conversion coefficients."""
    g = np.asarray(genome_data, dtype=float).ravel()
    n_int = len(INTERNAL_RESOURCES)
    expected = n_int * n_env
    if g.size < expected:
        # repeat or pad with small values to fit
        reps = int(np.ceil(expected / max(1, g.size)))
        g = np.tile(g, reps)[:expected]
    else:
        g = g[:expected]
    return g.reshape((n_int, n_env))


def step_pixel_metabolism(manager, idx: int, env_inputs: Dict[str, float], dt: float):
    """
    Update internal resources for a single pixel given environmental inputs.

    env_inputs: dict channel -> value (already sampled for this tile)
    """
    if manager.internal_resources is None:
        return

    stocks = manager.internal_resources[idx]

    # Extract genome coefficients
    genome_obj = manager.genomes[idx] if idx < len(manager.genomes) else None
    genome_data = getattr(genome_obj, "data", None)
    if genome_data is None:
        # no genome: simple baseline decay of energy
        stocks[IDX_ENERGY] -= 0.001 * dt
        stocks[IDX_ENERGY] = max(0.0, float(stocks[IDX_ENERGY]))
        manager.energies[idx] = float(stocks[IDX_ENERGY])
        return

    env_keys = list(env_inputs.keys())
    env_vec = np.array([env_inputs[k] for k in env_keys], dtype=float)
    mat = _coeff_matrix_from_genome(genome_data, n_env=len(env_keys))

    # Linear conversion env -> internal fluxes
    flux_internal = mat @ env_vec  # shape (n_internal,)

    # Simple bounds on fluxes
    flux_internal = np.clip(flux_internal, -1.0, 1.0)

    # Basal metabolic costs (energy + membrane maintenance)
    basal_energy_cost = 0.001
    membrane_cost = 0.0005 * stocks[IDX_MEMBRANE]

    # Apply fluxes
    stocks += flux_internal.astype(np.float32) * dt

    # Apply costs
    stocks[IDX_ENERGY] -= (basal_energy_cost + membrane_cost) * dt

    # Clamp stocks to non-negative
    stocks[:] = np.maximum(stocks, 0.0)

    # Mirror ENERGY into main energies array used elsewhere
    manager.energies[idx] = float(stocks[IDX_ENERGY])


# Backwards-compatible helpers used in older code paths
def apply_metabolic_costs(energies, dt: float, base_cost: float = 0.001):
    energies -= base_cost * dt


def nutrient_to_energy(atom_symbol: str) -> float:
    return 0.0
