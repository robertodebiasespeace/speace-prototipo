# SPEACE-EA Integration

## Panoramica

Sistema di trading semi-autonomo per **XAUUSD** su **MetaTrader 5 (Demo)**, orchestrato dall'architettura cognitiva SPEACE.

```
MT5 Terminal  <--JSON files-->  SPEACE Cortex  <-->  EA Evolver Agent
  SPEACE_XAUUSD_EA.mq5          trading_cortex.py    speace-ea-evolver.py
                              ea_genome.yaml        ea_epigenome.yaml
                              SafeProactive         (mutations)
```

## Architettura

### Loop Cognitivo SPEACE-EA

```
MT5 EA legge JSON  →  scr ive metrics  →  trading_cortex legge metrics
  →  valuta fitness  →  evo agent propone mutazioni
  →  SafeProactive approva  →  ea_params.json aggiornato
  →  EA ricarica parametri  →  ciclo riparte (ogni 5 min)
```

### 3 Componenti Principali

| File | Ruolo |
|------|-------|
| `SPEACE_XAUUSD_EA.mq5` | Expert Advisor MQL5 — esegue trades, scrive metrics |
| `trading_cortex.py` | Compartment L2 — analizza metrics, propone mutazioni |
| `speace-ea-evolver.py` | Agente — applica mutazioni approvate, gestisce rollback |

### Ciclo SMFOI (EA Evolver)

1. **Self-Location** — posizione nella sessione di trading
2. **Constraint Mapping** — balance, drawdown, limiti di rischio
3. **Push Detection** — metriche EA, fitness attuale
4. **Survival Stack** — Lv0 (emergency) → Lv1 (monitor) → Lv2 (optimize) → Lv3 (evolve)
5. **Output Action** — applica mutazioni / emergency params
6. **Outcome Evaluation** — fitness score, auto-rollback

### Fitness Function (6 componenti)

```
fitness = alignment×0.25 + task_success×0.20 + stability×0.15
         + efficiency×0.10 + ethics×0.05 + c_index×0.25
```

## Installazione

### 1. MT5 Setup

1. Apri MetaTrader 5
2. Apri un **Demo account** su XAUUSD
3. Menu → Tools → Options → Expert Advisors:
   - ✅ `Allow live trading`
   - ✅ `Allow DLL imports`
4. Menu → File → Open Data Folder → `MQL5\Experts\`
5. Copia `SPEACE_XAUUSD_EA.mq5` in quella cartella
6. Apri MetaEditor (F7), compila l'EA
7. Trascina l'EA sul chart XAUUSD
8. Nella scheda **Inputs** imposta:
   - `SPEACE_SharedPath = C:\Users\rober\Documents\Claude\Projects\SPEACE-prototipo\speace-ea-integration\shared_state\`

### 2. Avvio SPEACE-EA

```batch
cd C:\Users\rober\Documents\Claude\Projects\SPEACE-prototipo
.\speace-ea-integration\LAUNCH-SPEACE-EA.bat
```

Oppure manualmente:
```bash
# Terminale 1: EA Evolver (ogni 5 min)
python speace-ea-integration\speace-ea-evolver.py --interval 5

# Terminale 2: Status Monitor (ogni 5 min)
python speace-ea-integration\speace-ea-monitor.py --interval 5
```

## Parametri Mutabili (epigenetici)

| Parametro | Default | Range | Trigger |
|-----------|---------|-------|---------|
| `LotSize` | 0.10 | 0.01–1.0 | Drawdown > 10% |
| `StopLossPips` | 500 | 50–5000 | Alta volatilità |
| `TakeProfitPips` | 1000 | 100–10000 | Basso win rate |
| `RSI_Period` | 14 | 2–100 | Win rate < 40% |
| `MA_Fast_Period` | 10 | 2–200 | Nessun trade |
| `MA_Slow_Period` | 30 | 5–500 | Nessun trade |
| `MaxTrades` | 3 | 1–10 | Drawdown > 15% |

## Parametri Immutabili (safety hard limit)

- `MaxDrawdownPct = 20%` — chiusura forzata di tutte le posizioni
- `MaxDailyLoss = $100` — stop giornaliero
- `MaxSingleTradeRisk = 2%` — rischio max per trade

## File Interface (JSON)

### ea_metrics.json (EA → SPEACE)
```json
{
  "timestamp": "2026-04-20 10:30:00",
  "balance": 10000.00,
  "equity": 10150.00,
  "drawdown_pct": 2.1,
  "win_rate": 0.583,
  "total_trades": 12,
  "open_trades": 1,
  "rsi": 45.2,
  "ma_fast": 2345.67,
  "ma_slow": 2340.12,
  "spread_pips": 25.0
}
```

### ea_params.json (SPEACE → EA)
```json
{
  "LotSize": 0.1,
  "StopLossPips": 500,
  "TakeProfitPips": 1000,
  "RSI_Period": 14,
  "MA_Fast_Period": 10,
  "MA_Slow_Period": 30,
  "MaxTrades": 3
}
```

## Integrazione con SPEACE Cortex

Il `trading_cortex.py` è un compartment L2 registrato nel cortex di SPEACE. Si integra nel loop SMFOI principale di SPEACE come un qualsiasi altro comparto cerebrale:

- Riceve lo `state_bus` dallo stato condiviso
- Legge `ea_metrics.json`
- Valuta fitness e propone mutazioni
- Scrive in `PROPOSALS.md` di SafeProactive
- Se fitness cala > 10% → auto-rollback via SafeProactive

## Sicurezza

- **SafeProactive WAL**: ogni mutazione viene loggata con snapshot pre/post
- **Approval Gates**: mutazioni epigenetiche = LOW (auto), strutturali = HIGH
- **Emergency Mode**: drawdown > 15% → lotto minimo, 1 trade max
- **Human Override**: sempre possibile intervenire manualmente su MT5

## Struttura File

```
speace-ea-integration/
├── mt5_experts/
│   └── SPEACE_XAUUSD_EA.mq5      ← EA da caricare in MT5
├── shared_state/
│   ├── ea_metrics.json            ← Metrics EA (letto da SPEACE)
│   ├── ea_state.json             ← State EA
│   └── ea_params.json            ← Parametri modificati (letto da EA)
├── logs/
│   └── ea_evolver_log.jsonl      ← Log cicli evolver
├── snapshots/                     ← Snapshots SafeProactive
├── ea_genome.yaml                ← Identity (immutabile)
├── ea_epigenome.yaml             ← Parametri (mutabile)
├── speace-ea-evolver.py          ← Agente evolver
├── speace-ea-monitor.py          ← Status monitor
└── LAUNCH-SPEACE-EA.bat          ← Launcher


-----------

dir "C:\Users\rober\Documents\Claude\Projects\SPEACE-prototipo\speace-ea-integration\shared_state\"

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----        20/04/2026     15:58            165 ea_params.json
-a----        20/04/2026     15:58            161 ea_state.json
                                                 metrics


 Get-Content "C:\Users\rober\Documents\Claude\Projects\SPEACE-prototipo\speace-ea-integration\shared_state\ea_metrics.json"


```
