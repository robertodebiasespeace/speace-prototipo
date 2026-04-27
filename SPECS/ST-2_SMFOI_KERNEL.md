# SCHEDA TECNICA ST-2 – SMFOI-KERNEL
**Versione:** 0.3 (target)  
**Data:** 17 aprile 2026  
**Stato:** v0.2 in produzione · v0.3 in sviluppo

---

## 1. Descrizione

**SMFOI-KERNEL** (Schema Minimo Fondamentale di Orientamento dell'Intelligenza) è un protocollo ricorsivo e substrate-agnostico che trasforma agenti reattivi in intelligenze auto-orientate, proattive e autonome.

## 2. Evoluzione del Protocollo

### v0.2 (Attuale – 5 step)

```
Self-Location → Constraint Mapping → Push Detection → Survival & Evolution Stack → Output Action
```

### v0.3 (Target – 6 step) ← NUOVO STEP AGGIUNTO

```
Self-Location → Constraint Mapping → Push Detection → Survival & Evolution Stack → Output Action → Outcome Evaluation & Learning
                                                                                              ↑
                                                                                     NUOVO: Outcome Evaluation & Learning
```

## 3. Architettura 6-Step v0.3

### Step 1: SELF-LOCATION

**Scopo:** Definire posizione attuale nel SEA (Self-Evolving Agent)

**Domande chiave:**
- Chi sono?
- Cosa sono?
- Dove opero?
- Qual è il mio stato attuale?

**Output:** `self_state` object

```yaml
self_location:
  identity: "SPEACE v1.0"
  type: "SuPer Entità Autonoma Cibernetica Evolutiva"
  position: "Cloud/Server - OpenClaw framework"
  current_state:
    alignment_score: 67.3
    active_compartments: 9
    team_status: "operational"
    proposals_queue: 28
  last_heartbeat: "2026-04-17T12:00:00Z"
```

### Step 2: CONSTRAINT MAPPING

**Scopo:** Identificare vincoli attuali

**Vincoli mappati:**
- Risorse: RAM, CPU, GPU, storage
- Policy: DigitalDNA rules, SafeProactive gates
- Hardware: 16GB RAM, i9-11900H, RTX 3060
- Regolatori: EU AI Act, NIST, ISO 42001

**Output:** `constraints` object

```yaml
constraint_mapping:
  resources:
    ram_available: "16GB"
    ram_allocated: "12.5GB"
    cpu: "i9-11900H @ 2.50GHz"
    gpu: "RTX 3060"
  policies:
    digitaldna_active: true
    safeproactive_gates: ["low", "medium", "high", "regulatory"]
    human_in_loop: mandatory_for_critical
  hardware_limits:
    max_concurrent_agents: 8
    max_ram_usage: "13GB"
  regulatory:
    eu_ai_act_compliance: required
    nist_framework: required
```

### Step 3: PUSH DETECTION

**Scopo:** Rilevare forze esterne che richiedono azione

**Tipi di push:**
- User request (prompt, task)
- IoT events (sensor data, alerts)
- Market data (crypto, commodities)
- Temporal triggers (60-min heartbeat)
- Team Scientifico proposals
- SelfImproving feedback

**Output:** `push_signals` array

```yaml
push_detection:
  signals:
    - type: "user_request"
      priority: high
      content: "Analizza stato ecosistema"
    - type: "iot_event"
      priority: medium
      source: "climate_sensors"
      data: {...}
    - type: "heartbeat"
      priority: low
      interval: 60_minutes
    - type: "proposal"
      priority: medium
      id: "PROPOSAL-28"
      from: "Team Scientifico"
```

### Step 4: SURVIVAL & EVOLUTION STACK

**Scopo:** Determinare livello di risposta appropriato

**Livelli:**

| Livello | Nome | Comportamento |
|---------|------|---------------|
| Lv0 | Reattivo | Risposta diretta a stimulus |
| Lv1 | Adattivo | Apprendimento da feedback |
| Lv2 | Proattivo | Goal-seeking, pianificazione |
| Lv3 | Auto-modificante | Modifica del protocollo stesso |

**Output:** `response_level` + `strategy`

```yaml
survival_evolution_stack:
  selected_level: 2
  reasoning: "User request richiede goal-seeking + planning"
  strategy:
    primary: "Analizza → Pianifica → Esegui"
    fallback_level: 1
    max_retries: 3
```

### Step 5: OUTPUT ACTION

**Scopo:** Eseguire azione con safety gates

**Pipeline:**
```
Proposta → SafeProactive Review → Approval/Rejection → Execution → Logging
```

**Output:** `action_result`

```yaml
output_action:
  action_type: "query_world_model"
  safe_proactive:
    proposal_id: "PROPOSAL-28"
    risk_level: "low"
    status: "approved"
    approved_by: "auto"
  execution:
    endpoint: "http://localhost:8003/query"
    params: {...}
    status: "success"
  mutation_triggered: false
```

### Step 6: OUTCOME EVALUATION & LEARNING ← NUOVO (v0.3)

**Scopo:** Misurare esito reale e generare learning

**Funzioni:**
- Misurare successo/fallimento dell'azione
- Calcolare feedback per fitness function
- Aggiornare epigenome.yaml e World Model
- Generare mutazioni mirate o correzioni

**Output:** `evaluation_result`

```yaml
outcome_evaluation:
  action_id: "ACTION-28"
  success: true
  metrics:
    task_success_rate: 0.92
    alignment_delta: +0.3
    resource_efficiency: 0.87
  fitness_update:
    new_fitness: 0.71
    delta: +0.02
  world_model_update:
    entities_modified: ["climate_data", "noaa_feed"]
    confidence_increase: 0.05
  mutation_suggested: false
  reason: "Fitness acceptable, no mutation needed"
```

## 4. Caratteristiche Chiave

| Caratteristica | Valore |
|----------------|--------|
| Token overhead | 2-15 token/ciclo |
| Ricorsivo | Sì (Lv3 permette auto-modifica) |
| Intrinsic motivation | Curiosità + Esplorazione |
| Sicurezza | Integrato SafeProactive |
| Substrate-agnostic | Sì (portabile) |

## 5. Integrazioni

- SPEACE Cortex (kernel centrale)
- DigitalDNA (mutazioni epigenetiche)
- speace-cortex-evolver (stimolazione 60 min)
- World Model (Outcome Evaluation)
- SafeProactive (Output Action gate)

## 6. Perché il 6° Step è Obbligatorio

Senza **Outcome Evaluation & Learning** il sistema rischia di:
- Non imparare sistematicamente dagli errori
- Ripetere failure patterns
- Non aggiornare World Model con feedback reali
- Derivare da obiettivi fitness

## 7. Implementazione v0.3

```python
# Pseudo-codice SMFOI-KERNEL v0.3
def smfoi_cycle(agent_state, external_push):
    # Step 1-5 (esistenti)
    self_state = self_location(agent_state)
    constraints = constraint_mapping(agent_state, resources)
    push_signals = push_detection(external_push)
    response = survival_evolution_stack(self_state, push_signals)
    action_result = output_action(response, safe_proactive)
    
    # Step 6 NUOVO
    evaluation = outcome_evaluation(action_result)
    if evaluation.mutation_needed:
        trigger_epigenetic_mutation(evaluation)
    update_world_model(evaluation)
    update_fitness_function(evaluation)
    
    return action_result
```
