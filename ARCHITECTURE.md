# ARCHITECTURE

## 1. Scopo tecnico
Piattaforma modulare, data-oriented e riproducibile per simulazioni sintetiche di ecosistemi. Questo documento spiega come è costruito il sistema; per obiettivi scientifici e uso operativo rimandare rispettivamente a `PROJECT_OVERVIEW.md` e `README_EXTENDED.md`.

## 2. Tipo di modello
- Sistema dinamico discreto
- Multi-agente (pixel biologici)
- Griglia 2D con campi scalari
- Implementazione data-oriented (array NumPy condivisi)

## 3. Modello architetturale a strati
1. **World Layer** – genera mappe, biomi e canali ambientali.
2. **Pixel Layer** – gestisce stato, tratti, metabolismo e riproduzione degli agenti.
3. **Simulation Layer** – coordina update world/pixel, scheduling e metriche.
4. **Presentation Layer** – GUI DearPyGui o rendering headless.

## 4. Struttura delle cartelle
```
src/
  main.py
  world/
    biome.py
    world.py
    map_generator.py
    environment.py
    resources.py
  pixel/
    pixel_manager.py
    genome.py
    metabolism.py
    reproduction.py
    behaviors.py
    identity.py
    traits.py
  simulation/
    core.py
    metrics.py
  gui/
    dpg_app.py
    dpg_world_view.py
    dpg_sidebar.py
    dpg_topbar.py
    layout.py
  rendering/
    debug_renderer.py
  ui/
  commands/
data/
requirements.txt
PROJECT_OVERVIEW.md
README_EXTENDED.md
```

## 5. Responsabilità dei moduli
- **world/**
  - `map_generator.py`: rumori multi-scala, generazione campi elevazione/temperatura/umidità/pressione.
  - `biome.py`: enum `Biome`, colori, funzione `biome_from_env`.
  - `world.py`: orchestrazione globale di mappe, gas atmosferici, stato ambientale.
  - `environment.py`: definizione canali ambientali (LIGHT, ORGANIC_SOUP, ecc.) e sampling.
  - `resources.py`: `ResourceGrid` (tensor NumPy) per nutrienti/atomi con operazioni di diffusione e consumo.
- **pixel/**
  - `pixel_manager.py`: array condivisi per posizioni, energia, stamina, flag `alive`, specie, referenze a genome/traits; gestisce spawn, step, riproduzione.
  - `genome.py`: definizione dei genomi neutrali e decode dei tratti attivi.
  - `metabolism.py`: indici delle risorse interne (ENERGY, ORGANICS, MINERALS, MEMBRANE, INFO_ORDER) e funzioni di consumo/produzione.
  - `reproduction.py`: condizioni per divisione, mutazioni e allocazione risorse ai figli.
  - `behaviors.py`: heuristics di movimento per pixel con motilità avanzata.
  - `identity.py`, `traits.py`: nomenclatura e definizione trait set.
- **simulation/**
  - `core.py`: classe `Simulation`, loop principale, orchestrazione tick (world → pixel → renderer), hooking dei renderer.
  - `metrics.py`: `RunRecorder` (campionamento annuale, buffer in memoria e scrittura CSV).
- **gui/**
  - `dpg_app.py`: entry point DearPyGui.
  - `dpg_world_view.py`: rendering mappa e overlay.
  - `dpg_sidebar.py`: mixin per stats globali, pixel selezionato, log.
  - `dpg_topbar.py`, `layout.py`: controlli e costanti UI.
- **rendering/debug_renderer.py**: renderer testuale/headless per run batch.
- **main.py**: CLI, parsing argomenti, costruzione world/pixel/simulation, scelta renderer, aggancio metrics.

## 6. Flusso dei dati
### Setup
1. `main.py` carica gli argomenti CLI, setta seed, costruisce `World` (caricando `map_path` o generandone una).
2. Viene creata la `ResourceGrid` e assegnata al world.
3. `PixelManager` viene dimensionato e popolato tramite `spawn_random`.
4. `Simulation` riceve world, pixel manager e resource grid; opzionalmente viene creato `RunRecorder`.

### Runtime loop
1. `Simulation.step()` aggiorna world (processi ambientali).
2. PixelManager esegue update vettoriali: metabolismo, movimento, riproduzione, morte; aggiorna gli array interni.
3. Renderer selezionato (GUI o headless) legge world/pixel e visualizza/logga.
4. `RunRecorder.update()` campiona se è trascorso l'intervallo richiesto.

### Persistenza
- A chiusura della GUI o al termine dei tick headless, `RunRecorder.save()` serializza i campioni in CSV (cartella `data/metrics`).
- Non esistono snapshot di stato: tutte le altre strutture vivono in memoria.

## 7. Formato dei dati
- **CSV metrics**: header commentato con metadata (`datetime`, `run_id`, `seed`, `label`, meta extra).
- **Campi principali** per riga:
  - `tick`, `time`, `year`
  - `population`
  - `avg_energy`, `var_energy`
  - `trait_diversity`, `avg_traits_per_cell`
  - `mean_info_order`
  - `global_o2`, `global_co2`
  - `seed`, `run_id`

## 8. Parametri critici interni
- `PixelManager.capacity`: dimensiona tutti gli array; deve essere >= 4 × pixel iniziali per gestire duplicazioni.
- Soglie metaboliche: definite in `metabolism.py` e `reproduction.py` (energia minima per divisione, costi trait).
- Soglie biomi: in `biome_from_env` (altitudine, temperature, humidity, global_o2, organic_layer, noise).
- `sample_every` (RunRecorder) e convenzione 12 mesi = 1 anno: controllano la risoluzione temporale delle metriche.

## 9. Dipendenze tecniche
- NumPy – core data layout e operazioni vettoriali.
- noise – mappe procedurali (Perlin/simplex).
- DearPyGui – front-end grafico.
- Arcade (legacy) – parte del debug renderer.
- Pillow – supporto texture/testo.
- dataclasses-json – serializzazione opzionale di oggetti complessi.
- Typer/Rich/PyYAML – CLI helper, logging, parsing config.

## 10. Limiti tecnici strutturali
- Nessuna accelerazione GPU per la simulazione (solo per la GUI).
- Nessun event loop asincrono: tutti gli agenti aggiornano nello stesso tick.
- Nessun checkpoint/resume del mondo o dei pixel.
- Metriche aggregate: non viene salvata la storia completa per pixel.
- Headless renderer non copre tutte le feature della GUI.

## 11. Estensioni tecniche future
- Plugin climatici o generatori mondo intercambiabili.
- Batch runner headless con orchestrazione e raccolta centralizzata.
- Snapshot/restore degli stati (checkpoint su disco).
- Storage columnar (Parquet) per metriche e tracciamento lineage.
- Sistema eventi ambientali dinamici agganciato a `Simulation`.

## 12. Competenze tecniche dimostrate
- Architettura modulare a strati con responsabilità chiare.
- Progettazione data-oriented per gestire migliaia di agenti con NumPy.
- Pipeline di metriche personalizzata e integrata con il loop principale.
- Integrazione DearPyGui per monitoring e debugging in tempo reale.
- Tooling CLI/packaging per distribuire il sistema in ambienti riproducibili.
