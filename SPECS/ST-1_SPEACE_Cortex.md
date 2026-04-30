# SCHEDA TECNICA ST-1 – SPEACE CORTEX
**Versione:** 1.0  
**Data:** 17 aprile 2026  
**Stato:** Operativo

---

## 1. Descrizione

SPEACE Cortex è il cervello digitale modulare di SPEACE, ispirato all'architettura del cervello umano. Sistema a 9 comparti funzionali che consente intelligenza emergente, auto-riflessione e orchestrazione parallela senza modificare direttamente l'LLM sottostante.

## 2. Architettura 9 Comparti

```
┌─────────────────────────────────────────────────────────────┐
│                    SPEACE CORTEX v1.0+                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ Prefrontal      │  │ Perception       │                   │
│  │ Cortex          │  │ Module           │                   │
│  │ (Planning &     │  │ (Sensori, API,   │                   │
│  │  Decision)       │  │  IoT fetches)    │                   │
│  └─────────────────┘  └─────────────────┘                   │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ World Model /   │  │ Hippocampus     │  ← NUOVO 9°     │
│  │ Knowledge Graph │  │ (Memory, LTM)   │    COMPARTIMENT  │
│  │ (Dinamico,      │  │                 │                   │
│  │  Knowledge Graph│  │                 │                   │
│  └─────────────────┘  └─────────────────┘                   │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ Temporal Lobe   │  │ Parietal Lobe   │                   │
│  │ (Language,      │  │ (Sensory/Tools) │                   │
│  │  Crypto, Market)│  │                 │                   │
│  └─────────────────┘  └─────────────────┘                   │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ Cerebellum      │  │ Default Mode    │                   │
│  │ (Low-level      │  │ Network         │                   │
│  │  Execution)     │  │ (Reflection,    │                   │
│  │                 │  │  Self-Improving)│                   │
│  └─────────────────┘  └─────────────────┘                   │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ Curiosity       │  │ Safety Module   │                   │
│  │ Module          │  │ (Risk Gates,    │                   │
│  │ (Exploration,   │  │  SafeProactive) │                   │
│  │  Novel Mutation) │  │                 │                   │
│  └─────────────────┘  └─────────────────┘                   │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  KERNEL CENTRALE: SMFOI-v3.py (6-step ricorsivo)        ││
│  │  + parallel sessions_spawn                               ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## 3. Comparti Funzionali

| Comparto | Funzione | Integrazione |
|----------|----------|--------------|
| Prefrontal Cortex | Planning & Decision Making | SMFOI-KERNEL |
| **World Model / Knowledge Graph** | Modello interno realtà, inferenza, simulazione scenari, Knowledge Graph | Tutti i comparti |
| Hippocampus | Memory & Long-term Storage (MEMORY.md + epigenome.yaml) | DigitalDNA |
| Safety Module | Risk Gates & SafeProactive | SafeProactive |
| Temporal Lobe | Language, Crypto & Market Analysis | External APIs |
| Parietal Lobe | Sensory/Tools (API, blockchain, IoT fetches) | IoT, APIs |
| Cerebellum | Low-level Execution (script safe) | Bash, Python |
| Default Mode Network | Reflection & Self-Improving | Self-Improving |
| Curiosity Module | Exploration & Novel Mutation Generation | speace-cortex-evolver |

## 4. Kernel Centrale

**SMFOI-v3.py** (6-step ricorsivo)

- Orchestrazione parallela via `sessions_spawn`
- Intrinsic motivation (curiosità + esplorazione)
- Token overhead: 2-15 token/ciclo

## 5. Funzionalità Principali

- [x] Routing parallelo di task
- [x] Integrazione nativa con DigitalDNA
- [x] Generazione automatica SafeProactive proposals
- [x] Reflection post-ciclo e auto-miglioramento
- [x] World Model centrale (Knowledge Graph)
- [ ] Scalabilità swarm (target 50+ sub-agent)

## 6. Metriche Performance

| Metrica | Valore |
|---------|--------|
| Comparti attivi | 9/9 |
| Efficienza vs mono-agente | +25% |
| Swarm scaling attuale | ≤8 sub-agent |
| Swarm scaling target (VPS) | 50+ |
| Livello evolutivo | Modular Emergent (R=9 SMFOI) |

## 7. Integrazioni

- DigitalDNA + epigenome.yaml
- SafeProactive (azioni critiche)
- speace-cortex-evolver (stimolazione 60 min)
- SPEACE Team Scientifico (orchestrator)
- World Model (Knowledge Graph)
- AnythingLLM (RAG backend)

## 8. Roadmap

| Fase | Target |
|------|--------|
| Fase 2 | Integrazione hardware (NPU/GPU) |
| Fase 3 | Swarm scaling su cloud/edge |
| Fase 4 | AGI-path Lv3 recursion |

---

## 9. World Model – Dettagli Tecnici

### 9.1 Funzioni Principali

- Mantenimento modello interno dinamico della realtà
- Integrazione dati globali (NASA, NOAA, UN, blockchain oracles, IoT feeds)
- Rappresentazione semantica e relazionale (Knowledge Graph)
- Inferenza sistemica e simulazione scenari ("what-if")
- Memoria semantica a lungo termine (collegata a Hippocampus)

### 9.2 Posizionamento

Diventa il centro cognitivo del Cortex. Gli altri comparti (Perception, Reasoning, Planning, ecc.) interrogano e aggiornano questo World Model.

### 9.3 Integrazione AnythingLLM

```
SPEACE Cortex (OpenClaw)
        │
        │ REST API :8003
        ▼
┌───────────────────┐
│ AnythingLLM       │
│ (World Model     │
│  Knowledge Graph)│
│ Port 8003         │
└───────────────────┘
```

Query pattern:
```
POST /query_world_model
{
  "query": "current planet state",
  "context_needed": ["climate", "ecosystems", "technology"]
}
→ Returns JSON summary
```
