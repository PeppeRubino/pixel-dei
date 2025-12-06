# Research Objectives – Core Metrics to Extract from the Simulator

This document defines a first block of *quantitative* questions that the
simulator should help answer. For each question, we list the key
observables that future analysis code should log and aggregate over many
runs / seeds.

---

## 1. Birth of Complexity

**Question.** In which minimal conditions does complexity increase instead of collapsing?

**Targets.**

- Mean time to first non-trivial structure (first lineage with stable traits / non-zero INFORMATION_ORDER above threshold).
- Minimal thresholds for:
  - usable ENERGY
  - metabolic stability (low metabolic_stress variance)
  - local cell density
  - INFORMATION_ORDER
- Probability of total failure vs successful emergence of complex lineages across runs.

**Interpretation.**

- Complexity only in narrow windows → fine-tuned universe.
- Complexity almost always → life as an almost inevitable attractor.

---

## 2. Evolutionary Bottlenecks

**Question.** Is evolution governed more by continuous selection or by rare catastrophic events?

**Targets.**

- Temporal distribution of population bottlenecks (drops beyond a given percentile).
- Fraction of lineages extinct per bottleneck event.
- Mean recovery time (population and diversity) after collapses.
- “Genetic memory” after bottlenecks (similarity of traits/genomes before vs after).

**Interpretation.**

- Few events dominate outcomes → catastrofismo evolutivo.
- Mostly gradual change → darwinismo classico continuo.

---

## 3. Inevitability of Functions

**Question.** Do the same functional strategies emerge robustly across different initial worlds?

**Functions to track.**

- Phototrophy (photosynthesis, chloroplast-related traits).
- Motility (cilia, flagella, fins, legs, wings).
- Predation / heterotrophy (carnivore/omnivore traits).
- Cooperation (traits / behaviors that increase group fitness).
- Multicellularity (aggregation → multicell, if/when implemented).

**Targets.**

- Frequency of emergence per function across runs.
- Mean emergence time (in simulation months/years).
- Dependence on climate / biome distribution.

**Interpretation.**

- Functions that reappear in most runs → universal attractors.
- Rare, run-dependent functions → historical contingencies.

---

## 4. Energy–Information Relationship

**Question.** How much energy is required to sustain a given amount of organized information?

**Targets.**

- Joint statistics of internal ENERGY vs INFORMATION_ORDER per cell and per lineage.
- Dissipation vs complexity (energy flux consumed vs stable INFORMATION_ORDER).
- “Evolutionary efficiency”: increase in INFORMATION_ORDER per unit energy dissipated over time.

**Hypotheses to test.**

- Laws of the form:
  - `INFORMATION ∝ log(ENERGY)`
  - `COMPLEXITY ∝ ENERGY^α` (for some α)

**Interpretation.**

- Possible discovery of a physical law of biological organization (thermodynamics of information, Landauer-style limits).

---

## 5. Origin of Cooperation

**Question.** Is cooperation an accident or an inevitable phase beyond certain thresholds?

**Targets.**

- Time of first cooperative behavior/trait.
- Biomes and environmental regimes where cooperation first appears.
- Pressures present at emergence (density, resource scarcity, stress).
- Stability of cooperation in time (persistence vs collapse into cheating/extinction).

**Interpretation.**

- Cooperation always above certain density/conditions → near-universal law.
- Cooperation only in specific niches → strongly context-dependent phenomenon (ecology-driven).

---

## 7. Contingency vs Necessity

**Question.** If you rewind the tape of evolution, do you get essentially the same story?

**Protocol.**

- Fix a given world configuration (size, climate parameters, world seed).
- Run many simulations with:
  - same world, different random seeds for biology,
  - same global parameters but different histories (stochastic events).
- For each run, record a compressed “final signature” of the ecosystem:
  - distribution of trait clusters,
  - presence/absence of key functions (phototrophy, motility, predation, cooperation, multicellularity),
  - macroscopic biome/occupation pattern.

**Targets.**

- Pairwise similarity between final states of runs with same setup.
- Fraction of structures (functions/trait clusters) that repeat across runs.
- Robust vs fragile features of the ecological/functional landscape.

**Interpretation.**

- ≳90% of structures recur → evolution is almost deterministic under given constraints.
- ≲10% recur → evolution is deeply contingent, dominated by historical accidents.

---

## 8. Emergence Time of Simulated Intelligence

Here “intelligence” means *anticipatory* behaviour, not consciousness:

- prediction
- planning
- strategy under uncertainty

**Targets.**

- Time (in simulation months/years) to first clear anticipatory behaviour:
  - e.g. movement/foraging strategies that exploit predicted future resource states,
  - stable trait/behaviour combinations that increase success in variable environments.
- Minimal environmental conditions that support such behaviours:
  - energy flux,
  - complexity of resource landscape,
  - diversity of competitors/predators.
- Stability window:
  - how long such behaviours persist,
  - how robust they are to shocks and bottlenecks.

**Interpretation.**

- If anticipatory behaviours emerge easily and repeatedly → strong evidence that “intelligent” strategies are common outcomes in rich environments (astrobiological relevance, Drake-equation style inputs).
- If they require finely tuned conditions and appear rarely → intelligence is likely a rare, contingent phenomenon.

