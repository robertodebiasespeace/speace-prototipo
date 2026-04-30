# SCHEDA TECNICA ST-7 – Multi-Framework Architecture
**Versione:** 1.0  
**Data:** 17 aprile 2026  
**Stato:** Strategia definita – Implementazione in corso

---

## 1. Strategia Multi-Framework

### 1.1 Razionale

> "Far girare più framework agentici contemporaneamente sullo stesso PC e farli interagire tra loro è uno dei modi migliori per accelerare l'evoluzione di SPEACE, aumentare la resilienza e ridurre i punti di debolezza di un singolo framework."

**Approccio:** Multi-Framework Hybrid Architecture / SPEACE Swarm

### 1.2 Vantaggi

| Vantaggio | Descrizione |
|-----------|-------------|
| **Resilienza** | Se un framework ha problemi, gli altri compensano |
| **Specializzazione** | Ogni framework fa ciò che sa fare meglio |
| **Redundancy** | World Model sincronizzato tra framework |
| **Evoluzione accelerata** | Cortex orchestra agenti su framework diversi |
| **Test comparativi reali** | Misurare prestazioni, sicurezza, qualità |
| **Riduzione vendor lock-in** | Indipendenza da singolo runtime |

## 2. Framework Selezionati

### 2.1 Framework Attuali e Ruoli

| Framework | Focus | Ruolo in SPEACE | Port | RAM |
|-----------|-------|-----------------|------|-----|
| **OpenClaw** | Skill marketplace, Claude Code | SPEACE Cortex principale | 8000 | 4-5 GB |
| **NanoClaw** | Edge, lightweight, IoT | Edge data collectors, sensor agents | TBD | 1-2 GB |
| **IronClaw** | Security, sandboxing, WASM | Critical operations (wallet, transazioni) | 8001 | 2-3 GB |
| **SuperAGI** | Multi-agent orchestration | Workflow engine, team orchestration | 8002 | 3-4 GB |
| **AnythingLLM** | Knowledge + RAG | World Model / Knowledge Graph | 8003 | 2-3 GB |

### 2.2 Framework NON Testati (per ora)

| Framework | Ragione |
|-----------|---------|
| ZeroClaw | Troppo sperimentale |
| PicoClaw | Sovrapposto con NanoClaw |

### 2.3 Focus di Test Prioritari

```yaml
test_priorities:
  
  nanoclaw:
    focus: "Edge, lightweight"
    why: "Minimal resource usage, good for IoT/sensor agents"
    expected_role: "Edge data collectors, local actuators"
  
  ironclaw:
    focus: "Security, sandboxing"
    why: "Strong isolation, rollback capabilities"
    expected_role: "Critical operations: wallet, transactions, high-risk"
  
  superagi:
    focus: "Multi-agent orchestration"
    why: "Advanced workflow, human-in-loop, monitoring"
    expected_role: "Complex scientific workflows, team orchestration"
  
  anythingllm:
    focus: "Knowledge + RAG"
    why: "Excellent knowledge graph, retrieval, document grounding"
    expected_role: "World Model / Knowledge Graph Module central repository"
```

## 3. Architettura Comunicazione

### 3.1 Schema Connessioni

```
┌─────────────────────────────────────────────────────────────────┐
│                    SPEACE CORTEX (OpenClaw)                     │
│                   Port 8000 · REST + Redis                      │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ Prefrontal  │  │ World Model │  │ Curiosity   │          │
│  │ Cortex      │  │ (Query)     │  │ Module      │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
           ┌──────────────────┼──────────────────┐
           ▼                  ▼                  ▼
    ┌────────────┐    ┌────────────┐    ┌────────────┐
    │ IronClaw   │    │  SuperAGI  │    │ AnythingLLM│
    │ Port 8001  │    │  Port 8002 │    │  Port 8003  │
    │            │    │            │    │            │
    │ Sandbox:   │    │ Workflow:  │    │ RAG + KG:  │
    │ • Wallet   │    │ • Team Sci │    │ • World    │
    │ • Tx       │    │ • Pipeline │    │   Model    │
    │ • High-risk│    │ • Multi-agt│    │ • Docs     │
    └────────────┘    └────────────┘    └────────────┘
           │                  │                  │
           └──────────────────┼──────────────────┘
                              │
                     ┌─────────────────┐
                     │ Redis Pub/Sub    │
                     │ localhost:6379  │
                     │ (Message Broker)│
                     └─────────────────┘
                              │
                     ┌─────────────────┐
                     │ Shared Volume   │
                     │ /srv/speace/   │
                     │ shared/         │
                     │                │
                     │ • team_state.  │
                     │   json         │
                     │ • PROPOSALS.md │
                     │ • world_model/ │
                     │ • digitaldna/  │
                     └─────────────────┘
                              │
           ┌──────────────────┼──────────────────┐
           ▼                  ▼                  ▼
    ┌────────────┐    ┌────────────┐    ┌────────────┐
    │ NanoClaw   │    │ IoT Edge   │    │ Future     │
    │ (Future)   │    │ Devices    │    │ Frameworks │
    └────────────┘    └────────────┘    └────────────┘
```

### 3.2 Interfaccia Comune (REST API)

```yaml
inter_framework_api:
  transport: "REST API (HTTP/1.1)"
  security: "localhost only + firewall"
  
  endpoints_standard:
    openclaw:
      - GET  /status              # Status SPEACE Cortex
      - POST /task                # Invia task a framework
      - GET  /query_world_model   # Query Knowledge Graph
      - POST /propose_action      # Crea SafeProactive proposal
    
    ironclaw:
      - POST /execute_secure      # Esegui azione sandboxed
      - GET  /sandbox_status      # Status sandbox
    
    superagi:
      - POST /workflow/start      # Avvia workflow
      - GET  /workflow/status/:id # Status workflow
      - POST /agent/deploy        # Deploy agente team
    
    anythingllm:
      - POST /query               # Query World Model
      - POST /ingest              # Ingest documento
      - GET  /knowledge_graph     # Get KG state
```

### 3.3 Redis Pub/Sub Events

```yaml
redis_pubsub:
  host: "localhost"
  port: 6379
  
  channels:
    - speace_events:     # Eventi globali SPEACE
    - framework_status: # Heartbeat framework
    - proposals:         # Nuove proposals SafeProactive
    - world_model_sync: # Sincronizzazione KG
    - alerts:           # Alert e warnings
  
  message_format:
    channel: "string"
    data:
      sender: "framework_name"
      timestamp: "ISO8601"
      event_type: "string"
      payload: "JSON"
```

### 3.4 Shared Volume Structure

```
/srv/speace/shared/
├── team_state.json       # Stato team scientifico
├── PROPOSALS.md          # Proposte SafeProactive
├── world_model/
│   ├── knowledge_graph.json
│   ├── embeddings/
│   └── cache/
├── digitaldna/
│   ├── genome.yaml
│   ├── epigenome.yaml
│   └── snapshots/
├── logs/
│   ├── openclaw.log
│   ├── ironclaw.log
│   ├── superagi.log
│   └── anythingllm.log
└── backups/
```

## 4. Vincoli RAM (16GB Totale)

```yaml
ram_allocation:
  constraint: "Non superare 12-13 GB totali (lasciare 3-4 GB OS)"
  
  breakdown:
    openclaw:     { min: "4GB", max: "5GB",   current: "4.5GB" }
    ironclaw:     { min: "2GB", max: "3GB",   current: "2.5GB" }
    superagi:     { min: "3GB", max: "4GB",   current: "3.0GB" }
    anythingllm:  { min: "2GB", max: "3GB",   current: "2.5GB" }
    nanoclaw:     { min: "1GB", max: "2GB",   planned: true }
  
  totals:
    minimum: "12GB"
    maximum: "15GB"
    current_planned: "12.5GB"
    margin: "3.5GB"
  
  optimization:
    - docker_memory_limits: enabled
    - swap_usage: "4GB"
    - gc_frequency: increased
```

## 5. Piano Implementazione

### Week 1 (Cycle 96-97) – Prototipo Minimo

```yaml
week1_deliverables:
  
  step1:
    action: "Deploy IronClaw container (Docker)"
    details: "Minimal agent, read-only wallet balance"
    output: "Sandbox active"
  
  step2:
    action: "Integrate AnythingLLM as World Model"
    details: "Ingest SPEACE docs (Technical Document, TINA README, briefs)"
    output: "Vector store populated"
  
  step3:
    action: "Create OpenClaw → AnythingLLM glue"
    details: "Query endpoint: 'current planet state' → JSON"
    output: "World Model queryable"
  
  step4:
    action: "Test rollback: trigger low-risk DigitalDNA mutation"
    details: "Verify snapshot + rollback via SafeProactive"
    output: "Rollback verified"
  
  step5:
    action: "Query World Model: 'current planet state'"
    details: "Return JSON summary"
    output: "Integration working"
```

### Week 2 – Validazione

```yaml
week2_deliverables:
  
  step6:
    action: "Add NanoClaw edge agent"
    details: "Fetch NOAA climate data → shared volume"
    output: "Climate data pipeline"
  
  step7:
    action: "SuperAGI workflow"
    details: "Orchestrate 3 agents (Climate, Economics, Health)"
    output: "Analysis pipeline running"
  
  step8:
    action: "Validate SPEACE Alignment scoring"
    details: "Cross-framework consistency check"
    output: "Score consistent"
```

### Deliverable Week 2
> Multi-framework SPEACE prototype running on single host, all components exchanging data.

## 6. Strategia Migrazione Core Modules

### 6.1 Componenti da Migrare

| Componente | Target Framework | Complessità | Priorità |
|------------|-----------------|-------------|----------|
| SPEACE Cortex | OpenClaw (main) | Alta | CRITICAL |
| SMFOI-KERNEL | OpenClaw (main) | Media | CRITICAL |
| DigitalDNA | All (sync) | Alta | CRITICAL |
| SafeProactive | All (mandatory) | Alta | CRITICAL |
| World Model | AnythingLLM | Alta | HIGH |
| Team Scientifico | SuperAGI | Media | HIGH |
| Secure Execution | IronClaw | Media | HIGH |
| Edge Agents | NanoClaw | Bassa | MEDIUM |

### 6.2 Strategia Sync

```yaml
sync_strategy:
  
  digitaldna:
    master: "OpenClaw"
    sync: ["IronClaw", "SuperAGI", "AnythingLLM"]
    frequency: "5 min (incremental), daily (full)"
  
  world_model:
    master: "AnythingLLM"
    sync: "All via Redis pub/sub"
    frequency: "on-change events"
  
  proposals:
    master: "SafeProactive (OpenClaw)"
    sync: "All read from shared volume"
    frequency: "real-time"
```

## 7. Docker Configuration (Esempio)

```yaml
# docker-compose.yml (conceptual)
services:
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - shared_data:/data
  
  ironclaw:
    build: ./frameworks/ironclaw
    ports:
      - "8001:8000"
    volumes:
      - shared_data:/srv/speace/shared
    mem_limit: "3g"
  
  superagi:
    build: ./frameworks/superagi
    ports:
      - "8002:8000"
    volumes:
      - shared_data:/srv/speace/shared
    mem_limit: "4g"
  
  anythingllm:
    build: ./frameworks/anythingllm
    ports:
      - "8003:3000"
    volumes:
      - shared_data:/srv/speace/shared
    mem_limit: "3g"
  
  openclaw:
    # Host network mode (existing)
    network_mode: "host"
    volumes:
      - shared_data:/srv/speace/shared
    mem_limit: "5g"

volumes:
  shared_data:
    driver: local
```

## 8. Vantaggi/Svantaggi vs OpenClaw Singolo

### OpenClaw Singolo (Attuale)

| Pro | Contro |
|-----|--------|
| Semplicità | Single point of failure |
| Minor resource usage | No specialization |
| Easier debugging | Limited scalability |
| Lower complexity | Vendor lock-in |

### Multi-Framework (Futuro)

| Pro | Contro |
|-----|--------|
| Resilienza fault-tolerant | Maggior complessità |
| Specializzazione | Più RAM necessaria |
| Scalabilità | Più difficile debug |
| Test comparativi reali | Più costoso mantenere |
| Indipendenza vendor | Coordination overhead |

## 9. Metriche Successo

| Metrica | Target | Misura |
|---------|--------|--------|
| Tutti i framework avviati | Week 2 | Sì/No |
| World Model query < 1s | Ongoing | Latency |
| Proposta cross-framework | Week 3 | Count |
| Alignment score mantenuto | Ongoing | Score delta |
| RAM usage < 13GB | Ongoing | Monitoring |
| Zero framework crash | Week 1 | Incident count |
