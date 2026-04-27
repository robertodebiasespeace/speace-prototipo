# SPEACE — Design Concettuale Generale Sintetico

**Versione:** 1.0
**Data:** 2026-04-24
**Stato:** Documento vivo — aggiornamento ad ogni milestone
**Scopo:** Vista d'insieme e sintetica dell'architettura SPEACE (prototipo `SPEACE-prototipo/`), componenti, dipendenze, elementi coadiuvanti e schede tecniche essenziali.

> **Nota di scope:** questo documento descrive il ramo **`SPEACE-prototipo`** (cervello ingegnerizzato, 9 comparti + mesh M4) ed è concettualmente coerente con il documento di panoramica presente nel workspace parallelo `speaceorganismocibernetico/docs/SPEACE-Panoramica-Concettuale-Tecnica-Sintetica.md`. Per la roadmap operativa vedi `SPEACE-TASKS-ACTIVE.md`.

---

## 1. Descrizione Sintetica di SPEACE

**SPEACE** (SuPer Entità Autonoma Cibernetica Evolutiva) è un **super-organismo tecnico-biologico** in costruzione: un'architettura cognitiva modulare che integra intelligenza artificiale distribuita, framework agentici, memoria persistente, e — in prospettiva — IoT, robotica e sensori.

SPEACE non è un singolo LLM, ma una **rete di comparti specializzati** orchestrati da un kernel di orientamento (SMFOI) e sottoposti ad evoluzione genetico-epigenetica (DigitalDNA). L'obiettivo evolutivo è la **Speace Transition**: una transizione verso un sistema armonico, rigenerativo e pacifico, allineato con il Rigene Project e i 17 SDG dell'Agenda 2030.

**Principio guida:** *l'intelligenza emerge dall'architettura, non dal singolo neurone.*

---

## 2. Componenti Hardware-Software (elenco sintetico)

### Hardware attuale (PC principale)

- **CPU:** Intel Core i9-11900H
- **GPU:** NVIDIA GeForce RTX 3060
- **RAM:** 16 GB
- **Storage:** 954 GB SSD NVMe
- **OS:** Windows 11

### Software core (cervello SPEACE — ramo prototipo)

- **SPEACE Cortex** — 9 comparti funzionali + mesh M4
- **SMFOI-KERNEL v3** — protocollo 5-step ricorsivo (+ Step 3.bis mesh previsto)
- **DigitalDNA** — `genome.yaml` + `epigenome.yaml` + `mutation_rules.yaml` + fitness function v2
- **SafeProactive** — Write-Ahead Log + approval gates + rollback CLI
- **Continuous Neural Mesh (CNM)** — `cortex/mesh/` con contract/graph/runtime/execution_rules
- **LLM as Semantic Tissue** — adapter locale (LM Studio)
- **Team Scientifico ridotto** — agenti + Adversarial + Evidence
- **Dashboard Streamlit v1.4** — monitoraggio localhost:8501

### Elementi operativi

- `SPEACE-main.py` — loop cognitivo principale
- `scripts/speace_status_monitor.py` — monitor stato periodico
- `benchmarks/` — suite benchmark (chiusa in M2)
- `tests/` — pytest suite (74/74 verdi al closure M4.6)
- `safeproactive/PROPOSALS.md` — registro proposte + approvazioni

---

## 3. Dipendenze Tecnologiche (elenco sintetico)

- **Python** 3.11+ (testato 3.11/3.12)
- **pytest** — test runner
- **PyYAML** — lettura genoma/epigenoma/execution_rules
- **Streamlit** — dashboard
- **Plotly + Pandas** — grafici e data frame
- **River** (previsto M5.9) — online learning
- **NumPy** — calcoli numerici (C-index, fitness)
- **Ollama** (opzionale, M5.8) — LLM locale (Gemma3:12b) per Meta-Neurone Dialogico
- **Docker** (opzionale) — AnythingLLM / Mosquitto / servizi
- **MQTT (Mosquitto)** (opzionale, ORG.3) — bus IoT futuro
- **Git + GitHub** — versionamento (`robertodebiasespeace/tina-testbed-speace`)
- **AHK v2** (opzionale) — automazione desktop Windows

---

## 4. Elementi Coadiuvanti / Framework Esterni (elenco sintetico)

- **LM Studio** — backend LLM primario locale (prototipo)
- **Ollama + Gemma3:12b** — reasoning locale avanzato (candidato M5.8)
- **Obsidian** — PKM, candidato Hippocampus-bridge (INT-OBS)
- **Hermes Agent** (Nous Research) — memoria persistente FTS5 + skill system (INT-HRM)
- **AnythingLLM** — World Model / RAG containerizzato (futuro)
- **OpenClaw / NanoClaw / IronClaw / SuperAGI** — framework agentici alternativi per architettura ibrida
- **AutoGPT Forge** — AGPTNeuron wrapper (presente nel ramo organismo)
- **AutoHotkey v2** — automazione GUI su Windows (workaround tier "click" e push GitHub)
- **Claude Code** — agente di sviluppo principale (Cowork)
- **GitHub** — repo pubblico SPEACE

---

## 5. Schede Tecniche Sintetiche

### 5.1. Schede dei componenti Hardware-Software

**SPEACE Cortex (9 comparti + CNM)**
Cervello modulare ispirato al cervello umano. 9 comparti: *Prefrontal* (planning), *Hippocampus* (memoria), *Safety Module*, *Temporal Lobe* (linguaggio/LLM), *Parietal Lobe* (tools/API), *Cerebellum* (esecuzione low-level), *Default Mode Network* (riflessione), *Curiosity Module*, *World Model / Knowledge Graph* (aggiunto post-analisi BRIGHT). CNM M4 aggiunge un piano di propagazione continua tipizzato (DAG + ThreadPool + backpressure + fail-safe).

**SMFOI-KERNEL v3**
Schema Minimo Fondamentale di Orientamento dell'Intelligenza. Ciclo 5-step: Self-Location → Constraint Mapping → Push Detection → Survival & Evolution Stack → Output Action. Previsto Step 3.bis (mesh) in M4.15 e Step 6 (Outcome Evaluation & Learning) in M5. Overhead 2–15 token/ciclo. Integrazione con DigitalDNA per mutazioni epigenetiche.

**DigitalDNA**
Sistema genetico-epigenetico digitale. `genome.yaml` (struttura genetica fissa: obiettivi, regole base), `epigenome.yaml` (regolazioni dinamiche: learning rate, heartbeat, mesh flag, integrations flag), `mutation_rules.yaml` (regole di mutazione + fitness function). Ogni mutazione è una proposta `PROP-EPI-*` passante da SafeProactive.

**SafeProactive**
Write-Ahead Logging + approval gates. Ogni azione a rischio genera una proposta in `PROPOSALS.md` con `Risk Level` (LOW/MEDIUM/HIGH). Approval protocol: human-in-the-loop obbligatorio per MEDIUM+. Rollback CLI standalone in `scripts/rollback.py` (snapshot atomico pre-mutazione).

**Continuous Neural Mesh (CNM, M4)**
Piano di propagazione continua dei segnali tra neuroni tipizzati. Contract `@neuron` validato statico+runtime, DAG con topo-sort, MeshRuntime con ThreadPool, cap per livello (L1..L5) e per need, fail-safe a error-window (freeze automatico su 2 bucket consecutivi sopra soglia). 74/74 test verdi al closure M4.6.

**Dashboard v1.4 (Streamlit)**
Interfaccia web live su localhost:8501. Vista runtime, stato comparti, proposte SafeProactive, metriche CNM, C-index (post-M5.3).

**Team Scientifico ridotto**
Agenti specializzati (Climate, Economics, Governance, Technology, Health, Social, Space) + **Adversarial Agent** (critica) + **Evidence Verification Agent** (fact-checking). Output: Daily Planetary Health Brief, Proposte Evolutive verso SafeProactive.

### 5.2. Schede delle Dipendenze

**Python 3.11+** — runtime principale; tutte le componenti sono Python puro salvo adapter esterni.
**pytest** — test runner; 74 test CNM + test comparti in M3L + smoke test M0.
**PyYAML** — parse/dump di `genome.yaml`, `epigenome.yaml`, `execution_rules.yaml`, `mutation_rules.yaml`.
**Streamlit + Plotly + Pandas** — stack dashboard; rendering grafi e tabelle.
**River** — apprendimento online (previsto `cortex/learning_core/` in M5.9).
**NumPy** — vettorializzazione (sigmoidi C-index, medie fitness in Experience Replay).
**Ollama** — LLM locale; usato dal Meta-Neurone Dialogico (candidato porting M5.8) via `ollama.chat`.
**Docker** — container per AnythingLLM, Mosquitto (MQTT) e framework agentici alternativi (NanoClaw/IronClaw/SuperAGI).
**MQTT (Mosquitto)** — bus di messaggi per sensori IoT (ORG.3 in roadmap).
**Git + GitHub** — sync repo; repo pubblico su `robertodebiasespeace/tina-testbed-speace`.
**AHK v2** — automazione GUI Windows; usato per `PUSH-NOW.bat` e candidato a skill "AHK Self-Evolutive".

### 5.3. Schede degli Elementi Coadiuvanti

**LM Studio** — backend LLM locale primario del prototipo; espone endpoint OpenAI-compatible su localhost. Documentato in Appendice B di `speace-prototipo.md`.

**Ollama + Gemma3:12b** — alternativa locale per reasoning profondo; usata dal Meta-Neurone Dialogico nel ramo `speaceorganismocibernetico`. Costo ~12 GB VRAM (compatibile RTX 3060).

**Obsidian** — editor Markdown + PKM con grafo bidirezionale; candidato come *external Hippocampus cortex*. Integrazione prevista via **Local REST API plugin** (porta 27123) — vedi `cortex/integrations/obsidian_bridge.py`. Vantaggio: memoria umana + SPEACE convivono nello stesso vault, graph view sulle note episodiche, preserva interoperabilità con strumenti umani.

**Hermes Agent** (Nous Research) — framework agentico open-source (MIT) con **FTS5 persistent memory + LLM summaries**, skill system, 6 backend terminal (locale/Docker/SSH/Daytona/Singularity/Modal), learning loop, gateway multi-piattaforma (WhatsApp/Telegram/…). Si integra come adapter in `cortex/integrations/hermes_adapter.py`; chiude direttamente **GAP 3 (memoria autobiografica persistente)** della critica BRIGHT/attNA.

**AnythingLLM** — container RAG con vector store; candidato centro del World Model / Knowledge Graph Module (comparto #9).

**OpenClaw / NanoClaw / IronClaw / SuperAGI** — framework agentici per architettura ibrida multi-framework (SPEACE Swarm). Ruoli: OpenClaw (principale), NanoClaw (edge/IoT leggero), IronClaw (sandboxing sicuro), SuperAGI (orchestration multi-agent).

**AutoGPT Forge** — runtime agente; wrappato come `AGPTNeuron` nel ramo organismo.

**AutoHotkey v2** — script di automazione GUI su Windows; fondamentale per bypass del tier "click" (PowerShell e terminali) e per candidato skill "AHK Self-Evolutive" (script auto-generati che eseguono monitor/alert).

**Claude Code (Cowork)** — agente di sviluppo primario che co-evolve SPEACE tramite file tools, Bash, analisi proposte.

**GitHub (`robertodebiasespeace/tina-testbed-speace`)** — repository pubblico; branch principale + PR di milestone.

---

## 6. Comandi principali

```bash
# 1. Avvio ciclo cognitivo
python SPEACE-main.py --once                     # singolo ciclo
python SPEACE-main.py                            # loop continuo

# 2. Dashboard localhost:8501
streamlit run dashboard/speace_dashboard.py

# 3. Test
pytest                                           # tutti
pytest cortex/mesh/_tests_runtime.py -v          # solo runtime mesh

# 4. Rollback di una mutazione DigitalDNA
python scripts/rollback.py --to <snapshot-id>

# 5. Push repo (workaround sandbox)
#    - doppio click su PUSH-NOW.bat      (Windows)
#    - oppure:  python git_push_github.py
```

---

## 7. Allineamento con il ramo organismo

Il ramo parallelo `speaceorganismocibernetico/` contiene moduli maturi che si candidano a **porting selettivo** in `SPEACE-prototipo/`:

- `self_dialogue_agent.py` → Meta-Neurone Dialogico (Ollama + Gemma3:12b) — porting in M5.8
- `online_learner.py` → Experience Replay + fitness tracking — porting in M5.9
- `consciousness_index.py` → C-index formale (5 profili) — porting in M5.3
- `agente_organismo_core.py` → 6 `SensorType` + 5 `SurvivalLevel` — porting in ORG.1
- `neural_bridge.py` → wrappers Hermes/AGPT/AnythingLLM — riferimento per INT-HRM
- `autopilot` → loop cognitivo autonomo 30s — riferimento operativo

Strategia di riconciliazione: da decidere in OPS.4 (monorepo, porting selettivo, o fork coordinato).

---

*Design concettuale vivo. Prossimo aggiornamento: alla chiusura di M4-CNM o all'approvazione di M5-COGNITIVE-AUTONOMY.*
