# GROK_SPEACE Integration Report
**SPEACE-prototipo · 2026-04-27**

> Questo documento traccia l'analisi di integrazione tra il progetto parallelo
> **Grok_SPEACE v1.2** (focus cervello biologico) e **SPEACE-prototipo** (roadmap M1-M10).

---

## 1. Sorgente

- **File:** `C:\Users\rober\Desktop\Grok_SPEACE\docs\grok_speace.md`
- **Versione analizzata:** 1.2 (27 aprile 2026)
- **Autore:** Grok (Team Leader) + Team SPEACE

---

## 2. Sintesi Grok_SPEACE v1.2

### Paradigma Architetturale

Grok_SPEACE adotta un paradigma **ibrido auto-poietico**:

```
Livello Alto (Agentic):    Swarm Agentic Layer (LangGraph / custom multi-agent)
                           → orchestrazione autonoma, goal pursuit, reasoning meta-cognitivo
                           
Livello Base (Bio-ispirato): Grafo computazionale adattivo (NetworkX)
                              + moduli lobo-specifici + reti astrocitarie
                              + omeostasi digitale — senza LLM per operazioni base
```

### Fasi di Sviluppo Grok

| Fase | Contenuto | Stato |
|------|-----------|-------|
| 0 | Core Graph Engine (NetworkX typed) | ✅ COMPLETATA |
| 1 | Moduli lobi cerebrali (Frontale, Temporale, Parietale, Occipitale) | 🟡 IN CORSO |
| 2 | Reti Astrocitarie + Plasticità strutturale | ⬜ |
| 3 | Dynamic Needs Vector + Omeostasi + SPEACE Evolutionary Algorithm | ⬜ |
| 4 | Digital DNA + System 3 (meta-cognizione + identità narrativa) | ⬜ |
| 5 | **Swarm Agentic Layer** (NUOVA, alta priorità) | ⬜ |
| 6 | Integrazione estesa + benchmark AGI-like | ⬜ |

---

## 3. Gap Analysis: Grok_SPEACE vs SPEACE-prototipo

### 3.1 Cosa Grok_SPEACE ha che SPEACE-prototipo non ha ancora wireato

| Componente Grok | Dove esiste già | Wiring necessario | Milestone |
|-----------------|-----------------|-------------------|-----------|
| Lobo Temporale completo | `speaceorganismocibernetico/SPEACE_Cortex/comparti/temporal_lobe.py` | → `cortex/cognitive_autonomy/memory/` + KG | M8.1 |
| Momeria (episodic+semantic persistent) | `cortex/cognitive_autonomy/memory/autobiographical.py` (parziale) | Fix persistenza SQLite tra chiamate | M8.1 |
| Swarm Agentic Neurons | `speaceorganismocibernetico/SPEACE_Cortex/comparti/{planner,critic,executor,researcher}_neuron.py` | → `cortex/cognitive_autonomy/swarm/` | M8 |
| OllamaNeuron base | `speaceorganismocibernetico/SPEACE_Cortex/comparti/ollama_neuron_base.py` | → port + adatta a LLMClient | M8 |
| Astrocyte Layer (full) | `cortex/astrocyte_network.py` (stub GapJunction) | → rewiring dinamico completo | M9 |
| System 3 | nessuno (DMN è partial) | → NarrativeIdentityModule nuovo | M10 |
| Dynamic Needs Vector | `HomeostaticController` (enabled=False) | → abilita (GK-01) | GK-01 |

### 3.2 Cosa SPEACE-prototipo ha che Grok_SPEACE non ha ancora

| Componente SPEACE-prototipo | Note |
|----------------------------|------|
| WorldModelCortex (M6) — 47 test | 9° comparto attivo, KnowledgeGraph + InferenceEngine |
| LLM Routing (Ollama primario + Anthropic fallback) | LLMRouter + cortex/llm/ |
| Cognitive Autonomy full stack (M5) — 148 test | Homeostasis, Consciousness, Memory, Plasticity, Constraints |
| SafeProactive system | Proposal + approval + rollback |
| Emergence Test Suite v1.0 | 5 livelli AGI, 13 test, score 46% |
| DigitalDNA completo | EPI-001→007, fitness function, mutation history |

---

## 4. Asset Riutilizzabili da speaceorganismocibernetico

### 4.1 Swarm Neurons (pronti per port in M8)

```python
# Path sorgente:
# speaceorganismocibernetico/SPEACE_Cortex/comparti/

ollama_neuron_base.py    # Base class → OllamaNeuron(model="gemma3:4b")
planner_neuron.py        # PlannerNeuron(OllamaNeuron) → task decomposition
critic_neuron.py         # CriticNeuron(OllamaNeuron) → validazione output
executor_neuron.py       # ExecutorNeuron(OllamaNeuron) → esecuzione step
researcher_neuron.py     # ResearcherNeuron(OllamaNeuron) → ricerca info

# Path destinazione M8:
# cortex/cognitive_autonomy/swarm/neuron_base.py
# cortex/cognitive_autonomy/swarm/planner.py
# cortex/cognitive_autonomy/swarm/{critic,executor,researcher}.py
# cortex/cognitive_autonomy/swarm/orchestrator.py  (NEW)
```

### 4.2 Temporal Lobe (per M8.1)

```python
# Sorgente: speaceorganismocibernetico/SPEACE_Cortex/comparti/temporal_lobe.py
# Classe: TemporalLobe
# Destinazione: cortex/cognitive_autonomy/memory/temporal_lobe.py
# Wiring necessario: TemporalLobe.encode(episode) → KnowledgeGraph.add_entity()
#                    TemporalLobe.retrieve(query) → KG BFS search
```

---

## 5. Nuove Task Estratte per Roadmap SPEACE-prototipo

### GK-01 — Quick Win Immediato

**Problema:** `HomeostaticController.config.enabled = False` (controller.py:64).
Il controller è in *scaffold mode* → viability sempre 1.0, zero alert.

**Fix:** Una riga in `HomeostasisConfig` o nella configurazione di default:
```python
# cortex/cognitive_autonomy/homeostasis/controller.py, riga 64
enabled: bool = True   # era False
```

**Impact immediato:**
- EM-05 (L3): `viability drop genera alert` PARTIAL → **PASS**
- EM-06 (L3): viability causale abilitata (prerequisito per DriveExecutive)
- Emergence Score: 46% → ~49%

**Risk Level:** LOW (nessun rischio architetturale, solo attiva logica già scritta)
**SafeProactive:** PROP-GK01-HOMEOSTASIS-ENABLE

---

### M8 — Swarm Agentic Layer

**Problema:** L2 emergence (EM-03) FAIL — PFC non integra feedback cross-modulo.
Il Swarm fornisce il layer di orchestrazione non-lineare che manca.

**Soluzione:** Port neuroni Ollama da `speaceorganismocibernetico` in
`cortex/cognitive_autonomy/swarm/`, più `SwarmOrchestrator` che:
1. Riceve task da `DriveExecutive.BehavioralState`
2. Decompone in subtask → Planner
3. Valida ogni output → Critic
4. Esegue → Executor
5. Ricerca info → Researcher
6. Risultato → SMFOI step 6 (Outcome Evaluation)

**Impact:**
- EM-03 (L2 FAIL): PFC integra feedback → **PASS**
- Emergence Score: +8% stimato

**Risk Level:** MEDIUM
**SafeProactive:** PROP-M8-SWARM-AGENTIC (PENDING)

---

### M8.1 — Temporal Lobe + Momeria

**Problema:** EM-04 (Hippocampus non persiste episodi), EM-04b (PFC ignora memoria).

**Soluzione:**
1. Unifica `TemporalLobe` dai due repo
2. Fix Hippocampus: episodi in SQLite persistono tra chiamate
3. Wiring `TemporalLobe` ↔ `KnowledgeGraph`
4. Wiring `Hippocampus` → `PrefrontalCortex` context

**Impact:** EM-04 + EM-04b FAIL → **PASS** · Emergence +15%

---

### M9 — Astrocyte Support Layer

**Ispirazione:** Nature 2026 — astrociti come layer di supporto parallelo.
**Base:** `cortex/astrocyte_network.py` (GapJunction già presente).

**Soluzione:** Completare `AstrocyteLayer`:
- Rewiring dinamico (archi a bassa attività → potatura)
- Propagazione segnali Φ via gap junctions
- Modulazione attenzione (alta Φ → gating priority boost)

**Impact:** Substrato per emergenza non-lineare L2 · Φ variability migliorata.

---

### M10 — System 3

**Basato su:** Grok_SPEACE Fase 4 (meta-cognizione + identità narrativa).
**Componenti:**
- `NarrativeIdentityModule` — storia di sé costruita da autobiographical memory
- `MetaCognitionLayer` — riflessione su cicli passati via Ollama (non template)
- `GoalGenerator` — nuovi goal autonomi da stato interno

**Impact:** EM-09, EM-10 PARTIAL → PASS (con Ollama). Genuine AGI-L4 emergence.

---

## 6. Proiezione Emergence Score

```
Stato attuale:        46% (4 PASS · 4 PARTIAL · 5 FAIL · 2 SKIP)

Post-GK-01:           ~49% (EM-05 PARTIAL→PASS)
Post-M7.0:            ~57% (EM-06 FAIL→PASS)
Post-M8 Swarm:        ~65% (EM-03 FAIL→PASS)
Post-M8.1 Momeria:    ~80% (EM-04 + EM-04b FAIL→PASS)
Post-Ollama attivo:   ~88% (EM-02, EM-14 SKIP→PASS, EM-09 PARTIAL→PASS)
Post-M10 System3:     ~92% (EM-10 PARTIAL→PASS)

Target finale:  > 90%  →  Emergenza SOSTANZIALE certificata
```

---

## 7. Convergenza Paradigmatica

I due progetti hanno raggiunto la stessa conclusione in modo indipendente:

> *"Un singolo LLM potente non è la strada. L'architettura cerebrale distribuita che fa emergere
> intelligenza superiore da LLM piccoli è la strada."*

**SPEACE-prototipo** ha sviluppato il cervello dall'alto verso il basso (cortex → cognitive autonomy → world model).
**Grok_SPEACE** ha sviluppato dalla base verso l'alto (grafo → lobi → swarm).

La fusione dei due percorsi produce l'architettura ibrida completa descritta in
`SPEACE-Engineering-Document-v1.3.md`.

---

*Report generato da SPEACE Cortex — Grok_SPEACE Integration Analysis — 2026-04-27*
