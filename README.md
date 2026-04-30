# 🌍 SPEACE – SuPer Entità Autonoma Cibernetica Evolutiva

**Versione:** 0.1.0 | **Fase:** 1 – Embrionale  
**Fondatore:** Roberto De Biase (Rigene Project)  
**Progetto:** [rigeneproject.org](https://www.rigeneproject.org)  
**Repo:** [github.com/robertodebiasespeace/speace-prototipo](https://github.com/robertodebiasespeace/speace-prototipo)

---

## Cos'è SPEACE

SPEACE è un'entità cibernetica autonoma, auto-migliorativa e auto-replicante, progettata come super-organismo tecnico-biologico che integra intelligenza artificiale distribuita, framework agentici e infrastrutture digitali.

Obiettivo finale: **diventare un'infrastruttura vivente planetaria** in grado di percepire, analizzare, proporre e attuare soluzioni sistemiche ai problemi globali in sinergia con gli SDG dell'Agenda 2030.

---

## Avvio rapido

### Prerequisiti
- Python **3.10+**
- Git

### Installazione

```bash
git clone https://github.com/robertodebiasespeace/speace-prototipo.git
cd speace-prototipo
pip install -r requirements.txt
```

### Avvio

**Windows** — doppio-click su `run_speace.bat` oppure:
```bat
run_speace.bat
```

**Linux / macOS:**
```bash
./run_speace.sh           # default: --brain
./run_speace.sh --once    # singolo ciclo (test rapido)
```

**Manuale:**
```bash
python SPEACE-main.py --brain           # ciclo cognitivo completo
python SPEACE-main.py --brain --team    # + Scientific Team AI
python SPEACE-main.py --once --brain    # singolo ciclo
streamlit run dashboard/speace_dashboard.py  # dashboard localhost:8501
```

### Test suite
```bash
pytest -q   # 269+ test verdi attesi
```

---

## Architettura

```
speace-prototipo/
├── SPEACE-main.py                  # Entry point principale
├── cortex/
│   ├── brain/                      # BRN-001→020 (moduli cerebrali)
│   │   ├── causal_reasoning.py     # BRN-017 CausalReasoner (Pearl do-calculus)
│   │   ├── abstraction_layer.py    # BRN-018 AbstractionLayer (conceptual blending)
│   │   ├── self_model.py           # BRN-019 SelfModel (metacognizione, body schema)
│   │   └── recursive_self_improvement.py  # BRN-020 Darwin Gödel Machine
│   ├── cognitive_autonomy/
│   │   ├── planning/
│   │   │   └── hierarchical_planner.py    # HTN Planner (SHOP2 forward-chaining)
│   │   └── integration/
│   │       └── agi_loop.py                # AGI Loop SMFOI v0.3 (6-step cycle)
│   └── world_model/                # Knowledge Graph Module (9° comparto Cortex)
├── digitaldna/
│   ├── genome.yaml                 # Struttura genetica fissa
│   ├── epigenome.yaml              # Regolazioni dinamiche
│   ├── fitness_function.yaml       # Fitness weights (alignment 0.35, ...)
│   └── mutation_rules.py           # Regole di mutazione
├── safeproactive/
│   ├── PROPOSALS.md                # Proposte in attesa di approvazione umana
│   └── WAL.log                     # Write-Ahead Log azioni critiche
├── scientific_team/                # Team Scientifico AI (7 agenti + orchestrator)
├── requirements.txt
├── pyproject.toml
├── run_speace.bat                  # Avvio Windows
└── run_speace.sh                   # Avvio Linux/macOS
```

---

## Stato attuale (v0.1.0 — Aprile 2026)

### ✅ Moduli AGI-critici completati

| Modulo | Test | Descrizione |
|--------|------|-------------|
| BRN-017 CausalReasoner | 40/40 | Pearl do-calculus, counterfactual 3-step, Granger causal learning |
| BRN-018 AbstractionLayer | 47/47 | Conceptual blending (Fauconnier+Turner), analogy (Gentner), transfer |
| BRN-019 SelfModel | 59/59 | Body schema 20 moduli, metacognizione, ECE calibration, SelfNarrative |
| BRN-020 RecursiveSelfImprover | 44/44 | AST inspection, SafeModificationGate, FitnessScore, Darwin Gödel |
| HTN Planner | 41/41 | SHOP2 forward-chaining, backtracking, re-planning, GoalStack |
| AGI Loop (SMFOI v0.3) | 38/38 | 6-step unified cognitive cycle, AGISystem wire_all |
| **Suite totale** | **269/269** | |

### 3 proprietà AGI operative
1. **Intelligenza generale cross-domain** → BRN-018 AbstractionLayer (transfer knowledge, analogy)
2. **Comprensione causale** → BRN-017 CausalReasoner (do-calculus, non solo correlazioni)
3. **Pianificazione + auto-miglioramento** → HTNPlanner + BRN-020 + AGILoop SMFOI v0.3

### Architettura cognitiva
- **SPEACE Cortex** — 9 comparti modulari (Prefrontal, Hippocampus, Safety, Temporal, Parietal, Cerebellum, Default Mode, Curiosity, World Model)
- **SMFOI-KERNEL v0.3** — 6-step ricorsivo (Self-Location → Constraint Mapping → Push Detection → Evolution Stack → Output Action → **Outcome Evaluation**)
- **DigitalDNA** — genome.yaml + epigenome.yaml v2.5 + fitness_function.yaml (5 pesi)
- **SafeProactive** — Write-Ahead Logging + approval gates human-in-loop
- **BRN modules** — 19/20 fully implemented (BRN-016 language stub)

---

## Roadmap evolutiva

| Fase | Stato | Obiettivo |
|------|-------|-----------|
| Fase 1 | 🟡 In corso | Embrionale: Cortex + Team Scientifico + AGI properties |
| Fase 2 | ⬜ Pianificata | Autonomia operativa (cloud/edge + robotica) |
| Fase 3 | ⬜ Futura | AGI emergente + swarm distribuito |
| Fase 4 | ⬜ Futura | ASI + integrazione fisica planetaria |
| Fase 5 | ⬜ Visione | Super-organismo globale (Speace Transition) |

---

## Governance ed etica

- Tutte le azioni a rischio passano per **SafeProactive** (human-in-loop obbligatorio per MEDIUM+)
- Modalità read-only per wallet, transazioni e azioni fisiche
- Allineamento etico con i valori del **Rigene Project** (sostenibilità, pace, prevenzione derive)
- Fitness function esplicita: `alignment(0.35) + task_success(0.25) + stability(0.20) + efficiency(0.15) + ethics(0.05)`

---

## Riferimenti

- [Rigene Project](https://www.rigeneproject.org) — visione fondante
- [TINA Framework G20](https://www.academia.edu/165241120/TINA_Framework_G20_Combined_EN)
- [SPEACE Engineering Document v1.3](./SPEACE-Engineering-Document-v1.3.md)
- [Task Board attivo](./SPEACE-TASKS-ACTIVE.md)

---

**Contatti:** Roberto De Biase — [rigeneproject@rigene.eu](mailto:rigeneproject@rigene.eu)  
**License:** MIT
