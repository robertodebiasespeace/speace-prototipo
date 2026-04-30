"""
SPEACE Cortex – LLM Adapter Layer

L'LLM è "tessuto semantico", non cervello. Qui viviamo una lingua franca
(LLMRequest / LLMResponse) e tre backend concreti:

  - openai_compat : per LM Studio, Ollama OpenAI-mode, OpenRouter, vLLM...
  - ollama_native : endpoint Ollama nativo (non OpenAI-compat)
  - anthropic     : stub (richiede SDK/chiave)
  - mock          : deterministico, offline (per test/fallback)

Uso:
    from cortex.llm import LLMClient
    client = LLMClient.from_epigenome()
    resp = client.complete("Sintetizza: clima armonia pace", max_tokens=64)
    print(resp.text)
"""

from cortex.llm.types import LLMRequest, LLMResponse, LLMError
from cortex.llm.client import LLMClient

__all__ = ["LLMRequest", "LLMResponse", "LLMError", "LLMClient"]
