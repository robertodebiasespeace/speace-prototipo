# SPEACE Dashboard

GUI di monitoraggio su **localhost** per lo stato di SPEACE, il grado di intelligenza rispetto a una AGI, le capacità funzionali e l'efficienza dell'architettura.

## Avvio

```bash
# dalla root di SPEACE-prototipo/
python -m dashboard.speace_dashboard
```

Poi apri nel browser: <http://localhost:8765>

### Variabili d'ambiente

- `SPEACE_DASHBOARD_HOST` (default `127.0.0.1`) — bind address
- `SPEACE_DASHBOARD_PORT` (default `8765`) — porta TCP

## Cosa mostra

- **KPI** — Fase SPEACE, alignment score vs Rigene, AGI score /100, fitness DNA corrente
- **Radar AGI** — 5 assi (cross-dominio, generalizzazione, autonomia, meta-cognizione, embodiment) vs target AGI 8.5
- **Test CNM** — stato regression Continuous Neural Mesh: contract + graph + runtime + rules
- **Milestones M4-CNM** — progress bar + checklist di tutte le sotto-milestone M4.1..M4.20
- **Capacità** — donut chart + 3 liste (presenti / parziali / assenti) con ~30 voci
- **Benchmark M3L.6** — 8 benchmark letti da `benchmarks/results.json` (tests, smoke, cindex, fitness, latency, rollback_cli, llm_smoke, neural_flow)
- **Mutazioni DNA** — lista EPI-NNN attive lette da `digitaldna/epigenome.yaml`
- **Throughput chiave** — MeshRuntime 200 task / 4 worker, MeshGraph 100 nodi + topo sort
- **Storico cicli SMFOI** — line chart della fitness sugli ultimi 10 cicli

## API JSON (per integrazione)

| Endpoint | Contenuto |
|---|---|
| `GET /healthz` | liveness probe |
| `GET /api/status` | snapshot generale (fase, fitness, c_index, mesh_version) |
| `GET /api/agi` | assi AGI + score complessivo |
| `GET /api/capabilities` | capacità presenti/parziali/assenti |
| `GET /api/architecture` | test CNM + benchmark M3L.6 + throughput |
| `GET /api/milestones` | progress M4.x |
| `GET /api/epigenome` | mutazioni DNA attive |
| `GET /api/cycles` | ultimi 10 cicli SMFOI |

Auto-refresh ogni 10s lato client.

## Dipendenze

- **Lato server**: stdlib Python 3.10+ (no Flask, no FastAPI). Lettura file-system read-only.
- **Lato client**: Tailwind CSS + Chart.js 4 via CDN (cdn.tailwindcss.com, cdn.jsdelivr.net). Nessun build step.

## Sicurezza

Il server si bind di default su `127.0.0.1` — non è esposto a LAN. Per esporre ad altre macchine: `SPEACE_DASHBOARD_HOST=0.0.0.0`. **Non esporre su internet**: la dashboard è read-only ma rivela lo stato interno di SPEACE.

Nessuna API modifica file; tutti gli endpoint `/api/*` sono `GET` e leggono lo snapshot corrente.

## Roadmap

- v1.1: WebSocket live (invece di polling 10s)
- v1.2: dump live `mesh_state.jsonl` (dopo M4.13)
- v1.3: trigger di `run_benchmarks.py` via bottone (gated da SafeProactive)
- v1.4: grafo MeshGraph visualizzato con Cytoscape.js
