# SPEC — Neuron Contract v1.0

**Milestone:** M4.1 (PROP-CORTEX-NEURAL-MESH-M4)
**Stato:** DRAFT formale — input per M4.2 (`contract.py`)
**Data:** 2026-04-20
**Autore:** SPEACE (Evolutionary Dev Agent) sotto direzione di Roberto De Biase
**Ambito:** definizione di cosa è un "neurone" nella Continuous Neural Mesh.

> **Principio cardine.** Un neurone è l'**unità atomica di calcolo riusabile** della mesh. Non è un processo, non è un thread, non è un agente LLM: è una funzione pura tipizzata che consuma un input strutturato e produce un output strutturato, con metadata dichiarati, lifecycle deterministico e budget di risorse espliciti. L'intelligenza della mesh emerge dalla **composizione** tipizzata di neuroni, non dal singolo neurone.

---

## 1. Forma strutturale

### 1.1 Definizione (semantica informale)

Un **Neurone** è un artefatto eseguibile che soddisfa tutti i seguenti requisiti:

1. **È dichiarato** tramite il decoratore `@neuron(...)` (M4.7) oppure tramite ereditarietà dalla classe base `Neuron` (M4.2).
2. **Ha un identificatore stabile** (`name`) univoco nell'intera mesh (`str`, kebab-case, regex `^[a-z0-9][a-z0-9_.-]{1,63}$`).
3. **Dichiara il suo contratto I/O tipizzato** via i campi `input_type` e `output_type` (tipi dell'OLC — M4.3).
4. **Dichiara tutti i suoi metadata** (livello, needs, budget, side effects) — senza metadata il contratto è invalido.
5. **Implementa `execute(input: Tin) -> Tout`** come funzione **pura tipizzata**. Se ha side effect, DEVE dichiararli esplicitamente (vedi §4).
6. **Obbedisce agli invarianti di lifecycle** (vedi §5).
7. **È idempotente** rispetto allo stesso input quando `side_effects == []` (proprietà testabile al boot).

### 1.2 Forma minima (pseudo-API)

```python
from cortex.mesh.contract import neuron, Neuron, ContractViolation
from cortex.mesh.olc.types import SensoryFrame, InterpretationFrame

@neuron(
    name="neuron.example.echo",
    input_type=SensoryFrame,
    output_type=InterpretationFrame,
    level=2,                                # L1..L5 della control hierarchy
    needs_served=["integration"],
    resource_budget={"max_ms": 200, "max_mb": 32},
    side_effects=[],                        # funzione pura
    version="1.0.0",
)
def echo(inp: SensoryFrame) -> InterpretationFrame:
    return InterpretationFrame(intent="echo", confidence=1.0, source=inp.source)
```

Equivalentemente, per neuroni più complessi (state interno, init/cleanup):

```python
class EchoNeuron(Neuron):
    name = "neuron.example.echo"
    input_type = SensoryFrame
    output_type = InterpretationFrame
    level = 2
    needs_served = ["integration"]
    resource_budget = {"max_ms": 200, "max_mb": 32}
    side_effects: list[str] = []
    version = "1.0.0"

    def on_init(self) -> None: ...
    def execute(self, inp: SensoryFrame) -> InterpretationFrame: ...
    def on_cleanup(self) -> None: ...
```

## 2. Tipi (interfaccia con OLC)

L'OLC (M4.3) è l'unico registry autoritativo dei tipi scambiabili fra neuroni. Un neurone **non può** dichiarare `input_type` o `output_type` che non siano registrati nell'OLC (il validator rifiuta al boot).

### 2.1 Tipi fondamentali (M4.3 seed)

| Tipo OLC | Descrizione | Prodotto tipicamente da | Consumato tipicamente da |
|---|---|---|---|
| `SensoryFrame` | Input raw dal mondo (testo, numeri, dict arbitrario sotto schema) | Parietal Lobe, Agente Organismico | Temporal Lobe |
| `InterpretationFrame` | Intent + entità + confidenza | Temporal Lobe | World Model, Prefrontal |
| `WorldSnapshot` | Subset rilevante del World Model per il ciclo | World Model | Prefrontal, Scientific Team |
| `DecisionFrame` | Azione proposta + args + risk_level + pre_approved | Prefrontal Cortex | Safety Module, Cerebellum |
| `SafetyVerdict` | blocked + risk_level + reasons[] | Safety Module | Cerebellum, Telemetry |
| `ActionResult` | ok/error + output + latency_ms | Cerebellum | Hippocampus, Telemetry |
| `MemoryDelta` | Episodi da consolidare | Hippocampus | WorldModel, DMN |
| `ReflectionFrame` | Self-critique + suggerimenti | Default Mode Network | Curiosity |
| `MutationProposal` | Proposta di mutazione DNA/struttura → SafeProactive | Curiosity | SafeProactive gate |
| `NeedsSnapshot` | Stato dei 5 bisogni (v. §6.2) | Needs Driver | Task Generator, Runtime |
| `FeedbackFrame` | Segnali di fitness/latenza/errori per ciclo | Runtime | Needs Driver, Telemetry |
| `TaskProposal` | Task emergente da need sotto soglia → PROP-SP | Task Generator | SafeProactive |

**Regole sui tipi OLC:**
- Ogni tipo è una `@dataclass(frozen=True)` con tipi primitivi o altri OLC-types (nessun tipo arbitrario).
- Ogni tipo dichiara `_OLC_VERSION = "1.0"` e `_OLC_NAME` univoco.
- Serializzabile in JSON tramite `.to_dict()` / `.from_dict()` (simmetriche e senza perdita).
- Le aggiunte di campi opzionali sono backward-compatible; le aggiunte di campi required richiedono bump di versione OLC e migrazione esplicita.

### 2.2 Compatibilità dinamica

Un neurone A può feed un neurone B se e solo se `A.output_type.is_compatible_with(B.input_type)`. La compatibilità è:
- **Esatta**: `A.output_type == B.input_type`.
- **Sottotipo**: `A.output_type` include tutti i campi required di `B.input_type` e supera `B.input_type.validate()` (strutturale, non nominale).

Il validatore statico (M4.2) costruisce il grafo delle compatibilità al boot e rifiuta avvio se un edge è incompatibile.

## 3. Metadata obbligatori

Ogni neurone DEVE dichiarare, al minimo, i seguenti metadata (enumerato esaustivo; campi mancanti → `ContractViolation.MISSING_METADATA`):

| Campo | Tipo | Obbligatorio | Esempio | Semantica |
|---|---|---|---|---|
| `name` | `str` | ✅ | `"neuron.cortex.parietal"` | identificatore mesh-globale |
| `input_type` | OLC-type | ✅ | `SensoryFrame` | tipo input validato |
| `output_type` | OLC-type | ✅ | `InterpretationFrame` | tipo output validato |
| `level` | `int ∈ {1..5}` | ✅ | `4` | livello ControlHierarchy |
| `version` | `str` (semver) | ✅ | `"1.0.0"` | version del contratto |
| `needs_served` | `list[str] ⊆ NEEDS_CATALOG` | ✅ (≥1) | `["integration", "harmony"]` | a quali bisogni contribuisce |
| `resource_budget` | `dict` | ✅ | `{"max_ms": 500, "max_mb": 64}` | limiti runtime (M4.4) |
| `side_effects` | `list[SideEffectKind]` | ✅ (anche `[]`) | `["fs_write:mesh_state"]` | effetti dichiarati (v. §4) |
| `description` | `str` | ✅ | `"Consuma input sensoriale..."` | ≤ 200 char, umano |
| `tags` | `list[str]` | ⚪ | `["cortex", "sensing"]` | classificazione libera |
| `requires` | `list[str]` | ⚪ | `["llm:temporal", "kv:world"]` | dipendenze dichiarate |
| `deprecated_in` | `str` semver | ⚪ | `"2.0.0"` | versione rimozione programmata |
| `author` | `str` | ⚪ | `"evolutionary-dev-agent"` | traceability |

**Validazione statica:**
- `name` univoco nell'intera mesh.
- `level ∈ {1,2,3,4,5}` (hard check; 1=Controllo, 2=Cognizione, 3=Memoria, 4=Azione, 5=Evoluzione).
- `resource_budget.max_ms ≤ execution_rules.max_ms_hard_ceiling` (M4.4; default 30000).
- `resource_budget.max_mb ≤ execution_rules.max_mb_hard_ceiling` (M4.4; default 512).
- `needs_served ⊆ NEEDS_CATALOG = {"survival","expansion","self_improvement","integration","harmony"}`.
- `version` conforme a SemVer (`major.minor.patch`).

## 4. Side effects (dichiarativi)

I side effects NON sono vietati: sono **dichiarati**. Senza dichiarazione → `ContractViolation.UNDECLARED_SIDE_EFFECT`. Il runtime può rifiutare di eseguire un neurone che ha side effect non dichiarati (sandbox-based detection in M4.6).

### 4.1 Catalogo side effects (`SideEffectKind`)

| Kind | Formato | Esempio | Note |
|---|---|---|---|
| `fs_read:<path-pattern>` | glob | `"fs_read:digitaldna/*.yaml"` | path relativi al ROOT workspace |
| `fs_write:<path-pattern>` | glob | `"fs_write:mesh_state.jsonl"` | append-only preferito |
| `net:<host>[:port]` | host | `"net:api.anthropic.com:443"` | whitelist obbligatoria |
| `llm:<backend>` | backend | `"llm:openai_compat"` | usa cascade M3L.4 |
| `proposal:<risk>` | risk | `"proposal:medium"` | emette PROP-* in SafeProactive |
| `shell:<whitelisted>` | cmd | `"shell:git_status"` | solo comandi in `cerebellum.whitelist` |
| `kv:<namespace>` | ns | `"kv:world_model"` | KV store interno mesh |
| `state_bus:<key>` | key | `"state_bus:decision"` | scrittura sul StateBus (M3L.1) |

### 4.2 Regole

- `side_effects == []` ⇒ neurone **puro**; l'harness può eseguirlo idempotence test.
- `proposal:high` richiede anche `requires_human_approver=True` (enforced dal contract validator).
- Un neurone con `fs_write` fuori dalla whitelist del suo side_effect → rifiutato al boot.
- La detection runtime (M4.6) usa un FS watcher + wrapper di import per `requests`/`socket` per catturare violazioni. Primo strike → log, secondo strike → quarantena.

## 5. Lifecycle

Un neurone attraversa deterministicamente 5 fasi. Il runtime garantisce l'ordine; il contratto definisce gli invarianti per fase.

```
  (boot)          (per call)                     (shutdown)
REGISTERED → ACTIVATED ─┬─→ EXECUTING ──┬─→ COMPLETED → ... → RETIRED
                        │               │
                        │               └─(error)─→ ERRORED → (quarantine if N>=3)
                        │
                        └─(gate closed)─→ SKIPPED
```

### 5.1 Invarianti per fase

| Fase | Invariante | Violazione |
|---|---|---|
| `REGISTERED` | Tutti i metadata obbligatori presenti; `input/output_type` in OLC; name univoco | `ContractViolation.REGISTRATION_*` |
| `ACTIVATED` | `on_init()` completato senza eccezioni; `health()` ritorna True | `ContractViolation.ACTIVATION_FAILED` |
| `EXECUTING` | Input validato (`input_type.validate(inp) == []`); budget non scaduto | `ContractViolation.INPUT_INVALID` / `BUDGET_EXCEEDED` |
| `COMPLETED` | Output validato (`output_type.validate(out) == []`); side effects conformi a `side_effects` | `ContractViolation.OUTPUT_INVALID` / `UNDECLARED_SIDE_EFFECT` |
| `ERRORED` | Errore loggato, state_bus non corrotto, budget rilasciato | `ContractViolation.ERROR_NOT_HANDLED` |
| `SKIPPED` | `activation_gate(state) == False`; nessuna modifica state | — |
| `RETIRED` | `on_cleanup()` completato; risorse rilasciate | `ContractViolation.CLEANUP_FAILED` |

### 5.2 Gates

- **`activation_gate(state) -> bool`**: ereditato da BaseCompartment. Default: `True`. Un neurone può chiudere il gate se non ha motivo di girare in questo heartbeat (es. `novelty < threshold`).
- **`health() -> bool`**: boot-check. Default: `True`. Un neurone può sovrascrivere per verificare dipendenze (`llm.health`, `fs access`, etc.).
- **`precondition(input) -> list[str]`**: lista di violazioni pre-esecuzione (oltre al type-check). Default: `[]`.

### 5.3 Eventi lifecycle (osservabili da Telemetry M4.13)

Ogni transizione emette un evento su `mesh_state.jsonl`:

```jsonl
{"ts":"...","neuron":"neuron.cortex.parietal","event":"EXECUTING","cycle_id":"...","input_hash":"..."}
{"ts":"...","neuron":"neuron.cortex.parietal","event":"COMPLETED","latency_ms":12.4,"bytes_in":340,"bytes_out":712}
```

## 6. Livelli & needs (integrazione ControlHierarchy + Needs Driver)

### 6.1 Level (ControlHierarchy)

`level ∈ {1..5}` — invariato rispetto a M3L.2:

| Level | Nome | Neuroni tipici | Può override? |
|---|---|---|---|
| 1 | Controllo | prefrontal, safety | Safety sì |
| 2 | Cognizione | temporal, world_model, dmn | No |
| 3 | Memoria | hippocampus | No |
| 4 | Azione | parietal, cerebellum, organismic | No |
| 5 | Evoluzione | curiosity, mesh-plasticity (M5) | No |

Regola di scheduling: a parità di priorità, neuroni con `level` più basso (più vicino al controllo) precedono neuroni `level` più alto.

### 6.2 Needs catalog (chiusura enumerativa — decisione 11.3 "harmony-first")

`NEEDS_CATALOG = ["survival", "expansion", "self_improvement", "integration", "harmony"]`

Pesi default del Needs Driver (harmony-first, allineati Rigene):

| Need | Peso | Semantica |
|---|---|---|
| `harmony` | **0.35** | Equilibrio sistemico con ambiente e umani (priorità massima) |
| `survival` | 0.20 | Stabilità, resilienza, safety compliance |
| `self_improvement` | 0.15 | Fitness evoluzione, learning, mutation |
| `integration` | 0.15 | Coesione fra comparti Cortex / team / mesh |
| `expansion` | 0.15 | Crescita funzionale (nuove componenti, IoT, ecosistema) |

I pesi vivono in `epigenome.yaml → mesh.needs.weights` (EPI-004, M4.18). Un neurone che dichiara `needs_served` riceve priorità proporzionale al gap corrente (`need_target - need_current`) moltiplicato per il peso.

**Invariante 11.3:** la somma dei pesi = 1.0 (validata al boot). `harmony` è sempre `≥ max(altri)` in Fase 1 (hard gate — il needs_driver rifiuta configurazioni in cui `harmony < max(other needs)` per preservare l'allineamento Rigene).

## 7. Resource budget & execution rules (interfaccia con M4.4)

Ogni neurone dichiara:

```python
resource_budget = {
    "max_ms": int,          # wall-clock max per execute() (hard timeout)
    "max_mb": int,          # RAM max stimata (soft — monitored, warning-then-quarantine)
    "max_retries": int,     # default 0 (nessun retry); 1..3 consentito
    "priority_boost": int,  # default 0; -2..+2 (usato dal runtime per ordering)
}
```

Sono **hard** rispetto a `execution_rules.yaml` (M4.4): se un neurone dichiara `max_ms=10000` e il ceiling globale è `3000`, il validatore boot-time **riduce silenziosamente** `max_ms` a `3000` e logga warning. Non fa errore — principio di *clamp, non crash*.

## 8. Fallimenti e quarantena

### 8.1 Tassonomia errori (`ContractViolation`)

```
ContractViolation
├── REGISTRATION_*           (boot-time)
│   ├── DUPLICATE_NAME
│   ├── MISSING_METADATA
│   ├── UNKNOWN_TYPE          (input/output non in OLC)
│   └── INVALID_LEVEL
├── ACTIVATION_FAILED         (on_init o health())
├── INPUT_INVALID             (type check fallito)
├── OUTPUT_INVALID            (type check fallito)
├── UNDECLARED_SIDE_EFFECT    (sandbox detection)
├── BUDGET_EXCEEDED
│   ├── TIMEOUT
│   └── OOM
├── PRECONDITION_FAILED
└── CLEANUP_FAILED
```

### 8.2 Policy di quarantena

Contatore per neurone (`strike_count`) incrementato ad ogni violazione runtime (non boot-time). Thresholds default (in `execution_rules.yaml`):

| Strikes | Azione |
|---|---|
| 1 | Log + warning telemetry |
| 2 | Degradamento priority (−1) + alert su `mesh_state.jsonl` |
| 3+ | **Quarantena**: `status=DISABLED`, emette `PROP-NEURON-QUARANTINE-<name>` a SafeProactive (risk MEDIUM) |

Un neurone in quarantena è escluso dal runtime fino ad approvazione esplicita di riabilitazione (human-in-the-loop).

### 8.3 Fail-safe globale

Se `error_rate_global > 50%` per ≥ 2 heartbeat consecutivi → `runtime.freeze_mesh()` → flip `epigenome.mesh.enabled = false` automatico + proposta HIGH di investigazione. Evita cascate di errori.

## 9. Interoperabilità con l'architettura esistente

### 9.1 Wrapping dei 9 comparti Cortex (M4.8)

Ogni comparto esistente (`BaseCompartment`) può essere wrappato come neurone senza modifiche al codice legacy:

```python
@neuron(name="neuron.cortex.parietal", input_type=SensoryFrame,
        output_type=InterpretationFrame, level=4,
        needs_served=["integration"],
        resource_budget={"max_ms": 500, "max_mb": 64},
        side_effects=["state_bus:sensory_input"])
def neuron_parietal(inp: SensoryFrame) -> InterpretationFrame:
    compartment = ParietalLobe()
    state = state_bus.new_state("mesh-cycle", sensory_input=inp.to_dict())
    state = compartment.process(state)
    return InterpretationFrame.from_state(state)
```

Le API legacy (`NeuralFlow.run`, `SMFOI_v3.step`) rimangono attive e **indipendenti** dalla mesh — la mesh è strato aggiuntivo opt-in.

### 9.2 Compatibilità con SafeProactive

- Ogni neurone con `side_effects` contenenti `proposal:*` emette PROP tramite `SafeProactive.propose(...)` (non scrive direttamente su `PROPOSALS.md`).
- Mutazioni grafo (plasticity M5) → `PROP-MESH-MUTATE-<id>` risk MEDIUM minimo.
- Quarantena automatica → `PROP-NEURON-QUARANTINE-<name>` risk MEDIUM.

### 9.3 Compatibilità con StateBus (M3L.1)

Il `SensoryFrame` / `InterpretationFrame` / etc. sono tipi OLC **separati** dal `state` del StateBus ma si deserializzano da/a esso tramite:

```python
InterpretationFrame.from_state(state) -> InterpretationFrame
InterpretationFrame.to_state_patch(frame) -> dict  # dict da applicare al state con state_bus.log_compartment
```

Questo permette ai neuroni wrappanti dei comparti di **non conoscere** il StateBus e di restare funzioni pure tipizzate — il bridge è nell'adapter `cortex/mesh/neurons/`.

### 9.4 Compatibilità con epigenome (EPI-004 pending, M4.18)

Il blocco `mesh:` di `epigenome.yaml` fornirà:
- `mesh.enabled` (bool, default False — feature flag)
- `mesh.max_concurrent_neurons` (int, default 8)
- `mesh.harmony_threshold` (float, default 0.7)
- `mesh.heartbeat_s` (int, default 300)
- `mesh.needs.weights` (dict — §6.2)
- `mesh.quarantine_threshold` (int, default 3)
- `mesh.plasticity_enabled` (bool, default False — per M5)

Ogni neurone può leggere configurazione globale tramite `contract.config()` che fa caching con invalidation su file change.

## 10. Versionamento del contratto

### 10.1 Contract version vs neuron version

- **`CONTRACT_VERSION = "1.0"`** (questo documento) — fissato per M4, bump solo con nuovo PROP SafeProactive.
- **`Neuron.version = "x.y.z"`** — per-neurone, segue SemVer. Bump minor quando cambiano metadata compatibili, bump major quando cambia `input_type` o `output_type`.

### 10.2 Deprecazione

Un neurone con `deprecated_in = "2.0.0"` non viene rifiutato ma emette warning al boot e entra in lista "da rimuovere". Il grafo continua a funzionare; il system operator decide quando rimuovere.

### 10.3 Estensioni future (M5 e oltre — NON entrano in M4)

- `plasticity_enabled` → runtime può proporre `add/remove/rewire` edges del grafo.
- `neurons.wasm` / `neurons.rust` — neuroni non-Python in sandbox WASM.
- `requires_human_approver` fine-grained (per-campo, non solo per neurone intero).
- `A/B testing` di neuroni (canary routing).

## 11. Acceptance criteria (per M4.2)

Il validatore `cortex/mesh/contract.py` (M4.2) sarà considerato **acceptance-complete** quando:

- **AC-1** Decoratore `@neuron(...)` e classe base `Neuron` implementati.
- **AC-2** `validate_contract(neuron)` ritorna lista di `ContractViolation` (vuota = OK).
- **AC-3** Tutti i campi di §3 validati; violazioni con codice enum preciso.
- **AC-4** Registry OLC interrogabile: `contract.check_types_in_olc(neuron)`.
- **AC-5** Runtime validation hook (`wrap_execute()`) che fa type-check I/O e enforce `resource_budget.max_ms` via timeout.
- **AC-6** Lifecycle events emessi su telemetry (stub in M4.2, reale in M4.13).
- **AC-7** 100% coverage dei `ContractViolation` codes tramite unit test (≥ 10 casi sintetici).
- **AC-8** Compat test: wrappare 2 comparti Cortex esistenti (parietal + temporal) come neuroni e verificare execute end-to-end.
- **AC-9** Performance: validazione boot-time di 50 neuroni < 100ms totali.
- **AC-10** Documentazione: docstring su ogni classe pubblica, esempi runnable in `contract.__main__`.

## 12. Invariants summary (one-liners, per test M4.16)

- **I-1** `name` è globalmente univoco.
- **I-2** `level ∈ {1..5}`.
- **I-3** `input_type`, `output_type` sono registrati in OLC.
- **I-4** `needs_served ⊆ NEEDS_CATALOG` e `|needs_served| ≥ 1`.
- **I-5** `sum(epigenome.mesh.needs.weights.values()) == 1.0 ± 1e-6`.
- **I-6** `epigenome.mesh.needs.weights.harmony == max(weights.values())` in Fase 1.
- **I-7** `resource_budget.max_ms ≤ hard_ceiling`.
- **I-8** `side_effects == []` ⇒ execute() idempotente su stesso input (fuzz-tested).
- **I-9** Ogni transizione di lifecycle emette un evento telemetry.
- **I-10** Un neurone con `strike_count >= 3` è `DISABLED` (quarantena).
- **I-11** Safety-only neurons (level=1, name="neuron.cortex.safety") sono gli unici con `can_override=True`.
- **I-12** Error rate globale > 50% per ≥ 2 heartbeat ⇒ `mesh.enabled` flipped a False.

---

## Appendix A — Esempio completo (neurone "evidence-check")

```python
from dataclasses import dataclass
from cortex.mesh.contract import neuron
from cortex.mesh.olc.types import MemoryDelta, ReflectionFrame

@neuron(
    name="neuron.team.evidence-check",
    input_type=MemoryDelta,
    output_type=ReflectionFrame,
    level=2,                                  # cognizione
    needs_served=["self_improvement", "harmony"],
    resource_budget={"max_ms": 2000, "max_mb": 128, "max_retries": 1},
    side_effects=[
        "llm:openai_compat",                  # cascade cortex.llm
        "fs_read:scientific-team/outputs/*.json",
    ],
    version="1.0.0",
    description="Verifica reliability score aggregato dei brief recenti.",
    tags=["team", "evidence", "quality-gate"],
    requires=["llm:temporal"],
)
def evidence_check(inp: MemoryDelta) -> ReflectionFrame:
    from cortex.llm import LLMClient
    client = LLMClient.from_epigenome()
    # ... logica di verifica ...
    return ReflectionFrame(
        summary="reliability ok (0.62 avg)",
        confidence=0.82,
        suggestions=[],
    )
```

---

## Appendix B — Confronto con BaseCompartment (M3L.1)

| Aspetto | `BaseCompartment` (M3L) | `Neuron` (M4) |
|---|---|---|
| Input | `state: dict` non tipizzato | `Tin: OLC-type` tipizzato |
| Output | `state: dict` arricchito | `Tout: OLC-type` tipizzato |
| Discovery | Import esplicito in `neural_flow.py` | `@neuron` decorator + registry auto |
| Scheduler | NeuralFlow (ordine canonico) + ConditionalScheduler (gates) | Graph runtime asincrono con backpressure |
| Lifecycle | `process(state)` singolo | 5 fasi con invarianti |
| Side effects | Impliciti (mutazioni state) | Dichiarati in contract |
| Budget | Non imposto | `resource_budget` hard-enforced |
| Quarantena | Non prevista | Automatic dopo N strike |
| Override | Safety hard-coded in NeuralFlow | `level=1 ∧ name=safety` → can_override |

**Compatibilità:** la mesh M4 non sostituisce M3L; la mesh wrappa M3L. Entrambi vivono nel runtime SPEACE, attivabili indipendentemente (`flags.neural_flow_enabled` e `flags.mesh.enabled`).

---

*Fine SPEC — Neuron Contract v1.0. Questo documento è l'input autoritativo per M4.2 (`contract.py`).*
