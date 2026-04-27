# SCHEDA TECNICA ST-4 – SafeProactive
**Versione:** 1.0  
**Data:** 17 aprile 2026  
**Stato:** Operativo – Uno dei moduli più maturi

---

## 1. Descrizione

Sistema di Write-Ahead Logging + approval gates. Garantisce che nessuna azione a rischio venga eseguita senza revisione umana o approvazione esplicita.

## 2. Architettura

```
SafeProactive/
├── PROPOSALS.md              # Registro proposte azioni
├── WAL/                      # Write-Ahead Log
│   ├── action_log.md
│   └── mutation_log.md
├── approval_gates/           # Gate di approvazione
│   ├── low_risk/
│   ├── medium_risk/
│   ├── high_risk/
│   └── regulatory/
├── rollback_system/         # ← NUOVO: Sistema rollback
│   ├── snapshots/
│   ├── version_control/
│   └── rollback_commands/
└── risk_classification/
    ├── low.yaml
    ├── medium.yaml
    ├── high.yaml
    └── regulatory.yaml
```

## 3. Livelli di Rischio

| Livello | Descrizione | Azione | Esempi |
|---------|-------------|--------|--------|
| **Low** | Operazioni di sola lettura, non destructive | Auto-approved | Query, read, status check |
| **Medium** | Modifiche reversibili, impatto limitato | Human-in-loop | Aggiornamento parametri, task execution |
| **High** | Transazioni, modifiche permanenti, azioni esterne | Human + Legal review | Transazioni wallet, mutazioni DigitalDNA |
| **Regulatory** | Impatto sistemico, conformità normativa | Human + Legal + Compliance | EU AI Act, NIST, ISO changes |

## 4. Flusso Approval

```
┌─────────────┐
│  Proposta    │ (Azione desiderata)
└──────┬──────┘
       ▼
┌─────────────┐
│ Risk Assess │ (SafeProactive classifica)
└──────┬──────┘
       ▼
┌─────────────────────────────────────────┐
│          Approval Gate                  │
├─────────────────────────────────────────┤
│ Low      → Auto-approved                │
│ Medium   → Human-in-loop                │
│ High     → Human + Legal review         │
│ Regulatory→ Human + Legal + Compliance  │
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────┐
│  Esecuzione │ (Se approvata)
└──────┬──────┘
       ▼
┌─────────────┐
│  Logging    │ (WAL)
└─────────────┘
```

## 5. PROPOSALS.md – Formato

```markdown
# SPEACE SafeProactive Proposals

## Proposal #[ID]
- **Data:** [timestamp]
- **Azione:** [descrizione]
- **Risk Level:** [low/medium/high/regulatory]
- **Stato:** [pending/approved/rejected/executed/rolled_back]
- **Richiesto da:** [source]
- **Dettagli:**
  - Target: [cosa verrà modificato]
  - Motivazione: [perché necessario]
  - Impact: [impatto stimato]
- **Approvazione:**
  - [Approvatore] - [Data] - [Decisione]
  - Note: [eventuali note]
```

## 6. Rollback System ← NUOVO (REQUISITI)

### 6.1 Componenti

```yaml
rollback_system:
  enabled: true
  
  components:
    - name: "Versioning Automatico"
      files_tracked:
        - "genome.yaml"
        - "epigenome.yaml"
        - "state.json"
        - "DigitalDNA/snapshots/"
      format: "timestamp_based"
      
    - name: "Snapshot Pre-Mutazione"
      automatic: true
      storage: "SafeProactive/rollback_system/snapshots/"
      retention: 30_days
      
    - name: "Comando Rollback Sicuro"
      requires_approval: true
      approval_level: "human_in_loop"
      syntax: "safeproactive rollback [snapshot_id]"
      
    - name: "Mutation Revert Log"
      file: "mutation_revert_log.md"
      content: "[timestamp] REVERTED [mutation_id] → [reason]"
```

### 6.2 Flusso Rollback

```
1. Trigger Rollback (manuale o automatico su fitness < threshold)
   ↓
2. SafeProactive valuta richiesta
   ↓
3. Human approval (se high/regulatory)
   ↓
4. Snapshot stato corrente
   ↓
5. Recupero snapshot pre-mutazione
   ↓
6. Restore file
   ↓
7. Update WAL: "MUTATION REVERTED"
   ↓
8. Verifica integrità sistema
```

### 6.3 Criteri Rollback Automatico

```yaml
auto_rollback:
  enabled: true
  
  triggers:
    - fitness_below_threshold: 0.50
    - stability_drop: 0.70
    - alignment_drift: -10.0
    - safeproactive_violation: true
    - regulatory_breach: true
  
  actions:
    - snapshot_current_state
    - notify_human: true
    - log_incident: true
```

## 7. Write-Ahead Log (WAL)

```markdown
# SafeProactive WAL

## Action Log Entry
- **Timestamp:** [YYYY-MM-DD HH:MM:SS]
- **Action ID:** [unique_id]
- **Type:** [proposal_execution/mutation/rollback]
- **Risk Level:** [level]
- **Actor:** [who/what triggered]
- **Target:** [affected file/system]
- **Before State:** [hash/summary]
- **After State:** [hash/summary]
- **Approved By:** [human/auto]
- **Result:** [success/failure]

## Mutation Log Entry
- **Timestamp:** [YYYY-MM-DD HH:MM:SS]
- **Mutation ID:** [MUT-XXX]
- **Type:** [epigenetic/genome]
- **Fitness Before:** [value]
- **Fitness After:** [value]
- **Auto-Rollback Triggered:** [true/false]
```

## 8. Integrazione con DigitalDNA

```yaml
integration:
  digitaldna:
    mutation_requires_safeproactive: true
    snapshot_before_mutation: true
    rollback_capability: true
    
  speace_cortex:
    all_critical_actions: "pass_through_safeproactive"
    risk_classification: "automatic"
    
  team_scientifico:
    proposals_require_approval: true
    evolutionary_proposals: "medium_risk"
```

## 9. Esempio Flow Completo

```
1. speace-cortex-evolver genera proposta mutazione
2. SafeProactive classifica: "medium_risk"
3. Human-in-loop avvisato (Roberto De Biase)
4. Roberto approva via WhatsApp/email
5. SafeProactive:
   - Crea snapshot pre-mutazione
   - Esegue mutazione su epigenome.yaml
   - Logga in WAL
   - Aggiorna fitness
6. Outcome Evaluation misura risultato
7. Se fitness < 0.50 → Auto-rollback trigger
```

## 10. Metriche

| Metrica | Valore |
|---------|--------|
| Proposals processati | 28 |
| Approval rate | ~85% |
| Reject rate | ~15% |
| Rollback eseguiti | 0 (nessuno ancora necessario) |
| Mean time to approval | ~2 minuti |

---

## 11. Enhancement Proposti

| Enhancement | Priorità | Impatto |
|-------------|----------|----------|
| Rollback System | ALTA | Resilienza mutazioni negative |
| Regulatory Risk Level | ALTA | Conformità EU AI Act |
| Auto-rollback su fitness threshold | ALTA | Prevenzione derive |
| Telegram/SMS notification | MEDIA | Faster human approval |
| Dashboard web per approvals | MEDIA | UX migliore |
