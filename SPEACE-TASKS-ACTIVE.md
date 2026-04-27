# SPEACE — Tasks Board Attivo

**Versione:** 2.1
**Data:** 2026-04-26
**Stato:** Documento vivo — aggiornato al completamento/inserimento di task
**Scopo:** Vista sintetica e dinamica di tutti i task attivi per lo sviluppo di SPEACE, con snapshot dello stato complessivo.

> **Regola di aggiornamento:** ogni chiusura o apertura di task deve aggiornare (1) la riga relativa, (2) la sezione "Snapshot Stato SPEACE", (3) la data del documento. Il documento è la single-source-of-truth operativa tra `safeproactive/PROPOSALS.md` (governance) e il runtime (`SPEACE-main.py`).

---

## Legenda

**Stato:** ⬜ Non iniziato · 📋 In analisi · 🔄 In sviluppo · 🧪 Testing · 👁️ Review · ✅ Completato · 🚫 Bloccato
**Priorità:** 🔴 Critica · 🟠 Alta · 🟡 Media · 🟢 Bassa
**Area:** CNM (Continuous Neural Mesh) · COG (Cognitive Autonomy M5) · BRN (Brain Biologico BRN-001→020) · INT (Integrazioni esterne) · OPS (Operazioni/CI/Repo) · DOC (Documentazione) · ORG (Agente Organismico)

---

## Snapshot Stato SPEACE (2026-04-26)

- **Milestone chiuse:** M0 (scaffolding), M1 (SafeProactive+DigitalDNA), M2 (Team Scientifico ridotto), M3 (Cortex 9 comparti), M3L (LLM as Semantic Tissue).
- **Milestone CHIUSA (2026-04-26): M4-CNM** — tutti i task completati: M4.1→M4.11, M4.13→M4.16, M4.18, M4.20. Suite mesh: **158/158 + 26/26 e2e = 184 test verdi**. EPI-004 applicata (`epigenome.yaml` v1.4, blocco `mesh:` default OFF). `SPEACE-main.py` v1.1 con `--brain` flag e `_run_brain_cycle()`. **M5.1+ ora sbloccato.**
- **Milestone APPROVATA (2026-04-24):** **M5 — Cognitive Autonomy** (`PROP-COGNITIVE-AUTONOMY-M5`, scope full). **M5.0 completato**: scaffold `cortex/cognitive_autonomy/` con 6 sottopacchetti, 5 drive, `HomeostaticController` stub. **M5.1+ in attesa di closure M4.20.**
- **Milestone COMPLETATA (2026-04-26): MIG-001 — Migrazione Brain Biologico** da `speaceorganismocibernetico/`. Porting integrale completato:
  - `cortex/brain/` — **22 file**, **20/20 moduli BRN** verificati importabili: BRN-001→015 fully implemented, BRN-016→020 stub (language, causal, abstraction, self-model, recursive-self-improvement).
  - Moduli avanzati copiati in `cortex/`: `digital_brain.py` (neutrasmettitori), `astrocyte_network.py` (Nature 2026), `autopoietic_engine.py`, `system3_controller.py`, `morphogenesis_engine.py`, `myelination_engine.py`, `neural_parliament.py`, `epigenetic_modulator.py`, `graph_engine.py`, `neural_bridge.py`.
  - `cortex/world_model/` — Knowledge Graph Module (9° comparto Cortex).
  - `digitaldna/fitness_function.yaml` + `mutation_rules.py` — fitness function esplicita con 5 pesi (alignment 0.35, task_success 0.25, stability 0.20, efficiency 0.15, ethics 0.05).
  - `SPECS/` — 10 documenti spec ST-1→ST-10.
  - `SPEACE-Engineering-Document-v1.1.md` + `v1.2.md`.
  - **Prossimo passo BRN:** wiring `cortex/brain/` nel `cortex/__init__.py` + collegamento `BrainIntegration` al loop principale (`SPEACE-main.py`) via `NEU-003`.
- **Dashboard Streamlit v1.4** online in localhost (8501).
- **Integrazioni esterne:** Obsidian + Hermes Agent — **decisione: INTEGRARE** (default OFF, opt-in via `epigenome.integrations.*`).
- **Rischi aperti:** git push bloccato da sandbox (workaround: `PUSH-NOW.bat`); AGI-gap BRIGHT in attesa di approvazione M5; BRN-016→020 stubs da implementare; `cortex/brain/` non ancora wired nel runtime principale.

**C-index (ultimo ciclo runtime):** ~0.427 (SMFOI) + ~0.311 (Brain) — dual C-index operativo.
**Livello evolutivo dichiarato:** Modular Emergent (R=9 SMFOI).
**BRN integrati:** 15/20 fully implemented · 5/20 stub · wired via `--brain` flag (NEU-003 ✅).
**M5 progress:** M5.0→M5.11 ✅ (A+B+M5C.1) · M5.12→M5.20 ⬜ · Test coverage: 25+39+24+22+32=**142 test green** · Dashboard v2: viability KPI + drives grid + cognitive section.

---

## AREA: CNM — Continuous Neural Mesh (M4)

| ID | Stato | Prio | Descrizione | Criterio chiusura |
|----|-------|------|-------------|-------------------|
| M4.1 | ✅ | 🔴 | Contratto `@neuron` (`cortex/mesh/contract.py`) | Decorator + validazione firma |
| M4.2 | ✅ | 🔴 | Grafo mesh (`cortex/mesh/graph.py`) | DAG, topo-sort, 6 violazioni |
| M4.3 | ✅ | 🔴 | Runtime asincrono (`cortex/mesh/runtime.py`) | ThreadPool + backpressure |
| M4.4 | ✅ | 🔴 | Cap concorrenza per livello (L1..L5) + per need | Semafori bounded |
| M4.5 | ✅ | 🔴 | Quarantine + error-window fail-safe | Freeze automatico |
| M4.6 | ✅ | 🔴 | Propagate BFS nel DAG + telemetria base | 200 task < 110 ms |
| M4.7 | ✅ | 🟠 | Registry neuron auto-discovery (`cortex/mesh/registry.py`) | `discover_neurons()` walk+sys.modules fallback, 10/10 AC test verdi, idempotenza via `skip_existing`, graph integration verificato |
| M4.8 | ✅ | 🟠 | Adapter neuroni per 9 comparti + DNA + SPT | 11 adapter (9 comparti + DigitalDNA evaluator + SPT review), 8/8 AC test, fail-soft pattern, lazy cache, fix `OLCBase.validate()` (elif su List/Dict) |
| M4.9 | ✅ | 🟡 | Needs driver (`cortex/mesh/needs_driver.py`) | `NeedsDriver` con 5 funzioni di calcolo (survival/expansion/self_improvement/integration/harmony), priority_gap, history ring buffer, 10/10 AC test |
| M4.10 | ✅ | 🟡 | Harmony safeguard (`cortex/mesh/harmony.py`) | `HarmonyPolicy` produce `HarmonyVerdict` (HEALTHY/WATCH/ALERT/CRITICAL) + 9 kind di `CompensationAction` + `allowed_risk_levels` per gating SafeProactive, 12/12 AC test |
| M4.11 | ✅ | 🟡 | Task Generator (`cortex/mesh/task_generator.py`) | `TaskGenerator` con TEMPLATES per ciascun need, downgrade automatico risk vs `allowed_risk_levels`, round-robin diversità, `to_safeproactive_dicts()`, 11/11 AC test |
| M4.13 | ✅ | 🟢 | Telemetria mesh (`cortex/mesh/telemetry.py` + `dashboard_cli.py`) | JSONL append-only su `safeproactive/state/mesh_state.jsonl`, `build_event()` JSON-safe, `MeshTelemetry.record_cycle()`, dashboard ASCII (VERDICT/NEED/GRAPH/PROPOSALS/COMPENSATIONS/DISTRIBUTION) + CLI (`--path/--last/--json/--stats`), 11/11 AC test |
| M4.14 | ✅ | 🟡 | Daemon mesh (`cortex/mesh/daemon.py`) | `MeshDaemon` con DI (registry+graph+driver+policy+gen+telemetry), `tick()` fail-soft (observe→evaluate→generate→record→listener), `start(interval_s)` heartbeat thread, `run_n()`, `record_fitness()` ring buffer, `_inspect_risk_queue()` stub (TODO M4.15), 11/11 AC test |
| M4.15 | ✅ | 🟠 | Integrazione CNM ↔ SMFOI-KERNEL Step 3.bis (`cortex/mesh/smfoi_bridge.py`) | `MeshNeedsCheck` + `step3bis_needs_check()` cachano daemon canonico, promuovono push secondo `HarmonyVerdict` (WATCH+1 / ALERT+2 / CRITICAL+3), default OFF via `epigenome.mesh.enabled` (retrocompatibile, abilitato da EPI-004 in M4.18). Smoke kernel OK (default-OFF invariato; ON: verdict=watch, content non-dict preservato sotto `_original`). 11/11 AC test |
| M4.16 | ✅ | 🟠 | Test integrazione CNM end-to-end | **26/26 PASS** — `_tests_e2e.py`: tick, topology, needs, harmony, proposals, telemetry, brain-sensor, smfoi-bridge |
| M4.17 | ⬜ | 🟢 | Benchmark mesh vs pipeline classica | Report comparativo latenza/throughput |
| M4.18 | ✅ | 🔴 | Mutazione DigitalDNA `EPI-004` (mesh block) | `epigenome.yaml` v1.4: blocco `mesh:` con `enabled=false`, `smfoi_bridge_step3bis=false` |
| M4.20 | ✅ | 🟠 | Report finale M4-CNM + aggiornamento task board | SPEACE-TASKS-ACTIVE.md v1.6, milestone M4 chiusa, M5 sbloccata |

**Dipendenze:** M4.7→M4.8→M4.15→M4.16→M4.18→M4.20. M4.9/4.10/4.11 possono procedere in parallelo dopo M4.7.

---

## AREA: BRN — Brain Biologico (M6 — Integrazione BRN-001→020)

> Migrazione `speaceorganismocibernetico → cortex/brain/` completata (MIG-001, 2026-04-26). 20/20 moduli presenti. Task M6 coprono: (a) wiring nel runtime, (b) completamento stub BRN-016→020, (c) integrazione con CNM mesh e Cognitive Autonomy.

| ID | Stato | Prio | Modulo BRN | Descrizione | Criterio chiusura |
|----|-------|------|------------|-------------|-------------------|
| BRN.W1 | ✅ | 🔴 | — | Wiring `cortex/brain/` in `cortex/__init__.py` | `WorldModel` esposta da `world_model/compartment.py`; import 4/4 path OK |
| BRN.W2 | ✅ | 🔴 | — | `NEU-003`: collegare `BrainIntegration` a `SPEACE-main.py` | `_run_brain_cycle()` nel loop; flag `--brain`; riepilogo finale Brain; syntax OK |
| BRN.W3 | ✅ | 🟠 | BRN-001→015 | Smoke test runtime completo tutti i moduli implemented | **21/21 import OK** (BRN-001→020 + brain_integration); functional test: 3 cicli, consciousness=0.36, dopamine=0.50 |
| BRN.W4 | ⬜ | 🟠 | — | Adapter neuroni BRN nel CNM Registry (`cortex/mesh/registry.py`) | `discover_neurons()` individua almeno 5 moduli brain |
| BRN.W5 | ⬜ | 🟡 | — | Esporre metriche BRN su telemetria mesh (`mesh_state.jsonl`) | Campo `brain_state` nel record ciclo |
| BRN.16 | ⬜ | 🟡 | BRN-016 | Implementare `LanguageAcquisition` (da stub a pieno) | Phonological + Semantic + Syntactic layers attivi |
| BRN.17 | ⬜ | 🟡 | BRN-017 | Implementare `CausalReasoner` (Pearl hierarchy) | `do_operator()` funzionante su grafo semplice |
| BRN.18 | ⬜ | 🟡 | BRN-018 | Implementare `AbstractionLayer` (conceptual blending) | `ConceptualBlender.blend()` su 2 concetti |
| BRN.19 | ⬜ | 🟡 | BRN-019 | Implementare `SelfModel` (body schema + metacognizione) | `introspect()` ritorna stato coerente |
| BRN.20 | ⬜ | 🟠 | BRN-020 | Implementare `RecursiveSelfImprover` (Darwin Gödel) | `SafeModificationGate` attivo, approval human-in-loop |
| BRN.AST | ⬜ | 🟡 | AST | Wiring `astrocyte_network.py` con `glial_controller` (AST-002) | `CalciumWave` propagazione verificabile |
| BRN.AUT | ⬜ | 🟡 | AUT | Test `autopoietic_engine.py` + `system3_controller.py` integrati | Score autopoiesi > 0 nel ciclo runtime |
| BRN.DNA | ⬜ | 🟠 | DNA | Attivare `fitness_function.yaml` nel loop DigitalDNA | `mutation_rules.py` legge fitness e filtra mutazioni |
| BRN.DOC | ⬜ | 🟢 | — | Aggiornare `SPEACE-Engineering-Document-v1.2.md` con sezione M6 | Sezione "Brain Integration Layer" presente |

**Dipendenze:** BRN.W1 → BRN.W2 → BRN.W3 → BRN.W4. BRN.16→BRN.20 indipendenti, ma BRN.20 richiede SafeProactive HIGH review. BRN.DNA sblocca EPI-005 (M5.7).

---

## AREA: COG — Cognitive Autonomy (M5 — **APPROVED** 2026-04-24)

> `PROP-COGNITIVE-AUTONOMY-M5` approvata in scope full da Roberto De Biase. M5.0 completato in giornata. M5.0.a (snapshot) e M5.0.b (validazione M4.20) in corso. M5.1+ bloccati fino a closure M4-CNM (dipendenza `addBlockedBy=M4.20`).

| Fase | ID | Stato | Prio | Descrizione | Task runtime |
|------|----|-------|------|-------------|--------------|
| — | M5.0 | ✅ | 🔴 | Scaffold `cortex/cognitive_autonomy/` (6 sottopacchetti + `HomeostaticController` stub) | #65 |
| — | M5.0.a | ✅ | 🔴 | Snapshot pre-esecuzione `snap_20260426_091325_startup` | Creato da SafeProactive al primo avvio --brain |
| — | M5.0.b | ✅ | 🔴 | Validare prerequisito M4.20 chiuso | **M4.20 CHIUSO** (2026-04-26) — M5.1+ sbloccato |
| **M5A** | M5.1 | ✅ | 🟠 | `homeostasis/controller.py` `dh/dt` + setpoint statici | **25/25 test** — equazione `dh/dt = -k_r*(h-sp) + k_i*(r-h)`, Euler integration, viability score, alerts |
| M5A | M5.2 | ✅ | 🟠 | Receptors: wiring a system/CNM/DNA | **SystemReceptors**: energy←psutil, safety←PROPOSALS.md, curiosity←NeedsDriver, coherence←mesh_state, alignment←epigenome |
| M5A | M5.3 | ✅ | 🔴 | Port `consciousness_index.py` + emergenza setpoint | C-index = α*Φ_norm + β*W + γ*A; EMA tau=20 → `emergent_coherence_setpoint`; wiring `SystemReceptors.read_coherence()` → BrainIntegration |
| M5A | M5.4 | ✅ | 🟠 | `viability_score` esposto in dashboard | KPI card + drives grid + `api_status()` + `persist_cognitive_state()` in controller |
| M5A | M5.5 | ✅ | 🟠 | `motivation/value_field.py` `V_internal(s, h)` | `V_internal = Σ w_d*f_d(h_d) + ε*novelty`; gradiente ∇V; `suggest_action()`; `motivation_level` low/moderate/high/critical |
| M5A | M5.6 | ✅ | 🟠 | Φ(t) coherence (3 componenti) | `PhiComponents` (integration/differentiation/global_workspace) + `calculate_from_phi3()` + `from_brain_state()` — **22/22 PASS** (PHI-01→12) |
| M5A | M5.7 | ✅ | 🔴 | Mutazione DigitalDNA `EPI-005` (blocchi `homeostasis`, `motivation`) | `epigenome.yaml` v1.5: `homeostasis.enabled=true`, `motivation.enabled=true` |
| **M5B** | M5.8 | ✅ | 🟠 | `memory/autobiographical.py` SQLite + ops | `AutobiographicalMemory`: SQLite+FTS5, `record_cycle()`, `recall()`, `recent()`, `store()`, `metrics()`, `continuity_score()` |
| M5B | M5.9 | ✅ | 🟡 | Classificatore event vs structure + **port** `online_learner.py` | `EventClassifier` (outcome+novelty→EVENT/STRUCTURE); `SPEACEOnlineLearner` (`learn()`, `experience_replay()`, `predict()`); **39/39 PASS** (MEM-01→MEM-15) |
| M5B | M5.10 | ⬜ | 🟡 | Continuity score + test mutazione DNA simulata | #77 |
| **M5C** | M5.11 | ⬜ | 🟡 | `attention/gating.py` policy uniforme | #78 |
| M5C | M5.12 | ⬜ | 🟡 | Attention policy RL-driven (reward = ΔΦ(t)) | #79 |
| M5C | M5.13 | ⬜ | 🟢 | Diversity entropy check in benchmark (≥ 2.0 bit) | #80 |
| M5C | M5.14 | ⬜ | 🟡 | `plasticity/edge_pruning.py` conservative | #81 |
| M5C | M5.15 | ⬜ | 🟡 | Edge growth rules (sotto SafeProactive HIGH) | #82 |
| M5C | M5.16 | ⬜ | 🟢 | Plasticity log su `mesh_state.jsonl` | #83 |
| **M5D** | M5.17 | ✅ | 🟠 | `constraints/constraint_layer.py` (3 vincoli iniziali) | #84 |
| M5D | M5.18 | ✅ | 🟠 | Wiring: violazione → penalità omeostatica | #85 |
| M5D | M5.19 | ✅ | 🟠 | Test end-to-end iniezione violazione + degrado viability | #86 |
| — | M5.20 | ✅ | 🔴 | Report finale + Cognitive Autonomy Score (≥ 4/6) + proposta M6 | #87 |

**Note aggiunte:**
- M5.0 introduce il decimo comparto Cortex come *scaffold vuoto*: nessun sottosistema è attivo, ogni chiamata al controller disabilitato ritorna `viability=1.0` e `scaffold=True`. Questo isola il rischio architetturale durante il completamento di M4-CNM.
- M5.3/5.8/5.9 sono **porting selettivi** dal workspace parallelo `speaceorganismocibernetico/` (c.f. OPS.4). Accelerano la milestone di 4–8 settimane vs implementazione da zero.
- L'ordine di attivazione dei flag OFF→ON sarà: M5A prima (omeostasi+coerenza), poi M5B, poi M5C, infine M5D con ≥1 settimana di telemetria pulita alle spalle. Ogni flip richiede una proposta SafeProactive dedicata.

---

## AREA: INT — Integrazioni Esterne

> **Decisione 2026-04-24:** sia Obsidian sia Hermes Agent sono utili per SPEACE e vengono integrati come moduli opzionali (default OFF, opt-in via `epigenome.integrations.*`).

| ID | Stato | Prio | Descrizione | Criterio chiusura |
|----|-------|------|-------------|-------------------|
| INT-OBS.1 | 🔄 | 🟠 | Scaffold `cortex/integrations/obsidian_bridge.py` | Client Local REST API, default OFF |
| INT-OBS.2 | ⬜ | 🟡 | Sync bidirezionale Hippocampus ↔ vault Obsidian | MEMORY.md → note + metadati |
| INT-OBS.3 | ⬜ | 🟢 | Plugin Obsidian (TypeScript) per comandi SPEACE dall'UI | "Ask SPEACE from Obsidian" |
| INT-HRM.1 | 🔄 | 🟠 | Scaffold `cortex/integrations/hermes_adapter.py` | Wrapper, default OFF |
| INT-HRM.2 | ⬜ | 🟠 | Memoria persistente FTS5 backend per M5.6 | Sostituisce implementazione custom |
| INT-HRM.3 | ⬜ | 🟡 | Gateway multi-piattaforma (WhatsApp/Telegram → SPEACE) | Richiede approvazione SafeProactive High |
| INT-OLL.1 | ⬜ | 🟢 | Adapter Ollama standardizzato in `cortex/llm/ollama_client.py` | Usato da M5.8 (Meta-Neurone) |

**Snippet di epigenome (preparatorio, non attivo):**
```yaml
integrations:
  obsidian:
    enabled: false
    vault_path: null
    rest_api_port: 27123
  hermes:
    enabled: false
    base_url: null
    memory_db: memory/hermes.sqlite
```

---

## AREA: ORG — Agente Organismico (espansione fisica/IoT)

| ID | Stato | Prio | Descrizione | Note |
|----|-------|------|-------------|------|
| ORG.1 | ⬜ | 🟢 | **Port** `agente_organismo_core.py` da workspace parallelo | 6 `SensorType` + 5 `SurvivalLevel` |
| ORG.2 | ⬜ | 🟢 | `smfoi_step3_extended()` per push IoT | Step 3 SMFOI esteso a segnali ambientali |
| ORG.3 | ⬜ | 🟢 | Driver MQTT (Mosquitto) | Richiede Docker |
| ORG.4 | 🚫 | 🟢 | Integrazione prima telecamera/micro | Prerequisito hardware reale |

---

## AREA: OPS — Operazioni / CI / Repo

| ID | Stato | Prio | Descrizione | Note |
|----|-------|------|-------------|------|
| OPS.1 | 🔄 | 🟠 | Commit + push GitHub | Workaround `PUSH-NOW.bat` (sandbox blocca `.git/`) |
| OPS.2 | ⬜ | 🟡 | CI GitHub Actions (pytest su 3.11/3.12) | Eseguire i 74 test CNM in CI |
| OPS.3 | ⬜ | 🟢 | Badge test/coverage nel `README.md` | Dipende da OPS.2 |
| OPS.4 | ⬜ | 🟢 | Riconciliazione `SPEACE-prototipo` ↔ `speaceorganismocibernetico` | Decidere: monorepo, porting selettivo, o fork |

---

## AREA: DOC — Documentazione

| ID | Stato | Prio | Descrizione | File |
|----|-------|------|-------------|------|
| DOC.1 | ✅ | 🟠 | `references/organismic_ai_initiative/INDEX.md` (23 PDF catalogati) | — |
| DOC.2 | ✅ | 🟠 | `SPEACE-TASKS-ACTIVE.md` (questo documento) | — |
| DOC.3 | ✅ | 🟠 | `SPEACE-DESIGN-CONCETTUALE.md` | — |
| DOC.4 | 🔄 | 🟠 | `speace-prototipo.md` — Appendice F (Integrazioni esterne) | In corso |
| DOC.5 | ⬜ | 🟡 | `speace-prototipo.md` — Appendice G (Cognitive Autonomy M5) | Post-approvazione M5 |
| DOC.6 | ⬜ | 🟢 | Riconciliazione `SPEACE-Technical-Scientific-Document-v1.0` | Unire diff dei due workspace |

---

## Prossimi passi immediati

1. **M5.10 — Continuity score full**: implementazione formale in `autobiographical.py` (attuale: stub `1 - std(outcomes)`). Criterio: score dinamico multi-dimensionale (outcome + memory_type + temporal coherence).
2. **M5.4 — viability_score in dashboard**: esporre `HomeostaticController.viability_score` nel Streamlit dashboard (porta 8501).
3. **M5.6 — Φ(t) coherence 3 componenti**: estendere `ConsciousnessIndex` con 3 componenti Φ (integration, differentiation, global workspace).
4. **M5.11 — Attention gating**: `cortex/cognitive_autonomy/attention/gating.py` policy uniforme iniziale.
5. **BRN.W4 — Adapter BRN nel CNM Registry**: `discover_neurons()` per i moduli brain principali.
3. **Chiusura OPS.1** (push GitHub) tramite `PUSH-NOW.bat` lato utente — per sincronizzare su `robertodebiasespeace/tina-testbed-speace` scaffold M5 e PROPOSALS.md aggiornato.
4. **Ripresa M4.7 → M4.20** per chiudere la mesh e sbloccare M5.1+.
5. **Decisione su OPS.4** (strategia di riconciliazione dei due workspace — necessaria prima di M5.3/5.8/5.9 che sono porting).

---

*Tasks board dinamico. v1.8 — 2026-04-26 (M5.3+M5.5 COMPLETATI: ConsciousnessIndex port con EMA setpoint emergenti + wiring BrainIntegration; ValueField V_internal con gradiente ∇V e suggest_action; integrazione HC+VF+CI verificata. Prossimo: M5.7 EPI-005 + M5.8 autobiographical memory.)*

---

## AREA: M7 — DriveExecutive + Sensor Integration

> **Prerequisito critico identificato (2026-04-27):** Prima di qualsiasi integrazione sensoriale
> è obbligatorio implementare il `DriveExecutive` — il bridge causale che trasforma i drive
> omeostatici (viability, curiosity, coherence, energy, alignment) in parametri comportamentali
> effettivi. Senza questo componente i drive restano epifenomeni computazionali (dashboard theater).
>
> SafeProactive: PROP-M7-DRIVE-EXECUTIVE (PENDING_APPROVAL)

### M7.0 — DriveExecutive (OBBLIGATORIO, PRIMO)

| ID | Stato | Prio | Descrizione | Criterio chiusura |
|----|-------|------|-------------|-------------------|
| M7.01 | ⬜ | 🔴 | `drive_executive.py` — DriveExecutive + BehavioralState dataclass | BehavioralState emesso a ogni tick |
| M7.02 | ⬜ | 🔴 | `task_selector.py` — TaskSelector drive-aware (legge BehavioralState) | Task selection cambia in base a viability/curiosity |
| M7.03 | ⬜ | 🔴 | `self_repair.py` — SelfRepairTrigger (viability recovery protocol) | viability < 0.4 → sospende task, avvia recupero |
| M7.04 | ⬜ | 🔴 | Wiring SMFOI_v3.py step 4 → legge BehavioralState prima di Output Action | Step 4 modificato, test smoke pass |
| M7.05 | ⬜ | 🔴 | Test suite causale (≥ 25 test) — verifica comportamenti, non snapshot | ≥ 2 comportamenti causali dimostrati |
| M7.06 | ⬜ | 🔴 | EPI-008: `cognitive_autonomy.executive.enabled: true` | epigenome.yaml aggiornato |

**Regole causali fondamentali (da implementare in DriveExecutive):**

| Drive | Condizione | Effetto comportamentale |
|-------|------------|------------------------|
| viability | < 0.4 | `self_repair_mode=True` — sospendi task non critici, avvia recovery |
| viability | < 0.6 | `focus_shift="conserve"` — riduce parallelismo, ottimizza risorse |
| curiosity | > 0.7 | `exploration_bonus=+0.3` — genera task esplorative spontanee |
| coherence | < 0.4 | `memory_priority_boost=+0.5` — prioritizza consolidamento memoria |
| energy | < 0.3 | `planning_depth=1` — solo pianificazione superficiale |
| alignment | < 0.5 | `mutation_gate_open=False` — blocca mutazioni epigenetiche |
| Φ (phi) | > 0.7 | `max_parallel_tasks=4` — altrimenti 1-2 |

**Criterio avanzamento M7.0 → M7.1:**
Dimostrare almeno 2 comportamenti causali verificabili nei test:
1. viability scende sotto soglia → task selection cambia → registrato in AutobiographicalMemory
2. curiosity supera soglia → task esplorativa generata spontaneamente → proposta SafeProactive

### M7.1–M7.6 — Sensor Integration (BLOCCATO fino a M7.0 completato)

| ID | Stato | Prio | Descrizione | Criterio chiusura |
|----|-------|------|-------------|-------------------|
| M7.11 | ⬜ | 🟠 | `SensorHub` — gateway unificato stream sensoriali | Riceve mock stream, aggiorna WorldSnapshot |
| M7.12 | ⬜ | 🟠 | `IoT Connector` — MQTT/WebSocket bridge per dispositivi reali/simulati | Connessione a broker MQTT locale (Mosquitto) |
| M7.13 | ⬜ | 🟡 | `PerceptionModule` — pre-processing segnali → entità WorldSnapshot | Video/audio/temp → planet_state aggiornato |
| M7.14 | ⬜ | 🟡 | `SensorSimulator` — dati sintetici ambientali per test e sviluppo | 5 tipi di segnale simulato (video, audio, temp, gas, pressione) |
| M7.15 | ⬜ | 🟡 | WorldModel ← SensorHub wiring (aggiorna planet_state in real-time) | CO2/temp aggiornati da sensore → inference rieseguita |
| M7.16 | ⬜ | 🟡 | Test suite ≥ 40 test | Suite completa con SensorSimulator |
| M7.17 | ⬜ | 🟡 | EPI-009: `sensor_integration.enabled: true` | epigenome.yaml aggiornato |

---

*v1.9 — 2026-04-27: M5 COMPLETATA (6/6, 148 test), M6 COMPLETATA (6/6, 47 test, 9° comparto Cortex attivo).
EPI-006 + EPI-007 applicati. Dashboard v1.2.0. Push GitHub commit 23be94f.
M7.0 DriveExecutive inserito come prerequisito obbligatorio — PROP-M7-DRIVE-EXECUTIVE PENDING_APPROVAL.*
