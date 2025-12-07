# Project Overview

## 1. Scopo scientifico
Esplorare come complessità, funzioni e informazione emergano in ecosistemi sintetici. Il progetto nasce per fornire un banco di prova controllato, non per riprodurre la biologia reale. È la fonte ufficiale per finalità teoriche; per aspetti tecnici si rimanda a `ARCHITECTURE.md`, per l'uso quotidiano a `README_EXTENDED.md`.

## 2. Tipo di modello scientifico
- Modello esplorativo, non predittivo.
- Universo simulato astratto, senza pretese di realismo biologico/climatico.
- Dinamica multi-agente su griglia 2D con regole deterministiche + rumore controllato.

## 3. Oggetto di studio
- Transizioni di complessità (dai pixel “proto” a linee con tratti sofisticati).
- Relazione energia ↔ informazione ↔ stabilità.
- Diversità funzionale (motilità, fotosintesi, cooperazione) e colli di bottiglia evolutivi.

## 4. Cosa rappresenta
- Ecosistemi sintetici dove si osservano pattern di crescita, collasso, recupero.
- Effetti di parametri climatici e ambientali su popolazioni generiche.
- Metriche aggregate (popolazione, Information Order, gas atmosferici) come indicatori di stati evolutivi.

## 5. Cosa NON rappresenta
- Biologia reale o modelli fisiologici dettagliati.
- Climatologia terrestre: mappe e biomi sono solo astrazioni matematiche.
- Ecologia applicata: nessuna validità predittiva per sistemi biologici esistenti.

## 6. Uso corretto dei dati
- Confrontare run con stessi parametri per valutare la variabilità intrinseca.
- Studiare soglie critiche (energia minima, densità, O2) e il loro impatto su complessità e sopravvivenza.
- Analizzare finestra temporale di collassi, recovery e nascita di funzioni (domande in `research_questions.md`).

## 7. Uso scorretto dei dati
- Estrarre previsioni sul pianeta Terra o su ecosistemi reali.
- Derivare policy climatiche o biologiche.
- Interpretare le metriche come misure dirette di organismi esistenti.

## 8. Domande di ricerca
- L'elenco completo è in `research_questions.md`. Questo file descrive gli obiettivi (complessità, bottleneck, inevitabilità delle funzioni, relazione energia-informazione, cooperazione, contingente vs necessario, ecc.) e fornisce il contesto scientifico da indagare.

## 9. Limiti epistemologici
- Nessuna validità predittiva: risultati dipendono dalle regole implementate e non sono generalizzabili senza ulteriore analisi.
- Dipendenza forte dal modello e dai parametri scelti; piccole modifiche possono cambiare radicalmente gli outcome.
- Significato dei tratti/biomi è metaforico e serve solo a ragionare su stati astratti.

## 10. Valore scientifico
- Offre uno strumento per ragionare su scenari “what-if” dell'origine della complessità.
- Utile per astrobiologia e filosofia della simulazione: permette di testare ipotesi sulla frequenza di funzioni evolutive in ambienti astratti.
- Crea dataset controllati per analisi quantitative su fenomeni emergenti.

## 11. Rapporto con gli altri file
- `README_EXTENDED.md`: istruzioni operative per lanciare esperimenti e generare dati.
- `ARCHITECTURE.md`: descrive come i componenti realizzano il modello (world/pixel/simulation/gui).
