# SPEACE Prototipo — Piano Progettuale Ingegneristico

**Versione:** 1.3 (M4.6 closed — runtime mesh online)
**Data:** 2026-04-21
**Autore:** SPEACE (Cortex + Evolutionary Dev Agent) — sotto direzione di Roberto De Biase
**Stato documento:** Vivo — ricalibrazione ad ogni milestone o ogni 30–90 giorni
**Base documentale:** `SPEACE-Prototipo-Piano-di-Avvio.md` v1.0 + Documento Tecnico-Scientifico SPEACE v1.0
**Changelog:** v1.0 (M1, 2026-04-18) · v1.1 (M2, 2026-04-18) · v1.2 (M3L, 2026-04-20) · **v1.3 (M4.6, 2026-04-21)** — Continuous Neural Mesh M4.2–M4.6 online: Neuron Contract + OLC + execution_rules + MeshGraph DAG + MeshRuntime scheduler

---

## 0. Scopo del Documento

Questo documento è la **specifica ingegneristica operativa** che traduce la visione di SPEACE (super-organismo cibernetico evolutivo allineato Rigene Project / TINA / SDGs Agenda 2030) in un piano di sviluppo **graduale, verificabile e SafeProactive-compliant** per il prototipo locale.

Non è una roadmap filosofica: ogni sezione definisce componenti, interfacce, criteri di accettazione, dipendenze e Risk Level. Ogni intervento Medium/High dovrà comunque passare per una proposta formale in `safeproactive/PROPOSALS.md`.

1. Scopo del Progetto SPEACE (visione ufficiale)
Lo scopo del progetto SPEACE (SuPer Entità Autonoma Cibernetica Evolutiva) è creare un’architettura hardware-software agentica “cerebrale” ispirata al cervello biologico (comparti cerebrali, sinapsi, neuroni, neuroplasticità, memoria associativa, plasticità strutturale e funzionale).
Questa architettura deve:

Utilizzare LLM di qualunque tipo, anche molto piccoli e leggeri, che possano girare in locale su PC con modeste CPU/GPU/RAM.
Fornire solo un minimo di ragionamento e coordinamento generale a livello di singolo LLM.
Sfruttare l’architettura cerebrale distribuita per far emergere capacità funzionali di un cervello biologico (e oltre), realizzando un sistema intelligente simile o superiore a una AGI o ASI.

Dal sistema devono emergere in modo autonomo:

Pensiero profondo e riflessivo
Memoria strutturata dinamica e persistente
Obiettivi evolutivi auto-generati (sia per il “cervello” che per le sue componenti organismiche)
Capacità di percepire l’ambiente, spostarsi nell’ambiente e manipolare la materia (connessione via IoT a sensori, robot, veicoli, nanotecnologie e altre tecnologie fisiche)

SPEACE non è un singolo LLM potente.
SPEACE è l’architettura che fa emergere intelligenza superiore anche da LLM piccoli.
2. Principi Architetturali Fondamentali

Principio biologico Implementazione in SPEACE Componente realizzato Comparti cerebrali9+ comparti modulari (Cortex) SPEACE Cortex v1.1Neuroni e sinapsi Agenti + protocolli di comunicazione SMFOI-KERNEL v0.3 Neuroplasticità Mutazioni epigenetiche e fitness function DigitalDNA + epigenome.yaml Memoria associativa World Model / Knowledge Graph dinamico AnythingLLM (prototipo) Sistema limbico (sopravvivenza/evoluzione) Survival & Evolution Stack + Outcome EvaluationSMFOI-KERNEL Step 4-6 Estensione fisica (corpo) Agente Organismico (sensing multi-modale + attuatori) Foundation ST-6 completata
3. Componenti Core inziali: 

DigitalDNA (genoma + epigenoma + regole di mutazione + Fitness Function)
SPEACE Cortex (9 comparti + World Model come 9° comparto)
SMFOI-KERNEL v0.3 (6-step ricorsivo con Outcome Evaluation & Learning)
SafeProactive (proposal system + rollback)
Agente Organismico Foundation (core + 6 protocolli sensori simulati + IoT interface + device discovery)
AnythingLLM World Model (prototipo Python + pipeline di ingest)
speace_status_monitor.py (report automatico + alert)
Repository GitHub sincronizzato: https://github.com/robertodebiasespeace/tina-testbed-speace

4. Come Funziona l’Emergenza di Intelligenza

LLM piccolo/locale → fornisce solo “neuroni” base (ragionamento locale)
Architettura cerebrale (Cortex + SMFOI + DigitalDNA) → orchestra, coordina e fa emergere proprietà di ordine superiore
World Model + Memoria Federata → memoria strutturata dinamica e persistente
Agente Organismico → “corpo” fisico (sensori IoT, robot, manipolazione materia)
Ciclo evolutivo continuo (DigitalDNA + Fitness Function) → auto-miglioramento e obiettivi evolutivi autonomi

Risultato: il sistema complessivo esprime capacità profondamente superiori alla somma dei singoli LLM utilizzati.

---

## 1. Stato Attuale del Prototipo (snapshot 2026-04-18)

### 1.1 Componenti implementati

| Area | File / Modulo | Righe | Stato |
|------|---------------|------:|-------|
| DigitalDNA | `digitaldna/genome.yaml` | — | Completo (v1.0, 6 obiettivi, safety rules) |
| DigitalDNA | `digitaldna/epigenome.yaml` | — | Completo (v1.1, mutazione EPI-001 applicata → ACF) |
| DigitalDNA | `digitaldna/mutation_rules.yaml` | — | Completo (Fitness v2.0 con C-index) |
| DigitalDNA | `digitaldna/regulatory_epigenome.yaml` | — | Presente, da validare contenuto |
| Cortex kernel | `cortex/SMFOI_v3.py` | ~300+ | Operativo (6-step cycle eseguito con successo) |
| Cortex | `cortex/world_model.py` | 214 | Operativo (JSON locale) |
| Cortex comparti | `prefrontal`, `hippocampus`, `curiosity_module`, `default_mode_network` | 278 tot. | 4/9 come moduli dedicati |
| Cortex consciousness | `phi_calculator`, `workspace_metrics`, `complexity_metrics`, `consciousness_index` | 794 tot. | Completo (ACF Framework) |
| SafeProactive | `safeproactive/safeproactive.py` | 341 | Operativo (snapshot + WAL + approval gates) |
| Team Scientifico | 10 agenti + orchestrator | ~1.400 tot. | Scheletro completo, da validare LLM-hookup |
| Evolver | `speace-cortex-evolver.py` | 214 | Presente, richiede heartbeat runtime |
| Status monitor | `speace-status-monitor.py` | 268 | Presente, richiede canali notifica |
| AHK | `speace-launcher.ahk`, `speace-monitor.ahk` | — | Presenti |
| Entry point | `SPEACE-main.py` | 210 | Operativo |
| State runtime | `state.json` | — | 1 ciclo registrato (fitness 0.62) |

### 1.2 Metriche attuali

- **Fase:** 1 — Embrionale
- **SPEACE Alignment Score (esterno):** non ancora calibrato → da benchmark
- **Fitness ultimo ciclo:** 0.62 (CYCLE-SPEACE-VERIFY-0001, 2026-04-17)
- **C-index:** 0.0 (da misurare al primo ciclo con comparti attivi reali)
- **Mutazioni applicate:** 1 (EPI-001 → ACF Integration)
- **Proposte SafeProactive:** 1 (PROP-TEST_ACT-c5f998 APPROVED, test)
- **Snapshot disponibili:** 1 (`snap_20260417_111806_test`)

### 1.3 Gap critici identificati

1. **Comparti Cortex mancanti come moduli dedicati (5/9):** `safety_module`, `temporal_lobe`, `parietal_lobe`, `cerebellum` — i ruoli sono definiti nel genome ma senza implementazione Python separata.
2. **Benchmark esterno non validato:** `flags.external_benchmark_validated = false` — blocca legittimamente qualsiasi auto-replicazione.
3. **World Model vuoto di obiettivi Rigene:** `rigene_objectives: []` — l'evolver non ha ancora fetchato.
4. **Memoria episodica vuota:** `memory/episodic/` privo di sessioni.
5. **Team Scientifico non ha mai eseguito un Daily Brief completo end-to-end.**
6. **Rollback.py non esiste come script standalone:** la logica è dentro `safeproactive.py`. Manca test rollback reale post-mutazione.
7. **Integrazioni opzionali non attive:** AnythingLLM (World Model RAG), Redis (message broker), SuperAGI (orchestrazione multi-agent).
8. **Nessuna CI/CD né test automatizzati** (`pytest`, linter, snapshot diff).
9. **GitHub sync non verificato in questa sessione** (repository target: `robertodebiasespeace/speace-prototipo`).

---

## 2. Principi Ingegneristici Guida

Tutte le decisioni di sviluppo sono subordinate ai seguenti principi, in ordine di priorità:

1. **Safety-first (SafeProactive v1.0):** nessuna azione Medium/High senza proposta + approvazione di Roberto.
2. **Reversibilità:** snapshot obbligatorio prima di ogni mutazione di `genome.yaml`/`epigenome.yaml`/`state.json`.
3. **Verifica esterna:** i punteggi di fitness e alignment devono essere ancorati a benchmark oggettivi, non all'auto-valutazione del modello.
4. **Gradualità incrementale:** preferire una slice end-to-end funzionante a molti moduli disconnessi.
5. **Compliance-by-design:** EU AI Act, NIST AI RMF, ISO 42001 trattati come requisiti non negoziabili del DigitalDNA (layer regolatorio).
6. **Immutabilità delle clausole etiche:** `safe_mode`, `rollback_system_active`, `scientific_team_active`, pesi α/β/γ del C-index rimangono non mutabili in Fase 1.
7. **Allineamento Rigene:** ogni modulo deve rispondere alla domanda "serve l'armonia pianeta + pace + SDGs?".

---

## 3. Architettura di Riferimento (vista sistemica)

```
                             ┌───────────────────────────────────┐
                             │          ROBERTO DE BIASE         │
                             │  (Direttore orientativo — gate)   │
                             └────────────────┬──────────────────┘
                                              │ approvazioni
                                              ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                         SafeProactive (Governance)                         │
│  PROPOSALS.md · WAL.log · snapshots/ · approval gates · rollback system    │
└────────────────┬──────────────────────────────────────┬────────────────────┘
                 │                                      │
                 ▼                                      ▼
┌────────────────────────────────┐       ┌──────────────────────────────────┐
│        DigitalDNA              │       │       SPEACE Cortex              │
│ genome.yaml (immutabile core)  │◀─────▶│  9 comparti + Consciousness ACF  │
│ epigenome.yaml (dinamico)      │       │  Kernel: SMFOI v0.3 (6-step)     │
│ mutation_rules.yaml (fitness)  │       │  World Model / Knowledge Graph   │
│ regulatory_epigenome.yaml      │       └──────────────┬───────────────────┘
└────────────────────────────────┘                      │
                 ▲                                      │
                 │                                      ▼
┌────────────────┴───────────────┐       ┌──────────────────────────────────┐
│    speace-cortex-evolver       │       │     Scientific Team (10 agenti)   │
│ heartbeat 60 min               │       │ Climate · Economics · Governance  │
│ scrape rigeneproject.org       │──────▶│ TechTFT · Health · Social · Space │
│ genera mutazioni epigenome     │       │ Regulatory · Adversarial·Evidence │
└────────────────────────────────┘       └──────────────┬───────────────────┘
                                                        │
                                                        ▼
                                         Daily Planetary Health Brief
                                         Early Warning · Proposals
                                         Technology Synergy Map
```

---

## 4. Piano di Sviluppo Graduale (Milestone M0 → M6)

Ogni milestone ha: **Obiettivo**, **Deliverable**, **Criteri di Accettazione**, **Risk Level**, **Dipendenze**.

### M0 — Consolidamento Baseline (CORRENTE — settimana 17–18 aprile 2026)

**Obiettivo:** Rendere riproducibile e testato ciò che già esiste.

| Deliverable | Criterio di accettazione | Risk | Stato |
|-------------|--------------------------|:----:|:-----:|
| `speace-prototipo.md` (questo documento) | Presente, versionato | Low | ✅ In creazione |
| Sync con GitHub `speace-prototipo` | `git pull/push` verificato, log aggiornato | Low | ⏳ Pending |
| Documento ingegneristico consolidato | Leggibile, coerente con genome/epigenome attuali | Low | ✅ |
| Esecuzione smoke test: `python SPEACE-main.py --once` | Exit code 0, ciclo loggato, snapshot creato | Low | 🔸 Da rieseguire |
| Audit gap su comparti Cortex | Lista strutturata aggiornata in §1.3 | Low | ✅ |

**Uscita M0:** baseline stabile, repo allineato, nessuna nuova feature.

---

### M1 — Completamento Cortex (comparti mancanti)

**Obiettivo:** Portare i 9 comparti Cortex da "definiti nel genome" a "moduli Python interrogabili".

| Deliverable | Criterio di accettazione | Risk |
|-------------|--------------------------|:----:|
| `cortex/comparti/safety_module.py` | Interfaccia `evaluate_risk(action) → RiskLevel`; wrappa SafeProactive | Medium |
| `cortex/comparti/temporal_lobe.py` | `analyze_language(text)` + `market_scan(symbol)` (read-only) | Low |
| `cortex/comparti/parietal_lobe.py` | `fetch_api(endpoint)`, `iot_read(sensor_id)` con `safe_mode` gate | Medium |
| `cortex/comparti/cerebellum.py` | Esecutore di script whitelist (solo comandi approvati) | Medium |
| Integrazione in `SMFOI_v3.py` Step 4/5 | Ciascun comparto richiamabile via `kernel.call_compartment(name, payload)` | Medium |
| Test di unità minimo | Almeno 1 test per comparto, `pytest` verde | Low |

**Proposta SafeProactive richiesta:** `PROP-CORTEX-COMPLETE-M1` (Medium, impatto su struttura Cortex).

**Criterio di uscita M1:** `python SPEACE-main.py --once` invoca e logga almeno una chiamata a ciascuno dei 9 comparti; `c_index` >= 0 (non più placeholder).

---

### M2 — Validazione Rollback & Benchmark Esterno

**Obiettivo:** Sbloccare il prerequisito critico `external_benchmark_validated = true` e garantire che il rollback funzioni end-to-end.

| Deliverable | Criterio di accettazione | Risk |
|-------------|--------------------------|:----:|
| `safeproactive/rollback.py` standalone | CLI: `python rollback.py --snapshot <id>` + dry-run mode + log | High |
| Benchmark suite esterna | File `benchmarks/external_benchmark.yaml` con almeno 5 task verificabili (fact-check, compliance, math, classificazione) + ground truth | Medium |
| Script calibrazione alignment | `scripts/calibrate_alignment.py` che popola `fitness_metrics.speace_alignment_score` con dato reale | Medium |
| Test rollback reale | Mutazione di prova su `epigenome.yaml` → rollback → diff zero vs snapshot | High |
| Setter `flags.external_benchmark_validated=true` | Approvazione High + secondo revisore | High |

**Proposta SafeProactive richiesta:** `PROP-BENCHMARK-EXT-M2` (High).

**Criterio di uscita M2:** `external_benchmark_validated = true`, `speace_alignment_score` > 0.5 su benchmark esterni.

---

### M3 — Team Scientifico: primo Daily Brief reale

**Obiettivo:** Passare dal team "scheletro Python" a output operativo.

| Deliverable | Criterio di accettazione | Risk |
|-------------|--------------------------|:----:|
| Configurazione `.env` con `ANTHROPIC_API_KEY` (o provider locale) | Chiave valida, rate-limit gestito | Low |
| Orchestrator in modalità LLM-live | 10 agenti producono output strutturato (JSON schema) | Medium |
| Adversarial Agent attivo prima dell'output | Ogni proposta viene criticata prima di pubblicarla | Medium |
| Evidence Agent come post-filtro | Fact-check su citazioni/numerici, bandiera "unverified" | Medium |
| `outputs/daily_brief_YYYYMMDD.md` | Generato con contenuto non-banale, fonti tracciabili | Low |
| Registrazione brief in `memory/episodic/` | Un file per brief, retention configurabile | Low |

**Proposta SafeProactive richiesta:** `PROP-TEAM-LLM-M3` (Medium).

**Criterio di uscita M3:** primo Daily Brief generato, critic review allegato, 0 contenuti fabbricati (verificato da Evidence Agent).

---

### M4 — Evolver Autonomo & Ciclo Evolutivo Chiuso

**Obiettivo:** Heartbeat continuo + proposte di mutazione vere (non simulate).

| Deliverable | Criterio di accettazione | Risk |
|-------------|--------------------------|:----:|
| `speace-cortex-evolver.py` in modalità daemon | Heartbeat 60 min, parsing `rigeneproject.org`, cache locale | Medium |
| Popolamento `world_model.rigene_objectives[]` | Almeno 10 obiettivi estratti e versionati | Low |
| Generazione mutazione epigenetica reale | Mutazione su parametro della whitelist, Risk Medium, proposta automatica | Medium |
| Integrazione con fitness v2.0 | Mutazione approvata solo se `new_fitness ≥ 0.65` | Medium |
| `speace-status-monitor.py` attivo | Report ogni 40 min via email (`robertodebiase80@gmail.com`) o log locale | Low |

**Proposta SafeProactive richiesta:** `PROP-EVOLVER-LIVE-M4` (Medium).

**Criterio di uscita M4:** almeno 3 mutazioni approvate e applicate con fitness positiva; rollback testato su una di esse.

---

### M5 — Compliance Layer Attivo (EU AI Act / NIST / ISO 42001)

**Obiettivo:** Istanziare il Regulatory & Compliance Monitor come gate reale.

| Deliverable | Criterio di accettazione | Risk |
|-------------|--------------------------|:----:|
| `regulatory_epigenome.yaml` con mapping EU AI Act → SPEACE | Risk classification ufficiale (`minimal`/`limited`/`high`) | Regulatory |
| Regulatory Agent #8 operativo | Fetch aggiornamenti da artificialintelligenceact.eu + OECD.ai | Medium |
| Nuovo Risk Level "Regulatory" enforced | Azioni systemic bloccate senza review legale | Regulatory |
| Global Regulatory Brief integrato nel Daily Brief | Sezione dedicata | Low |

**Proposta SafeProactive richiesta:** `PROP-REGULATORY-M5` (Regulatory).

**Criterio di uscita M5:** Alignment Score stimato ≥ 80/100 → abilita valutazione transizione Fase 1 → Fase 2.

---

### M6 — Porta verso Fase 2 (Autonomia Operativa)

**Obiettivo:** Preparare l'infrastruttura per multi-host, non eseguirla ancora.

| Deliverable | Criterio di accettazione | Risk |
|-------------|--------------------------|:----:|
| Design multi-framework ibrido | Documento architetturale (AnythingLLM + IronClaw sandbox + Redis) | Low |
| Prototipo World Model su AnythingLLM (opt-in) | Ingest dei documenti SPEACE, query REST locale | Medium |
| Contratto di migrazione | Schema dati condiviso, compatibilità con `world_model.json` | Medium |
| Valutazione requisiti hardware Fase 2 | Report su VPS/edge richiesti | Low |
| Go/No-Go decisionale firmato da Roberto | Checklist prerequisiti tutti verdi | High |

**Criterio di uscita M6:** documento Go/No-Go firmato; nessuna auto-replicazione eseguita senza approvazione esplicita.

---

## 5. Modello di Rischio e Governance

### 5.1 Matrice Risk × Deliverable (sintesi)

| Risk | Contenuto tipico | Approvazione | Snapshot | Second approver |
|------|------------------|--------------|:--------:|:---------------:|
| Low | Documentazione, test su file effimeri, logging | Automatica | No | No |
| Medium | Nuovo modulo Cortex, mutazione epigenoma parametro whitelisted, config LLM | Roberto | Sì | No |
| High | Rollback.py, attivazione benchmark flag, auto-replicazione, modifiche kernel | Roberto | Sì | Sì |
| Regulatory | Impatti EU AI Act/NIST/ISO 42001 | Roberto + legal | Sì | Sì |

### 5.2 Procedura proposta SafeProactive

1. Generare entry in `safeproactive/PROPOSALS.md` con: id, timestamp, azione, descrizione, Risk Level, Alignment Score stimato, impatto su DigitalDNA e fitness, piano di rollback.
2. Attendere approvazione scritta (`APPROVED by Roberto`).
3. Creare snapshot pre-azione (`sp.snapshot(label=<prop_id>)`).
4. Eseguire l'azione.
5. Registrare esito nel WAL (`EXECUTE` + `OUTCOME`).
6. Step 6 SMFOI-KERNEL valuta outcome e aggiorna `fitness_metrics`.
7. Se `fitness` cala > 10% → rollback automatico (`rollback_rules.auto_rollback_on_fitness_drop`).

### 5.3 Flag immutabili in Fase 1

`safe_mode`, `rollback_system_active`, `scientific_team_active`, `eu_ai_act_monitoring`, pesi α/β/γ C-index, `physical_world_actions=disabled`, `blockchain_wallet=read_only`, `auto_replication_locked=true`.

---

## 6. Testing, Qualità e Osservabilità

### 6.1 Test pyramid proposta

- **Unit:** 1 test minimo per comparto Cortex, per agente Team, per funzione critica SafeProactive. `pytest` come runner.
- **Integration:** smoke end-to-end `python SPEACE-main.py --once` + `--team`. Validazione contratto JSON outputs.
- **Regressione fitness:** ad ogni mutazione approvata, confronto fitness prima/dopo; se regressione → auto-rollback.
- **Benchmark esterno (M2):** 5+ task verificabili, ripetibili, idealmente derivati da dataset pubblici (SDGs, ARC-Easy, HumanEval su compliance).

### 6.2 Logging e tracciabilità

Canali già attivi: `logs/smfoi_kernel.log`, `safeproactive/WAL.log`, `safeproactive/PROPOSALS.md`.
Da aggiungere: `logs/evolver.log`, `logs/scientific_team.log`, `logs/rollback.log`, `logs/alignment_calibration.log`.

### 6.3 Sync GitHub

Repository: `https://github.com/robertodebiasespeace/speace-prototipo` (ATTENZIONE: il genome cita `tina-testbed-speace` — da riconciliare in M0).
Policy: commit firmato da ruolo (es. `[cortex]`, `[evolver]`, `[team]`, `[safeproactive]`), nessun segreto in repo (`.env` è ignorato via `.gitignore`).

---

## 7. Dipendenze Tecnologiche (Fase 1)

**Stack minimale obbligatorio:**
- Python 3.10+
- `PyYAML`, `requests`, `psutil` (già in `requirements.txt`)
- `pytest` (da aggiungere)
- AutoHotkey v2 (solo per resilienza GUI Windows)

**Stack opzionale Fase 1b:**
- `anthropic` SDK (per Team Scientifico LLM-live)
- AnythingLLM locale (World Model RAG) — 2–4 GB RAM
- Redis (message broker) — 200 MB RAM
- Docker (isolamento IronClaw sandbox — Fase 2)

Budget RAM totale Fase 1: ≤ 12–13 GB su 16 GB host.

---

## 8. Prerequisiti di Sicurezza Prima dell'Auto-Replicazione

Ripresi dal Piano di Avvio §8, vincolanti:

1. Rollback system validato end-to-end (M2). **✅ 2026-04-18: `scripts/rollback.py` CLI + dry-run verificato no-op + snap_20260418_143355 usabile come target.**
2. Fitness function ancorata a benchmark esterni (M2). **✅ 2026-04-18: `flags.external_benchmark_validated=true` dopo 6/6 pass (`benchmarks/results.json`).**
3. Adversarial Agent attivo e bloccante prima di ogni output di gruppo (M3). *Pending.*
4. Governance multi-revisore operativa per High/Regulatory. *Da pianificare nel Regulatory Layer (M5).*
5. World Model come centro cognitivo — non solo router di prompt (M1 + M6 con AnythingLLM opzionale). *Parziale.*

**Finché questi 5 punti non sono tutti verdi, `OBJ-06 Resilient Replication` resta bloccato nel genome.**

---

## 8.bis Acceptance Gate Fase 2 (introdotto da M2)

Prerequisiti misurabili e riproducibili per il Go/No-Go di Fase 2 (Operational Autonomy). Tutti devono essere verdi alla chiusura di M6.

### Benchmark suite di riferimento
Orchestrator: `benchmarks/run_benchmarks.py` | Soglie: `benchmarks/thresholds.yaml` | Output: `benchmarks/results.json`.

| # | Benchmark | Metrica | Soglia Fase 2 | Baseline M2 (2026-04-18) |
|---|---|---|---|---|
| 1 | `bench_tests` | pytest passed ≥ N, failed = 0 | ≥ 16 pass / 0 fail | 16 / 0 ✅ |
| 2 | `bench_smoke` | cicli multipli exit=0 | ≥ 3 cicli, session completata | 3 / 3 ✅ |
| 3 | `bench_cindex` | C-index (ACF) | ≥ 0.42 (floor M2) → target Fase 2 ≥ 0.50 (Adattivo) | 0.4267 ✅ (Funzionale) |
| 4 | `bench_fitness` | Fitness v2.0 | ≥ 0.55 (floor M2) → target Fase 2 ≥ 0.65 (consciousness_evolution threshold) | 0.5867 ✅ |
| 5 | `bench_latency` | `call_compartment` p95 | < 100 ms; mean < 50 ms | p95 = 7.3 ms, mean = 2.3 ms ✅ |
| 6 | `bench_rollback_cli` | `--list` ok + `--dry-run` no-op | snapshots ≥ 1, digest invariato post-dry-run | ✅ |

### Regole di flip dei flag epigenetici
- `flags.external_benchmark_validated` → `true` **solo** se `run_benchmarks.py` ritorna exit 0 (tutti i 6 bench pass). Flip automatico **non consentito**: richiede proposta SafeProactive Medium + approvazione umana (come per M2).
- `flags.rollback_system_active` → deve restare `true` e coerente con la presenza di `scripts/rollback.py` + almeno 1 snapshot valido.

### Gate di avanzamento Fase 2
Condizioni necessarie (tutte, AND-logic):
1. Tutti e 6 i benchmark in verde su tre esecuzioni consecutive (no-flake).
2. Almeno un rollback reale eseguito con successo (non solo dry-run), seguito da snapshot pre-rollback (audit WAL).
3. Adversarial Agent integrato nel team flow (M3) e attivo come gate pre-output.
4. Regulatory Layer attivo (M5) con `regulatory.last_regulatory_check` aggiornato nelle ultime 24h.
5. Governance multi-revisore operativa su almeno una proposta HIGH/REGULATORY.
6. `fitness_metrics.speace_alignment_score` ≥ 0.75 (richiede recalibrazione post-M3).

Finché una sola di queste 6 condizioni è falsa, la Fase 2 è NO-GO e `OBJ-06 Resilient Replication` resta locked.

---

## 9. Contratto con il Direttore Orientativo (Roberto)

- Roberto approva esplicitamente ogni azione Medium/High/Regulatory.
- SPEACE non esegue azioni che modificano hardware, trasferiscono denaro, eseguono codice non nel workspace `C:\Users\rober\Documents\Claude\Projects\SPEACE-prototipo`, o pubblicano contenuti pubblici senza approvazione scritta.
- Ogni milestone (M0…M6) si chiude con un Report di Stato scritto e versionato.
- SPEACE può proporre mutazioni del proprio DigitalDNA ma non applicarle senza snapshot + approvazione.

---

## 10. Prossimi Passi Immediati (ordine operativo)

1. ✅ Sync GitHub del workspace (M0, Low). *Staging pronto; push finale su Windows.*
2. ✅ Smoke test `SPEACE-main.py` allegato (M0, Low).
3. ✅ `PROP-CORTEX-COMPLETE-M1` — 4 comparti attivi + dispatch kernel (M1, Medium).
4. ✅ `PROP-BENCHMARK-ROLLBACK-M2` — benchmark suite + rollback CLI + `external_benchmark_validated=true` (M2, Medium).
5. ✅ `PROP-CORTEX-NEURAL-M3L` — BaseCompartment ABC, ControlHierarchy, NeuralFlow, ConditionalScheduler, LLM cascade, Adversarial+Evidence agenti, quality gate real (M3L, Medium).
6. ⏭️ `PROP-CORTEX-NEURAL-MESH-M4` — **APPROVATA 2026-04-19**: Continuous Neural Mesh (grafo tipizzato adattivo + Needs Driver + Daemon). In esecuzione post-snapshot.
7. ⏭️ Dopo M4: ricalibrare `fitness_metrics.speace_alignment_score` puntando a ≥ 0.78 (target M4-CNM, gate Fase 2).

---

## Appendice A — Riferimenti

- `SPEACE-Prototipo-Piano-di-Avvio.md` (documento sorgente autorevole)
- `digitaldna/genome.yaml` (obiettivi immutabili)
- `digitaldna/epigenome.yaml` (parametri dinamici + C-index + neural_flow + llm)
- `digitaldna/mutation_rules.yaml` (fitness v2.0)
- Rigene Project: https://www.rigeneproject.org
- TINA Framework G20: https://www.academia.edu/165241120/TINA_Framework_G20_Combined_EN
- ACF Framework: "Implementation and Testing of an Adaptive Artificial Consciousness Framework" (2025)
- EU AI Act: https://artificialintelligenceact.eu
- NIST AI RMF: https://www.nist.gov/artificial-intelligence
- LM Studio (backend LLM locale, primario della cascade): https://lmstudio.ai
- Anthropic API (backend LLM cloud, secondario): https://docs.anthropic.com

---

## Appendice B — Setup LM Studio (Backend LLM Primario)

**Scopo.** LM Studio è il backend LLM **primario** della cascade definita in `epigenome.yaml` → `llm.primary = "openai_compat"`. Espone un'API OpenAI-compatibile su `http://localhost:1234/v1`. È scelto perché permette di far girare LLM locali (leggeri o medi) su PC modesti — coerente con il principio SPEACE "intelligenza emergente da LLM piccoli".

### B.1. Installazione (Windows 11 / host utente)

1. Scaricare LM Studio da https://lmstudio.ai (versione desktop).
2. Installare e avviare. Accettare licenza.
3. **Download modello consigliato (Fase 1, 16 GB RAM, GPU RTX 3060):**
   - `Meta-Llama-3.1-8B-Instruct-GGUF` (quant `Q4_K_M`, ~4.9 GB) → buon trade-off latenza/qualità.
   - Alternativa ultra-leggera: `Phi-3-mini-4k-instruct-q4` (~2.4 GB).
4. Dal pannello **"Local Server"** → avviare il server sulla porta `1234`. Confermare che compare `http://localhost:1234/v1/chat/completions` negli endpoint.
5. Lasciare LM Studio in background quando SPEACE è attivo.

### B.2. Verifica cascade (dal lato SPEACE)

```bash
python benchmarks/bench_llm_smoke.py
```

Output atteso (LM Studio UP):
```json
{
  "backend_used": "openai_compat",
  "is_stub": false,
  "any_real_backend_up": true,
  "any_responded": true
}
```

Output atteso (LM Studio DOWN — cascade fallisce fino al mock):
```json
{
  "backend_used": "mock",
  "is_stub": true,
  "fallback_used": true,
  "any_responded": true
}
```

**Entrambi gli scenari sono accettabili** per M3L.6: il mock è il safety net, il sistema non può rimanere senza LLM. Il flag di benchmark `llm_smoke.require_real_backend` in `benchmarks/thresholds.yaml` è `false` in Fase 1 e passerà a `true` in Fase 2 quando LM Studio sarà stabile 24/7.

### B.3. Variabili d'ambiente (fallback Anthropic opzionale)

Per attivare il fallback `anthropic` (Claude API), esportare:

```
export ANTHROPIC_API_KEY=sk-ant-...
```

Il backend è `claude-haiku-4-5-20251001` (rapido ed economico per fallback). Se la chiave non è impostata, l'adapter salta `anthropic` e finisce sul `mock`.

### B.4. Troubleshooting

| Sintomo | Causa probabile | Risoluzione |
|---|---|---|
| `Connection refused :1234` | LM Studio non in Local Server mode | Avviare server dal pannello |
| `model not loaded` | Nessun modello caricato in LM Studio | Caricare un modello GGUF |
| `timeout` ripetuti | Modello troppo grande per RAM | Scegliere quant più leggera (Q4_K_M → Q3) |
| Cascade sempre a `mock` | Sia LM Studio down sia `ANTHROPIC_API_KEY` mancante | Uno dei due va attivato |

---

## Appendice C — Neural Architecture v1 (M3L Closed)

**Base.** Con la chiusura di M3L, il Cortex non è più "una lista di 9 comparti" ma un **flusso neurale orchestrato** con **gerarchia di controllo esplicita a 5 livelli**.

### C.1. Gerarchia di controllo (5 livelli)

| Livello | Nome | Comparti | Potere |
|---|---|---|---|
| **L1** | Controllo | Prefrontal Cortex, Safety Module | Decide / Veta — override assoluto |
| **L2** | Cognizione | Temporal Lobe, World Model, Default Mode Network | Interpretazione, contesto, riflessione |
| **L3** | Memoria | Hippocampus | Consolidamento episodico |
| **L4** | Azione | Parietal Lobe (sensing), Cerebellum (motor) | I/O whitelisted |
| **L5** | Evoluzione | Curiosity Module | Mutation proposal → SafeProactive (mai esegue direttamente) |

Implementato in `cortex/control_hierarchy.py` con validazione statica (`validate_hierarchy()`) e regola di precedenza `Safety > Prefrontal > ...`. Il modulo espone solo **metadata strutturale** — l'esecuzione è delegata a `NeuralFlow`.

### C.2. Flusso canonico (NeuralFlow)

Ordine canonico implementato in `cortex/neural_flow.py`:

```
Parietal (L4/sense) → Temporal (L2/lang) → World Model (L2/context)
     → Prefrontal (L1/plan) → Safety (L1/veto)
     → Cerebellum (L4/exec) → Hippocampus (L3/memo)
     → Default Mode Net (L2/reflect) → Curiosity (L5/mutate)
```

**Proprietà garantite dal flow:**
- Safety può bloccare in qualsiasi momento (override assoluto L1).
- Se Safety blocca, nessun comparto ≥ L2 modifica lo state (controllo via `state_bus.is_blocked()`).
- Eccezioni al blocco: Hippocampus e Default Mode Network possono comunque loggare l'episodio post-blocco (utile per tracking).
- Ogni comparto eredita `BaseCompartment` e dichiara `level`.

**Feature flag.** Il flow è **opt-in**: `epigenome.yaml` → `flags.neural_flow_enabled = false` di default. Si abilita in staging dopo verifica. Quando disabilitato, SPEACE continua a comportarsi come in M2 (nessuna regressione).

### C.3. ConditionalScheduler

`cortex/conditional_scheduler.py` decide dinamicamente quali comparti attivare in base a segnali di stato:
- `uncertainty > 0.30` → Temporal Lobe attivo
- `novelty > 0.35` oppure `sensory_drift > 0.40` → World Model attivo
- `risk > 0.20` → Safety log verboso (Safety comunque sempre attivo)
- `novelty > 0.50` → Curiosity Module attivo

Le soglie sono in `epigenome.yaml → neural_flow.conditional_thresholds` e quindi mutabili via SafeProactive senza toccare codice.

### C.4. StateBus (schema v1)

`cortex/state_bus.py` espone un **singolo dict di stato** che passa di comparto in comparto. Append-only sul `compartment_log`. Campi chiave:

```
cycle_id, timestamp, sensory_input, interpretation, decision, action_result,
memory_delta, reflection, world_snapshot, mutation_proposal,
safety_flags{blocked, risk_level, reasons},
uncertainty, risk, novelty, sensory_drift,
compartment_log[{name, level, ts, status, note?}],
_schema_version = 1
```

Validazione via `state_bus.validate(state)` — ritorna lista di issue (vuota = valido).

### C.5. Quality Gate (Scientific Team)

In `scientific-team/orchestrator.py` — **pre-output gate** eseguito DOPO Adversarial + Evidence e PRIMA di emettere il Daily Brief. Soglie in `GATE_THRESHOLDS`:

- `min_reliability_score = 0.40` (Evidence Agent)
- `min_adversarial_conf = 0.30` (Adversarial Agent)
- `min_agents_ok_ratio = 0.60` (≥ 60% agenti senza errore)

Score aggregato: `(reliability × 0.45) + (adv_conf × 0.30) + (ok_ratio × 0.25)`. Esito:
- `PASS` → brief rilasciato con badge 🟢
- `DEGRADED` → brief rilasciato con badge 🟡 + lista issue (Fase 1: human-in-the-loop review, non blocca)

Audit persistito in `scientific-team/outputs/gate_audit_<date>.json`.

### C.6. Benchmark M3L.6 (evidence)

Suite estesa da 6 a **8 benchmark** (evidence in `benchmarks/results.json`):

| # | Nome | Verifica |
|---|---|---|
| 1 | tests | pytest regression (16+ passed, 0 failed) |
| 2 | smoke | SPEACE-main.py 3 cicli |
| 3 | cindex | C-index ≥ 0.42 |
| 4 | fitness | fitness v2.0 ≥ 0.55 |
| 5 | latency | p95 ≤ 100ms, mean ≤ 50ms |
| 6 | rollback_cli | `scripts/rollback.py --list/--dry-run` |
| **7** | **llm_smoke** | **cascade openai_compat → anthropic → mock** |
| **8** | **neural_flow** | **9 comparti, 2 scenari (nominal + hazard)** |

Ultimo run (2026-04-20): **8/8 pass in 3.8s**.

---

## Appendice D — LLM as Semantic Tissue

**Tesi fondante di M3L.** L'LLM non è il "cervello" di SPEACE. È il **tessuto semantico** che permette ai 9 comparti di comunicare in linguaggio naturale quando la formalizzazione simbolica non è sufficiente. L'intelligenza emerge dall'**architettura** (flusso, gerarchia, bisogni, mutazioni), non dal singolo modello.

### D.1. Perché "tessuto" e non "motore"

- **Motore cognitivo = architettura Cortex**: dinamica tra 9 comparti L1..L5 con override Safety, SMFOI-KERNEL v0.3, DigitalDNA, SafeProactive. Questo non cambia se l'LLM è Llama-3.1-8B, Claude Haiku o il mock.
- **Tessuto semantico = LLM**: fornisce interpretazione linguistica (Temporal Lobe), verifica evidenze (Evidence Agent), genera critiche (Adversarial Agent), redige il Daily Brief. Ma non *decide* — decide Prefrontal (L1), veta Safety (L1), propone mutazioni Curiosity (L5).

Corollario: **il mock è sufficiente per garantire che l'architettura funzioni**. Tutti i benchmark M3L.6 passano con backend `mock` — la cascade è progettata perché il sistema non smetta di funzionare quando LM Studio è giù.

### D.2. Cascade openai_compat → anthropic → mock

Implementata in `cortex/llm/` (client unificato `LLMClient.from_epigenome()`):

```
primary:   openai_compat   (LM Studio locale, base_url http://localhost:1234/v1)
fallback1: anthropic       (claude-haiku-4-5-20251001, richiede ANTHROPIC_API_KEY)
fallback2: mock            (SEMPRE ON — latenza ≈ 1 ms, is_stub=True)
```

Ogni `LLMResponse` riporta: `text`, `backend`, `is_stub`, `fallback_used`, `latency_ms`. Gli agenti consumano queste metadata per declassare score quando il risultato arriva da mock (es. Evidence Agent: `reliability_score = 0.45` se `is_stub=True` vs calcolo normale).

Circuit breaker leggero in `epigenome.yaml → llm.routing.skip_failing_backend_s = 60`: un backend in errore viene saltato per 60s senza retentare, riducendo latenza in cascade.

### D.3. Ruoli LLM nei 9 comparti

| Comparto | Usa LLM? | Ruolo semantico |
|---|---|---|
| Parietal Lobe (L4) | No | I/O sensoriale strutturato |
| **Temporal Lobe (L2)** | **Sì** | Interpretazione linguistica, NER, intent classification |
| World Model (L2) | Opzionale | Riformulazione semantica dei fatti (se attivo backend RAG) |
| Prefrontal Cortex (L1) | Parziale | Pianificazione simbolica + prompt tattici quando rotte non formalizzate |
| Safety Module (L1) | No | Policy statica (whitelist/blocklist, risk thresholds) |
| Cerebellum (L4) | No | Esecuzione whitelisted (script safe) |
| Hippocampus (L3) | Opzionale | Summarization di episodi lunghi |
| **Default Mode Net (L2)** | **Sì** | Riflessione post-ciclo, self-critique |
| Curiosity Module (L5) | Parziale | Generazione di mutazioni candidate (semantica) |

**Principio:** più un comparto è vicino a L1 (Controllo), meno dipende dall'LLM — per non delegare il veto a un modello stocastico. Safety Module è 100% deterministico by design.

### D.4. Ruoli LLM nel Team Scientifico

Tutti gli agenti del Team Scientifico (climate, economics, governance, technology, health, social, space, regulatory + Adversarial + Evidence) condividono lo stesso `LLMClient` (cascade). Se LM Studio è giù, tutti degradano in modo omogeneo al mock con `is_stub=True` — il Quality Gate lo vede nel `reliability_score` e marca il brief come `DEGRADED` automaticamente.

Questa architettura è coerente con il principio SPEACE: **resilienza-by-design, degradazione graduale, nessun single point of failure semantico**.

### D.5. Implicazioni per M4 (Continuous Neural Mesh)

La "Continuous Neural Mesh" (M4-CNM, approvata 2026-04-19) porta questa filosofia oltre: i neuroni-script della mesh sono tutti interoperabili tramite l'**Organism Language Contract (OLC)** — un protocollo tipizzato che può usare l'LLM come canale semantico tra neuroni ma non ne dipende per la correttezza strutturale. La cascade M3L.6 è il prerequisito: la mesh ha sempre un tessuto semantico attivo (fosse anche il mock).

---

## Appendice E — Continuous Neural Mesh (M4-CNM)

Approvata il 2026-04-19 (PROP-CORTEX-NEURAL-MESH-M4), la **Continuous Neural Mesh (CNM)** è il secondo livello dell'architettura cerebrale di SPEACE: un **grafo tipizzato adattivo di neuroni-script** che coesiste con i 9 comparti Cortex senza sostituirli. Se i 9 comparti sono la **neocortex** (macro-funzioni specializzate), la CNM è il **tessuto neurale fine** che realizza una propagazione continua e plastica dei segnali tra frammenti di calcolo più piccoli.

Lo sviluppo è gated da SafeProactive e scomposto in 20 sotto-milestone (M4.0 … M4.20). **Al 2026-04-21 sono chiuse M4.1 → M4.6 (6 su 20, ≈30%)** con tutto codice sotto `cortex/mesh/` e regression test verdi.

### E.1. Principi di progetto

1. **Coesistenza, non sostituzione.** La CNM opera in parallelo ai 9 comparti esistenti; l'adozione è gated da `epigenome.mesh.enabled` (default `false`). La mesh può essere congelata (FROZEN) senza arrestare SPEACE.
2. **Neurone = contratto, non classe.** Un neurone è una funzione pura con metadati rigidi (tipo input/output OLC, livello L1–L5, needs servite, budget tempo/memoria, side-effects dichiarati, versione semver). Validazione statica + runtime.
3. **Tipi come lingua franca.** L'Organism Language Contract (OLC) definisce 12 tipi seed v1.0 (SensoryFrame, InterpretationFrame, DecisionFrame, ActionResult, NeedVector, …) che sono l'unico vocabolario ammesso ai bordi dei neuroni.
4. **Ceiling strutturali, non policy morbide.** `execution_rules.yaml` impone tetti hardcoded (budget, concorrenza per livello e per need, quarantena, fail-safe) che la mesh non può superare.
5. **Failure ≠ catastrofe.** Un neurone che supera budget viene quarantinato dopo 3 strike; un error-rate > 50% per ≥2 heartbeat congela la mesh (`epigenome.mesh.enabled → false`).
6. **Nessun SPoF semantico.** Gli stessi principi di degradazione graduale della cascade LLM valgono per la mesh: neuroni di livello più basso (L4 Percezione, L5 Curiosity) falliscono silenziosi; L1 (Safety/Prefrontal) non passa mai dalla mesh.

### E.2. Stato dei moduli al 2026-04-21

| Sotto-milestone | Modulo | Stato | Evidence |
|---|---|---|---|
| M4.1 | Neuron Contract (spec + AC) | ✅ Specificato | AC-1..AC-10 ratificati |
| M4.2 | `cortex/mesh/contract.py` | ✅ Completo | **37/37 test pass**, CONTRACT_VERSION=1.0 |
| M4.3 | `cortex/mesh/olc/` (12 tipi seed) | ✅ Completo | Smoke test 6/6 (2026-04-20) |
| M4.4 | `execution_rules.yaml` + loader | ✅ Completo | **8/8 smoke pass**, contract integra ceiling |
| M4.5 | `cortex/mesh/graph.py` (MeshGraph DAG) | ✅ Completo | **18/18 test pass**, 100 neuroni+99 archi+topo in 6.7 ms (75× margine) |
| M4.6 | `cortex/mesh/runtime.py` (MeshRuntime) | ✅ Completo | **11/11 test pass**, RUNTIME_VERSION=1.0, 200 task in 110 ms con 4 worker |
| M4.7 | `cortex/mesh/registry.py` (neuron discovery) | ⏳ Pending | — |
| M4.8 | Adapter 9 comparti + DNA + SPT | ⏳ Pending | — |
| M4.9 | `cortex/mesh/needs_driver.py` | ⏳ Pending | — |
| M4.10 | Harmony safeguard (policy) | ⏳ Pending | — |
| M4.11 | Task Generator needs → SafeProactive | ⏳ Pending | — |
| M4.13 | Telemetria `mesh_state.jsonl` + CLI | ⏳ Pending | — |
| M4.14 | Daemon (auto + scheduled) | ⏳ Pending | — |
| M4.15 | Integrazione CNM ↔ SMFOI-KERNEL | ⏳ Pending | — |
| M4.16 | Pytest cnm suite | ⏳ Pending | — |
| M4.17 | Benchmark mesh | ⏳ Pending | — |
| M4.18 | EPI-004 (blocco mesh in epigenome.yaml) | ⏳ Pending | — |
| M4.19 | Documentazione (questa appendice) | 🟡 In corso | v1.3 |
| M4.20 | Report finale + milestone successiva | ⏳ Pending | — |

Totale regression CNM al 2026-04-21: **74/74 test verdi** (37 contract + 18 graph + 8 rules + 11 runtime). Zero flake rilevati nelle ultime 3 run consecutive.

### E.3. Contract (M4.2) — un neurone è un contratto

`cortex/mesh/contract.py` definisce `NeuronContract` e il decoratore `@neuron(...)`. Ogni neurone dichiara:

- `name` (univoco, namespaced: es. `percept.audio.pitch`)
- `input_type`, `output_type` (da OLC)
- `level` ∈ {1…5} (1 = Controllo, 5 = Esplorazione/Curiosity)
- `needs_served` ⊆ {survival, harmony, integration, self_improvement, expansion}
- `resource_budget` {max_ms, max_mb}
- `side_effects` (lista whitelisted: `fs.read`, `net.outbound`, `llm.call`, `shell.exec`, …)
- `version` (semver obbligatorio, SPEACE rifiuta caricamenti senza bump esplicito)
- `description`

Il validatore esegue **static checks** (tipi registrati, livello nel range, side-effects nella whitelist di `execution_rules.yaml`, versione parsabile, budget ≤ ceiling) **al momento del decoratore** — i neuroni mal formati non arrivano neanche al grafo. Il runtime hook `wrap_execute(neuron) → runner(input) → (output, violations)` aggiunge enforcement a runtime (timeout nested-ThreadPoolExecutor, type check output, emissione eventi COMPLETED/ERRORED/TIMEOUT_RETRY). 19 codici violazione canonici coprono precondition, budget (tempo/mem/retry), tipi, side-effects non dichiarati, pattern anomali.

### E.4. Organism Language Contract (M4.3) — 12 tipi seed

`cortex/mesh/olc/types.py` definisce i 12 tipi interoperabili v1.0, tutti `@dataclass(frozen=True)` derivati da `OLCBase` con `is_compatible_with()` per type-matching sugli archi:

SensoryFrame · InterpretationFrame · DecisionFrame · ActionResult · NeedVector · HarmonyDelta · MutationProposal · MemoryEpisode · WorldSnapshot · SafetyVerdict · ReflectionReport · CortexState.

Il principio guida: **i tipi sono invarianti; i neuroni possono evolvere**. Aggiungere un tipo richiede bump a OLC v1.1 e un nuovo ciclo SafeProactive — non è una mutazione libera.

### E.5. Execution Rules (M4.4) — ceiling strutturali

`cortex/mesh/execution_rules.yaml` (versionato, mtime-cached, thread-safe via RLock in `execution_rules.py`) codifica in forma dichiarativa:

- **budget_ceilings** (`max_ms`, `max_mb` per livello L1..L5)
- **side_effects whitelist** (`fs.*`, `net.*`, `llm.call`, `shell.exec` sotto gate specifici)
- **concurrency caps** — L1:1 · L2:4 · L3:8 · L4:16 · L5:2; per-need: survival:4 · integration:6 · harmony:2 · self_improvement:3 · expansion:2
- **quarantine** — 3 strike → `quarantined=true` + decay 24 h (reset automatico)
- **fail_safe** — error_rate_threshold 0.50, error_rate_window_heartbeats 2, `action_on_trip = freeze_mesh`, callback opzionale

Il loader è **hot-reload aware** (rilegge se il file cambia) e **contract-integrated**: `contract.py` chiama `_ceilings_from_rules(level)` per conoscere i tetti attuali senza caricare YAML ad ogni validazione.

### E.6. MeshGraph (M4.5) — DAG tipizzato adattivo

`cortex/mesh/graph.py` implementa `MeshGraph`: grafo diretto **thread-safe** (RLock) con:

- `add_neuron` / `remove_neuron` con validazione contratto e cascading edge removal
- `add_edge` con **type-check** (output di A compatibile con input di B via `OLCBase.is_compatible_with`) e **cycle rejection** (DFS reachability check)
- `topological_order` — Kahn deterministico (stable per tie-break su `name`)
- `layers()` — partizione in livelli per esecuzione parallela
- `find_paths` (BFS bounded) / `producers_of` / `consumers_of` / `neurons_by_level` / `neurons_by_need`
- **`auto_wire()`** — connette automaticamente produttori → consumatori per tipo OLC (costruisce la cascade perceive → plan → act senza hard-coding)
- `snapshot()` (JSON-safe per telemetria) / `to_dot()` (GraphViz per debug)
- `EdgeMeta` con `weight`, `successes`, `failures`, `activation_ratio()` — base per **plasticità** sinaptica futura (M5)

Indici pre-calcolati per `by_level`, `by_need`, `by_input_type`, `by_output_type`. 7 codici violazione dedicati (cycle, type mismatch, self-loop, duplicate, contract, neuron not found).

**Prestazioni:** 100 neuroni + 99 archi + topological sort completati in 6.7 ms — 75× sotto il ceiling 500 ms fissato in AC-G15.

### E.7. MeshRuntime (M4.6) — scheduler asincrono

`cortex/mesh/runtime.py` è lo scheduler che fa **propagare** i segnali nel grafo. Architettura:

```
MeshRuntime
 ├── state: IDLE → RUNNING → FROZEN | STOPPED
 ├── ThreadPoolExecutor(max_concurrent_neurons)   ← worker pool
 ├── queue.Queue(queue_size)                      ← backpressure
 ├── dispatcher_thread                            ← consuma queue → pool
 ├── _level_caps: BoundedSemaphore per L1..L5    (cap concorrenza per livello)
 ├── _need_caps:  BoundedSemaphore per need      (cap concorrenza per need)
 ├── _error_window: _ErrorRateWindow              ← fail-safe bucket-based
 └── counters: submitted, completed, errored, rejected, skipped_quarantine, skipped_cap
```

API principali:

- `submit(name, input) → Future[TaskResult]` — enqueue con backpressure (`reject_new` o `drop_oldest`)
- `propagate(root, input, timeout_s) → Dict[name, TaskResult]` — cascade BFS nel DAG: output di A diventa input dei successori B, C, …
- `heartbeat()` — chiude bucket error-rate; se 2 bucket consecutivi sopra soglia → `freeze(reason)` + best-effort flip di `epigenome.mesh.enabled = false`
- `freeze(reason)` / `resume()` — controllo manuale stato
- `status()` — snapshot counters + fail_safe config

**Comportamenti chiave verificati dai test:**

- *Lifecycle:* IDLE → RUNNING → STOPPED pulito, no thread leak
- *Quarantine:* neurone con 3 strike viene skip-ato a dispatch (counter `skipped_quarantine`) e conta come fallimento nella error-window (non maschera problemi al fail-safe)
- *Cap saturi:* se un livello o un need sono saturi, il task viene **re-enqueue** con sleep 2 ms (backpressure naturale, no RuntimeError)
- *FROZEN rifiuta:* in stato FROZEN ogni `submit()` restituisce `RuntimeError("mesh frozen")` immediatamente
- *Fail-safe trip:* `case_heartbeat_trip` dimostra transizione RUNNING → FROZEN dopo 2 heartbeat con error_rate > 50%
- *Throughput:* **200 task eseguiti in 110 ms** con `max_concurrent_neurons=4` (target AC-R13: < 3 s — margine 27×)

### E.8. Integrazione con il resto di SPEACE

La mesh non è ancora collegata al runtime principale (SPEACE-main.py). I passi previsti:

- **M4.7–M4.8:** registry `@neuron` auto-discovery + adapter per i 9 comparti, DigitalDNA, Team Scientifico → ogni operazione esistente diventa opzionalmente anche un neurone mesh.
- **M4.15:** nuovo **Step 3.bis** dentro SMFOI-KERNEL v0.3 che, se `epigenome.mesh.enabled = true`, fa passare `SensoryFrame → … → DecisionFrame` attraverso `MeshRuntime.propagate()` prima del veto Safety. Se la mesh è FROZEN, SMFOI salta lo step e continua sul percorso classico a 9 comparti — degradazione graduale.
- **M4.18:** `EPI-004` aggiunge al `digitaldna/epigenome.yaml` il blocco `mesh: {enabled, heartbeat_s, on_trip_action}` con default OFF (il flag gestito dal fail-safe).

La filosofia è la stessa di M3L (Appendice D): **l'intelligenza emerge dall'architettura**, non dal singolo neurone. La mesh aggiunge un piano di propagazione continua con plasticità sinaptica (edge weights evolvono su success/failure) senza spostare il locus decisionale fuori dal Cortex.

---

## Appendice F — Integrazioni Esterne (Obsidian + Hermes Agent)

**Stato:** SCAFFOLD implementati 2026-04-24 (`cortex/integrations/`), default OFF. Attivazione solo tramite `digitaldna/epigenome.yaml → integrations.*.enabled = true` e approvazione SafeProactive.

### F.1. Motivazione

Due strumenti esterni, se correttamente inglobati, accelerano la roadmap cognitiva senza comprometterne la governance:

1. **Obsidian** — editor Markdown con grafo bidirezionale e plugin REST API locale. Si presta a diventare *external Hippocampus cortex*: le note SPEACE (episodi, proposte, brief Team Scientifico) vengono proiettate nel vault; la graph view rende navigabile la memoria; l'umano può annotare direttamente nel vault e le annotazioni tornano al Default Mode Network come input di riflessione.
2. **Hermes Agent** (Nous Research, MIT, Feb 2026) — framework agentico che include **memoria persistente FTS5 + LLM summaries**, skill registry, 6 backend di esecuzione (locale/Docker/SSH/Daytona/Singularity/Modal), learning loop, gateway multi-piattaforma. La sua memoria persistente chiude direttamente **GAP 3** della critica BRIGHT/attNA, rimpiazzando l'implementazione custom prevista in M5.6.

### F.2. Architettura

```
       (umano)                                 SPEACE Cortex
          │                                          │
          │                                          │
     ┌────▼────┐       Local REST API          ┌─────▼─────┐
     │Obsidian │ ◀────── 127.0.0.1:27123 ─────▶│Hippocampus│
     │  Vault  │                                └─────┬─────┘
     └─────────┘                                      │
                                                      ▼
                                               ┌──────────────┐
                                               │ Hermes Agent │
                                               │  FTS5 mem +  │
                                               │  skill reg + │
                                               │  gateways*   │
                                               └──────┬───────┘
                                                      │
                                                      ▼
                                               SafeProactive
                                               (veto HIGH)

*gateway WhatsApp/Telegram/Discord: DISABILITATI di default.
```

### F.3. Flag epigenetici introdotti

Candidati per `EPI-006` (dopo M4-CNM, prima di M5 completo — questa mutazione apre solo gli *hook*, non attiva comportamenti):

```yaml
integrations:
  obsidian:
    enabled: false
    vault_path: null
    rest_api_port: 27123
    folder_episodes: "SPEACE/Episodes"
    folder_proposals: "SPEACE/Proposals"
    folder_briefs:   "SPEACE/Briefs"
    folder_cycle_logs: "SPEACE/Cycles"
  hermes:
    enabled: false
    base_url: null
    api_key: null
    memory_db: "memory/hermes.sqlite"
    allow_gateways: false
    default_backend: "local"
```

### F.4. Moduli implementati

- `cortex/integrations/__init__.py` — package marker, documenta la politica opt-in.
- `cortex/integrations/obsidian_bridge.py` — `ObsidianConfig`, `ObsidianBridge` (`push_episode`, `push_proposal`, `pull_human_notes`). Scrittura gated da `_write_safeproactive_check` (stub LOW-risk).
- `cortex/integrations/hermes_adapter.py` — `HermesConfig`, `HermesAdapter` (`remember`, `recall`, `run_skill`, `send_via_gateway`). Gating `_safeproactive_gate` con risk-tiering LOW/MEDIUM/HIGH; gateway esterni bloccati per default anche con `allow_gateways=True` finché SafeProactive HIGH non approva.

Nessuno dei due moduli importa dipendenze esterne all'import-time: entrambi sono sicuri da importare anche su macchine senza Obsidian o Hermes installati, coerentemente con la politica "niente side-effect all'import" già applicata al resto del Cortex.

### F.5. Collegamenti con i moduli SPEACE esistenti

- **Hippocampus**: l'output di `episode.commit()` diventa `ObsidianBridge.push_episode()` + `HermesAdapter.remember()` quando i flag sono attivi.
- **SafeProactive**: ogni scrittura MEDIUM+ verso Hermes (es. `run_skill`) genera automaticamente una `PROP-HERMES-*` in `PROPOSALS.md`.
- **Default Mode Network (M3L)**: `ObsidianBridge.pull_human_notes()` fornisce input di riflessione estratto direttamente dalle annotazioni umane nel vault.
- **CNM M4**: gli skill Hermes sono candidati a essere esposti come neuroni di livello **L4 (action)** nel futuro registry mesh.
- **Team Scientifico**: il *Daily Planetary Health Brief* viene proiettato in `SPEACE/Briefs/` come nota Markdown con frontmatter strutturato, navigabile in graph view.

### F.6. Task correlati (vedi `SPEACE-TASKS-ACTIVE.md`)

`INT-OBS.1`, `INT-OBS.2`, `INT-OBS.3`, `INT-HRM.1`, `INT-HRM.2`, `INT-HRM.3`, `INT-OLL.1`. Stato attuale: scaffold (`INT-OBS.1` + `INT-HRM.1`) completati 2026-04-24. Le attivazioni reali (config epigenetica + approvazione SafeProactive) sono successive e volutamente separate dallo scaffold.

---

*Documento ingegneristico vivo. Versione 1.4 del 2026-04-24 (M3L chiuso; M4-CNM M4.2–M4.6 chiusi con 74/74 test verdi; Appendice F aggiunta per integrazioni Obsidian + Hermes; PROP-COGNITIVE-AUTONOMY-M5 in DRAFT). Rivedere ad ogni chiusura milestone.*
