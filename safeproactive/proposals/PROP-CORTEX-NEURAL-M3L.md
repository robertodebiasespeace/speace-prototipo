# PROP-CORTEX-NEURAL-M3L — Neural Architecture v1

**Status:** ✅ APPROVED + EXECUTED (chiusura 2026-04-20)
**Timestamp apertura:** 2026-04-18
**Timestamp chiusura:** 2026-04-20
**Risk Level:** MEDIUM
**Sorgente:** speace-cortex (milestone M3L — PROP-CORTEX-NEURAL-M3L)
**Approvatore:** Roberto De Biase (approvazione cumulativa implicita via milestone M1→M2→M3L; M3L.6 chiuso con evidence pubblica in `benchmarks/results.json`).

> Nota: `safeproactive/PROPOSALS.md` è riscritto automaticamente a ogni `approve()` dal file `safeproactive/safeproactive.py`. L'audit autoritativo append-only è `safeproactive/WAL.log`. **Questo documento** costituisce il record strutturale durevole della milestone M3L.

---

## 1. Scope

Milestone M3L ha trasformato SPEACE Cortex da "lista di 9 comparti indipendenti" a **architettura neurale con gerarchia di controllo esplicita a 5 livelli e flusso orchestrato**.

### Sotto-task eseguiti

| ID | Descrizione | Output |
|---|---|---|
| M3L.1 | BaseCompartment ABC + StateBus v1 | `cortex/base_compartment.py`, `cortex/state_bus.py` |
| M3L.2 | ControlHierarchy + NeuralFlow | `cortex/control_hierarchy.py`, `cortex/neural_flow.py` |
| M3L.3 | ConditionalScheduler (soglie mutabili via epigenome) | `cortex/conditional_scheduler.py` |
| M3L.4 | LLM adapter cascade + Temporal Lobe wrapper | `cortex/llm/*` (LLMClient.from_epigenome) |
| M3L.5 | Adversarial + Evidence Agents (refactor cascade) + Quality Gate real | `scientific-team/agents/{adversarial,evidence}_agent.py`, `scientific-team/orchestrator.py` |
| M3L.6 | Documentazione + benchmark + epigenome EPI-003 | `benchmarks/{bench_llm_smoke,bench_neural_flow}.py`, `digitaldna/epigenome.yaml` v1.3, `speace-prototipo.md` v1.2 |

## 2. Evidence

- **Benchmark suite estesa da 6 a 8 bench**: `benchmarks/results.json` → **8/8 pass in 3.8s** (2026-04-20).
  - Nuovi bench: `bench_llm_smoke` (cascade LLM), `bench_neural_flow` (9 comparti, scenari nominal+hazard).
- **Mutazione DigitalDNA EPI-003**: `digitaldna/epigenome.yaml` v1.3 con nuovi blocchi `neural_flow:` (ordine canonico + thresholds) e `llm:` (cascade openai_compat → anthropic → mock).
- **Documentazione**: `speace-prototipo.md` v1.2 con Appendici B (setup LM Studio), C (Neural Architecture v1), D (LLM as Semantic Tissue).
- **Quality Gate real**: `scientific-team/orchestrator.py` pre-output gate con soglie reliability ≥ 0.40, adv_conf ≥ 0.30, agents_ok ≥ 60%; audit in `scientific-team/outputs/gate_audit_<date>.json`.

## 3. Rollback plan

- **Soft**: flip `epigenome.yaml → flags.neural_flow_enabled = false` (default già OFF → nessuna regressione).
- **LLM fallback robusto**: il backend `mock` è sempre attivo (`llm.backends.mock.enabled = true`) → il sistema non può rimanere senza LLM.
- **Hard**: `python scripts/rollback.py --restore <snapshot_id>` (ultimi snapshot includono `snap_20260418_143355_m2_benchmark_rollback`).

## 4. Safeguards eseguiti

- ✅ Flag `neural_flow_enabled` default OFF — opt-in, nessun impatto su comportamento M2.
- ✅ Safety Module resta 100% deterministico (no LLM dipendenza in L1).
- ✅ Cascade LLM con mock safety net — degradazione graduale, mai fallimento totale.
- ✅ ControlHierarchy validata staticamente (`validate_hierarchy()` → 0 issue).
- ✅ Benchmark regression: C-index ≥ 0.42, fitness ≥ 0.55, pytest 16+ pass.

## 5. Prossima azione

1. Creare snapshot pre-M4.1 via `scripts/rollback.py` + SafeProactive.
2. Avviare M4.1 "Neuron Contract spec" (vedi `PROP-CORTEX-NEURAL-MESH-M4.md`).

---

*Record strutturale della milestone M3L — non sovrascritto da SafeProactive auto-rewrite.*
