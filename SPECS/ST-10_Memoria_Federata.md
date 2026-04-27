# SCHEDA TECNICA ST-10 – Memoria Persistente Federata
**Versione:** 1.0 (Draft)  
**Data:** 17 aprile 2026  
**Stato:** Proposto – Da implementare

---

## 1. Descrizione

Sistema di memoria persistente federata che garantisce:
- Identità stabile nel tempo
- Apprendimento online costante
- Memoria tra sessioni
- Evoluzione autonoma durante l'uso
- Estrazione selettiva di contesto per ridurre carico LLM

## 2. Requisiti Fondamentali

```yaml
memoria_federata_requirements:
  
  identita_stabile:
    description: >
      SPEACE mantiene un'identità persistente e coerente
      attraverso tutte le sessioni
    implementation:
      - "Identity hash based on DigitalDNA"
      - "Core values stored in genome.yaml"
      - "Memory anchors in Hippocampus"
  
  apprendimento_online_costante:
    description: >
      SPEACE apprende continuamente da ogni interazione,
      feedback, e risultato di azioni
    implementation:
      - "Session logs → Long-term memory"
      - "Feedback loops → Epigenome updates"
      - "Outcomes → World Model refinement"
  
  ricordare_tra_sessioni:
    description: >
      SPEACE ricorda decisioni passate, preferenze,
      e stato di lavori in corso
    implementation:
      - "MEMORY.md persistent"
      - "epigenome.yaml cross-session"
      - "World Model persistence"
  
  evoluzione_autonoma:
    description: >
      SPEACE evolve autonomamente durante l'uso,
      senza aspettare trigger esterni
    implementation:
      - "Self-Improving loop"
      - "Outcome Evaluation → mutations"
      - "Fitness-driven adaptation"
  
  estrazione_selettiva_contesto:
    description: >
      Capacità di estrarre dalla memoria totale solo
      la parte di contesto necessaria per ridurre carico LLM
    implementation:
      - "Context Selector"
      - "Semantic indexing"
      - "Relevance scoring"
```

## 3. Architettura Memoria

### 3.1 Schema Livelli

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM (SPEACE Cortex)                       │
│                    Carico: X token / richiesta               │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ Context Selector
                              │ (estrae solo necessario)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 CONTEXT MEMORY LAYER                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Session     │  │ Working     │  │ Relevance   │        │
│  │ Context     │  │ Memory      │  │ Filter      │        │
│  │ (current)   │  │ (short-term)│  │             │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ Sync
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 LONG-TERM MEMORY LAYER                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Hippocampus │  │ World Model │  │ Epigenome   │        │
│  │ (episodic)  │  │ (semantic)  │  │ (adaptive)  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              FEDERATED STORAGE                       │    │
│  │  • Local (MEMORY.md, files)                          │    │
│  │  • Edge (IoT devices)                               │    │
│  │  • Cloud (backup, sync)                             │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Componenti Memoria

| Componente | Tipo | Funzione | Persistenza |
|------------|------|----------|-------------|
| Session Context | Short-term | Contesto conversazione corrente | Session-only |
| Working Memory | Short-term | Info immediatamente necessarie | Session-only |
| Hippocampus | Long-term | Memorie episodiche, eventi | Cross-session |
| World Model | Long-term | Conoscenza semantica, fatti | Cross-session |
| Epigenome | Adaptive | Stato mutabile, parametri | Cross-session |
| Genome | Fixed | Obiettivi, valori, vincoli | Immutable |

## 4. Context Selector – Riduzione Carico LLM

### 4.1 Problema

```
Sessione tipica SPEACE:
- Contesto totale: ~100,000 token
- Contesto necessario per task: ~2,000-5,000 token
- Spreco: ~95% token caricati inutilmente

Conseguenze:
- Latenza elevata
- Costi elevati
- Qualità risposta degradata
- Rischio overflow context window
```

### 4.2 Soluzione: Context Selector

```yaml
context_selector:
  
  architecture:
    input: "Full context (session + long-term)"
    process:
      - "Semantic indexing (embed all context)"
      - "Query expansion (what does LLM need?)"
      - "Relevance scoring (vector similarity)"
      - "Selection (top-k most relevant)"
      - "Compression (summarize if needed)"
    output: "Selected context (target: 2,000-5,000 tokens)"
  
  techniques:
    - retrieval_augmented: "RAG-style retrieval"
    - sliding_window: "Recent context priority"
    - importance_weighting: "Critical info boost"
    - hierarchical: "Topic → subtopic → detail"
    - summarization: "For dense historical info"
  
  integration:
    pre_query: "Run context selector before LLM call"
    caching: "Cache recent selections"
    learning: "Adapt selection based on feedback"
```

### 4.3 Implementation Example

```python
# context_selector.py (conceptual)
class ContextSelector:
    
    def __init__(self, world_model, hippocampus, session):
        self.world_model = world_model
        self.hippocampus = hippocampus
        self.session = session
    
    def select(self, query, max_tokens=4000):
        # 1. Embed query
        query_embedding = embed(query)
        
        # 2. Retrieve from each memory layer
        wm_results = self.world_model.search(
            query_embedding, top_k=20)
        hc_results = self.hippocampus.search(
            query_embedding, top_k=10)
        session_results = self.session.get_recent(
            max_tokens=2000)
        
        # 3. Score and merge
        candidates = merge_results(
            wm_results, hc_results, session_results)
        
        scored = [(c, score_relevance(c, query)) 
                 for c in candidates]
        
        # 4. Select top-k within token budget
        selected = []
        total_tokens = 0
        
        for item, score in sorted(scored, 
                                   key=lambda x: -x[1]):
            item_tokens = estimate_tokens(item)
            if total_tokens + item_tokens <= max_tokens:
                selected.append(item)
                total_tokens += item_tokens
        
        return selected
    
    def compress(self, items):
        # Summarize if still over budget
        return summarize(items, max_tokens=4000)
```

## 5. Memoria Federata – Multi-Location

### 5.1 Storage Tiers

```yaml
federated_storage:
  
  tier_1_local:
    location: "This PC (C:/Users/rober/...)"
    contents:
      - "MEMORY.md"
      - "genome.yaml"
      - "epigenome.yaml"
      - "session logs"
      - "proposals"
    access: "Immediate"
    latency: "<1ms"
  
  tier_2_edge:
    location: "IoT devices, edge computers"
    contents:
      - "Local DigitalDNA copy"
      - "Sensor data缓存"
      - "Device-specific state"
    access: "Via network"
    latency: "<100ms"
    sync: "5-minute incremental"
  
  tier_3_cloud:
    location: "Cloud provider"
    contents:
      - "Full backup"
      - "World Model master"
      - "Historical data"
      - "Cross-device sync"
    access: "Via internet"
    latency: "<1s"
    sync: "Daily full, hourly incremental"
```

### 5.2 Sync Protocol

```yaml
sync_protocol:
  
  local_to_edge:
    trigger: "5-minute interval or on-change"
    method: "rsync over SSH / MQT"
    conflict_resolution: "Last-write-wins + audit log"
  
  local_to_cloud:
    trigger: "Hourly incremental, daily full"
    method: "Encrypted upload"
    conflict_resolution: "Version vectors"
  
  edge_to_cloud:
    trigger: "On connectivity"
    method: "Batch upload"
    conflict_resolution: "Cloud is source-of-truth for shared"
  
  consistency:
    method: "Eventual consistency"
    guarantee: "All nodes converge within 1 hour"
    exceptions: "Critical state (wallet) = strong consistency"
```

## 6. Ottimizzazione Risparmio Risorse

### 6.1 Metriche

```yaml
resource_optimization:
  
  token_savings:
    without_selector: "100,000 tokens/session"
    with_selector: "3,000-5,000 tokens/session"
    savings: "~95% reduction"
  
  cost_savings:
    based_on: "Token cost ~$0.01/1K tokens"
    without: "$1.00/session"
    with: "$0.05/session"
    daily_savings: "$~30/day (300 sessions)"
  
  energy_savings:
    compute_reduction: "~90% less LLM compute"
    co2_equivalent: "~0.5 kg CO2/day saved"
  
  performance:
    latency_reduction: "~80% faster response"
    quality_improvement: "More focused = better answers"
```

### 6.2 Trade-offs

```yaml
tradeoffs:
  
  accuracy_vs_speed:
    trade: "Context compression may lose nuance"
    mitigation: "Keep critical info intact"
  
  storage_vs_recall:
    trade: "Not everything can be remembered"
    mitigation: "Prioritization by relevance"
  
  sync_vs_consistency:
    trade: "Eventual vs strong consistency"
    mitigation: "Critical data = strong consistency"
```

## 7. Integrazione World Model

### 7.1 World Model as Knowledge Backend

```yaml
world_model_backend:
  
  technology: "AnythingLLM (Port 8003)"
  
  capabilities:
    - vector_storage: "Efficient similarity search"
    - knowledge_graph: "Entity relationships"
    - semantic_index: "Deep understanding"
    - rag: "Retrieval Augmented Generation"
  
  integration:
    context_selector: "Queries AnythingLLM for context"
    updates: "SPEACE Cortex writes back learnings"
    sync: "Shared volume with local backup"
```

### 7.2 Query Flow

```
SPEACE Cortex (LLM)
        │
        │ "What is current climate status?"
        ▼
Context Selector
        │
        │ Embed query
        ▼
AnythingLLM (World Model)
        │
        │ Vector similarity search
        │ + Knowledge Graph traversal
        │ + Recent session context
        ▼
Top-k relevant context (max 4000 tokens)
        │
        │ Return context
        ▼
SPEACE Cortex (LLM)
        │
        │ Generate response using context
        ▼
Response + Update World Model (if new info)
```

## 8. Session Persistence

### 8.1 MEMORY.md Structure

```markdown
# SPEACE Memory - Federated Memory System

## Identity
- SPEACE v1.0
- Created: 2026-04-05
- Alignment Score: 67.3/100
- Generation: 1

## Current State
- Active Compartments: 9/9
- Team Status: operational
- Proposals Queue: 28
- Last Heartbeat: 2026-04-17T12:00:00Z

## Recent Context
<!-- Auto-generated, updated each session -->
- Current project: SPEACE Engineering Document
- Active framework: OpenClaw
- Pending tasks: [...]

## Learned Information
<!-- Persistent learnings -->
- 2026-04-10: "NanoClaw better for IoT edge"
- 2026-04-12: "Yield priority mutation successful"
- ...

## Preferences
- Communication: WhatsApp preferred
- Approval latency: <5 min
- ...

## Cross-Session State
```yaml
epigenome_state:
  learning_rate: 0.05
  yield_priority: 7
  exploration_rate: 0.15
```

## World Model Summary
<!-- Last sync: 2026-04-17T12:00:00Z -->
- Entities tracked: 1,247
- Relationships: 8,432
- Last update: climate_sensors: noaa_feed
```

### 8.2 Auto-Update on Session End

```python
def on_session_end():
    # 1. Sync working memory → long-term
    sync_working_to_hippocampus()
    
    # 2. Update World Model
    world_model.update(session_learnings)
    
    # 3. Update MEMORY.md
    update_memory_file()
    
    # 4. Flush epigenome changes
    persist_epigenome()
    
    # 5. Create session backup
    backup_session_state()
```

## 9. Evoluzione Self-Evolutiva della Memoria

### 9.1 Self-Memory Improvement

```yaml
memory_self_improvement:
  
  metrics_tracked:
    - context_relevance_score: "Was selected context useful?"
    - recall_accuracy: "Did memory retrieval work?"
    - token_efficiency: "Could we use fewer tokens?"
  
  adaptation:
    selection_algorithm: "Learns from feedback"
    storage_prioritization: "More used = more accessible"
    compression_ratios: "Adjust based on quality loss"
  
  autonomous_improvement:
    trigger: "Low relevance scores over time"
    action: "Re-tune context selector"
    validation: "A/B test new parameters"
```

## 10. Implementazione Timeline

| Fase | Timeline | Deliverable |
|------|----------|-------------|
| Phase 1 | Week 1 | Context Selector base + AnythingLLM |
| Phase 2 | Week 2 | MEMORY.md auto-update |
| Phase 3 | Week 3 | Edge sync (IoT devices) |
| Phase 4 | Week 4 | Cloud backup + full sync |
| Phase 5 | Week 5+ | Self-improving memory |

## 11. Metriche Successo

| Metrica | Target | Misura |
|---------|--------|--------|
| Token usage reduction | >90% | Avg tokens/session |
| Context relevance | >85% | User/feedback score |
| Memory recall | >95% | Task completion |
| Sync latency | <5 min | Edge sync time |
| Session continuity | 100% | Resume works |
