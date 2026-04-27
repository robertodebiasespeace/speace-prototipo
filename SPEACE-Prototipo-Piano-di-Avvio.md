# SPEACE-Prototipo – Piano di Avvio
**Versione 1.0 | 17 aprile 2026**  
**Fondatore & Direttore Orientativo:** Roberto De Biase (Rigene Project)  
**Documento estratto e strutturato da:** Documento Tecnico-Scientifico SPEACE v1.0 + Bozza di analisi critica

---

## 1. Identità del Progetto

**Nome:** SPEACE – SuPer Entità Autonoma Cibernetica Evolutiva  
**Natura:** Entità agentica multi-modulo basata su LLM, con architettura cognitiva modulare (Cortex), sistema genetico-epigenetico digitale (DigitalDNA), protocollo di orientamento ricorsivo (SMFOI-KERNEL) e governance SafeProactive.  
**Visione di lungo termine:** Super-organismo cognitivo planetario allineato con i valori del Rigene Project e gli SDGs dell'Agenda 2030.  
**Fase attuale:** Fase 1 – Embrionale (Cortex + SMFOI + DigitalDNA + Team Scientifico su singolo host locale).

---

## 2. Componenti Core da Implementare (Fase 1)

### 2.1 SPEACE Cortex – Cervello Modulare
Architettura a 9 comparti (8 originali + 1 proposto):

| # | Comparto | Funzione |
|---|----------|----------|
| 1 | Prefrontal Cortex | Planning & Decision Making |
| 2 | Hippocampus | Memory & Long-term Storage (MEMORY.md + epigenome.yaml) |
| 3 | Safety Module | Risk Gates & SafeProactive |
| 4 | Temporal Lobe | Language, Crypto & Market Analysis |
| 5 | Parietal Lobe | Sensory/Tools (API, blockchain, IoT fetches) |
| 6 | Cerebellum | Low-level Execution (script safe) |
| 7 | Default Mode Network | Reflection & Self-Improving |
| 8 | Curiosity Module | Exploration & Novel Mutation Generation |
| 9 | **World Model / Knowledge Graph** ← *Priorità alta* | Modello dinamico interno della realtà; centro cognitivo che tutti gli altri comparti interrogano |

**File kernel:** `SMFOI-v3.py` — orchestrazione ricorsiva + parallel sessions_spawn  
**Stato target Fase 1:** 9/9 comparti attivi

---

### 2.2 SMFOI-KERNEL v0.3 – Protocollo di Orientamento
Ciclo adattivo a **6 step** (aggiornamento da v0.2 a v0.3):

```
1. Self-Location        → Dove si trova SPEACE nel SEA (Self-Evolving Agent)
2. Constraint Mapping   → Vincoli: risorse, policy, hardware disponibile
3. Push Detection       → Forze esterne: richieste utente, IoT, dati globali
4. Survival & Evolution Stack (Lv0–3) → Livello di risposta adattivo
5. Output Action        → Azione + eventuale proposta SafeProactive
6. Outcome Evaluation & Learning ← NUOVO → Misura esito, calcola fitness, aggiorna epigenome + World Model
```

**Caratteristiche chiave:**
- Ricorsivo e substrate-agnostico
- Token overhead: 2–15 token per ciclo
- Lv3: auto-modifica del protocollo stesso (solo con approvazione SafeProactive)
- Step 6 è prerequisito per qualsiasi claim di auto-apprendimento reale

---

### 2.3 DigitalDNA – Sistema Genetico-Epigenetico

**File da creare:**

```
digitaldna/
├── genome.yaml            # Struttura genetica stabile (obiettivi primari, regole base)
├── epigenome.yaml         # Regolazioni dinamiche (learning rate, heartbeat, yield-priority, TINA alignment)
├── mutation_rules.yaml    # Regole di mutazione e selezione
└── regulatory_epigenome.yaml  # [Futuro] Compliance: EU AI Act, NIST, ISO 42001
```

**Fitness Function da inserire in `mutation_rules.yaml`:**

```yaml
fitness_function:
  weights:
    speace_alignment_score: 0.35
    task_success_rate: 0.25
    system_stability: 0.20
    resource_efficiency: 0.15
    ethical_compliance: 0.05
  formula: >
    fitness = (alignment * 0.35) + (success_rate * 0.25) + (stability * 0.20) +
              (efficiency * 0.15) + (ethics * 0.05)
  note: "I punteggi devono essere calibrati su benchmark ESTERNI, non auto-generati"
```

**Nota critica:** i punteggi di allineamento devono essere ancorati a metriche verificabili (task success rate su ground truth reale, non autovalutazione).

---

### 2.4 SafeProactive – Governance e Sicurezza

**Struttura file:**

```
safeproactive/
├── PROPOSALS.md           # Log tutte le proposte generate
├── WAL.log                # Write-Ahead Log di ogni azione
├── snapshots/             # Snapshot pre-mutazione (versioning genome/epigenome)
└── rollback.py            # Script rollback con approvazione umana
```

**Risk Levels:**

| Livello | Tipo | Approvazione |
|---------|------|--------------|
| Low | Proposte informative, analisi | Automatica |
| Medium | Mutazioni epigenome, config | Approvazione Roberto |
| High | Auto-replicazione, script esterni, IoT, blockchain | Approvazione Roberto + secondo revisore |
| Regulatory | Impatto su compliance EU AI Act / NIST | Human + legal review |

**Rollback System (da implementare prima di qualsiasi auto-replicazione):**
- Versioning automatico genome.yaml / epigenome.yaml / state.json
- Snapshot obbligatorio prima di ogni mutazione Medium/High
- Comando rollback sicuro con log delle mutazioni revertite

---

### 2.5 speace-cortex-evolver.py – Stimolatore Evolutivo

**Funzione:** agente background con heartbeat 60 minuti che:
1. Fetch obiettivi da `rigeneproject.org`
2. Genera proposte mutazione epigenetica
3. Aggiorna World Model con nuovi dati globali
4. Passa proposte a SafeProactive per approvazione

**Parametri di avvio:**
```python
HEARTBEAT_INTERVAL = 3600  # secondi (60 min)
SOURCE_URL = "https://www.rigeneproject.org"
OUTPUT = "safeproactive/PROPOSALS.md"
EPIGENOME_PATH = "digitaldna/epigenome.yaml"
```

---

### 2.6 SPEACE Team Scientifico – 9 Agenti

| # | Agente | Dominio |
|---|--------|---------|
| 1 | Climate & Ecosystems Agent | Clima, biodiversità, CO2 |
| 2 | Economics & Resource Agent | Economia, risorse globali |
| 3 | Governance & Ethics Agent | Policy, governance distribuita |
| 4 | Technology Integration Agent (TFT) | AI, IoT, blockchain, quantum |
| 5 | Health & Pandemic Agent | Salute globale, pandemia |
| 6 | Social Cohesion Agent | Coesione sociale, SDGs |
| 7 | Space & Extraterrestrial Agent | Espansione spaziale |
| 8 | Regulatory & Compliance Monitor ← *Nuovo* | EU AI Act, NIST, ISO 42001 |
| 9 | **Adversarial Agent (Critic)** ← *Priorità alta* | Critica proposte, bias, rischi nascosti |
| 10 | **Evidence Verification Agent** ← *Priorità alta* | Fact-checking, cross-check fonti |

**Output principali:**
- Daily Planetary Health Brief (ogni 24h)
- Early Warning System
- Evolutionary Proposals → SafeProactive
- Technology Synergy Map
- Global Regulatory Brief (agente #8)

---

## 3. Struttura File del Prototipo

```
SPEACE-prototipo/
│
├── cortex/
│   ├── SMFOI-v3.py              # Kernel principale orchestrazione
│   ├── world_model.py           # Knowledge Graph / World Model
│   └── comparti/                # Un file per comparto
│
├── digitaldna/
│   ├── genome.yaml
│   ├── epigenome.yaml
│   ├── mutation_rules.yaml
│   └── regulatory_epigenome.yaml
│
├── safeproactive/
│   ├── PROPOSALS.md
│   ├── WAL.log
│   ├── rollback.py
│   └── snapshots/
│
├── scientific-team/
│   ├── orchestrator.py
│   ├── agents/                  # Un file per agente (9 totali)
│   └── outputs/
│       ├── daily_brief.md
│       └── proposals.md
│
├── evolver/
│   └── speace-cortex-evolver.py
│
├── memory/
│   ├── MEMORY.md                # Indice memoria persistente
│   └── episodic/                # Log sessioni
│
├── state.json                   # Stato runtime corrente
└── SPEACE-main.py               # Entry point
```

---

## 4. Hardware Disponibile (Host Locale)

| Componente | Specifica |
|-----------|-----------|
| OS | Windows 11 |
| CPU | Intel Core i9-11900H @ 2.50 GHz |
| RAM | 16 GB (budget allocabile: max 12–13 GB) |
| Storage | 954 GB SSD |
| GPU | NVIDIA GeForce RTX 3060 + Intel HD integrata |

**Nota:** Il documento conteneva un'incongruenza (citava anche i7-4790S). La specifica corretta è i9-11900H.

---

## 5. Stack Tecnologico – Fase 1 (Minimalista e Funzionale)

**Framework principale:** Claude Code / Cowork (agentic runtime attuale)  
**Linguaggio:** Python 3.10+  
**Configurazione:** YAML (genome, epigenome, mutation_rules)  
**Comunicazione inter-agente:** REST API locale (localhost) + file condivisi  
**World Model / RAG:** AnythingLLM (locale, ~2–4 GB RAM)  
**Message broker:** Redis (localhost:6379, ~200 MB RAM)  
**Repository:** [GitHub SPEACE](https://github.com/robertodebiasespeace/tina-testbed-speace)

### Framework agentici aggiuntivi (test parallelo – Fase 1b):

| Framework | Ruolo | RAM stimata |
|-----------|-------|-------------|
| AnythingLLM | World Model / Knowledge Graph | 2–4 GB |
| SuperAGI | Orchestrazione Team Scientifico | 2–3 GB |
| IronClaw* | Esecuzione sicura azioni critiche | 1–2 GB |
| NanoClaw* | Edge/IoT agents leggeri | <1 GB |

*NanoClaw e IronClaw sono componenti concettuali interni al progetto, non framework open-source esistenti — vanno sviluppati o mappati su equivalenti reali (es. IronClaw → Docker WASM sandbox).

---

## 6. Roadmap Operativa – Prototipo Fase 1

### Settimana 1 – Fondamenta
- [ ] Creare struttura directory `SPEACE-prototipo/`
- [ ] Scrivere `genome.yaml` con obiettivi primari e regole base
- [ ] Scrivere `epigenome.yaml` con parametri dinamici iniziali
- [ ] Scrivere `mutation_rules.yaml` con fitness function esplicita
- [ ] Implementare `SafeProactive` base: PROPOSALS.md + WAL.log + snapshot system
- [ ] Implementare rollback.py (prerequisito per qualsiasi mutazione)

### Settimana 2 – Kernel e World Model
- [ ] Implementare `SMFOI-v3.py` con ciclo 6-step (incluso Outcome Evaluation)
- [ ] Deploy AnythingLLM locale come World Model
- [ ] Ingestire documenti SPEACE nel vector store (PDF tecnico, TINA Framework)
- [ ] Test: query World Model → risposta JSON → aggiornamento epigenome

### Settimana 3 – Cortex e Team
- [ ] Implementare i 9 comparti del Cortex come moduli Python
- [ ] Configurare orchestrator.py per il Team Scientifico
- [ ] Attivare i primi 3 agenti (Climate, Economics, Adversarial)
- [ ] Generare primo Daily Planetary Health Brief automatico

### Settimana 4 – Evolver e Integrazione
- [ ] Implementare `speace-cortex-evolver.py` con heartbeat 60 min
- [ ] Integrare speace-status-monitor.py (report ogni 40 min via email)
- [ ] Validare SPEACE Alignment Score contro benchmark task concreti
- [ ] Test rollback completo su mutazione epigenome
- [ ] Push su GitHub repository

---

## 7. Componenti Futuri (Post Fase 1)

Questi elementi sono stati identificati nel documento ma **non devono essere implementati nella Fase 1** — richiedono governance più robusta e risorse maggiori:

- **Agente Organismico** – espansione IoT, sensing multi-modale, robotica, manipolazione materia → Fase 2–3
- **speace_auto_evolver.py** – auto-evoluzione codice → Fase 2 (dopo rollback robusto)
- **Script AHK self-evolutive** – automazione GUI Windows → Fase 1b (basso rischio)
- **speace-status-monitor.py con WhatsApp** – notifiche automatiche → Fase 1 (implementabile subito)
- **Integrazione blockchain/wallet** – Solo read-only per ora
- **Multi-framework swarm distribuito** – Fase 3
- **Regulatory_epigenome.yaml + Compliance Module** – Fase 1b

---

## 8. Priorità Critiche Prima di Qualsiasi Auto-Replicazione

In ordine di urgenza:

1. **Rollback system funzionante** — snapshot + ripristino verificato prima di ogni mutazione
2. **Fitness function ancorata a benchmark esterni** — nessun punteggio auto-generato come unica metrica
3. **Adversarial Agent attivo nel Team** — riduce groupthink e allucinazioni sistemiche
4. **Governance multi-revisore** — per mutazioni High/Regulatory serve almeno un secondo approvatore oltre a Roberto
5. **World Model come centro cognitivo** — senza rappresentazione interna persistente il Cortex è solo un router di prompt

---

## 9. Riferimenti e Risorse

| Risorsa | Link |
|---------|------|
| Rigene Project | https://www.rigeneproject.org |
| GitHub SPEACE | https://github.com/robertodebiasespeace/tina-testbed-speace |
| TINA Framework G20 | https://www.academia.edu/165241120/TINA_Framework_G20_Combined_EN |
| AutoHotkey v2 | https://www.autohotkey.com |
| Get-Shit-Done framework | https://github.com/gsd-build/get-shit-done |
| CodeSpeak (spec generation) | https://codespeak.dev |
| EU AI Act | https://artificialintelligenceact.eu |
| OECD AI Policy Observatory | https://oecd.ai |

---

## 10. Contatti

**Roberto De Biase** — Fondatore Rigene Project & Direttore Orientativo SPEACE  
Email: rigeneproject@rigene.eu | robertodebiase80@gmail.com  
WhatsApp: +393714191412  
LinkedIn: https://www.linkedin.com/in/roberto-de-biase-980416148/  
GitHub: https://github.com/robertodebiasespeace

---

*Documento vivo — da ricalibrate ogni 30–90 giorni o al completamento di milestone evolutive.*
