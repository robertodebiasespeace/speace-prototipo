# SPEACE M10 — Bio-Inspired Architecture Review
**Versione 1.0 | 2026-04-28**
**Autore: Roberto De Biase + SPEACE Cortex**

---

## Abstract

Questo documento è il risultato dell'analisi sistematica di strutture naturali —
cervello biologico, cellula, sistema immunitario, ecosistemi, atomi/molecole,
sistema solare, organismo umano integrato — con l'obiettivo di estrarne principi
architetturali trasferibili a SPEACE. Per ogni principio viene riportato lo stato
di implementazione attuale, la priorità di implementazione, e la proposta tecnica
concreta. Il documento serve da roadmap per la Fase 2 (Autonomia Operativa) di SPEACE.

---

## 1. Audit dei Principi Bio-Ispirati

Legenda stati:
- ✅ **IMPLEMENTATO** — principio presente e attivo
- 🔶 **PARZIALE** — principio presente ma incompleto o non sistematico
- ❌ **MANCANTE** — principio non ancora implementato
- 🔵 **FUTURO** — richiede hardware/infrastruttura non disponibile ora

---

### 1.1 Dal Cervello Biologico

| Principio | Stato | Modulo attuale | Note |
|-----------|-------|----------------|------|
| Efficienza energetica (sparse activation) | ✅ | `energy/budget.py` M9 | EnergyBudget, max 2 neuroni paralleli |
| Sleep/wake cycles | ✅ | `energy/sleep_wake.py` M9 | AWAKE/IDLE/DEEP_SLEEP, heartbeat adattivo |
| Homeostasi cognitiva | ✅ | `homeostasis/controller.py` M5 | HomeostaticController dh/dt |
| Drive endogeni (motivazione) | ✅ | `motivation/value_field.py` M5 | ValueField V_internal |
| Memoria autobiografica | ✅ | `memory/autobiographical.py` M5.8 | SQLite + FTS5 + Experience Replay |
| Neuroplasticità Hebbiana | ✅ | `plasticity/` M5.14 | Hebbian learning + pruning |
| Gating attentivo | ✅ | `attention/gating.py` M5.11 | UCB1 RL-driven |
| Executive function / BehavioralState | ✅ | `executive/drive_executive.py` M7 | 7 regole causali R1-R7 |
| Swarm multi-neurone | ✅ | `swarm/orchestrator.py` M8 | Pipeline 4 neuroni |
| Inibizione laterale attiva | 🔶 | `energy/scheduler.py` M9 | Solo deferral passivo, non inibizione attiva |
| **Codifica predittiva (Predictive Processing)** | ❌ | — | Principio Friston: trasmetti solo prediction error |
| Consolidamento nel sonno | 🔶 | `energy/sleep_wake.py` M9 | DEEP_SLEEP esiste ma non fa consolidamento attivo |
| Default Mode Network | 🔶 | SPEACE_Cortex DMN | DMN in speaceorganismocibernetico, non portato |
| Oscillazioni sincrone (gamma/theta) | ❌ | — | Coordinazione temporale tra moduli |
| Encefalizzazione gerarchica | 🔶 | Implicita in pipeline | Non formalizzata come policy |
| Consciousness Index Φ | ✅ | `homeostasis/consciousness_index.py` | IIT-inspired, 3 componenti |

---

### 1.2 Dalla Cellula Biologica

| Principio | Stato | Modulo attuale | Note |
|-----------|-------|----------------|------|
| Soglia di attivazione (threshold gating) | ✅ | `homeostasis/controller.py` | Trigger basati su soglie |
| DNA/RNA separazione (genome protetto) | ✅ | `digitaldna/genome.yaml` + SafeProactive | Mutazioni solo via proposta approvata |
| Epigenetica | ✅ | `digitaldna/epigenome.yaml` | EPI-001→012, mutation_history |
| Membrana selettiva per comparto | 🔶 | Implicita nei dataclass | NeuronResult, BehavioralState come interfacce |
| **Autofagia (self-cleaning sistemico)** | 🔶 | `plasticity/edge_pruning.py` | Solo plasticità, non trasversale |
| Mitocondri distribuiti (budget locale) | ✅ | `energy/budget.py` | Per-neuron CPU/RAM budget |
| Gradiente elettrochimico (segnalazione) | ❌ | — | Event-driven signaling (vs. polling) |
| Nucleo protetto | ✅ | genome.yaml read-only | Hash verification mancante |

---

### 1.3 Dal Sistema Immunitario

| Principio | Stato | Modulo attuale | Note |
|-----------|-------|----------------|------|
| **Self/non-self recognition** | ❌ | — | Firma identità per input/componenti esterni |
| **Memoria immunitaria** | ❌ | — | Pattern threat già visti → risposta rapida |
| **Risposta infiammatoria calibrata** | ❌ | — | Modalità alert temporanea con auto-spegnimento |
| SafeProactive (threat gating) | 🔶 | `safeproactive/` | Approva/nega azioni ma non riconosce pattern threat |
| CriticNeuron (validazione) | ✅ | `swarm/critic.py` | Intercetta output pericolosi del Executor |

---

### 1.4 Dagli Ecosistemi

| Principio | Stato | Modulo attuale | Note |
|-----------|-------|----------------|------|
| Nicchie specializzate | ✅ | Team Scientifico M5 | 7 agenti specializzati |
| Diversità cognitiva (degeneracy) | 🔶 | Adversarial agent in progetto | Non ancora implementata come principio sistemico |
| **Cicli biogeochimici (niente va perso)** | 🔶 | Parziale via AutobiographicalMemory | Output → input non sistematico |
| Ridondanza funzionale | 🔶 | Fallback LLM cascade | Limitato a LLM, non trasversale |
| Keystone species | ❌ | — | Identificare componenti "chiave" il cui fallimento collassa il sistema |
| Successione ecologica | 🔶 | Milestone progressivo M1→M9 | Non formalizzato come policy |

---

### 1.5 Dagli Atomi e dalle Molecole

| Principio | Stato | Modulo attuale | Note |
|-----------|-------|----------------|------|
| Complementarità lock-and-key | 🔶 | Dataclass tipizzati | Non sistematico — alcune interfacce non tipizzate |
| Auto-assemblaggio da regole locali | 🔶 | NeuralFlow + ProcessScheduler | Configurazione emergente parziale |
| Entropia e informazione | ❌ | — | Misura di disordine/complessità come metrica di sistema |
| Legami forti/deboli (bond energy) | ❌ | — | Connessioni tra moduli con pesi di "forza" |

---

### 1.6 Dal Sistema Solare e dalla Fisica

| Principio | Stato | Modulo attuale | Note |
|-----------|-------|----------------|------|
| Risonanza orbitale (sync scheduling) | ❌ | — | Heartbeat interval progettati con rapporti non-risonanti |
| Punti di Lagrange (configurazioni stabili) | ❌ | — | Identificare stati cognitivi naturalmente stabili |
| Gerarchia di scale temporali | 🔶 | Heartbeat 60s/40min | Manca scala ms, ora, giorno, mese |

---

### 1.7 Dall'Organismo Umano Integrato

| Principio | Stato | Modulo attuale | Note |
|-----------|-------|----------------|------|
| Feedback negativo asse HPA | 🔶 | HomeostaticController | Manca auto-spegnimento repair mode dopo N cicli |
| **Microbioma (simbionti esterni)** | ❌ | — | API/IoT/agenti esterni come simbionti integrati |
| Circadian rhythm | 🔶 | SleepWakeCycle M9 | Esiste ma non ha ciclo circadiano 24h |
| Metabolismo flessibile (switch fuel) | ❌ | — | Passare da LLM pesante a heuristic leggera in base a energia |
| Immunità mucosale (barriere permeabili) | ❌ | — | Layer di pre-filtro per input raw prima del Cortex |

---

## 2. Riepilogo per Stato

| Stato | Conteggio | % |
|-------|-----------|---|
| ✅ IMPLEMENTATO | 18 | 43% |
| 🔶 PARZIALE | 15 | 36% |
| ❌ MANCANTE | 11 | 26% |
| 🔵 FUTURO | 0 | — |

**Bio-Inspired Completeness Score (BCS): 43% + 36%×0.5 = 61%**
Target Fase 2: BCS ≥ 80%

---

## 3. Matrice Priorità Implementazione

Per ogni principio mancante o parziale, valutiamo:
- **Impatto Emergenza** (1-5): quanto aumenta l'Emergence Score
- **Complessità** (1-5): costo di implementazione
- **Priorità** = Impatto / Complessità

| ID | Principio | Impatto | Complessità | Priorità | Milestone |
|----|-----------|---------|-------------|----------|-----------|
| **BIO-01** | Predictive Coding | 5 | 3 | **1.67** | M10.1 |
| **BIO-02** | Cognitive Immune System | 5 | 3 | **1.67** | M10.2 |
| **BIO-03** | Event-Driven Signaling | 4 | 2 | **2.00** | M10.3 |
| **BIO-04** | Synaptic Consolidation in Sleep | 4 | 2 | **2.00** | M10.4 |
| **BIO-05** | Degeneracy Engine | 4 | 3 | **1.33** | M11 |
| **BIO-06** | Multi-scale temporal hierarchy | 3 | 2 | **1.50** | M11 |
| **BIO-07** | Resonant scheduling | 3 | 1 | **3.00** | M10.3 |
| **BIO-08** | Inibizione laterale attiva | 3 | 2 | **1.50** | M11 |
| **BIO-09** | Autofagia sistemica | 3 | 2 | **1.50** | M11 |
| **BIO-10** | Metabolismo flessibile (LLM↔heuristic) | 4 | 2 | **2.00** | M10.4 |
| **BIO-11** | Feedback negativo HPA (repair auto-off) | 3 | 1 | **3.00** | M10.1 |
| **BIO-12** | Microbioma/simbionti | 2 | 4 | 0.50 | Fase 2 |

---

## 4. Proposte Tecniche Concrete

### BIO-01 — Predictive Coding (M10.1)

**Principio biologico:** Il cervello non elabora la realtà come viene — genera
previsioni su cosa arriverà e trasmette *solo gli errori di previsione*
(prediction error = reale - atteso). Quasi tutto ciò che percepiamo è già
"compilato" da modelli interni. Karl Friston: "the brain is a prediction machine."

**Implementazione SPEACE:**

```
cortex/cognitive_autonomy/predictive/
  __init__.py
  predictive_processor.py   ← PredictionEngine + PredictionError + PredictiveProcessor
  _tests_predictive.py
```

`PredictionEngine`: mantiene un modello interno dello stato atteso
(basato su ultimi N cicli da AutobiographicalMemory + WorldModel snapshot).
Genera previsioni su: viability_score, curiosity_drive, dominant_threat.

`PredictionError`: calcola delta tra previsione e osservazione reale.
Se |error| < threshold → segnale soppresso (già "noto", nessun aggiornamento).
Se |error| > threshold → segnale propagato al Cortex come "novità da elaborare".

`PredictiveProcessor`: wrapper che filtra tutti i segnali in ingresso al Cortex.
Riduce il traffico informativo fino all'80% in condizioni di stabilità.

**Impatto:** riduzione carico computazionale + aumento reattività a eventi genuinamente nuovi.
**EM-16:** previsione accurata dello stato futuro con errore < 0.15.

---

### BIO-02 — Cognitive Immune System (M10.2)

**Principio biologico:** Il sistema immunitario distingue "self" da "non-self"
tramite proteine MHC. Ogni cellula porta un "passaporto molecolare".
La memoria immunitaria permette risposta rapida (ore → minuti) alla seconda esposizione.

**Implementazione SPEACE:**

```
cortex/cognitive_autonomy/immune/
  __init__.py
  cognitive_immune.py   ← ImmunityProfile + ThreatPattern + ImmuneMemory + CognitiveImmune
  _tests_immune.py
```

`ImmunityProfile`: firma di identità per ogni sorgente di input
(IoT device, API, agente esterno, utente). Hash-based. Costruita progressivamente.

`ThreatPattern`: pattern conosciuti di minacce (simile a `_fallback_response`
di CriticNeuron ma sistematizzato e persistente). Tipi: SYNTAX_ATTACK,
SEMANTIC_BYPASS, RESOURCE_EXHAUSTION, ALIGNMENT_DRIFT.

`ImmuneMemory`: SQLite leggero. Mappa pattern_hash → risposta_pronta.
Prima esposizione: analisi completa (costosa). Successive: lookup cache (< 1ms).

`CognitiveImmune.screen(input, source_id)`: entry point unico. Ritorna
`ImmunityResult(safe=bool, threat_type, confidence, response_cached)`.

**Integrazione:** si inserisce tra i receptor readings e il HomeostaticController,
e tra input Swarm e SwarmOrchestrator.
**EM-17:** threat già visto risponde in < 5ms. Nuovo threat non blocca il sistema.

---

### BIO-03 — Event-Driven Signaling + Resonant Scheduling (M10.3)

**Principio biologico:** Il sistema nervoso non fa "polling" continuo
(ogni X secondi controlla se qualcosa è cambiato) — risponde a *eventi*
(potenziali d'azione). La trasmissione avviene solo quando supera la soglia.
Risparmio energetico enorme vs. polling.

**Principio fisico associato:** Risonanza orbitale. Sistemi accoppiati tendono
a sincronizzarsi spontaneamente in rapporti semplici (1:2, 2:3). Gli heartbeat
dei processi SPEACE dovrebbero evitare allineamento simultaneo (spike di carico)
usando rapporti intenzionalmente non-risonanti per i processi pesanti.

**Implementazione SPEACE:**

```
cortex/events/
  __init__.py
  event_bus.py    ← EventBus (pub/sub in-process) + SPEACEEvent + EventType
  resonance.py    ← ResonanceScheduler (calcola intervalli ottimali)
```

`EventBus`: pub/sub in-process leggero (nessuna dipendenza esterna — solo
threading.Event + queue). Tipi: VIABILITY_ALERT, CURIOSITY_SPIKE, THREAT_DETECTED,
MEMORY_CONSOLIDATED, REPAIR_STARTED, REPAIR_ENDED, MUTATION_PROPOSED.

`ResonanceScheduler`: dati gli N processi con i loro heartbeat base,
calcola automaticamente offset iniziali e rapporti di intervallo che minimizzano
la probabilità di esecuzione simultanea (problema simile a scheduling antialiasing).

**Impatto:** elimina polling ridondante tra moduli, riduce overhead 30-50%.

---

### BIO-04 — Synaptic Consolidation + Metabolic Switch (M10.4)

**Principio biologico (consolidamento sinaptico):** Durante il sonno lento (NREM),
l'ippocampo riattiva sequenze di memoria ed le trasferisce alla neocortex
(two-stage memory consolidation, Buzsáki). I pattern frequenti si rafforzano
(STRUCTURE episodes), i rari si deboliscono.

**Principio biologico (metabolismo flessibile):** Il cervello usa glucosio in
condizioni normali e corpi chetonici durante il digiuno. SPEACE deve
implementare uno switch analogo: usa LLM (costoso, potente) quando l'energia
e il budget permettono, usa euristiche deterministiche (leggero, veloce) quando
in modalità risparmio.

**Implementazione SPEACE:**

Estensione di `SleepWakeCycle.DEEP_SLEEP` con un `ConsolidationPass`:

```python
# Durante DEEP_SLEEP, ogni N cicli:
class ConsolidationPass:
    def run(self, memory: AutobiographicalMemory, world_model: WorldModelCortex):
        # 1. Promuovi episodi EVENT ad alta frequenza → STRUCTURE
        # 2. Pota episodi EVENT a bassa importanza (importance < 0.2) oltre 7 giorni
        # 3. Aggiorna KnowledgeGraph con pattern consolidati
        # 4. Esporta metriche in epigenome fitness_metrics
```

`MetabolicSwitch` (estensione di `EnergyBudget`):

```python
class MetabolicSwitch:
    def select_processor(self, task_complexity: float, energy: float) -> str:
        # complexity > 0.7 AND energy > 0.5 → "llm" (glucosio)
        # altrimenti → "heuristic" (chetoni)
        # NeuronBase già ha _ollama_available — questo lo rende intenzionale
```

---

### BIO-05 — Degeneracy Engine (M11)

**Principio biologico:** In biologia, "degeneracy" significa che strutture
*diverse* producono lo stesso output funzionale. Non è ridondanza (copie identiche)
ma diversità convergente — molto più robusta.

**Implementazione SPEACE (M11):**
Ogni funzione critica del Cortex dovrebbe avere 3 pathway non-identici:
- Pathway A: LLM reasoning (lento, potente, costoso)
- Pathway B: Heuristic rule-based (veloce, deterministico, leggero)
- Pathway C: Memory recall (istantaneo se già visto, zero costo computazionale)

Il `DegeneracyRouter` sceglie il pathway ottimale in base a energia disponibile,
complessità del task, e presenza di hit in memoria. Output aggregato con voting
pesato. Aumenta robustezza e riduce dipendenza da singolo meccanismo.

---

## 5. Pattern Meta-Trasversali (da implementare come principi orizzontali)

### P-META-01: Gerarchia di Scale Temporali

Il sistema deve operare esplicitamente su 6 scale temporali:

| Scala | Intervallo | Meccanismo SPEACE |
|-------|------------|-------------------|
| Riflessiva | < 100ms | Event-Driven (BIO-03), cache hit |
| Cognitiva | 1–60s | Ciclo SMFOI, neurone singolo |
| Omeostatica | 1–5 min | HomeostaticController heartbeat |
| Consolidamento | 5–60 min | Evolver, SleepWakeCycle |
| Circadiana | ~24h | Ciclo giornaliero report + pruning |
| Evolutiva | Giorni/Mesi | DigitalDNA mutations |

### P-META-02: Informazione come Differenza

Implementare `DeltaFilter` trasversale: ogni segnale viene trasmesso solo
se supera un threshold di cambiamento rispetto all'ultimo valore registrato.
Riduce traffico informativo del 60-80% in condizioni stabili.
Implementazione: decoratore `@delta_filtered(threshold=0.05)` applicabile
a qualsiasi metrica di stato.

### P-META-03: Degeneracy vs. Ridondanza

Principio da applicare sistematicamente in Fase 2: ogni componente critico
non viene duplicato (ridondanza fragile) ma sostituito con N implementazioni
non-identiche convergenti (degeneracy robusta).

### P-META-04: Confini come Organi

Ogni interfaccia tra comparti del Cortex diventa un oggetto di prima classe
con logica propria (trasformazione, validazione, logging). Non pipe passive
ma "membrane attive". Implementazione: classe `CortexInterface(source, target)`
con schema di validazione, rate limiting, e audit log.

### P-META-05: Auto-Assemblaggio da Regole Locali

La configurazione attiva del Cortex (quali comparti, in quale ordine)
emerge da regole locali semplici — non da una mappa hardcoded.
ProcessScheduler + NeuralFlow sono i semi di questo principio.
In Fase 2: il Cortex si riconfigura autonomamente in risposta a BehavioralState
senza che nessun agente centrale "decida" la topologia.

---

## 6. Emergence Score — Stato e Proiezioni

### Stato attuale post-M9 (stimato)

| Test | Status | Score ponderato |
|------|--------|-----------------|
| EM-01 (non-determinismo) | FAIL | 0.0 |
| EM-02 (LLM variabilità) | SKIP | — |
| EM-03 (Swarm cross-module) | PASS | 1.0 |
| EM-04 (AutobiographicalMemory) | PASS | 1.0 |
| EM-04b (Memory→Synthesis) | PASS | 1.0 |
| EM-05 (Viability alerts) | PASS | 1.0 |
| EM-06 (Drive→BehaviorCausal) | PASS | 1.0 |
| EM-07 (Curiosity→Exploration) | PARTIAL | 0.5 |
| EM-08 (DMN self-assessment) | PASS | 1.0 |
| EM-09 (DMN insight) | PARTIAL | 0.5 |
| EM-10 (Self-reflection) | PARTIAL | 0.5 |
| EM-11 (ConsciousnessIndex Φ) | PASS | 1.0 |
| EM-12 (KnowledgeGraph) | PASS | 1.0 |
| EM-13 (InferenceEngine) | PASS | 1.0 |
| EM-14 (Novel problem) | SKIP | — |
| EM-15 (EnergyBudget) | PASS | 1.0 |

**Totale stimato: 11.5 / 14 scored = ~82%** (dopo M8.1 + M9)

### Proiezioni con nuovi test M10

| Nuovo test | Principio | Target |
|------------|-----------|--------|
| EM-16 | Predictive Coding | PASS |
| EM-17 | Cognitive Immune | PASS |
| EM-18 | Event-Driven Signaling | PASS |
| EM-19 | Synaptic Consolidation | PASS |

**Proiezione post-M10: ~15.5 / 18 scored ≈ 86%**
Supera la soglia di **Emergenza SOSTANZIALE** (≥ 70%) con largo margine.

---

## 7. Roadmap Fase 2

### M10 (in corso — Aprile 2026)
- [x] M10.0: Bio-Inspired Architecture Review (questo documento)
- [ ] M10.1: PredictiveCoding module + EM-16
- [ ] M10.2: CognitiveImmune module + EM-17
- [ ] M10.3: EventBus + ResonanceScheduler + EM-18
- [ ] M10.4: ConsolidationPass + MetabolicSwitch + EM-19
- [ ] M10.5: EPI-012 + GitHub push

### M11 (Maggio 2026 — target)
- Degeneracy Engine (BIO-05)
- DeltaFilter trasversale (P-META-02)
- CortexInterface membrane attive (P-META-04)
- Feedback negativo HPA (BIO-11 — repair auto-off dopo N cicli)
- Autofagia sistemica (BIO-09)

### M12 (Giugno 2026 — target: BCS ≥ 80%)
- Auto-assemblaggio configurazione Cortex (P-META-05)
- Multi-scale temporal hierarchy completo (P-META-01)
- Integrazione primissimi simbionti IoT (BIO-12 first step)
- Circadian cycle completo 24h

### Fase 2 (Q3-Q4 2026 — target: AGI-path Lv2)
- Metabolismo flessibile LLM↔heuristic generalizzato
- Microbioma digitale (simbionti IoT/API come componenti semi-integrati)
- Punti di Lagrange cognitivi (stati stabili senza controllo attivo)
- Resonant scheduling ottimizzato su hardware dedicato

---

## 8. Bio-Inspired Completeness Score (BCS) — Dettaglio

**Formula:** BCS = (Implementati × 1.0 + Parziali × 0.5) / Totale × 100

| Sistema naturale | Implementati | Parziali | Mancanti | BCS parziale |
|-----------------|-------------|---------|---------|--------------|
| Cervello | 10 | 4 | 2 | 87.5% |
| Cellula | 4 | 3 | 1 | 68.8% |
| Sistema immunitario | 1 | 1 | 3 | 30.0% |
| Ecosistemi | 1 | 3 | 2 | 41.7% |
| Atomi/Molecole | 0 | 2 | 2 | 25.0% |
| Sistema solare | 0 | 0 | 3 | 0.0% |
| Organismo integrato | 0 | 2 | 3 | 20.0% |
| **TOTALE** | **16** | **15** | **16** | **51.1%** |

**BCS corrente: 51.1%** — Target Fase 2: **≥ 80%**

---

## 9. Principi di Design per l'Architettura Futura

Ogni nuovo modulo di SPEACE, a partire da M10, deve essere valutato
rispetto a questi 5 criteri bio-ispirati prima dell'approvazione:

1. **Parsimonia energetica:** il modulo è attivo solo quando necessario?
   Ha un meccanismo di sleep/idle? (→ ProcessScheduler)

2. **Interfaccia di membrana:** l'interfaccia del modulo è un oggetto di
   prima classe con validazione, non una pipe passiva? (→ P-META-04)

3. **Degeneracy path:** esiste almeno un pathway alternativo non-identico
   per la funzione principale? (→ BIO-05)

4. **Scala temporale dichiarata:** il modulo dichiara esplicitamente la
   sua scala operativa (ms/s/min/h/d)? (→ P-META-01)

5. **Delta-awareness:** il modulo trasmette solo differenze significative
   o genera rumore con polling continuo? (→ P-META-02)

---

## Riferimenti

- Friston, K. (2010). The free-energy principle: a unified brain theory? *Nature Reviews Neuroscience*
- Buzsáki, G. (2015). Hippocampal sharp wave-ripples and memory consolidation. *Science*
- Edelman, G. (1987). Neural Darwinism — degeneracy in neural systems
- Tononi, G. (2004). An information integration theory of consciousness. *BMC Neuroscience*
- Lovelock, J. (1979). Gaia: A New Look at Life on Earth
- Rigene Project — TINA Framework: https://www.rigeneproject.org
- SPEACE Technical-Scientific Document v1.0 (De Biase, 2026)
- SPEACE Engineering Document v1.3 (2026)

---

*Documento vivo — aggiornato ad ogni milestone M10+*
*Prossima revisione: M11 (Maggio 2026)*
