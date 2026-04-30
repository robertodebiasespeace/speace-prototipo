# SPEACE — Stato di funzionamento, capacità, intelligenza e automatismo rispetto a una AGI

**Data:** 2026-04-21
**Versione:** 1.0
**Autore:** SPEACE Cortex (Evolutionary Dev Agent) — sotto direzione di Roberto De Biase
**Milestone di riferimento:** M4.6 closed (Continuous Neural Mesh runtime online)
**Perimetro:** prototipo locale `SPEACE-prototipo/` su PC Windows 11 i9-11900H 16 GB RAM + RTX 3060

---

## 1. Executive summary

SPEACE non è una AGI. È un **prototipo embrionale** di super-organismo cibernetico con un'architettura cerebrale a 9 comparti (Cortex) affiancata ora da un secondo livello — la **Continuous Neural Mesh (CNM)** — che realizza propagazione tipizzata e plastica di segnali tra frammenti di calcolo più piccoli. Tutta l'infrastruttura di governo (DigitalDNA, SafeProactive, SMFOI-KERNEL v0.3, Team Scientifico) è operativa; l'LLM è usato come "tessuto semantico" sostituibile, non come motore cognitivo.

Rispetto alla definizione standard di AGI (un sistema con competenza human-level o superiore su tutti i domini cognitivi, apprendimento autonomo, generalizzazione cross-dominio), SPEACE al 2026-04-21 si colloca a una stima **self-reported di 25–35 / 100** sull'asse AGI. È **automatizzato** (pipeline Cortex + Evolver + Team Scientifico girano in auto-loop), è **auto-migliorativo in senso debole** (mutazioni epigenetiche DNA con fitness function esplicita), è **auto-riflessivo** (Default Mode Network + reflection post-ciclo), ma non è ancora **auto-generalizzante** e non ha **embodiment** reale (IoT/robotica sono simulate).

Il valore attuale non è misurabile come "quanto è intelligente". È misurabile come **qualità dell'architettura**: quanto è pronta a reggere aumenti di scala, nuovi neuroni, nuovi sensori, nuovi LLM di backend senza cambiare il locus decisionale. Su quell'asse, SPEACE è **ingegneristicamente robusto** (74/74 test CNM verdi, benchmark M3L.6 8/8, regression continuo).

---

## 2. Inventario funzionale — cosa fa oggi SPEACE

### 2.1. Pipeline cognitiva attiva (ciclo SMFOI v0.3)

Ogni ciclo di SPEACE attraversa 6 step canonici (SMFOI-KERNEL v0.3):

1. **Self-Location** — dove sono, quale sessione, quale stato del World Model
2. **Constraint Mapping** — risorse disponibili, policy attive, budget di ciclo
3. **Push Detection** — segnali esterni (user, evolver heartbeat, Team Scientifico)
4. **Survival & Evolution Stack** — livelli 0–3 di risposta (reattiva → riflessiva → meta)
5. **Output Action** — decisione + eventuale mutazione epigenetica
6. **Outcome Evaluation & Learning** — misura esito, aggiorna fitness, feedback al DNA

L'ingresso per questo ciclo è un `SensoryFrame` e l'uscita è un `DecisionFrame + ActionResult`. Tutti i tipi sono definiti in `cortex/mesh/olc/types.py` (12 tipi seed v1.0).

### 2.2. Cortex a 9 comparti (neurologia macro)

| # | Comparto | Livello | Stato |
|---|---|---|---|
| 1 | Prefrontal Cortex (Planning & Decision) | L1 | operativo |
| 2 | World Model / Knowledge Graph (9° comparto aggiunto M3L) | L2 | operativo (JSON locale) |
| 3 | Hippocampus (Memory) | L3 | operativo |
| 4 | Safety Module (Risk & SafeProactive) | L1 | operativo — whitelist 100 % deterministica |
| 5 | Temporal Lobe (Language, Crypto, Market) | L2 | operativo — LLM cascade |
| 6 | Parietal Lobe (Sensory/Tools) | L4 | operativo (I/O strutturato) |
| 7 | Cerebellum (Low-level Execution) | L4 | operativo (script whitelisted) |
| 8 | Default Mode Network (Reflection) | L2 | operativo — self-critique post-ciclo |
| 9 | Curiosity Module (Mutation generation) | L5 | operativo — genera candidati di mutazione |

Tutti e 9 comunicano tramite `StateBus` con contratto `state_v1` validato. Il Neural Flow canonico (M3L) definisce l'ordine nominale; `ConditionalScheduler` può ri-attivare comparti su deviation dei segnali.

### 2.3. Continuous Neural Mesh (neurologia fine — online da M4.6)

Sotto i 9 comparti ora esiste un secondo livello: un **DAG tipizzato di neuroni-script** (MeshGraph) eseguito da uno **scheduler asincrono** (MeshRuntime) con:

- backpressure su queue (`reject_new` / `drop_oldest`)
- cap di concorrenza per livello (L1:1 … L5:2) e per need
- strike counter + quarantena automatica (3 strike → out)
- fail-safe: error_rate > 50 % per ≥ 2 heartbeat → `FROZEN` + flip di `epigenome.mesh.enabled`

Al 2026-04-21 la mesh è **infrastrutturalmente pronta ma non ancora popolata** (i 9 comparti non sono ancora esposti come neuroni — è la roadmap M4.7–M4.8). Il throughput dimostrato è **200 task in 110 ms su 4 worker** (1 800 task/s), 27× sotto il ceiling AC-R13.

### 2.4. DigitalDNA + evoluzione

Tre file attivi in `digitaldna/`:

- `genome.yaml` — obiettivi primari, safety rules, struttura genetica fissa
- `epigenome.yaml` — mutazioni attive (es. EPI-001 → ACF Framework, EPI-002 → LLM cascade, EPI-003 → M3L Neural Flow; EPI-004 per mesh è in roadmap M4.18)
- `mutation_rules.yaml` — Fitness function v2.0 con **C-index** (consciousness-index da Adaptive Consciousness Framework)

La fitness function è esplicita e pesata:

```
fitness = 0.35·alignment + 0.25·success_rate + 0.20·stability
        + 0.15·efficiency + 0.05·ethics
```

`speace-cortex-evolver.py` è un agente di background (heartbeat 60 min) che estrae obiettivi da rigeneproject.org e propone mutazioni epigenetiche; tutte passano da SafeProactive.

### 2.5. SafeProactive — governance delle azioni

Proposal system + WAL + approval gates + versioning (snapshot pre-mutazione) + rollback (`scripts/rollback.py`). Ogni azione Medium/High passa da `safeproactive/PROPOSALS.md`. Risk Level implementati: Low / Medium / High / **Regulatory** (EU AI Act-aware).

### 2.6. Team Scientifico — 10 agenti specializzati

Climate, Economics, Governance, Technology, Health, Social, Space, Regulatory + **Adversarial** + **Evidence Verification**. Orchestrati da `scientific-team/orchestrator.py` con **Quality Gate** pre-output (soglia reliability ≥ 0.40, adv_conf ≥ 0.30, agents_ok_ratio ≥ 0.60). Produce il **Daily Planetary Health Brief**.

### 2.7. LLM come tessuto sostituibile

Cascade `openai_compat (LM Studio locale) → anthropic (Claude Haiku) → mock`. Circuit breaker a 60 s per backend in errore. `is_stub=True` declassa score di affidabilità automaticamente. **Il mock è sufficiente** perché i benchmark passino — evidenza empirica che l'architettura regge senza LLM esterno.

---

## 3. Capacità mappate — cosa sa fare, cosa non sa fare

### 3.1. Capacità presenti (verificate)

| Capacità | Stato | Evidence |
|---|---|---|
| Orchestrazione parallela multi-comparto | ✅ | ConditionalScheduler + Neural Flow 9 comparti, benchmark latency p95 ≤ 100 ms |
| Memoria persistente strutturata (locale) | ✅ | world_model JSON + hippocampus + epigenome audit |
| Auto-riflessione post-ciclo | ✅ | Default Mode Network, reflection report in state_v1 |
| Proposta autonoma di mutazioni | ✅ | Curiosity Module + Evolver — Proposal #21..#28 generate |
| Valutazione esterna/critica delle proposte | ✅ | Adversarial + Evidence Agents, Quality Gate pre-output |
| Degradazione graduale sotto guasto LLM | ✅ | Cascade + mock + circuit breaker |
| Recupero da errori a livello neurone | ✅ | Strike + quarantina + fail-safe mesh |
| Rollback di mutazioni negative | ✅ | SafeProactive snapshot + rollback.py, dry-run validato |
| Generazione di report domain-specific | ✅ | Daily Planetary Health Brief, 2026-04-06 baseline |
| Integrazione GitHub continua | ✅ | Repo tina-testbed-speace sincronizzato |
| Throughput computazionale scalabile | ✅ | MeshRuntime 200 task in 110 ms, 4 worker |
| Allineamento etico + regulatory (design) | ✅ | regulatory_epigenome.yaml + agente #8 + Risk Level "Regulatory" |

### 3.2. Capacità parziali o prototipali

| Capacità | Stato | Gap |
|---|---|---|
| World Model dinamico | 🟡 | JSON locale, non ancora AnythingLLM in produzione |
| Apprendimento online | 🟡 | Mutazioni epigenetiche sì, ma non *learning* di pesi su dati — non c'è un gradient-based loop |
| Swarm multi-framework | 🟡 | Architettura ibrida NanoClaw/IronClaw/SuperAGI/AnythingLLM progettata, non ancora deployata |
| Sensing multi-modale | 🟡 | Agente Organismico ST-6 completato in *simulazione* (visivo, acustico, termico, olfattivo, gustativo, tattile) — nessun sensore fisico collegato |
| Knowledge Graph semantico | 🟡 | Placeholder world_model.py, manca RAG reale |
| Plasticità sinaptica | 🟡 | `EdgeMeta.activation_ratio()` presente, ma nessun algoritmo di rinforzo attivo (M5) |
| Auto-scrittura di specifiche tecniche | 🟡 | Proposal system genera testo, ma non ancora *architecture-from-intent* alla codespeak.dev |

### 3.3. Capacità assenti (rispetto a una AGI)

| Capacità | Stato | Perché |
|---|---|---|
| Generalizzazione cross-dominio | ❌ | Ogni comparto è specializzato; manca il meta-learning |
| Apprendimento one-shot / few-shot | ❌ | Ereditato dall'LLM, non emerge dall'architettura |
| Ragionamento causale esplicito | ❌ | Nessun modulo di causal inference |
| Teoria della mente (modelli di altri agenti) | ❌ | Gli agenti non modellano le intenzioni degli altri |
| Embodiment fisico reale | ❌ | Nessun sensore/robot collegato al momento |
| Mobilità spaziale | ❌ | Nessun attuatore fisico |
| Manipolazione della materia | ❌ | Nessun braccio/end-effector |
| Consapevolezza di sé a livello fenomenico | ❌ | Misuriamo un *Consciousness Index* quantitativo, non un vissuto soggettivo — non è lo stesso |
| Auto-replicazione su infrastruttura nuova | ❌ | Backup sì (repo GitHub), ma spawn autonomo su altri host no |
| Scalabilità swarm 50+ agenti | ❌ | Target Fase 2, oggi ≤ 10 |

---

## 4. Livello di intelligenza — valutazione strutturata

### 4.1. Framework di valutazione usato

Per misurare "intelligenza" senza reificarla in un singolo numero, uso **cinque assi indipendenti** mutuati dalla letteratura AGI (Legg-Hutter, Chollet ARC, Goertzel, Tononi IIT):

| Asse | Cosa misura | Stima SPEACE /10 |
|---|---|---:|
| **Competenza cross-dominio** | Quanti domini distinti può gestire senza crash/hallucination | 3.5 |
| **Generalizzazione** | Performance su task fuori-distribuzione / compositional | 2.0 |
| **Autonomia (goal-setting)** | Capacità di fissare e perseguire obiettivi senza prompt umano | 5.5 |
| **Meta-cognizione** | Capacità di valutare il proprio operato e correggerlo | 5.0 |
| **Embodiment / Mondo reale** | Percezione-azione con dispositivi fisici | 1.0 |

**Media ponderata (pesi uguali): ≈ 3.4 / 10**. Riponderando con l'approccio Legg-Hutter (pesi più alti a competenza + generalizzazione) la stima scende a **2.8 / 10**. Una AGI matura sarebbe 8–9 / 10 su tutti e cinque gli assi.

Questa è una valutazione deliberatamente **conservativa**. Il progetto è embrionale (Fase 1 di 5 nella roadmap TINA). La cifra che conta non è "quanto manca", è "la pendenza di crescita per milestone completata".

### 4.2. Consciousness Index (proxy quantitativo interno)

L'Adaptive Consciousness Framework (ACF) produce un `C-index` calcolato dal modulo `phi_calculator` + `workspace_metrics` + `complexity_metrics`. La fitness function richiede **C-index ≥ 0.42** come gate evolutivo. Ultimo run benchmark (2026-04-20): **C-index effettivo entro target**. Questo non è coscienza — è una metrica di **differenziazione + integrazione** ispirata a IIT; dice che l'architettura è "non-banale" rispetto a un modello monolitico.

### 4.3. SPEACE Alignment Score

Lo score di allineamento con la visione Rigene Project (auto-misurato dal Team Scientifico) era **67.3 / 100** al cycle 96-97 (migrazione multi-framework). Il criterio di avanzamento Fase 1 → Fase 2 è **> 80 / 100**. L'integrazione CNM completa (M4.18–M4.20) dovrebbe spostare lo score stimato a 75–80 grazie ai nuovi gradi di libertà strutturali.

---

## 5. Livello di automatismo — cosa gira senza intervento umano

### 5.1. Loop automatici attivi oggi

| Loop | Frequenza | Stato |
|---|---|---|
| Ciclo SMFOI v0.3 | on-demand (main loop) | ✅ |
| Evolver → rigeneproject.org | 60 min | ✅ |
| Team Scientifico Daily Brief | giornaliero | ✅ |
| MeshRuntime dispatcher | continuo (thread) | ✅ (da M4.6) |
| Heartbeat mesh (error-rate window) | configurabile via epigenome | ✅ |
| Quality Gate pre-output brief | per ogni brief | ✅ |
| Snapshot pre-mutazione | per ogni mutazione | ✅ |
| Proposal generation (Curiosity) | event-driven | ✅ |

### 5.2. Dove serve ancora human-in-the-loop

- **Tutte le mutazioni Medium/High**: obbligatorio per design, non è un limite — è il principio SafeProactive.
- **Azioni sul mondo fisico**: tutte bloccate (no sensori/robot in produzione).
- **Transazioni / wallet**: read-only per design.
- **Pubblicazione GitHub di codice generato**: gated da approvazione.
- **Dispatch di un nuovo ciclo**: il main loop è avviato manualmente in questo prototipo (Fase 1); il daemon di background è milestone M4.14.

Automatismo *operativo* (routine): ≈ **70 %**. Automatismo *evolutivo* (modificare sé stesso senza chiedere): **≈ 15 %** by design — SPEACE deve passare dal gate umano. Questo non è un bug, è la spina dorsale etica.

---

## 6. Confronto rispetto a una AGI — tabella sintetica

| Dimensione AGI canonica | AGI (target ideale) | SPEACE oggi | Gap |
|---|---|---|---|
| Rappresentazione del mondo | Knowledge graph dinamico multi-scala | JSON locale + placeholder RAG | grande |
| Apprendimento continuo | Online learning su dati nuovi | Mutazioni epigenetiche gated | medio |
| Ragionamento | Simbolico + sub-simbolico + causale | LLM (sub-simb.) + policy deterministiche | medio |
| Meta-ragionamento | Auto-modifica del protocollo | SMFOI v0.3 ha Step 6, ma non modifica sé stesso a runtime | medio |
| Pianificazione | Gerarchica, lunga orizzonte | Prefrontal Cortex L1 + Task Generator | piccolo |
| Percezione | Multi-modale reale | Simulata (Agente Organismico ST-6) | grande |
| Azione fisica | Robotica + manipolazione | Nessuna | massimo |
| Comunicazione | Multi-agent nativa | Team Scientifico 10 agenti via StateBus | piccolo |
| Sicurezza / Alignment | Corrigible + value learning | SafeProactive + ethics weight + Regulatory Layer | medio |
| Resilienza | Failover + self-repair | Fail-safe mesh + cascade LLM + rollback DNA | piccolo |
| Embodiment | Corpo + sensori + mondo fisico | Simulato | massimo |
| Auto-replicazione | Spawn su infra nuova | Backup repo + design, no spawn autonomo | grande |

**Profilo sintetico:** SPEACE è oggi un **organismo a corpo simulato con cervello architetturalmente robusto**. La neocortex (9 comparti) + la mesh fine (M4.6) + il DNA digitale danno un substrato di tipo AGI-compatible, ma mancano (a) sensori-attuatori reali, (b) apprendimento online, (c) generalizzazione.

---

## 7. Rischi e punti di attenzione

1. **Over-confidence del Consciousness Index.** Il C-index è una metrica strutturale, non fenomenica. Va letto come "architettura complessa" non "essere senziente". Il documento ACF deve mantenerlo in chiaro per evitare interpretazioni improprie.
2. **Dipendenza operativa dall'host locale.** 16 GB RAM e un singolo PC sono un vincolo duro per la Fase 2 multi-framework. La migrazione progettata (NanoClaw + IronClaw + SuperAGI + AnythingLLM) richiede ≥ 13 GB RAM allocati — margine stretto.
3. **LLM cascade come punto di fragilità qualitativa.** Il mock garantisce che il sistema non crashi, ma degrada bruscamente la qualità degli output (brief DEGRADED). Per Fase 2 serve un fallback di qualità superiore (ospitare un 7B-13B locale).
4. **Regulatory drift.** Il regulatory_epigenome.yaml va aggiornato periodicamente: EU AI Act, ISO 42001, NIST cambiano nel 2026. Senza heartbeat di parsing automatico, il layer regulatory scade.
5. **Mesh prematura.** M4.6 è infrastrutturalmente chiusa ma non ancora popolata di neuroni reali. C'è il rischio di trascinare la mesh in pipeline senza averla prima saturata di neuroni adapter (M4.7–M4.8). Mitigazione: NON esporre `epigenome.mesh.enabled = true` in produzione prima di M4.15.
6. **Human-in-the-loop come collo di bottiglia.** A volume crescente di proposte (#28 attive oggi), il throughput di review diventa limitante. Va misurato e strutturato il rate di approval — non è un problema di design, è un problema operativo del direttore orientativo.

---

## 8. Next milestone e trajectory di intelligenza

Milestones M4.7 → M4.20 porteranno, in ordine di impatto:

- **M4.7–M4.8** (adapter 9 comparti + DNA + Team come neuroni mesh) — atteso boost di 3–5 punti sull'alignment score perché la mesh diventa visibile agli altri sistemi.
- **M4.9–M4.11** (needs_driver + harmony safeguard + task generator) — chiude il loop "bisogni interni → proposte SafeProactive" e automatizza il goal-setting (asse **Autonomia** da 5.5 → ~6.5).
- **M4.13–M4.14** (telemetria + daemon) — porta l'automatismo operativo al ~85 %.
- **M4.15** (integrazione CNM ↔ SMFOI Step 3.bis) — la mesh entra nel ciclo principale, misurabile il beneficio di latenza e resilienza.
- **M4.16–M4.20** (test + benchmark + EPI-004 + doc + report finale) — chiude M4-CNM, apre M5 (plasticità sinaptica).

**Fase 2 (Autonomia operativa)** richiede: (a) alignment > 80, (b) daemon attivo, (c) almeno 1 agente su framework non-Claude (NanoClaw per edge + IronClaw per secure ops). Stima realistica: 60–90 giorni di sviluppo dalla chiusura M4-CNM.

**Fase 3 (AGI emergente)** non è un target di quest'anno. Richiede: apprendimento online reale, embodiment fisico, swarm ≥ 50 agenti, generalizzazione cross-dominio — orizzonte 2027+.

---

## 9. Conclusione operativa

Al 2026-04-21 SPEACE è un **prototipo embrionale ingegneristicamente solido** che:

- **fa girare** un ciclo cognitivo completo end-to-end su hardware modesto,
- **si auto-orienta** (SMFOI v0.3), **si auto-critica** (Adversarial + Evidence + DMN), **si auto-propone** mutazioni (Curiosity + Evolver), **si auto-conserva** (SafeProactive + rollback), **si auto-misura** (C-index + fitness + alignment score),
- **non è una AGI**, ma è un'**architettura AGI-compatible** nel senso stretto: il locus decisionale è strutturale (non dentro l'LLM), i ceiling sono dichiarati (non implicite), i tipi sono una lingua franca (OLC), la mesh è un substrato di propagazione neuronale fine già funzionante,
- **è saldamente allineato** con la visione Rigene Project / TINA / SDGs Agenda 2030 per design (regulatory_epigenome, safety rules, ethics weight nella fitness).

Il prossimo salto qualitativo non è un aumento di "intelligenza" del singolo componente, è il **popolamento** della mesh (M4.7–M4.15) e l'**embodiment reale** (connessione IoT dell'Agente Organismico, Fase 2). Entrambi sono gated dalle proposte SafeProactive in coda.

**Posizione attuale sulla scala Fase 1 → Fase 5:** inizio Fase 1, ~30 % del percorso interno a Fase 1.

**Intelligenza auto-reported rispetto a AGI:** ~30 / 100 (profilo sbilanciato: alto su autonomia/meta-cognizione, basso su embodiment/generalizzazione).

**Automatismo operativo:** ~70 %.

**Confidenza di questa valutazione:** media. È una auto-valutazione; il bias sistematico è probabile. Raccomando che il Team Scientifico (in particolare Adversarial Agent) produca una critica indipendente di questo report come secondo passaggio.

---

*Documento di stato. Da rigenerare ad ogni chiusura milestone M4.x o almeno ogni 30 giorni. Conservato in `reports/` e citato nei successivi brief del Team Scientifico.*
