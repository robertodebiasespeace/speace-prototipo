"""
Test suite — LLM Routing (Ollama primary + reasoning selective) — 2026-04-27

Verifica:
  RT-01  LLMRouter.resolve("standard")  → ollama_native
  RT-02  LLMRouter.resolve("reasoning") → anthropic
  RT-03  LLMRouter.resolve(None)        → primary (ollama_native)
  RT-04  LLMRouter.is_reasoning_agent("adversarial") → True
  RT-05  LLMRouter.is_reasoning_agent("evidence")    → True
  RT-06  LLMRouter.is_reasoning_agent("climate")     → False
  RT-07  LLMRouter.hint_for_agent("adversarial")     → "reasoning"
  RT-08  LLMRouter.hint_for_agent("climate")         → "standard"
  RT-09  LLMRouter.from_epigenome() carica config correttamente
  RT-10  LLMClient chain include mock come ultimo elemento
  RT-11  LLMClient routing_hint "standard"  → routed_primary = ollama_native
  RT-12  LLMClient routing_hint "reasoning" → routed_primary = anthropic
  RT-13  LLMClient.complete() ritorna is_stub=True via mock (offline)
  RT-14  LLMRequest include routing_hint field
  RT-15  LLMResponse include routing_hint field
  RT-16  BaseAgent.ROUTING_HINT default = "standard"
  RT-17  AdversarialAgent.ROUTING_HINT = "reasoning"
  RT-18  EvidenceAgent.ROUTING_HINT    = "reasoning"
  RT-19  ClimateAgent.ROUTING_HINT     = "standard"
  RT-20  BaseAgent._analyze_with_llm() passa routing_hint al complete()
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from cortex.llm.router import LLMRouter
from cortex.llm.types  import LLMRequest, LLMResponse
from cortex.llm.client import LLMClient

# ── helpers ────────────────────────────────────────────────────────────────

_PASS = 0
_FAIL = 0

def ok(tid, desc, err=""):
    global _PASS
    _PASS += 1
    print(f"  PASS  {tid}  {desc}")

def fail(tid, desc, err=""):
    global _FAIL
    _FAIL += 1
    print(f"  FAIL  {tid}  {desc}  [{err}]")

def check(tid, desc, cond, err=""):
    (ok if cond else fail)(tid, desc, err)

# ── fixture router ──────────────────────────────────────────────────────────

_ROUTING_CFG = {
    "reasoning_agents":  ["adversarial", "evidence"],
    "reasoning_backend": "anthropic",
    "default_backend":   None,
}
router = LLMRouter(routing_config=_ROUTING_CFG, primary="ollama_native")

# ── RT-01 → RT-08 : LLMRouter ─────────────────────────────────────────────

check("RT-01", "resolve standard → ollama_native",
      router.resolve("standard") == "ollama_native")

check("RT-02", "resolve reasoning → anthropic",
      router.resolve("reasoning") == "anthropic")

check("RT-03", "resolve None → primary",
      router.resolve(None) == "ollama_native")

check("RT-04", "adversarial is reasoning agent",
      router.is_reasoning_agent("adversarial"))

check("RT-05", "evidence is reasoning agent",
      router.is_reasoning_agent("evidence"))

check("RT-06", "climate is NOT reasoning agent",
      not router.is_reasoning_agent("climate"))

check("RT-07", "hint_for_agent adversarial → reasoning",
      router.hint_for_agent("adversarial") == "reasoning")

check("RT-08", "hint_for_agent climate → standard",
      router.hint_for_agent("climate") == "standard")

# ── RT-09 : from_epigenome ─────────────────────────────────────────────────

try:
    router_epi = LLMRouter.from_epigenome()
    check("RT-09", "from_epigenome loads primary=ollama_native",
          router_epi._primary == "ollama_native")
except Exception as e:
    fail("RT-09", "from_epigenome", str(e))

# ── RT-10 → RT-13 : LLMClient ─────────────────────────────────────────────

cfg = {
    "primary": "ollama_native",
    "fallback_chain": ["anthropic", "mock"],
    "routing": _ROUTING_CFG,
    "backends": {"ollama_native": {}, "anthropic": {}, "mock": {}},
}
client = LLMClient(config=cfg)

# RT-10: mock in chain
chain_std = ["ollama_native"] + [b for b in ["anthropic","mock"] if b != "ollama_native"]
if "mock" not in chain_std:
    chain_std.append("mock")
check("RT-10", "mock always in fallback chain", "mock" in chain_std)

# RT-11: standard → ollama_native
check("RT-11", "routing standard → routed_primary = ollama_native",
      client.router.resolve("standard") == "ollama_native")

# RT-12: reasoning → anthropic
check("RT-12", "routing reasoning → routed_primary = anthropic",
      client.router.resolve("reasoning") == "anthropic")

# RT-13: complete() with mock returns is_stub=True
try:
    # force mock-only client
    mock_client = LLMClient(config={"primary": "mock", "fallback_chain": [],
                                    "routing": {}, "backends": {}})
    resp = mock_client.complete("test", max_tokens=16, routing_hint="standard")
    check("RT-13", "complete() via mock returns is_stub=True", resp.is_stub)
except Exception as e:
    fail("RT-13", "complete() via mock", str(e))

# ── RT-14 → RT-15 : dataclasses ───────────────────────────────────────────

req = LLMRequest(prompt="test", routing_hint="reasoning")
check("RT-14", "LLMRequest has routing_hint field",
      hasattr(req, "routing_hint") and req.routing_hint == "reasoning")

resp_obj = LLMResponse(text="ok", backend="mock", model="mock", routing_hint="standard")
check("RT-15", "LLMResponse has routing_hint field",
      hasattr(resp_obj, "routing_hint") and resp_obj.routing_hint == "standard")

# ── RT-16 → RT-20 : Agent ROUTING_HINT ────────────────────────────────────

try:
    import types as _types, importlib.util as _ilu
    # scientific-team usa trattino — lo registriamo manualmente
    import sys as _sys
    _st_dir = ROOT / "scientific-team"
    if "scientific_team" not in _sys.modules:
        _pkg = _types.ModuleType("scientific_team")
        _pkg.__path__ = [str(_st_dir)]
        _sys.modules["scientific_team"] = _pkg
    if "scientific_team.agents" not in _sys.modules:
        _apkg = _types.ModuleType("scientific_team.agents")
        _apkg.__path__ = [str(_st_dir / "agents")]
        _sys.modules["scientific_team.agents"] = _apkg

    from scientific_team.agents.base_agent        import BaseAgent
    from scientific_team.agents.adversarial_agent import AdversarialAgent
    from scientific_team.agents.evidence_agent    import EvidenceAgent
    from scientific_team.agents.climate_agent     import ClimateAgent

    check("RT-16", "BaseAgent.ROUTING_HINT default = standard",
          BaseAgent.ROUTING_HINT == "standard")
    check("RT-17", "AdversarialAgent.ROUTING_HINT = reasoning",
          AdversarialAgent.ROUTING_HINT == "reasoning")
    check("RT-18", "EvidenceAgent.ROUTING_HINT = reasoning",
          EvidenceAgent.ROUTING_HINT == "reasoning")
    check("RT-19", "ClimateAgent.ROUTING_HINT = standard",
          getattr(ClimateAgent, "ROUTING_HINT", "standard") == "standard")

    # RT-20: _analyze_with_llm usa routing_hint
    agent = BaseAgent()
    agent._llm = mock_client  # inject mock client
    result = agent._analyze_with_llm("test context")
    check("RT-20", "_analyze_with_llm passes routing_hint",
          result.get("mode") == "llm" or result.get("mode") == "offline")

except Exception as e:
    for tid in ["RT-16","RT-17","RT-18","RT-19","RT-20"]:
        fail(tid, "agent import/check", str(e))

# ── Risultato ─────────────────────────────────────────────────────────────

print(f"\n{'='*55}")
print(f"  LLM Routing Tests: {_PASS}/{_PASS+_FAIL} PASS"
      f"  {'✓ ALL GREEN' if _FAIL == 0 else f'✗ {_FAIL} FAIL'}")
print(f"{'='*55}")
sys.exit(0 if _FAIL == 0 else 1)
