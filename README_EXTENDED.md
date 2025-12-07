# README (Extended)

Guida operativa rapida per clonare, installare ed eseguire l'Evolutive Simulator. Se ti serve capire come funziona internamente leggi `ARCHITECTURE.md`; se ti interessa il perché scientifico vai su `PROJECT_OVERVIEW.md`. Qui trovi solo le istruzioni pratiche.

## 1. Descrizione rapida
- Simulatore 2D di ecosistemi sintetici con pixel biologici e mappe climatiche procedurali.
- Serve per lanciare run riproducibili, osservare la GUI DearPyGui o ottenere CSV di metriche.
- Progettato per esperimenti veloci: una CLI unica, un renderer grafico, uno headless.
- Tutto ciò che riguarda scopi scientifici è spiegato in `PROJECT_OVERVIEW.md`.

## 2. Requisiti di sistema
- **Python**: 3.10 (consigliato, testato).
- **OS**: Windows 10+, macOS 12+, qualsiasi Linux recente con supporto OpenGL 3+.
- **GPU**: consigliata per la GUI DearPyGui su mappe > 512×256; headless funziona anche solo CPU.
- **Dipendenze native**: nessuna oltre a quelle installate via `pip`.

## 3. Installazione
```bash
python -m venv venv
venv\Scripts\activate    # su Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
```

## 4. Avvio rapido
```bash
python -m src.main --seed 42 --size 1024 512 --pixels 300
```
Attende il caricamento della GUI; al termine della run vengono scritti CSV in `data/metrics/`. Per lanciare headless aggiungi `--headless` (uscita testuale e CSV).

## 5. Parametri CLI principali
- `--seed <int>`: seed globale per generazione mondo e popolazione; usalo per run ripetibili.
- `--size <width height>`: dimensioni del pianeta; valori più grandi aumentano memoria/tempo.
- `--pixels <int>`: numero di pixel iniziali spawnati casualmente.
- `--map <path.npz>`: carica una mappa esistente (formato documentato in `ARCHITECTURE.md`); se omesso viene generata on-the-fly.

## 6. Struttura minima del progetto
```
src/
data/
requirements.txt
```
Per il dettaglio completo delle cartelle e dei moduli consulta `ARCHITECTURE.md`.

## 7. Output generati
- **Percorso**: `data/metrics/metrics_<label>_<run_id>.csv`.
- **Contenuto**: una riga per anno simulato con popolazione, energia media/varianza, diversità tratti, O2/CO2 e metadati run (seed, run_id).
- Eventuali log testuali compaiono in console; screenshot o altri asset non vengono generati automaticamente.

## 8. Limitazioni pratiche
- Performance: la GUI rallenta con mondi molto grandi (>2048 px) o con oltre 5k pixel attivi.
- Nessun resume/checkpoint: interrompere la run significa perdere i dati non ancora salvati.
- Nessuna gestione automatica dello storage: pulisci manualmente `data/metrics/` se fai molte run.

## 9. Rimandi ufficiali
- Dettagli architetturali (moduli, formati, parametri interni) → `ARCHITECTURE.md`
- Motivazioni, modello scientifico, uso corretto dei dati → `PROJECT_OVERVIEW.md`
