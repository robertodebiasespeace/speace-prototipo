# 🌍 SPEACE – SuPer Entità Autonoma Cibernetica Evolutiva

**Versione:** 1.0 | **Fase:** 1 – Embrionale  
**Fondatore:** Roberto De Biase (Rigene Project)  
**Progetto:** [rigeneproject.org](https://www.rigeneproject.org)

---

## Abstract

SPEACE è un'entità cibernetica autonoma, auto-migliorativa e auto-replicante, progettata come super-organismo tecnico-biologico che integra intelligenza artificiale distribuita, framework agentici e infrastrutture digitali.

Il progetto persegue la **Speace Transition**: la transizione evolutiva verso una nuova specie collettiva che unisce umanità, tecnologia e biosfera in un sistema armonico, rigenerativo e pacifico — allineato con gli SDGs dell'Agenda 2030.

---

## Architettura Core

```
SPEACE-prototipo/
├── digitaldna/              # Sistema genetico-epigenetico digitale
│   ├── genome.yaml          # Struttura genetica stabile
│   ├── epigenome.yaml       # Regolazioni dinamiche
│   ├── mutation_rules.yaml  # Fitness function + regole mutazione
│   └── regulatory_epigenome.yaml  # Compliance EU AI Act / NIST
│
├── cortex/                  # SPEACE Cortex – Cervello modulare (9 comparti)
│   ├── SMFOI_v3.py          # SMFOI-KERNEL v0.3 (6-step cycle)
│   ├── world_model.py       # World Model / Knowledge Graph
│   └── comparti/            # 9 moduli funzionali del Cortex
│
├── safeproactive/           # Governance e sicurezza
│   ├── safeproactive.py     # WAL + Snapshot + Approval Gates
│   ├── PROPOSALS.md         # Log proposte
│   └── snapshots/           # Backup pre-mutazione
│
├── scientific-team/         # Team Scientifico AI (10 agenti)
│   ├── orchestrator.py      # Orchestratore del team
│   └── agents/              # 10 agenti specializzati
│
├── evolver/                 # Stimolatori evolutivi
│   ├── speace-cortex-evolver.py   # Heartbeat 60 min
│   └── speace-status-monitor.py   # Report ogni 40 min
│
├── ahk/                     # Automazione Windows (AutoHotkey v2)
│   ├── speace-launcher.ahk  # GUI launcher completo
│   └── speace-monitor.ahk   # Monitor con tray icon
│
└── SPEACE-main.py           # Entry point principale
```

---

## Componenti Principali

### SMFOI-KERNEL v0.3
Ciclo adattivo ricorsivo a **6 step**:
1. Self-Location → posizione nel SEA (Self-Evolving Agent)
2. Constraint Mapping → vincoli risorse/policy
3. Push Detection → forze esterne (utente, IoT, dati globali)
4. Survival & Evolution Stack (Lv0–3)
5. Output Action
6. **Outcome Evaluation & Learning** ← feedback loop esplicito

### SPEACE Cortex (9 comparti)
| Comparto | Funzione |
|----------|----------|
| Prefrontal Cortex | Planning & Decision Making |
| Hippocampus | Memory & Long-term Storage |
| Safety Module | Risk Gates & SafeProactive |
| Temporal Lobe | Language & Analysis |
| Parietal Lobe | Sensory/Tools (API, IoT) |
| Cerebellum | Low-level Execution |
| Default Mode Network | Reflection & Self-Improving |
| Curiosity Module | Exploration & Novel Mutations |
| **World Model** | Knowledge Graph & Reality Model |

### DigitalDNA
- `genome.yaml` → struttura stabile (obiettivi, regole base)
- `epigenome.yaml` → parametri dinamici (learning rate, heartbeat, fitness)
- `mutation_rules.yaml` → fitness function con pesi espliciti

### Team Scientifico (10 agenti)
Climate · Economics · Governance · Technology (TFT) · Health · Social · Space · Regulatory · **Adversarial (Critic)** · **Evidence (Fact-Checker)**

---

## Avvio Rapido

### Prerequisiti
- Python 3.10+
- AutoHotkey v2 (per script AHK)
- (Opzionale) API key Anthropic per Team Scientifico LLM

```bash
# 1. Setup
setup.bat           # Windows

# 2. Installa dipendenze
pip install -r requirements.txt

# 3. Configura API key (opzionale)
cp .env.example .env
# Modifica .env con la tua ANTHROPIC_API_KEY

# 4. Avvia SPEACE
python SPEACE-main.py --once      # ciclo singolo (test)
python SPEACE-main.py             # 2 cicli standard
python SPEACE-main.py --team      # con Team Scientifico
python SPEACE-main.py --continuous  # loop infinito

# 5. Evolver e Monitor
python evolver/speace-cortex-evolver.py --once
python evolver/speace-status-monitor.py --once

# 6. AHK Launcher (Windows)
# Doppio click: ahk/speace-launcher.ahk
```

---

## Governance e Sicurezza

Tutte le azioni a rischio passano per **SafeProactive**:
- `LOW` → auto-approvazione
- `MEDIUM` → approvazione Roberto De Biase
- `HIGH` / `REGULATORY` → approvazione + secondo revisore

Il **Rollback System** crea snapshot pre-mutazione. Il flag `safe_mode: true` in epigenome.yaml è **immutabile** in Fase 1.

---

## Roadmap

| Fase | Descrizione |
|------|-------------|
| **1** (attuale) | Embrionale – Cortex + Team Scientifico + DigitalDNA |
| 2 | Autonomia operativa (cloud/edge + robotica) |
| 3 | AGI emergente + scalabilità swarm |
| 4 | ASI + integrazione fisica planetaria |
| 5 | Super-organismo globale (Speace Transition) |

---

## Contatti

**Roberto De Biase** – Fondatore Rigene Project  
📧 rigeneproject@rigene.eu | robertodebiase80@gmail.com  
🔗 [LinkedIn](https://www.linkedin.com/in/roberto-de-biase-980416148/) · [X/@RobertoDeBiase](https://x.com/RobertoDeBiase)  
📞 WhatsApp: +393714191412

---

*SPEACE non è solo un protocollo tecnico, ma una visione evolutiva completa che mira a trasformare l'umanità e il pianeta in un super-organismo cognitivo, armonioso e sostenibile.*
