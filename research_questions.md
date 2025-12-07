# Research Objectives — Current Scope

Questa lista allinea le ambizioni di analisi con ciò che il simulatore fornisce oggi (vedi `README_EXTENDED.md` per l’uso operativo e `ARCHITECTURE.md` per i formati dei dati). I CSV generati da `RunRecorder` espongono solo campioni annuali di:

- `population`
- `avg_energy`, `var_energy`
- `trait_diversity`, `avg_traits_per_cell`
- `mean_info_order`
- `global_o2`, `global_co2`
- metadati run (`seed`, `run_id`, parametri CLI)

Le domande che seguono sono quindi limitate a questi osservabili. Le richieste storiche che richiedono tracciamento per-lineage, informazioni genomiche o eventi comportamentali avanzati sono spostate in fondo come backlog di ricerca.

---

## 1. Finest window di vitalità (Birth of Complexity v0.5)

**Domanda.** In quali combinazioni di `avg_energy`, `mean_info_order` e densità (`population`) osserviamo un aumento stabile della complessità (trend crescita contemporaneo di info e trait)?

**Metriche disponibili.**
- `population` vs `trait_diversity`
- `mean_info_order`
- `avg_energy`, `var_energy`

**Analisi possibile oggi.**
- Calcolare, run per run, il primo anno in cui `mean_info_order > threshold` e `trait_diversity` cresce oltre il valore iniziale.
- Confrontare il tempo a tale evento con i parametri CLI (`seed`, `size`, `pixels`), dedotti dai metadati.
- Stimare finestre di energia minima: `avg_energy - sqrt(var_energy)` come limite inferiore.

**Limitazioni.** Non si dispone di dati per lineage specifici o per tratti individuali; quindi si parla solo di trend aggregati.

---

## 2. Bottleneck evolutivi (Popolazione & Diversità)

**Domanda.** Quanto spesso e con che severità la popolazione scende sotto frazioni del massimo storico? Quanto rapidamente si recupera la diversità dei tratti?

**Metriche disponibili.**
- `population` (per anno)
- `trait_diversity`, `avg_traits_per_cell`

**Analisi possibile oggi.**
- Identificare anni con `population < 0.2 * max_population`.
- Misurare anni necessari per tornare sopra il 50% del massimo e per recuperare il valore precedente di `trait_diversity`.
- Classificare run in “stabili” vs “catastrofiche” basandosi sul numero di bottleneck per 100 anni simulati.

**Limitazioni.** Il CSV non espone lineages; quindi “fraction of lineages extinct” non è calcolabile. Si può solo usare `trait_diversity` come proxy.

---

## 3. Relazione Energia ↔ Informazione

**Domanda.** Esistono correlazioni robuste tra `avg_energy` (o `var_energy`) e `mean_info_order`? Quali regioni del piano (energia, informazione) sono visitate più spesso da run di successo?

**Metriche disponibili.**
- `avg_energy`, `var_energy`
- `mean_info_order`
- `trait_diversity`

**Analisi possibile oggi.**
- Scatter plot energia vs info per ogni run e regressioni log/lineari.
- Definizione di indicatori “efficienza evolutiva”: Δ`mean_info_order` / Δ`avg_energy` su finestre di anni.
- Segmentazione per parametri CLI (es. differenze tra mappe caricate e generate).

**Limitazioni.** Non si dispone del flusso energetico istantaneo né di consumi per trait specifico; i risultati sono aggregati e non distinguono cause/effetti.

---

## 4. Divergenza funzionale aggregata

**Domanda.** Quanto varia `trait_diversity` e il numero medio di tratti per cellula (`avg_traits_per_cell`) tra run con stessi parametri globali?

**Metriche disponibili.**
- `trait_diversity`
- `avg_traits_per_cell`

**Analisi possibile oggi.**
- Per una tripla (`seed_world`, `size`, `pixels`), confrontare la distribuzione di `trait_diversity` finale su più run biologici.
- Identificare run che mostrano “plateau” di diversità vs run che collassano.
- Collegare eventuali aumenti di diversità a variazioni di `global_o2`/`global_co2`.

**Limitazioni.** Non è possibile distinguere funzioni specifiche (motilità, cooperazione, ecc.) perché i CSV non salvano tag di trait; serve solo come proxy di varietà.

---

## 5. Feedback atmosferici globali

**Domanda.** Le dinamiche interne influenzano in modo misurabile `global_o2` e `global_co2`? Esistono correlazioni con `population` e `mean_info_order`?

**Metriche disponibili.**
- `global_o2`, `global_co2`
- `population`, `mean_info_order`

**Analisi possibile oggi.**
- Time-series analysis di O₂ e CO₂ rispetto alla popolazione totale.
- Identificazione di “eventi” dove un aumento persistente di O₂ segue un incremento di `trait_diversity`.
- Confronto tra run generati e run caricati con mappe diverse.

**Limitazioni.** Le metriche sono globali (nessuna mappa spaziale); interpretazioni locali richiedono nuovi log o snapshot del world grid.

---

## Backlog: domande che richiedono nuova strumentazione

Le richieste storiche qui sotto restano obiettivi di lungo termine, ma non sono attualmente calcolabili senza aggiungere log specifici (vedi `ARCHITECTURE.md` per dove intervenire):

1. **Inevitabilità delle funzioni.** Servirebbero contatori per trait “chiave” (motility, photosynthesis, ecc.) e timestamp di comparsa.
2. **Origine della cooperazione.** Richiede flag comportamentali o metriche di interazione; oggi abbiamo solo `trait_diversity`.
3. **Contingency vs Necessity.** Servono “signature” finali dettagliate (trait cluster, mappe di occupazione); i CSV annuali non bastano.
4. **Emergenza di intelligenza simulata.** Necessita di telemetria sui pattern di movimento/decisione, attualmente assente.

Per ognuna di queste, la roadmap è:
1. Estendere `PixelManager` o `RunRecorder` per registrare gli eventi necessari.
2. Documentare il nuovo formato in `ARCHITECTURE.md`.
3. Aggiornare questo file spostando la domanda nella sezione “attiva”.
