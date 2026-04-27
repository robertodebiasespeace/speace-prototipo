# PROP-COGNITIVE-AUTONOMY-M5

> **Proposta SafeProactive estesa** — Milestone architetturale M5 "Cognitive Autonomy" (post M4-CNM).
> **Status: APPROVED** — approvata dall'utente (Roberto De Biase, direttore orientativo) con stringa canonica `APPROVATA PROP-COGNITIVE-AUTONOMY-M5` il 2026-04-24. Scope full (nessuna opzione 9.x restrittiva specificata).

---

## 0. Metadata

| Campo | Valore |
|---|---|
| **ID proposta** | `PROP-COGNITIVE-AUTONOMY-M5` |
| **Timestamp bozza** | 2026-04-21 |
| **Sorgente** | speace-cortex (evolutionary-dev-agent) post-analisi corpus Organismic AI Initiative (23 PDF) |
| **Milestone** | M5-COGNITIVE-AUTONOMY (post-M4-CNM) |
| **Risk Level complessivo** | **MEDIUM** (tutti i moduli di default OFF / opt-in via flag epigenome, nessuna mutazione operativa automatica) |
| **Human-in-the-loop** | **Obbligatorio** per M5.0.a (approvazione) e per ogni attivazione di default OFF → ON |
| **Snapshot pre-esecuzione richiesto** | Sì: `snap_YYYYMMDD_HHMMSS_m5_autonomy_init` prima di M5.1 |
| **Rollback plan** | Sì (vedi §7) |
| **Prerequisito** | M4-CNM completato (task `#31–#52`, almeno fino a M4.20 chiuso) |
| **Source di razionale** | Corpus "Organismic AI Initiative" (23 PDF), in particolare `BRIGHT_attNA_SPEACE_Critical_Analysis.pdf`, `Artificial Organismic General Intelligence.pdf`, `attNA.pdf`, `Organismic AI - From Tools to Organisms.pdf` |

---

## 1. Executive Summary

Colmare i **6 gap funzionali di autonomia cognitiva** identificati nell'analisi critica BRIGHT/attNA a SPEACE, trasformando l'architettura attuale (che è *orchestrazione esterna di componenti con vincoli imposti*) in un organismo con **autonomia cognitiva endogena**: omeostasi intrinseca, motivazione endogena, memoria autobiografica, loop sensoriomotorio autonomo, plasticità strutturale virtuale, vincoli evolutivi emergenti.

Non è una riscrittura: è un **layer aggiuntivo** (il decimo comparto Cortex + tre sottosistemi) che riusa il MeshRuntime M4.6 come substrato per segnali omeostatici continui e mappa gli attNA validation constraint nell'architettura interna di SPEACE, anziché mantenerli come regole esterne in SafeProactive. SafeProactive resta invariato come meccanismo di approval, ma si aggiunge un *secondo livello* di vincoli intrinseci la cui violazione produce perdita di viabilità misurabile (non divieto normativo).

**Obiettivo misurabile**: passare il *Cognitive Autonomy Score* da 0/6 (baseline attuale, BRIGHT critique) a ≥4/6 entro M5.20, con metriche quantitative per ogni gap chiuso.

---

## 2. Razionale

### 2.1 Perché ora

1. **M4-CNM fornisce il substrato computazionale necessario.** MeshRuntime + MeshGraph + Needs Driver offrono già il flusso continuo di task tipizzati e il loop di feedback su cui innestare omeostasi e motivazione endogena senza dover riprogettare l'infrastruttura.
2. **Il corpus Organismic AI Initiative è ora letto e mappato.** L'analisi dei 23 PDF (21 Apr 2026) ha prodotto una lista di 6 gap funzionali concreti, misurabili, con soluzioni architetturali già abbozzate in letteratura (AOGI, attNA, Informational Governance).
3. **Allineamento Rigene richiede autonomia genuina, non eteronomia.** SPEACE come "super-organismo" nella visione TINA non può restare un orchestratore guidato da obiettivi esterni: deve avere *stato interno* che risponde alla sua stessa viabilità. Senza questo, la Fase 2 (Autonomia operativa) non è raggiungibile in senso proprio.
4. **Alignment score in stallo a 67.3/100.** Il gate Fase 2 è 80/100. L'analisi suggerisce che i gap di autonomia cognitiva sono la principale barriera residua — non servono più feature, serve profondità.
5. **Compliance-by-design rafforzato.** Vincoli intrinseci architetturali (GAP 6) sono una risposta più robusta all'EU AI Act "high-risk system integrity" rispetto ai soli approval gate: il sistema *non può* violare i vincoli senza degradare se stesso, non *non deve*.

### 2.2 Allineamento Rigene Project / TINA

| Principio Rigene | Realizzazione in M5-COGNITIVE-AUTONOMY |
|---|---|
| Super-organismo cognitivo autonomo | Omeostasi intrinseca + motivazione endogena → stato interno proprio |
| Armonia funzionale | Homeostatic Controller penalizza deviazioni dallo stato armonico interno |
| Digital DNA evolutivo | Autobiographical Consolidation preserva identità strutturale attraverso mutazioni |
| Governance etica distribuita | Vincoli intrinseci emergenti complementano SafeProactive (non lo sostituiscono) |
| Interconnessione bio-tecnologica | Sensorimotor Loop autonomo = primo passo verso sensing attivo IoT/ambiente |
| Evoluzione continua | Plasticità strutturale virtuale sul MeshGraph → topology discovery dinamica |

### 2.3 Mapping dei 6 gap BRIGHT sui task M5

| Gap BRIGHT | Componente M5 | Task cluster | Metrica di chiusura |
|---|---|---|---|
| GAP 1 – Omeostasi cognitiva | Homeostatic Controller (10° comparto Cortex) | M5.1–M5.4 | `dh/dt` presente, `h_setpoint` emergente, `viability_score ∈ [0,1]` calcolato ogni heartbeat |
| GAP 2 – Motivazione endogena | Endogenous Value Field | M5.5–M5.7 | Coherence Φ(t) nella fitness function; peso alignment 0.35 → 0.20, nuovo peso coherence 0.15 |
| GAP 3 – Memoria autobiografica | Autobiographical Consolidator | M5.8–M5.10 | Identity graph persistente (SQLite), distinzione event/structure, score continuity ≥ 0.90 |
| GAP 4 – Loop sensoriomotorio | Attentional Gating Policy | M5.11–M5.13 | `π(s(t))` che sceglie query IoT/world_model; diversità entropy ≥ 2.0 bit |
| GAP 5 – Plasticità strutturale | Virtual Plasticity sul MeshGraph | M5.14–M5.16 | Edge pruning/growth con metaplasticity rules; topo delta/settimana > 0 sotto soglia |
| GAP 6 – Vincoli evolutivi intrinseci | Intrinsic Constraint Layer | M5.17–M5.19 | Violazione genera dh/dt negativo; no regola esterna aggiunta |

---

## 3. Scope

### 3.1 Componenti che M5 **introduce**

```
cortex/
  homeostasis/              (NEW)
    controller.py           — setpoint emergenti, segnale dh/dt, viability scoring
    receptors.py            — adapter che leggono metriche da CNM, LLM, DNA, SPT
  motivation/               (NEW)
    value_field.py          — campo valore interno V_internal(s, h)
    coherence.py            — calcolo Phi(t) = Σ wi·Ci(t)
  memory/
    autobiographical.py     (NEW) — consolidator multi-timescale
    identity_graph.sqlite   (NEW, runtime) — store persistente identità
  attention/                (NEW)
    gating.py               — π(s(t)) policy, selezione sensory input
    curiosity.py            — refactor del Curiosity Module esistente
cortex/mesh/
  plasticity.py             (NEW) — metaplasticity rules per MeshGraph
  constraint_layer.py       (NEW) — vincoli intrinseci architetturali
digitaldna/
  fitness_function.py       (UPDATE) — ricalibra pesi: alignment 0.20, coherence 0.15
benchmarks/
  bench_autonomy.py         (NEW) — suite che misura Cognitive Autonomy Score 0..6
reports/
  cognitive_autonomy_score.md (NEW, runtime) — aggiornato ogni ciclo
```

### 3.2 Componenti che M5 **non tocca**

- `SMFOI-KERNEL` (nessuna modifica ai 5/6 step, solo nuovo input dal Homeostatic Controller allo Step 4 Survival Stack)
- `SafeProactive` (rimane invariato; vincoli intrinseci sono *complementari*, non sostitutivi)
- `MeshRuntime` M4.6 (usato come substrato, non modificato)
- `Neural Flow` M3L.2 (continuazione, nessuna rottura)
- `Team Scientifico` (Adversarial e Evidence restano esterni al loop di autonomia)

### 3.3 Fasi di implementazione (proposta, da validare in M5.0)

**Fase M5A — Omeostasi + Coerenza (M5.1–M5.7)**. Chiude GAP 1 e GAP 2. Introduce il decimo comparto Cortex e ricalibra la fitness function. Default OFF via `epigenome.homeostasis_enabled: false`.

**Fase M5B — Memoria autobiografica (M5.8–M5.10)**. Chiude GAP 3. Consolidator che distingue event memory da structural memory. Nessun impatto sul flusso principale finché non viene consultato esplicitamente.

**Fase M5C — Attenzione e plasticità (M5.11–M5.16)**. Chiude GAP 4 e GAP 5. Richiede MeshGraph stabile. Default OFF.

**Fase M5D — Vincoli intrinseci (M5.17–M5.19)**. Chiude GAP 6. Da attivare solo dopo almeno 1 settimana di telemetria omeostasi pulita.

**Chiusura M5.20**. Report finale, calcolo Cognitive Autonomy Score, decisione su M6 (eventuale integrazione attNA distributed validation o salto a Fase 2 operativa).

---

## 4. Task breakdown proposto

Richiede approvazione dettagliata in M5.0; elenco qui come bozza.

- `#59 M5.0` — Approvazione umana stringa canonica `APPROVATA PROP-COGNITIVE-AUTONOMY-M5`.
- `#60 M5.0.a` — Snapshot pre-esecuzione, `snap_..._m5_autonomy_init`.
- `#61 M5.0.b` — Validare prerequisito M4.20 closed.
- `#62 M5.1` — Draft `cortex/homeostasis/controller.py` con `dh/dt` minimale, setpoint statici temporanei.
- `#63 M5.2` — Receptors: wiring a CNM/LLM/DNA/SPT metrics.
- `#64 M5.3` — Emergenza setpoint (learning online dei valori di riposo).
- `#65 M5.4` — Viability scoring nel Cortex + esposizione via dashboard.
- `#66 M5.5` — `motivation/value_field.py` con V_internal(s,h) e test.
- `#67 M5.6` — Calcolo Φ(t) con 3 componenti iniziali (integrazione funzionale, coerenza output, stabilità omeostatica).
- `#68 M5.7` — Mutazione `EPI-005` preparatoria: aggiunta blocchi `homeostasis:` e `motivation:` in epigenome.yaml (flag OFF di default).
- `#69 M5.8` — `memory/autobiographical.py` schema SQLite + operazioni base.
- `#70 M5.9` — Classificatore event vs structure memory.
- `#71 M5.10` — Continuity score + test con mutazione DNA simulata.
- `#72 M5.11` — `attention/gating.py` policy statica iniziale (uniforme).
- `#73 M5.12` — Trasformare policy in RL-driven (reward = Φ(t) incremento).
- `#74 M5.13` — Diversity entropy check nel benchmark.
- `#75 M5.14` — `mesh/plasticity.py` edge pruning rules (conservative).
- `#76 M5.15` — Edge growth rules (solo sotto approval SafeProactive per HIGH).
- `#77 M5.16` — Plasticity log su `mesh_state.jsonl`.
- `#78 M5.17` — `mesh/constraint_layer.py` definisce 3 vincoli intrinseci iniziali (coherence ≥ soglia, homeostasis balance, audit trail presence).
- `#79 M5.18` — Wiring: violazione → penalità omeostatica.
- `#80 M5.19` — Test end-to-end: iniettare violazione, verificare degrado viability.
- `#81 M5.20` — Report finale + Cognitive Autonomy Score + proposta M6.

---

## 5. Mutazione DNA preparatoria — EPI-005

Da applicare in `digitaldna/epigenome.yaml` in M5.7, descrizione:

```yaml
meta:
  version: "1.4"
  last_mutation_id: "EPI-005"
  mutation_count: 5
  # EPI-004: M4-CNM — blocco mesh: + flag mesh_enabled: false (tracked in M4.18)
  # EPI-005: M5-COGNITIVE-AUTONOMY — blocchi homeostasis:, motivation:,
  #          autobiographical_memory:, attention:, plasticity:, intrinsic_constraints:
  #          Tutti i flag *_enabled: false di default. Opt-in per sperimentazioni.
  #          (PROP-COGNITIVE-AUTONOMY-M5, snap_..._m5_autonomy_init)

homeostasis:
  enabled: false
  setpoint_learning: "online"
  viability_threshold: 0.40
  heartbeat_integration: true

motivation:
  enabled: false
  coherence_weight_in_fitness: 0.15
  value_field_backend: "local"

autobiographical_memory:
  enabled: false
  store: "sqlite"
  continuity_threshold: 0.90
  retention_days: 365

attention:
  enabled: false
  gating_policy: "rl"
  min_diversity_entropy_bit: 2.0

plasticity:
  enabled: false
  pruning_rate: 0.01
  growth_rate: 0.005
  safe_proactive_gate_for_growth: true

intrinsic_constraints:
  enabled: false
  constraints:
    - name: "coherence_floor"
      metric: "coherence_phi"
      min_value: 0.50
    - name: "homeostasis_balance"
      metric: "viability_score"
      min_value: 0.40
    - name: "audit_trail_presence"
      metric: "wal_recent_entries_count"
      min_value: 1
```

Ricalibrazione **mutation_rules.yaml** (fitness function v3) proposta:

```yaml
fitness_function:
  version: 3
  weights:
    speace_alignment_score: 0.20   # era 0.35
    coherence_phi: 0.15            # NUOVO (GAP 2 closure)
    task_success_rate: 0.25
    system_stability: 0.20
    resource_efficiency: 0.15
    ethical_compliance: 0.05
```

Entrambe le modifiche richiedono approval gate esplicito SafeProactive e snapshot pre-esecuzione.

---

## 6. Analisi del rischio

| Rischio | Probabilità | Impatto | Mitigazione |
|---|---|---|---|
| Setpoint omeostasi diverge per bug learning | Media | Alto (instabilità sistema) | Default OFF; attivazione solo dopo 48h dry-run con setpoint statici; rollback automatico se viability < 0.20 per > 3 heartbeat |
| Ricalibrazione fitness rompe selezione mutazioni | Bassa | Medio | Snapshot genome+epigenome+mutation_rules pre-modifica; A/B su 10 cicli simulati prima di commit |
| Autobiographical memory esplode in dimensioni | Media | Basso | Retention 365gg + compressione eventi routine; alert se size > 500MB |
| Plasticity dimostra bug che altera grafo prod | Bassa | Alto | Default OFF; growth richiede approval SafeProactive HIGH per ogni arco |
| Vincoli intrinseci creano deadlock con SafeProactive | Bassa | Alto | Test end-to-end M5.19 con scenari di violazione simulata; vincoli iniziali volutamente "morbidi" |
| Overrun di contesto / token | Bassa | Medio | Stesso pattern M4: file-per-task, no monoliti |
| Naturalistic fallacy nell'interpretazione CUB/attNA | Alta (intellettuale, non tecnico) | Medio | Framing esplicito nella documentazione: "IF goal X THEN vincolo Y necessario"; no affermazioni di "legge naturale" |

---

## 7. Rollback plan

1. Snapshot completo pre-M5.1: `snap_..._m5_autonomy_init` (include cortex/, digitaldna/, mesh/, epigenome.yaml, mutation_rules.yaml).
2. Ogni fase (M5A/B/C/D) produce snapshot intermedio prima di abilitare nuovi flag.
3. Rollback tramite `scripts/rollback.py --to snap_..._m5_autonomy_init`, stesso CLI già validato in M2.
4. Se Cognitive Autonomy Score non raggiunge ≥3/6 entro M5.20: **non promuovere** i flag a ON di default; mantenere opt-in indefinitamente e aprire PROP-COGNITIVE-AUTONOMY-M5-REVIEW.
5. Se un singolo modulo degrada viability sotto 0.20 per 3 heartbeat consecutivi: flag forzato a OFF + log in WAL + notifica dashboard.

---

## 8. Criteri di successo

- **Test regression suite**: tutti i test M4-CNM (74/74) continuano a passare.
- **Nuovi test M5**: almeno 40 test per i 6 cluster (≥6 per gap).
- **Cognitive Autonomy Score ≥ 4/6** alla chiusura M5.20, misurato da `bench_autonomy.py`.
- **Alignment score** stabile o in crescita (baseline 67.3/100).
- **Viability score** > 0.60 in regime di operazione normale.
- **Nessuna regressione performance**: MeshRuntime throughput ≥ 180 task/2s con 4 worker (era 200/110ms, degrado tollerato ≤20% per overhead omeostasi).
- **Zero violazioni SafeProactive** durante l'intero ciclo M5.

---

## 9. Decisioni richieste all'utente (M5.0)

Al momento dell'approvazione, l'utente dovrebbe decidere:

| Decision Point | Opzioni | Default suggerito |
|---|---|---|
| **9.1 Scope** | [A] Tutti i 6 gap / [B] Solo GAP 1-2-3 (Fase M5A+B) / [C] Solo omeostasi (Fase M5A) | [B] — GAP 4-5-6 più rischiosi, meglio validare prima su 3 gap |
| **9.2 Plasticity M5C** | [A] In M5 / [B] Rimandare a M6 come per M4 | [A] — MeshGraph M4.5 è ora maturo, appropriato implementare ora |
| **9.3 Fitness recalibration** | [A] v3 in M5.7 / [B] A/B only / [C] Skip per ora | [A] con A/B pre-commit (10 cicli simulati) |
| **9.4 Intrinsic Constraints** | [A] 3 vincoli iniziali / [B] Solo 1 (coherence) / [C] Skip | [A] — servono almeno 3 per dimostrare il pattern |
| **9.5 Hardware sensory loop** | [A] Solo virtuale (world_model) / [B] Preparare hook IoT stub | [A] — IoT reale fuori scope M5, stub può essere aggiunto in M6 |

---

## 10. Stima budget

- **Nuovi file**: ~15 (6 moduli principali + test + benchmark + docs)
- **Modifiche**: 3 file (fitness_function.py, epigenome.yaml, mutation_rules.yaml)
- **LOC stimate**: 2000–2600
- **Durata stimata**: 3–5 settimane di lavoro iterativo (dopo chiusura M4.20)
- **Token/context**: milestone naturalmente segmentabile in 6 cluster, ogni cluster < 30% context window

---

## 11. Approvazione

**Status attuale**: DRAFT — attesa stringa canonica utente.

Per approvare l'intera milestone scrivere:

```
APPROVATA PROP-COGNITIVE-AUTONOMY-M5
```

Per approvare con scope ridotto specificare l'opzione 9.1 scelta, esempio:

```
APPROVATA PROP-COGNITIVE-AUTONOMY-M5 [scope=B, plasticity=A, fitness=A, constraints=A, sensory=A]
```

Un'approvazione parziale o richieste di modifica vanno come risposta testuale libera e questa proposta sarà ristrutturata di conseguenza.

---

**Fine proposta.**
