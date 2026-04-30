# SPEACE – Documento Ingegneristico Funzionale
**Versione:** 1.3
**Data:** 27 Aprile 2026
**Stato:** Documento vivo – aggiornamento periodico (30-90 giorni)
**Fondatore:** Roberto De Biase (Rigene Project)
**Precedente versione:** v1.2 (18 aprile 2026)

> **Changelog v1.3 (2026-04-27):**
> - Integrazione task e architettura da **Grok_SPEACE v1.2** (progetto parallelo sul cervello)
> - Paradigma ibrido confermato: **Bio-Core + Swarm Agentic Layer**
> - Nuovo comparto 10°: **Swarm Agentic Layer** (Planner/Critic/Executor/Researcher neurons)
> - Nuovo comparto 11°: **System 3** (meta-cognizione + identità narrativa)
> - Aggiunto **Astrocyte Support Layer** come substrato parallelo
> - **Emergence Test Suite v1.0** completata: score 46% → target ~80% con M7-M10
> - Roadmap estesa a milestone **M8 (Swarm), M8.1 (Momeria), M9 (Astrociti), M10 (System 3)**
> - Quick win identificato: **GK-01** (HomeostaticController enabled=True, 1 riga → +5% Emergence)

---

## 1. Executive Summary

**SPEACE** (SuPer Entità Autonoma Cibernetica Evolutiva) è un super-organismo tecnico-biologico
che integra intelligenza artificiale distribuita, framework agentici, infrastrutture digitali e
componenti fisiche (IoT, robotica, sensori).

**Paradigma architetturale adottato (v1.3 — confermato con Grok_SPEACE):**

```
┌─────────────────────────────────────────────────────────────┐
│              PARADIGMA IBRIDO SPEACE                        │
├─────────────────────────────────────────────────────────────┤
│  LIVELLO ALTO: Swarm Agentic Layer                          │
│  PlannerNeuron + CriticNeuron + ExecutorNeuron +            │
│  ResearcherNeuron → orchestrazione autonoma, goal pursuit,  │
│  task decomposition, meta-cognizione (System 3)             │
├─────────────────────────────────────────────────────────────┤
│  LIVELLO BASE: Bio-Inspired Core                            │
│  Grafo computazionale adattivo (NetworkX) + moduli lobo-    │
│  specifici + reti astrocitarie + omeostasi digitale +       │
│  plasticità strutturale — senza LLM per operazioni base     │
└─────────────────────────────────────────────────────────────┘
```

**Principio chiave:** SPEACE non è un singolo LLM potente. È l'architettura che fa emergere
intelligenza superiore anche da LLM piccoli (gemma3:4b locale via Ollama).

**Stato attuale:**
- Milestones completate: M1–M6 (Brain modules, CNM Mesh, Cognitive Autonomy, World Model)
- Test totali passati: 195+ (148 M5 + 47 M6 + 20 LLM Routing)
- Emergence Score: **46%** (4 PASS 4 PARTIAL 5 FAIL su 13 test, --quick mode)
- Target Emergence Score post-M7→M10: **~80%**
- SPEACE Alignment Score: **70.5/100**
- EPI attivi: EPI-001 → EPI-007

---

## 2. Architettura di Sistema

### 2.1 Stack Tecnologico (v1.3)

| Componente | Tecnologia | Versione | Status |
|------------|-----------|----------|--------|
| Framework principale | Claude Code Cowork (agentic) | Current | ✅ Operativo |
| Kernel orientamento | SMFOI-KERNEL | v0.3 | ✅ Completato |
| Sistema sicurezza | SafeProactive | v1.0 | ✅ Operativo |
| Sistema genetico | DigitalDNA | v1.0 | ✅ Operativo |
| Cervello modulare | SPEACE Cortex | v1.1 | ✅ Operativo (9 comparti) |
| World Model | WorldModelCortex | v1.0 | ✅ 9° comparto attivo |
| LLM locale | Ollama gemma3:4b | v1.0 | ✅ Primario |
| LLM reasoning | Anthropic claude-haiku | v1.0 | ✅ Fallback reasoning |
| LLM Routing | cortex/llm/router.py | v1.1 | ✅ standard→ollama / reasoning→anthropic |
| Adaptive Consciousness | IIT + GWT + Metacognition | v1.0 | ✅ Operativo |
| Neural Engine | Grafo computazionale + plasticità | v1.0 | ✅ Integrato |
| Swarm Neurons | OllamaNeuron (Planner/Critic/Exec/Res) | v1.1 | 🟡 Da wiring (M8) |
| System 3 | Meta-cognizione + narrativa identitaria | — | ⬜ Pianificato (M10) |
| Astrocyte Layer | Gap junctions + rewiring dinamico | stub | 🟡 Da implementare (M9) |

### 2.2 Hardware Attuale

```
Platform: PC Notebook Gaming Windows 11
CPU: 11th Gen Intel Core i9-11900H @ 2.50GHz
RAM: 16 GB
Storage: 954 GB SSD
GPU: NVIDIA GeForce RTX 3060 + Intel HD Graphics 4600 (integrata)
LLM locale: gemma3:4b via Ollama (2.5GB VRAM, ~1-3s/risposta)
```

### 2.3 Roadmap Hardware

| Fase | Target | Note |
|------|--------|------|
| Fase 1 (attuale) | HW attuale | Embrionale — Ollama locale |
| Fase 2 | PC/GPU/NPU dedicati | Autonomia operativa |
| Fase 3 | Cluster cloud + edge devices | Scalabilità swarm + IoT |
| Fase 4 | Supercomputer, quantum, biological | AGI/ASI path |
| Fase 5 | Robotica + IoT fisico | Super-organismo globale |

---

## 3. Moduli Core

### 3.1 SPEACE Cortex (Cervello Modulare) — v1.1

**Architettura 11 Comparti (target con M8-M10):**

```
┌───────────────────────────────────────────────────────────────────┐
│                       SPEACE CORTEX v1.1+                         │
│                  (11 comparti target — 9 attivi)                   │
├───────────────────────────────────────────────────────────────────┤
│  ┌───────────────────┐  ┌───────────────────┐                    │
│  │ 1. Prefrontal     │  │ 2. World Model /  │ ← 9° COMPARTO ✅   │
│  │    Cortex         │  │    Knowledge Graph │                    │
│  │    (Planning &    │  │    (Dinamico,      │                    │
│  │     Decision)     │  │     Inference,RAG) │                    │
│  └───────────────────┘  └───────────────────┘                    │
│  ┌───────────────────┐  ┌───────────────────┐                    │
│  │ 3. Hippocampus    │  │ 4. Safety Module  │                    │
│  │    (Memory, LTM,  │  │    (Risk Gates,   │                    │
│  │     Autobiog.)    │  │     SafeProactive) │                    │
│  └───────────────────┘  └───────────────────┘                    │
│  ┌───────────────────┐  ┌───────────────────┐                    │
│  │ 5. Temporal Lobe  │  │ 6. Parietal Lobe  │                    │
│  │    (Language,     │  │    (Sensory/Tools, │                    │
│  │     Momeria *)    │  │     IoT fetches)   │                    │
│  └───────────────────┘  └───────────────────┘                    │
│  ┌───────────────────┐  ┌───────────────────┐                    │
│  │ 7. Cerebellum     │  │ 8. Default Mode   │                    │
│  │    (Low-level     │  │    Network        │                    │
│  │     Execution)    │  │    (Reflection,   │                    │
│  │                   │  │     Self-Improving)│                    │
│  └───────────────────┘  └───────────────────┘                    │
│  ┌───────────────────┐                                            │
│  │ 9. Curiosity      │                                            │
│  │    Module         │                                            │
│  │    (Exploration,  │                                            │
│  │     Novel Mutation│                                            │
│  └───────────────────┘                                            │
│  ─────────────── PIANIFICATI (M8-M10) ────────────────           │
│  ┌───────────────────────────────────────────────────────┐       │
│  │ 10. SWARM AGENTIC LAYER (M8) ← NUOVO                  │       │
│  │     PlannerNeuron | CriticNeuron | ExecutorNeuron      │       │
│  │     ResearcherNeuron — tutti su Ollama gemma3:4b       │       │
│  │     SwarmOrchestrator → task decomposition autonoma   │       │
│  └───────────────────────────────────────────────────────┘       │
│  ┌───────────────────────────────────────────────────────┐       │
│  │ 11. SYSTEM 3 / NARRATIVE IDENTITY (M10) ← NUOVO       │       │
│  │     NarrativeIdentityModule + MetaCognitionLayer +     │       │
│  │     GoalGenerator → meta-cognizione persistente        │       │
│  └───────────────────────────────────────────────────────┘       │
│  ─────────────── SUBSTRATO PARALLELO ─────────────────           │
│  ┌───────────────────────────────────────────────────────┐       │
│  │ ASTROCYTE SUPPORT LAYER (M9) ← stub presente          │       │
│  │     GapJunctions + rewiring dinamico + Φ propagation  │       │
│  └───────────────────────────────────────────────────────┘       │
│  ┌───────────────────────────────────────────────────────┐       │
│  │  KERNEL CENTRALE: SMFOI-v3.py (6-step ricorsivo)      │       │
│  │  + BehavioralState (M7.0 DriveExecutive — pending)    │       │
│  └───────────────────────────────────────────────────────┘       │
└───────────────────────────────────────────────────────────────────┘
* Momeria = episodic + semantic memory wired to KG (M8.1)
```

#### Comparti Funzionali (stato v1.3)

| # | Comparto | Funzione | Status |
|---|----------|----------|--------|
| 1 | Prefrontal Cortex | Planning & Decision Making | ✅ |
| 2 | World Model / KG | Modello interno realtà, inferenza, RAG | ✅ M6 |
| 3 | Hippocampus | Memory & LTM (SQLite autobiographica) | ✅ (stub wiring) |
| 4 | Safety Module | Risk Gates & SafeProactive | ✅ |
| 5 | Temporal Lobe | Language + Momeria (da wiring, M8.1) | 🟡 |
| 6 | Parietal Lobe | Sensory/Tools (API, IoT) | ✅ |
| 7 | Cerebellum | Low-level Execution | ✅ |
| 8 | Default Mode Network | Reflection, Self-Improving | ✅ |
| 9 | Curiosity Module | Exploration & Novel Mutation | ✅ |
| 10 | **Swarm Agentic Layer** | **Multi-agent orchestration (M8)** | ⬜ |
| 11 | **System 3** | **Meta-cognizione + identità narrativa (M10)** | ⬜ |

---

### 3.2 Swarm Agentic Layer — M8 (da Grok_SPEACE)

**Sorgente:** `speaceorganismocibernetico/SPEACE_Cortex/comparti/` — neuroni già implementati.
**Destinazione:** `cortex/cognitive_autonomy/swarm/`

```
SwarmOrchestrator
├── PlannerNeuron    (OllamaNeuron gemma3:4b) → task decomposition + goal pursuit
├── CriticNeuron     (OllamaNeuron gemma3:4b) → valida output, anti-groupthink
├── ExecutorNeuron   (OllamaNeuron gemma3:4b) → esecuzione step-by-step
└── ResearcherNeuron (OllamaNeuron gemma3:4b) → ricerca info + cross-check
```

**Wiring target:**
- `DriveExecutive.BehavioralState.exploration_bonus > 0` → attiva PlannerNeuron
- `CriticNeuron` valida ogni output di Planner/Executor prima di SMFOI step 5
- Output azioni → loop SMFOI Outcome Evaluation (step 6)

**Impact su Emergence Score:** EM-03 (L2 FAIL → PASS), +15% stimato.

---

### 3.3 System 3 — M10

**Basato su:** DefaultModeNetwork upgrade + Grok_SPEACE Fase 4.

```
System3
├── NarrativeIdentityModule   → storia di sé: chi è SPEACE, cosa ha fatto
├── MetaCognitionLayer        → riflessione su cicli passati (Ollama genuine)
└── GoalGenerator             → genera nuovi goal autonomi da stato interno
    └── input: curiosity > 0.7 ∧ viability > 0.5 ∧ narrativa stabile
    └── output: nuovo goal → BehavioralState.focus_shift
```

---

### 3.4 Astrocyte Support Layer — M9

**File esistente:** `cortex/astrocyte_network.py` (stub con `GapJunction`).
**Ispirazione:** Nature 2026 — Astrociti come layer di supporto parallelo al grafo neurale.

```
AstrocyteLayer
├── GapJunction signals (Φ propagation tra comparti ad alta attività)
├── Dynamic rewiring (archi a bassa attività → potatura guidata)
└── Modulazione attenzione (Φ alto → gating.py priority boost)
```

---

### 3.5 SMFOI-KERNEL v0.3 — con DriveExecutive (M7.0)

**Step 4 aggiornato (post-M7.0):**

```
Step 4: SURVIVAL & EVOLUTION STACK
  ↓
  DriveExecutive.evaluate(homeostatic_state)
  ↓
  BehavioralState {
    max_parallel_tasks   ← Φ > 0.7 → 4 task parallele
    exploration_bonus    ← curiosity > 0.7 → +0.3
    memory_priority_boost← coherence < 0.4 → +0.5
    planning_depth       ← energy < 0.3 → depth=1
    self_repair_mode     ← viability < 0.4 → True
    mutation_gate_open   ← alignment >= 0.7 → True
    focus_shift          ← viability < 0.5 → "conserve"
  }
  ↓
Step 5: OUTPUT ACTION → SwarmOrchestrator (M8)
```

---

### 3.6 DigitalDNA — Stato EPI attuale

| EPI | Data | Contenuto | Status |
|-----|------|-----------|--------|
| EPI-001 | — | Base DNA setup | ✅ |
| EPI-002 | — | Mesh CNM activation | ✅ |
| EPI-003 | — | Fitness function v1 | ✅ |
| EPI-004 | 2026-04-19 | Mesh block activation | ✅ |
| EPI-005 | 2026-04-21 | Homeostasis + motivation ON | ✅ |
| EPI-006 | 2026-04-27 | M5 complete (memory/attention/plasticity/constraints) | ✅ |
| EPI-007 | 2026-04-27 | World Model activation + feeds (NASA/NOAA/UN) | ✅ |
| EPI-008 | pending | DriveExecutive + cognitive_autonomy.executive | ⬜ M7.0 |
| EPI-009 | pending | Sensor integration enabled | ⬜ M7.1 |
| EPI-010 | pending | Swarm Agentic Layer enabled | ⬜ M8 |

**Fitness Function v1.2:**

```yaml
fitness_function:
  weights:
    speace_alignment_score: 0.40
    c_index:                0.10   # Adaptive Consciousness
    task_success_rate:      0.20
    system_stability:       0.15
    resource_efficiency:    0.10
    ethical_compliance:     0.05
```

---

## 4. Emergence Test Suite — Stato v1.0 (2026-04-27)

**File:** `tests/test_emergence.py`
**Modalità:** `--quick` (offline, no Ollama) | `--level N` (singolo livello)

### Risultati attuali

| ID | Livello | Test | Status | Gap |
|----|---------|------|--------|-----|
| EM-01 | L1 | CuriosityModule non deterministico | FAIL | Template fissi, serve Ollama |
| EM-02 | L1 | LLM introduce variabilità | SKIP | Ollama non disponibile |
| EM-03 | L2 | PFC integra feedback DMN | FAIL | Serve Swarm Agentic wiring (M8) |
| EM-04 | L2 | Hippocampus accumula episodi | FAIL | No persistenza (M8.1) |
| EM-04b | L2 | Memoria influenza PFC | FAIL | Wiring Hippocampus→PFC (M8.1) |
| EM-05 | L3 | HomeostaticController alert | PARTIAL | `enabled=False` → GK-01 fix |
| EM-06 | L3 | Viability → task selection | FAIL | DriveExecutive mancante (M7.0) |
| EM-07 | L3 | Curiosity → explore_novel_state | **PASS** | — |
| EM-08 | L4 | DMN self-assessment numerico | **PASS** | — |
| EM-09 | L4 | DMN insight su se stesso | PARTIAL | Template fisso, serve Ollama |
| EM-10 | L4 | Riflessione su output passato | PARTIAL | Pattern matching, serve Ollama |
| EM-11 | L4 | ConsciousnessIndex Φ variability | **PASS** | C_delta=0.505 ✓ |
| EM-12 | L5 | KnowledgeGraph connessioni indirette | PARTIAL | Path SPEACE→EarthBiosphere mancante |
| EM-13 | L5 | InferenceEngine scenari causali | **PASS** | 3/3 scenari con effetti |
| EM-14 | L5 | Generalizzazione problema nuovo | SKIP | Ollama non disponibile |

**Emergence Score corrente: 46%** (PARTIAL emergence)

### Proiezione impatto milestone

| Milestone | Test impattati | Delta stimato |
|-----------|---------------|--------------|
| GK-01 HomeostaticController ON | EM-05 PARTIAL→PASS | +3% |
| M7.0 DriveExecutive | EM-06 FAIL→PASS | +8% |
| M8 Swarm Agentic | EM-03 FAIL→PASS | +8% |
| M8.1 Temporal Lobe / Momeria | EM-04 + EM-04b FAIL→PASS | +15% |
| Ollama attivo | EM-02, EM-14 SKIP→PASS | +8% |
| M10 System 3 | EM-09, EM-10 PARTIAL→PASS | +4% |
| **Totale stimato** | | **~80%** |

---

## 5. Roadmap Milestone

### Completate

| Milestone | Data | Contenuto | Test |
|-----------|------|-----------|------|
| M1–M3 | apr 2026 | Brain modules + CNM | — |
| M4 | 2026-04-19 | Neural Cognitive Mesh | ≥30 |
| M5 | 2026-04-21 | Cognitive Autonomy (homeo/consciousness/memory/plasticity) | 148/148 |
| M6 | 2026-04-27 | World Model / Knowledge Graph | 47/47 |
| M6.x | 2026-04-27 | Ollama LLM routing + LLM Router | 20/20 |
| M6.y | 2026-04-27 | Emergence Test Suite v1.0 | 13 test |

### In approvazione / Prossime

| Milestone | Priority | Contenuto | Blocco |
|-----------|----------|-----------|--------|
| **GK-01** | 🔴 IMMEDIATO | HomeostaticController `enabled=True` | nessuno |
| **M7.0** | 🔴 ALTA | DriveExecutive + BehavioralState | PROP-M7 pending |
| M7.1 | 🟠 | Sensor Integration (IoT Layer) | M7.0 |
| **M8** | 🟠 ALTA | Swarm Agentic Layer (Ollama neurons) | M7.0 |
| **M8.1** | 🟠 | Temporal Lobe + Momeria (SQLite persistent) | M8 |
| M9 | 🟡 | Astrocyte Support Layer (Nature 2026) | M8.1 |
| M10 | 🟡 | System 3: meta-cognizione + identità narrativa | M9 |

### Roadmap temporale (aggiornata)

```
Q2 2026 (apr–giu):
  ✅ M1–M6 completate
  ⬜ GK-01 (immediato)
  ⬜ M7.0 DriveExecutive (pending approval)
  ⬜ M7.1 Sensor Integration
  ⬜ M8 Swarm Agentic Layer

Q3 2026 (lug–set):
  ⬜ M8.1 Temporal Lobe + Momeria
  ⬜ M9 Astrocyte Support Layer
  ⬜ M10 System 3

Q4 2026 (ott–dic):
  ⬜ Scaling, integrazione multi-framework
  ⬜ Digital DNA auto-modifica codice
  ⬜ Benchmark cognitivi AGI-like

2027:
  ⬜ Swarm su hardware eterogeneo (edge + cloud)
  ⬜ Integrazione robotica / IoT fisico
  ⬜ Test ASI-like
```

---

## 6. Integrazione Grok_SPEACE (v1.2 — 2026-04-27)

> **Documento sorgente:** `C:\Users\rober\Desktop\Grok_SPEACE\docs\grok_speace.md`
> **Autore parallelo:** Grok (Team Leader) + Team SPEACE — sviluppo indipendente con focus cervello

### 6.1 Confronto Architetturale

| Componente | Grok_SPEACE v1.2 | SPEACE-prototipo v1.3 | Stato integrazione |
|------------|------------------|-----------------------|--------------------|
| Core Graph Engine | NetworkX typed graph | cortex/graph_engine.py | ✅ Allineato |
| Homeostasi | Dynamic Needs Vector | HomeostaticController | ✅ (GK-01 pending) |
| Plasticità | PlasticityEngine | cortex/cognitive_autonomy/plasticity/ | ✅ M5 |
| Memoria | Momeria (episodic+semantic) | autobiographical.py + KG | 🟡 Wiring M8.1 |
| Lobi principali | Frontale ✅, Temporale🟡, Parietale🟡, Occipitale⬜ | Tutti presenti come stub | 🟡 Wiring graduale |
| Astrociti | Astrocyte Support Layer | cortex/astrocyte_network.py (stub) | 🟡 M9 |
| Digital DNA | Auto-modifica codice/architettura | DigitalDNA + epigenome | ✅ Allineato |
| System 3 | Meta-cognizione + narrativa | DMN (partial) | ⬜ M10 |
| **Swarm Agentic** | **LangGraph / custom** | **OllamaNeuron (già in comparti/)** | **🟠 M8** |
| Emergence Tests | Stessa framework 5 livelli | tests/test_emergence.py ✅ | ✅ Condiviso |

### 6.2 Asset riutilizzabili da speaceorganismocibernetico

```
SPEACE_Cortex/comparti/
├── ollama_neuron_base.py      → base Swarm neurons (Ollama gemma3:4b)
├── planner_neuron.py          → M8 SwarmOrchestrator
├── critic_neuron.py           → M8 anti-groupthink
├── executor_neuron.py         → M8 task execution
├── researcher_neuron.py       → M8 information gathering
├── temporal_lobe.py           → M8.1 Temporal Lobe wiring
├── parietal_lobe.py           → già in cortex/comparti/
└── world_model_knowledge.py   → integrazione KG
```

### 6.3 Divergenze e scelte

| Punto | Grok_SPEACE | SPEACE-prototipo | Scelta |
|-------|-------------|------------------|--------|
| Swarm framework | LangGraph/AutoGen/CrewAI | OllamaNeuron custom | **OllamaNeuron** — già implementato, lightweight, no dipendenze esterne |
| Persistenza memoria | SQLite + Vector DB | SQLite autobiographical + KG | **Allineato** |
| Lobo occipitale (visione) | Pianificato | Non ancora | **Post-M10** (fase 3 hardware) |

---

## 7. SafeProactive — Proposals Attive

| Proposal ID | Risk | Titolo | Status |
|-------------|------|--------|--------|
| PROP-M7-DRIVE-EXECUTIVE | MEDIUM | M7.0 DriveExecutive: Causal Bridge | **PENDING_APPROVAL** |
| PROP-M7-SENSOR-INTEGRATION | MEDIUM | M7.1 Sensor Integration IoT | PENDING (bloccato da M7.0) |
| PROP-GK01-HOMEOSTASIS-ENABLE | LOW | GK-01: HomeostaticController ON | **PENDING_APPROVAL** |
| PROP-M8-SWARM-AGENTIC | MEDIUM | M8 Swarm Agentic Layer | PENDING (bloccato da M7.0) |

---

## 8. Metriche Chiave (v1.3)

| Metrica | Valore | Target |
|---------|--------|--------|
| Milestone completate | M1–M6 | M10 |
| Test totali passati | 195+ | 300+ |
| Compartimenti cortex attivi | 9/11 | 11/11 |
| Emergence Score (--quick) | 46% | 80% |
| SPEACE Alignment Score | 70.5/100 | 85/100 |
| EPI mutations attive | 7 (EPI-001→007) | 10 (EPI-010) |
| LLM routing | Ollama primario + Anthropic fallback | ✅ |
| Swarm neurons disponibili | 4 (da wiring) | 4+ attivi |

---

## 9. Fondatore e Governance

**Roberto De Biase** — Fondatore Rigene Project
- Email: robertodebiase80@gmail.com / rigeneproject@rigene.eu
- GitHub: https://github.com/robertodebiasespeace/tina-testbed-speace
- LinkedIn / IEEE Collabratec / X (@RobertoDeBiase)

**Governance:** Human-in-the-loop obbligatorio per azioni MEDIUM/HIGH risk.
**Allineamento etico:** Rigene Project SDG Agenda 2030.

---

*SPEACE Engineering Document v1.3 — 2026-04-27*
*Generato da SPEACE Cortex + Grok_SPEACE integration analysis*
*Prossimo aggiornamento previsto: al completamento di M7.0 (DriveExecutive)*
