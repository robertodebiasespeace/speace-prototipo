# PROP-CORTEX-NEURAL-MESH-M4

> **Proposta SafeProactive estesa** — Milestone architetturale M4 "Continuous Neural Mesh" (CNM).
> **Status: APPROVED** (approvata da Roberto De Biase il 2026-04-19 con stringa canonica `APPROVATA PROP-CORTEX-NEURAL-MESH-M4`).

---

## 0-bis. Decisioni approvate (2026-04-19)

| Decision Point | Scelta approvata | Impatto operativo |
|---|---|---|
| **11.1 Scope** | **[A] Scope pieno (22 task)** | Tutti i task `#31`–`#52` attivi, ma vedi 11.2 per esclusione plasticity. |
| **11.2 Plasticity** | **[B] Rimandare a M5** | Task `#44 M4.12` rimosso da M4 → spostato in futura M5. La mesh M4 sarà **grafo statico**. |
| **11.3 Needs weights** | **[C] Harmony-first (Rigene)** | `{harmony: 0.35, survival: 0.20, self_improvement: 0.15, expansion: 0.15, integration: 0.15}`. Armonia come driver centrale, in linea con la visione di "armonia funzionale" del Rigene Project. |
| **11.4 Daemon lifecycle** | **[B+C] Doppia modalità (auto + cron)** | Implementare entrambe le modalità configurabili via `epigenome.mesh.lifecycle: "auto" \| "scheduled"`. **Default `scheduled`** (più sicuro in Fase 1, usa skill `schedule`); `auto` opt-in per sperimentazioni avanzate. |
| **11.5 AHK hook** | **[A] Stub già in M4** | Preparare placeholder in `cortex/mesh/neurons/ahk/` come neurone stub (contratto + no-op execute); attivazione reale rimandata a M5-AHK dedicato. |

### Conseguenze sulla milestone

- **Task M4 effettivi: 21** (`#44` escluso, sarà rifocalizzato in M5 "Graph Plasticity + AHK Self-Evolutive").
- **Grafo mesh statico** in tutta M4: `plasticity_enabled` assente in EPI-004 (o hard-coded `false`, non esposto).
- **Needs Driver riflette l'ethos Rigene**: il bisogno dominante è *harmony*, quindi la policy di equilibrio (`harmony safeguard`, task #42) ha priorità massima sulle decisioni della mesh.
- **Daemon lifecycle doppio**: M4.14 creerà sia `speace_mesh_daemon.py` (auto) che `tools/mesh_cron_wrapper.py` (per skill `schedule`). Selettore via epigenome.
- **Budget aggiornato**: ~18-22 file nuovi (era 20), ~1500-2100 LOC (era 1800-2500, plasticity escluso).

---

## 0. Metadata

| Campo | Valore |
|---|---|
| **ID proposta** | `PROP-CORTEX-NEURAL-MESH-M4` |
| **Timestamp bozza** | 2026-04-19 |
| **Sorgente** | speace-cortex (evolutionary-dev-agent) |
| **Milestone** | M4-CNM (post-M3L.6) |
| **Risk Level complessivo** | **MEDIUM** (default flag OFF, opt-in, SafeProactive gate su ogni mutazione runtime) |
| **Human-in-the-loop** | **Obbligatorio** per M4.0.a (approvazione) e per ogni mutazione di grafo classificata HIGH |
| **Snapshot pre-esecuzione richiesto** | Sì: `snap_YYYYMMDD_HHMMSS_m4_cnm_init` prima di M4.1 |
| **Rollback plan** | Sì (vedi §7) |
| **Task di tracking** | `#31 M4.0` → `#52 M4.20` (22 task con grafo dipendenze definito) |
| **Prerequisito** | M3L.6 completato (task `#30`) |

---

## 1. Executive Summary

Introdurre in SPEACE un **modulo di miglioramento continuo in background** — la *Continuous Neural Mesh* (CNM) — costituito da un **grafo computazionale tipizzato e adattivo** in cui ogni script/algoritmo Python funziona come un **neurone funzionale** con interfacce rigorose. Il modulo automatizza l'orchestrazione fra SPEACE Cortex, DigitalDNA, memoria, Scientific Team, skill e plugin; è guidato da un **Needs Driver** (cinque bisogni dinamici: survival, expansion, self_improvement, integration, harmony) che genera task SafeProactive-compliant per soddisfarli, in equilibrio con l'ambiente (Natura, società umana, tecnologie, governi, leggi).

Questa milestone formalizza quello che finora è stato un insieme di componenti coordinati *esternamente* (SMFOI-KERNEL chiama Cortex, Cortex chiama Team Scientifico, evolver stimola mutazioni) in un **tessuto computazionale* vivente*** sempre attivo, con contratto di esecuzione formale e plasticità strutturale guidata da feedback — la rappresentazione operativa più fedele finora della visione "super-organismo digitale" del Rigene Project.

---

## 2. Razionale

### 2.1 Perché ora

1. **M3L ha dimostrato il Neural Flow single-cycle** (9 comparti orchestrati da NeuralFlow). Il passo logico è far passare da *flow* (una passata per ciclo) a *mesh* (topologia continuamente attiva con feedback loop).
2. **Il Needs Driver è la risposta architetturale** alla richiesta di "bisogni dinamici da soddisfare" presente da tempo in `CLAUDE.md` (sezione *Stimolatore evolutivo: bisogni, obiettivi evolutivi*) ma mai formalizzata.
3. **L'interoperabilità fra componenti SPEACE** (Cortex, DigitalDNA, skill, plugin, MCP, Scientific Team) è oggi *implicita*; cresce il debito architetturale. Un **Organism Language Contract** (OLC) tipizzato la rende esplicita, versionata e validabile.
4. **Fitness function** (M3L.2) e **Quality Gate** (M3L.5) forniscono già le **metriche di feedback** che il Needs Driver e la Plasticity consumeranno. L'infrastruttura è matura.
5. **Compliance-by-design**: contratti formali + audit trail mesh + plasticity gated da SafeProactive preparano il terreno per EU AI Act, ISO 42001, NIST AI RMF — in linea con la direttiva `CLAUDE.md` sul *Regulatory Compliance Layer*.

### 2.2 Allineamento Rigene Project / TINA

| Principio Rigene | Realizzazione in CNM |
|---|---|
| Super-organismo cognitivo | Grafo di neuroni-script → fisiologia digitale continua |
| Digital DNA (genoma-epigenoma) | Plasticity scrive epigenome.yaml; genoma resta immutabile |
| Armonia funzionale | Need `harmony` + policy di equilibrio anti-sovraccarico |
| Governance etica distribuita | Ogni mutazione HIGH passa da SafeProactive (human-in-the-loop) |
| Interconnessione bio-tecnologica | OLC prepara l'innesto IoT/sensori di Fase 2 senza rework |
| Evoluzione continua | Plasticity + Needs Driver = selezione adattativa in-process |

---

## 3. Scope

### 3.1 Componenti che M4 **introduce**

```
cortex/mesh/
├── SPEC_NEURON_CONTRACT.md           # specifica formale (M4.1)
├── contract.py                       # validatore statico/runtime (M4.2)
├── olc/                              # Organism Language Contract (M4.3)
│   ├── __init__.py
│   ├── sensory.py, interpretation.py, decision.py, mutation.py, feedback.py
├── execution_rules.yaml              # backpressure, timeouts, quotas (M4.4)
├── graph.py                          # DAG tipizzato adattivo (M4.5)
├── runtime.py                        # scheduler asincrono (M4.6)
├── registry.py                       # neuron discovery via @neuron (M4.7)
├── neurons/                          # adapter per componenti esistenti (M4.8)
│   ├── cortex/, dna/, team/, memory/
├── needs_driver.py                   # bisogni dinamici (M4.9)
├── harmony.py                        # policy di equilibrio (M4.10)
├── task_generator.py                 # needs → proposte SafeProactive (M4.11)
├── plasticity.py                     # mutazioni grafo (M4.12)
└── telemetry.py                      # mesh_state.jsonl (M4.13)

speace_mesh_daemon.py                 # loop continuo (M4.14)
tools/mesh_status.py                  # CLI dashboard (M4.13)
benchmarks/bench_mesh.py              # benchmark throughput/latenza (M4.17)
tests/test_mesh_*.py                  # ≥30 test (M4.16)
```

### 3.2 Componenti che M4 **modifica**

- `cortex/SMFOI_v3.py` → innesto Step 3.bis "Needs Check" (M4.15)
- `digitaldna/epigenome.yaml` → nuovo blocco `mesh:` (EPI-004, M4.18) — **flag OFF di default**
- `SPEACE-main.py` → nuovo flag `--mesh` per avviare il daemon (M4.14)
- `speace-prototipo.md` → Appendice E "Continuous Neural Mesh" (M4.19)

### 3.3 Componenti che M4 **NON** modifica (invarianti garantite)

- `digitaldna/genome.yaml` (immutabile per definizione)
- `safeproactive/safeproactive.py` (CNM lo *usa*, non lo modifica)
- I 9 comparti Cortex esistenti (vengono *wrappati* come neuroni — le API legacy restano attive)
- I 10 agenti del Scientific Team (vengono wrappati; l'orchestrator resta invocabile come oggi)
- Il neural_flow legacy (resta la via *primaria* finché `mesh.enabled=true` in epigenome)

### 3.4 Fuori scope (rimandato a M5+)

- Integrazione IoT reale (sensori fisici) — richiede Fase 2
- Distribuzione multi-host (swarm) — richiede Fase 3
- Esecuzione di neuroni non-Python (WASM, Rust, etc.)
- LLM fine-tuning o self-training dei modelli (continua a valere l'adapter LLM di M3L.4)
- Movimento nel mondo fisico (robotica) — Fase 4/5

---

## 4. Architettura di massima

```
                  ┌──────────────────────────────────────────────────┐
                  │            SPEACE Mesh Daemon (loop)             │
                  │  heartbeat_s: 300 (configurabile in epigenome)   │
                  └───────────────┬──────────────────────────────────┘
                                  │
         ┌────────────────────────┼──────────────────────────┐
         ▼                        ▼                          ▼
┌────────────────┐       ┌─────────────────┐      ┌────────────────────┐
│  Needs Driver  │       │  Graph Runtime  │      │   Plasticity       │
│ survival,exp., │◀──────│ asyncio/threads │─────▶│  add/remove/rewire │
│ self_impr.,    │ feed- │ backpressure,   │ feed-│ (gated by SP)      │
│ integration,   │ back  │ timeouts, quota │ back │                    │
│ harmony        │       └────────┬────────┘      └────────────────────┘
└────────┬───────┘                │
         │ task_gen               │ executes
         ▼                        ▼
┌────────────────┐     ┌──────────────────────────────────────────┐
│ Task Generator │     │         Neuron Registry                  │
│ → PROP (SP)    │     │  @neuron(name, needs=[...], level=...)   │
└────────┬───────┘     │                                          │
         │             │  Wrappers → Cortex(9), DNA, Team, Mem    │
         ▼             └──────────────────────────────────────────┘
┌────────────────┐
│  SafeProactive │  ← tutte le mutazioni HIGH e tutti i task generati
│  (human gate)  │    dal Needs Driver passano da qui
└────────────────┘
```

Flusso tipico di un ciclo daemon (5 minuti):

1. **Telemetria in**: runtime legge FeedbackFrame dell'ultimo ciclo; aggiorna needs + fitness per neurone.
2. **Needs Check**: needs_driver.step(dt) → applica decay + update. Se un need è sotto soglia → TaskGenerator emette PROP-NEED-xxx.
3. **Harmony safeguard**: se load > threshold → throttle (riduce max_concurrent_neurons, quarantena neuroni deboli).
4. **Graph execution**: runtime lancia neuroni attivi in topological order, rispettando execution_rules.
5. **Plasticity** (opzionale, flag off di default in M4): propone mutazioni grafo → SafeProactive.
6. **Persistenza**: telemetry append su `mesh_state.jsonl`; snapshot needs su `needs_state.json`.
7. **Integrazione SMFOI**: il ciclo SMFOI esterno legge needs_driver.snapshot in Step 3.bis (M4.15).

---

## 5. Sicurezza & Safeguards

### 5.1 Principio generale
**Zero azioni HIGH autonome.** Ogni mutazione che modifica codice, genoma, wallet, o scrittura persistente non-log passa da SafeProactive.approve() con human-in-the-loop.

### 5.2 Layer di protezione

| Layer | Difesa | Attivato in |
|---|---|---|
| **Feature flag** | `epigenome.mesh.enabled=false` di default | EPI-004 (M4.18) |
| **Contract validator** | Input/output tipizzati; violazione → ContractViolation + quarantena neurone | M4.2 |
| **Execution rules** | Timeout per-neurone, max_concurrent, CPU/RAM quota, circuit breaker | M4.4 |
| **Harmony safeguard** | Load > soglia → throttle globale, priorità ai neuroni survival/harmony | M4.10 |
| **SafeProactive gate** | Ogni mutazione grafo + ogni task HIGH generato → PROP pending | M4.11, M4.12 |
| **Plasticity flag** | `plasticity_enabled=false` di default, flip solo post-bench-validation | EPI-004 |
| **Quarantine** | Neuroni che violano contratto N volte → disabled automaticamente | M4.7 |
| **Audit trail** | `mesh_state.jsonl` append-only (compat EU AI Act art. 12) | M4.13 |

### 5.3 Limiti Fase 1 (hardware 16GB RAM, PC embrionale)

- `max_concurrent_neurons` default **8** (allineato con Cortex attuale)
- RAM budget mesh: ≤ **2 GB** (il resto per OS + Cortex + LM Studio)
- CPU budget: ≤ **50%** (anti-overload)
- `harmony_threshold` default **0.7** (sopra → throttle)
- Heartbeat default **300 s** (5 min); configurable down a 60 s, up a 3600 s

---

## 6. Success Criteria (misurabili)

La milestone M4 è considerata **completa** solo se tutti i criteri sono verificati:

| ID | Criterio | Misura | Target |
|---|---|---|---|
| SC-1 | Contract validator cattura violazioni | Test M4.16/a | 100% (≥5 casi sintetici) |
| SC-2 | Backpressure previene overload | Test M4.16/c | Load medio < 60% anche sotto stress |
| SC-3 | Harmony safeguard attivo | Test M4.16/e | Throttle entro 1 heartbeat da superamento soglia |
| SC-4 | Neural flow legacy non regredisce | pytest baseline | 16/16 + nuovi ≥ 30, tutti verdi |
| SC-5 | Daemon `--once` smoke | Esecuzione reale | Exit code 0, mesh_state.jsonl non vuoto |
| SC-6 | Needs Driver genera task utili | Bench M4.17 | ≥1 task generato per need sotto soglia, ≥95% rilevanza |
| SC-7 | Footprint Fase 1 rispettato | Monitor psutil | RAM mesh ≤ 2 GB, CPU medio ≤ 50% |
| SC-8 | SafeProactive gate sempre attivo | Audit log | 0 mutazioni HIGH auto-eseguite |
| SC-9 | SPEACE Alignment Score | Post-M4 | ≥ 75/100 (da ~67 attuale) |
| SC-10 | Documentazione completa | Review | Appendice E + SPEC_NEURON_CONTRACT.md redatti, rivisti |

---

## 7. Rollback Plan

### 7.1 Rollback soft (disattivazione)
- `epigenome.mesh.enabled=false` → il daemon esce al prossimo heartbeat; neural_flow legacy resta funzionale.
- Zero codice da rimuovere: SPEACE continua a girare come pre-M4.

### 7.2 Rollback hard (rimozione)
- `scripts/rollback.py --restore snap_YYYYMMDD_HHMMSS_m4_cnm_init` → ripristina snapshot pre-M4.1.
- Rimuove `cortex/mesh/`, `speace_mesh_daemon.py`, blocco `mesh:` da epigenome.
- Mantiene telemetria `mesh_state.jsonl` archiviata in `archive/m4_rollback_YYYYMMDD/` per audit.

### 7.3 Rollback parziale (plasticity)
- `epigenome.mesh.plasticity_enabled=false` → mesh gira ma il grafo resta statico. Utile se plasticity produce drift indesiderato.

### 7.4 Trigger di rollback automatico
Il daemon si auto-disattiva (senza intervento umano) se:
- Violazioni contratto > 10 in < 60 s
- RAM > 90% per > 3 heartbeat consecutivi
- Error rate neuroni > 50% per > 2 heartbeat
- SafeProactive PROPOSALS pending non approvate > 50

---

## 8. Risk Assessment

| Rischio | Probabilità | Impatto | Mitigazione |
|---|---|---|---|
| Sovraccarico sistema (RAM/CPU) | Media | Alto | Execution rules + harmony safeguard + auto-rollback §7.4 |
| Plasticity produce grafo instabile | Media | Medio | `plasticity_enabled=false` di default; flip solo post-bench + approvazione |
| Neuroni con side effect non dichiarato | Bassa | Alto | Contract validator + quarantena + review manuale pre-merge |
| Bias del Needs Driver (un need domina) | Media | Medio | Weights bilanciati in epigenome; Adversarial Agent analizza periodicamente |
| Drift etico (task HIGH autonomi) | Molto bassa | Critico | SafeProactive *hard gate* non bypassabile; audit log append-only |
| Incompatibilità SMFOI Step 3.bis | Bassa | Medio | Innesto opt-in, test di regressione 16/16 pytest |
| Debito tecnico (troppo scope) | Alta | Medio | Task atomici e dipendenze esplicite; milestone incrementali |
| Fallimento backup/restore snapshot | Bassa | Critico | Verifica preliminare `scripts/rollback.py --dry-run` prima di M4.1 |

---

## 9. Impatto su SPEACE Alignment Score

Baseline attuale: **~67/100** (post-M3L.4, stima orchestrator).

Contributi attesi post-M4:
- +4 *Autoregolazione* (Needs Driver sostituisce stimolazione esterna evolver)
- +3 *Interoperabilità* (OLC formalizza contratti)
- +3 *Resilienza* (auto-rollback, quarantena, harmony safeguard)
- +2 *Compliance-by-design* (audit trail mesh_state.jsonl)
- +1 *Adattività* (plasticity, anche se flag OFF)

**Target post-M4: 78-82/100** — gate avanzamento verso Fase 2 (`external_benchmark_validated` già true da M2; mancano `self_regulation_mature` e `compliance_layer_active` che M4 sblocca).

---

## 10. Budget & Complessità

| Dimensione | Stima |
|---|---|
| Task totali | 22 (#31–#52) |
| File nuovi | ~20 |
| File modificati | ~5 |
| Righe di codice nuove (stima) | 1800-2500 |
| Righe di test nuove | 500-800 (≥30 test) |
| Durata stimata (sessioni) | 3-5 sessioni da ~4h cad. |
| Budget LLM (token) | Basso: la maggior parte del lavoro è deterministica (grafi, contratti, runtime) |
| Dipendenze nuove Python | Pydantic (già disponibile); zero nuovi package esterni |

---

## 11. Decision Points per il direttore orientativo (Roberto)

Prima di approvare, richiedo orientamento esplicito su:

### 11.1 Scope
- **[A]** Scope pieno (22 task) come specificato.
- **[B]** Scope ridotto Fase 1: solo Contract + Graph + Runtime + Needs Driver (~12 task), rimandando Plasticity e Harmony safeguard a M4.2.
- **[C]** Altro (indicare).

### 11.2 Plasticity
- **[A]** Implementare con flag OFF di default (safe, richiede bench per flip manuale).
- **[B]** Non implementare in M4; rimandare a M5 quando il grafo statico sarà validato.

### 11.3 Needs weights iniziali (somma=1.0)
- **[A]** Bilanciati: `{survival: 0.25, expansion: 0.20, self_improvement: 0.20, integration: 0.15, harmony: 0.20}` (mia proposta)
- **[B]** Survival-first: `{survival: 0.40, ...}`
- **[C]** Harmony-first (Rigene oriented): `{harmony: 0.35, survival: 0.20, ...}`
- **[D]** Personalizzato (indicare).

### 11.4 Daemon lifecycle
- **[A]** Avvio manuale con `--mesh` flag.
- **[B]** Avvio automatico se `epigenome.mesh.enabled=true` (rischio: daemon sempre attivo).
- **[C]** Cron/scheduled task (richiede skill `schedule` da `CLAUDE.md` skills).

### 11.5 Integrazione con AHK Self-Evolutive (CLAUDE.md future task)
- **[A]** Preparare hook già in M4 (stub) ma non usare.
- **[B]** Non preparare; rimandare a M5-AHK dedicato.

---

## 12. Allineamento con skill esistenti

| Skill disponibile (CLAUDE.md) | Uso in CNM |
|---|---|
| `consolidate-memory` | Chiamata periodica dal daemon per pruning MEMORY.md |
| `schedule` | Alternativa per daemon avvio (decision point 11.4C) |
| `skill-creator` | Generazione skill da need.integration quando SPEACE incontra tool nuovi |

---

## 13. Prossimi passi (dipendenti da approvazione)

1. ☐ Approvazione esplicita di Roberto con stringa **`APPROVATA PROP-CORTEX-NEURAL-MESH-M4`** (e risposte ai decision points §11).
2. ☐ `scripts/rollback.py --snapshot snap_YYYYMMDD_HHMMSS_m4_cnm_init` (snapshot pre-esecuzione).
3. ☐ Task `#31 M4.0` → completed; sblocco `#33 M4.1` secondo il grafo dipendenze.

Fino all'approvazione, **nessun file di cortex/mesh/ viene creato**. Questa bozza è solo documento di design.

---

## 14. Firma e stato

- **Redatto da:** SPEACE (Claude) come evolutionary-dev-agent
- **Coordinatore progetto:** Roberto De Biase (direttore orientativo)
- **Data bozza:** 2026-04-19
- **Status:** `APPROVED` (2026-04-19 da Roberto De Biase)
- **Canale di feedback:** risposta diretta in sessione o via email `robertodebiase80@gmail.com`
- **Prossima azione:** snapshot pre-esecuzione + chiusura M3L.6 → avvio M4.1

---

*Proposta redatta in conformità con SafeProactive v1.0, DigitalDNA (genome.yaml immutabile), e linee guida `CLAUDE.md` v1.0 del 2026-04-05.*
