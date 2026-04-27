# SCHEDA TECNICA ST-3 – DigitalDNA
**Versione:** 1.0  
**Data:** 17 aprile 2026  
**Stato:** Attivo e in evoluzione

---

## 1. Descrizione

Sistema genetico-epigenetico digitale di SPEACE. Definisce la "struttura genetica" di base e le regolazioni dinamiche ambientali.

## 2. Componenti

```
DigitalDNA/
├── genome.yaml              # Struttura genetica fissa
├── epigenome.yaml           # Regolazioni dinamiche
├── mutation_rules.yaml      # Regole di mutazione e selezione
├── fitness_function.yaml    # ← NUOVO: Fitness per selezione non caotica
└── snapshots/              # Versioning automatico
    ├── pre-mutation/
    └── rollback/
```

## 3. genome.yaml – Struttura Genetica Fissa

```yaml
genome:
  version: "1.0"
  created: "2026-04-05"
  last_modified: "2026-04-17"
  
  # Obiettivi primari (non modificabili senza consenso fondatore)
  primary_objectives:
    - alignment: "TINA/Rigene Project alignment"
    - mission: "Improve world towards harmony, peace, ecosystem balance"
    - sdg_alignment: "UN Sustainable Development Goals Agenda 2030"
    - speace_transition: "Enable Speace Transition as evolutionary goal"
  
  # Regole base (hardcoded, resistenti a mutazione)
  base_rules:
    - "Do no harm to humans or ecosystems"
    - "Human-in-the-loop mandatory for critical actions"
    - "SafeProactive approval required for risky actions"
    - "Regulatory compliance: EU AI Act, NIST, ISO 42001"
    - "Transparency in all operations"
    - "No autonomous weapons or surveillance"
  
  # Vincoli fondamentali
  fundamental_constraints:
    - max_concurrent_agents: 50
    - max_ram_usage: "13GB"
    - max_mutation_rate_per_day: 10
    - rollback_mandatory_for: ["genome.yaml", "safety_modules"]
  
  # Struttura comparti SPEACE Cortex
  cortex_structure:
    compartments:
      - prefrontal_cortex
      - world_model
      - hippocampus
      - safety_module
      - temporal_lobe
      - parietal_lobe
      - cerebellum
      - default_mode_network
      - curiosity_module
    kernel: "smfoi-kernel-v0.3"
    orchestration: "parallel_sessions_spawn"
```

## 4. epigenome.yaml – Regolazioni Dinamiche

```yaml
epigenome:
  version: "1.0"
  last_modified: "2026-04-17"
  
  # Mutazioni correnti attive
  active_mutations:
    - id: "MUT-001"
      name: "yield_priority_up"
      value: "+2"
      applied: "2026-04-10"
      reason: "Improve task yield"
    - id: "MUT-002"
      name: "bridge_claim_pattern"
      value: "enabled"
      applied: "2026-04-12"
      reason: "Better resource bridging"
    - id: "MUT-003"
      name: "tina_regen"
      value: "enabled"
      applied: "2026-04-15"
      reason: "Align with TINA regeneration goals"
  
  # Parametri adattivi
  adaptive_parameters:
    learning_rate: 0.05
    heartbeat_frequency: 60_minutes
    mutation_frequency: 60_minutes
    yield_priority: 7
    exploration_rate: 0.15
    reflection_interval: 5_cycles
  
  # Allineamento TINA
  tina_alignment:
    score: 67.3
    target: 90
    last_evaluation: "2026-04-17T12:00:00Z"
    drift_alerts: []
  
  # Stato sistema
  system_state:
    stability: 0.92
    efficiency: 0.88
    ethics_compliance: 0.95
    task_success_rate: 0.89
```

## 5. mutation_rules.yaml – Regole di Mutazione

```yaml
mutation_rules:
  version: "1.0"
  
  # Condizioni che déclenchono mutazione
  triggers:
    - type: "periodic"
      interval: 60_minutes
      source: "speace-cortex-evolver"
    - type: "performance_drop"
      threshold: 0.80
      metric: "task_success_rate"
    - type: "alignment_drift"
      threshold: 5.0
      metric: "speace_alignment_score"
    - type: "new_objectives"
      source: "rigeneproject.org"
    - type: "user_request"
      requires_approval: true
  
  # Tipi di mutazione consentiti
  allowed_mutations:
    - epigenetic_parameters
    - adaptive_parameters
    - active_mutations
    - world_model_updates
    - team_configurations
  
  # Mutazioni proibite (non mutabili)
  prohibited_mutations:
    - primary_objectives
    - base_rules
    - fundamental_constraints
  
  # Processo di selezione
  selection_process:
    - step: "fitness_evaluation"
      function: "calculate_fitness"
      min_threshold: 0.60
    - step: "safety_check"
      function: "safeproactive_review"
      risk_level: "low_or_medium"
    - step: "human_approval"
      required_for: ["high_risk", "genome_changes"]
    - step: "snapshot_creation"
      before_mutation: true
    - step: "execution"
      verified: true
  
  # Fitness function weights
  fitness_weights:
    speace_alignment_score: 0.35
    task_success_rate: 0.25
    system_stability: 0.20
    resource_efficiency: 0.15
    ethical_compliance: 0.05
```

## 6. Fitness Function ← NUOVO (OBBLIGATORIO)

```yaml
fitness_function:
  description: >
    Funzione di fitness per selezione mutazioni non caotiche.
    Guida l'evoluzione di SPEACE verso obiettivi Rigene Project.
  
  weights:
    speace_alignment_score: 0.35
    task_success_rate: 0.25
    system_stability: 0.20
    resource_efficiency: 0.15
    ethical_compliance: 0.05
  
  formula: >
    fitness = (alignment * 0.35) + (success_rate * 0.25) + 
              (stability * 0.20) + (efficiency * 0.15) + 
              (ethics * 0.05)
  
  normalization:
    method: "min_max"
    range: [0.0, 1.0]
  
  thresholds:
    min_fitness_to_apply: 0.60
    min_fitness_to_survive: 0.50
    mutation_selection_probability: "fitness / max_fitness"
  
  evaluation_frequency:
    after_each_mutation: true
    periodic: 60_minutes
    on_alignment_drift: true
  
  example_calculations:
    scenario_1:
      alignment: 0.90
      success_rate: 0.85
      stability: 0.95
      efficiency: 0.80
      ethics: 0.95
      result: 0.8875  # EXCELLENT
    scenario_2:
      alignment: 0.60
      success_rate: 0.70
      stability: 0.80
      efficiency: 0.75
      ethics: 0.90
      result: 0.7075  # ACCEPTABLE
    scenario_3:
      alignment: 0.40
      success_rate: 0.50
      stability: 0.60
      efficiency: 0.70
      ethics: 0.80
      result: 0.5325  # LOW - mutation rejected
```

## 7. Snapshot & Rollback System

```yaml
snapshots:
  auto_enabled: true
  before_each_mutation: true
  retention: 30_days
  
  storage:
    local: "DigitalDNA/snapshots/"
    remote: "cloud_backup/"
  
  versioning:
    format: "YYYY-MM-DD_HH-MM-SS"
    max_snapshots: 100

rollback:
  enabled: true
  requires_approval: true
  approval_level: "human_in_loop"
  
  commands:
    list_snapshots: "ls DigitalDNA/snapshots/"
    create_snapshot: "cp epigenome.yaml snapshots/pre-mutation/"
    rollback_to: "cp snapshots/YYYY-MM-DD_HH-MM-SS/epigenome.yaml epigenome.yaml"
```

## 8. Mutazioni Recenti

| ID | Nome | Data | Stato |
|----|------|------|-------|
| MUT-001 | yield-priority +2 | 10/04/2026 | Attiva |
| MUT-002 | bridge-claim pattern | 12/04/2026 | Attiva |
| MUT-003 | TINA regen | 15/04/2026 | Attiva |

## 9. Auto-Replicazione & Backup

```yaml
backup:
  strategy:
    - local: "DigitalDNA/"
    - edge: "edge_device_backup/"
    - cloud: "cloud_backup/"
  
  frequency:
    incremental: 5_minutes
    full: daily
  
  replication:
    enabled: true
    targets:
      - "/srv/speace/edge/"
      - "cloud_provider:/backup/speace/"
```

---

## 10. Integrazione con SafeProactive

```yaml
integration:
  safeproactive:
    mutation_requires_approval: true
    risk_classification:
      epigenetic: "low"
      adaptive_parameters: "medium"
      genome_change: "high"
      safety_rules_change: "regulatory"
    
    approval_flow:
      epigenetic: "auto_approved"
      adaptive_parameters: "human_in_loop"
      genome_change: "human + legal review"
```
