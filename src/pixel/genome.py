# -------------------------------------------------
# src/pixel/genome.py
"""
Genome representation + helpers.

Per il nostro modello:
- Il genoma è un semplice vettore numerico.
- All'inizio tutte le unità condividono uno stato quasi neutro (quasi nessun tratto espresso).
- Alcuni indici del genoma vengono interpretati come "tratti" ad alto livello
  (photosynthesis, chemosynthesis, cilia, flagella, muscle, ecc.) che agiscono
  come skill e danno vantaggi concreti quando superano una soglia.
"""
from dataclasses import dataclass
from typing import Any, Dict, Set
import numpy as np

from .traits import TRAIT_PREREQS, all_prereqs_met


@dataclass
class Genome:
    data: Any


def random_genome(length: int = 8):
    """
    Initial genome for primordial units.

    All individuals start from the *same* neutral state with no
    strong traits expressed. Real diversity emerges only via
    mutations during reproduction.
    """
    # very small random noise around zero, identical distribution
    base = np.zeros((length,), dtype=float)
    noise = np.random.normal(loc=0.0, scale=0.01, size=length)
    return Genome(data=(base + noise))


def similarity(g1: Genome, g2: Genome) -> float:
    """Return similarity in range 0..1 (1 = identical).
    If genomes are incompatible types, fallback to 0.0.
    """
    try:
        a = np.asarray(g1.data, dtype=float)
        b = np.asarray(g2.data, dtype=float)
        if a.shape != b.shape:
            return 0.0
        # cosine similarity or 1 - normalized L2
        d = np.linalg.norm(a - b)
        maxd = np.linalg.norm(np.ones_like(a)) * np.sqrt(2)
        sim = 1.0 - (d / (d + 1e-9))
        return float(np.clip(sim, 0.0, 1.0))
    except Exception:
        return 0.0


# -------------------------------------------------
# Trait decoding
# -------------------------------------------------

# Mappa indice_gene -> trait simbolico principale che sblocca uno "skill"
# Quando il valore del gene supera una soglia, il tratto diventa attivo
# (se i suoi prerequisiti sono soddisfatti).
GENE_TRAIT_MAP: Dict[int, str] = {
    # metabolismo di base
    2: "photosynthesis",
    3: "chemosynthesis",
    # adattamento termico
    4: "antifreeze_proteins",
    5: "heat_resistance",
    # locomozione
    6: "cilia",
    7: "flagella",
}

TRAIT_GENE_THRESHOLD = 0.6


def decode_traits(genome: Genome) -> Set[str]:
    """
    Interpreta il vettore del genoma come insieme di tratti attivi.

    - Ogni gene mappato in GENE_TRAIT_MAP che supera TRAIT_GENE_THRESHOLD
      propone un tratto.
    - Vengono poi applicati i prerequisiti da TRAIT_PREREQS per filtrare
      solo i tratti coerenti.
    """
    try:
        g = np.asarray(genome.data, dtype=float).ravel()
    except Exception:
        return set()

    proposed: Set[str] = set()
    for idx, trait in GENE_TRAIT_MAP.items():
        if idx < g.size and g[idx] >= TRAIT_GENE_THRESHOLD:
            proposed.add(trait)

    # chiusura rispetto ai prerequisiti: teniamo solo i tratti che hanno
    # tutti i prerequisiti dentro proposed stessa (schema minimale ma coerente)
    active: Set[str] = set()
    for t in proposed:
        if all_prereqs_met(t, list(proposed), TRAIT_PREREQS):
            active.add(t)

    return active
