"""
SPEACE Neural Parliament - Batch Request Ottimizzato.
Una singola chiamata Ollama produce tutte e 5 le risposte dei neuroni.
Temperature bassa (0.4), context ridotto, parallel mode sempre.
Version: 3.1 – Fix ParliamentSession.add_response e neurons attr
"""

import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

NEURON_PROMPTS = {
    "planner": """[PLANNER] Crea un piano strategico. Alla fine scrivi esattamente:
FILE: <percorso>
MODIFICA: <descrizione>
MOTIVAZIONE: <perché>
RISCHIO: basso/medio/alto""",

    "critic": """[CRITIC] Analisi critica. Identifica rischi, bias, punti deboli. Dai un verdetto: APPROVATO/MODIFICARE/RIFIUTATO.""",

    "creative": """[CREATIVE] Proponi 2 idee innovative e originali per migliorare il sistema.""",

    "researcher": """[RESEARCHER] Analizza pattern e correlazioni nei dati. Fornisci osservazioni chiave e raccomandazioni.""",

    "executor": """[EXECUTOR] Produci codice concreto. Usa blocchi ```python o ```yaml. Indica il file destinazione.""",
}


@dataclass
class ParliamentSession:
    query: str
    responses: Dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_response(self, neuron_name: str, response: str):
        self.responses[neuron_name] = response


class NeuralParliament:
    """Coordina 5 neuroni con BATCH REQUEST."""

    def __init__(self, bridge=None):
        self.bridge = bridge
        self.model = "gemma3:4b"
        self.temperature = 0.4
        self.num_ctx = 4096
        self.session_history: List[ParliamentSession] = []
        self.ollama_available = False
        # Per compatibilità con NeuralBridge
        self.neurons = list(NEURON_PROMPTS.keys())

        try:
            import ollama
            ollama.list()
            self.ollama_available = True
            logger.info(f"Neural Parliament: batch mode con {self.model} (temp={self.temperature})")
        except Exception as e:
            logger.error(f"Ollama non disponibile: {e}")

    async def deliberate(self, query: str, mode: str = "parallel",
                         context: Optional[Dict] = None) -> ParliamentSession:
        session = ParliamentSession(query=query)

        if not self.ollama_available:
            for name in NEURON_PROMPTS:
                session.add_response(name, "[Fallback] Ollama offline")
            return session

        try:
            batch_responses = await self._batch_call(query, context)
            for name, response in batch_responses.items():
                session.add_response(name, response)
        except Exception as e:
            logger.error(f"Batch request fallita: {e}")
            for name in NEURON_PROMPTS:
                session.add_response(name, f"[Errore batch: {str(e)}]")

        self.session_history.append(session)
        return session

    async def _batch_call(self, query: str, context: Optional[Dict] = None) -> Dict[str, str]:
        import ollama

        ctx_str = ""
        if context:
            ctx_parts = []
            for k, v in context.items():
                v_str = str(v)
                if len(v_str) > 500:
                    v_str = v_str[:500] + "..."
                ctx_parts.append(f"{k}: {v_str}")
            if ctx_parts:
                ctx_str = "CONTESTO:\n" + "\n".join(ctx_parts[-8:]) + "\n\n"

        roles_section = "\n\n".join([
            f"--- {name.upper()} ---\n{NEURON_PROMPTS[name]}"
            for name in NEURON_PROMPTS
        ])

        system_prompt = """Sei il Parlamento Neurale di SPEACE. Rispondi simulando TUTTI e 5 i neuroni.
Usa ESATTAMENTE il formato:
--- PLANNER ---
[risposta]
--- CRITIC ---
[risposta]
--- CREATIVE ---
[risposta]
--- RESEARCHER ---
[risposta]
--- EXECUTOR ---
[risposta]
Ogni neurone risponde in italiano, in modo CONCISO (max 200 parole ciascuno)."""

        user_message = f"""{ctx_str}QUERY: {query}

{roles_section}

IMPORTANTE: Rispetta ESATTAMENTE il formato con le intestazioni --- NOME ---. Ogni neurone risponde in modo autonomo e conciso."""

        response = await asyncio.to_thread(
            ollama.chat,
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            options={
                "temperature": self.temperature,
                "num_ctx": self.num_ctx,
                "num_predict": 2048,
            },
        )

        full_text = response["message"]["content"].strip()
        return self._parse_batch_response(full_text)

    def _parse_batch_response(self, text: str) -> Dict[str, str]:
        responses = {}
        current_neuron = None
        current_lines = []

        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("---") and stripped.endswith("---"):
                if current_neuron and current_neuron in NEURON_PROMPTS:
                    responses[current_neuron] = "\n".join(current_lines).strip()
                name = stripped.strip("-").strip().lower()
                if name in NEURON_PROMPTS:
                    current_neuron = name
                    current_lines = []
                else:
                    for known in NEURON_PROMPTS:
                        if known in name:
                            current_neuron = known
                            current_lines = []
                            break
                    else:
                        current_neuron = None
            elif current_neuron:
                current_lines.append(line)

        if current_neuron and current_neuron in NEURON_PROMPTS:
            responses[current_neuron] = "\n".join(current_lines).strip()

        for name in NEURON_PROMPTS:
            if name not in responses:
                responses[name] = f"[{name}] Nessuna risposta estratta dal batch."
        return responses

    def evaluate_coherence(self, session: ParliamentSession) -> Dict:
        if self.bridge and hasattr(self.bridge, 'glia'):
            return self.bridge.glia.evaluate_coherence({
                "task_success_rate": self._estimate_success(session),
                "cycle_success": len(session.responses) >= 3,
                "phi": 0.7,
            })
        return {"phi": 0.7, "action": "STABLE", "components": {}}

    def _estimate_success(self, session: ParliamentSession) -> float:
        if not session.responses:
            return 0.0
        responded = len(session.responses)
        total = len(NEURON_PROMPTS)
        valid = sum(1 for r in session.responses.values()
                    if "Errore" not in r and "Nessuna risposta" not in r and len(r) > 10)
        avg_len = sum(len(r) for r in session.responses.values()) / max(1, responded)
        return (responded / total) * 0.4 + (valid / total) * 0.4 + min(1.0, avg_len / 200) * 0.2

    def register_synapses(self, session: ParliamentSession):
        if self.bridge and hasattr(self.bridge, 'myelin'):
            myelin = self.bridge.myelin
            responders = [n for n in session.responses
                         if "Errore" not in session.responses[n] and len(session.responses[n]) > 10]
            for i, s in enumerate(responders):
                for t in responders[i + 1:]:
                    myelin.register_synapse(s, t)
                    myelin.activate_path(s, t, 0.7)
            for n in responders:
                myelin.register_synapse(n, "glial_controller")
                myelin.activate_path(n, "glial_controller", 0.7)

    def get_consensus(self, session: ParliamentSession) -> str:
        if "executor" in session.responses and "Errore" not in session.responses["executor"]:
            return session.responses["executor"]
        if "planner" in session.responses and "Errore" not in session.responses["planner"]:
            return session.responses["planner"]
        valid = {k: v for k, v in session.responses.items()
                 if "Errore" not in v and "Nessuna risposta" not in v and len(v) > 10}
        return max(valid.values(), key=len) if valid else "[Fallback] Nessuna risposta."

    def get_status(self) -> Dict:
        return {
            "active_neurons": len(NEURON_PROMPTS),
            "model": self.model,
            "temperature": self.temperature,
            "mode": "batch_request",
            "ollama_available": self.ollama_available,
            "sessions_completed": len(self.session_history),
        }
