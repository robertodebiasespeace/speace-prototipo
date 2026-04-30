"""
L6 → L2 Epigenetic Modulator.
DigitalDNA modifica automaticamente i prompt/parametri LLM
in base al trend Φ. Mutazioni benefiche vengono consolidate.
Version: 1.0
Data: 24 Aprile 2026
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger("EpigeneticModulator")

ROOT_DIR = Path(__file__).parent.parent


class EpigeneticModulator:
    """
    Traduce i trend Φ in modifiche concrete ai moduli L2 (LLM).

    - Φ crescente (>0.05 trend): rafforza prompt pattern, riduci temperature
    - Φ decrescente (<-0.05 trend): attiva mutazione prompt, alza exploration
    - Φ stabile: mantieni, logga per apprendimento futuro
    """

    def __init__(self, dna_log_path: Optional[Path] = None):
        self.dna_log = dna_log_path or ROOT_DIR / "evolution" / "dna_log.json"
        self.mutation_log = ROOT_DIR / "evolution" / "prompt_mutations.jsonl"
        self.dna_log.parent.mkdir(parents=True, exist_ok=True)

        self.prompt_templates = self._load_prompt_templates()
        self.mutation_history: List[Dict] = self._load_mutation_history()

        self.llm_params = {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_ctx": 8192,
            "system_prompt_suffix": ""
        }

        logger.info("EpigeneticModulator inizializzato")

    def _load_prompt_templates(self) -> Dict[str, str]:
        """Carica o crea template prompt di base"""
        templates_path = ROOT_DIR / "DigitalDNA" / "prompt_templates.json"

        defaults = {
            "self_dialogue": (
                "Sei il Meta-Neurone Dialogico di SPEACE, parte del Rigene Project.\n"
                "Stato attuale: C-index {c_index:.3f}, {compartments} comparti, {cycles} cicli.\n"
                "Ragiona in modo profondo, autocritico, propositivo e allineato "
                "con armonia, rigenerazione ed evoluzione."
            ),
            "scientific_agent": (
                "Sei un agente scientifico di SPEACE. Analizza dati con rigore metodologico.\n"
                "Esplorazione rate: {exploration_rate:.2f}.\n"
                "Proponi ipotesi verificabili e identifica limiti."
            ),
            "coherence_analyst": (
                "Analizza la coerenza interna tra i seguenti output di moduli SPEACE.\n"
                "Φ attuale: {phi:.3f}. Identifica contraddizioni e sinergie."
            )
        }

        if templates_path.exists():
            try:
                with open(templates_path, encoding='utf-8') as f:
                    loaded = json.load(f)
                    defaults.update(loaded)
            except:
                pass
        else:
            with open(templates_path, 'w', encoding='utf-8') as f:
                json.dump(defaults, f, indent=2)

        return defaults

    def _load_mutation_history(self) -> List[Dict]:
        if self.mutation_log.exists():
            with open(self.mutation_log, encoding='utf-8') as f:
                return [json.loads(l) for l in f if l.strip()]
        return []

    def evaluate_and_mutate(
        self,
        phi_history: List[Dict],
        current_prompt: str,
        prompt_type: str = "self_dialogue"
    ) -> Dict[str, Any]:
        """Analizza trend Φ e decide se mutare i prompt L2."""
        if len(phi_history) < 5:
            return {
                "action": "insufficient_data",
                "prompt": current_prompt,
                "params": self.llm_params,
                "message": "Need 5+ Phi readings for epigenetic modulation"
            }

        trend = self._calc_phi_trend(phi_history)
        last_phi = phi_history[-1]["phi"]

        result = {
            "action": "maintain",
            "prompt": current_prompt,
            "params": self.llm_params.copy(),
            "trend": trend,
            "phi": last_phi
        }

        if trend > 0.05 and last_phi > 0.75:
            result = self._reinforce_pattern(current_prompt, prompt_type, result)
        elif trend < -0.03 and last_phi < 0.65:
            result = self._mutate_prompt(current_prompt, prompt_type, phi_history, result)
        elif abs(trend) < 0.02 and last_phi > 0.8:
            result = self._consolidate_pattern(current_prompt, prompt_type, result)

        result["params"] = self._update_llm_params(trend, last_phi)

        return result

    def _calc_phi_trend(self, phi_history: List[Dict]) -> float:
        """Calcola pendenza lineare degli ultimi N valori Φ"""
        recent = [h["phi"] for h in phi_history[-10:]]
        n = len(recent)
        if n < 2:
            return 0.0
        x_mean = (n - 1) / 2
        y_mean = sum(recent) / n
        num = sum((i - x_mean) * (recent[i] - y_mean) for i in range(n))
        den = sum((i - x_mean) ** 2 for i in range(n))
        return num / den if den != 0 else 0.0

    def _reinforce_pattern(self, prompt: str, prompt_type: str, result: Dict) -> Dict:
        """Rafforza il pattern corrente: riduci temperature, aggiungi confidence"""
        result["action"] = "reinforce"
        result["message"] = "Phi crescente: rafforzo pattern corrente"

        self.llm_params["temperature"] = max(0.3, self.llm_params["temperature"] - 0.05)
        self.llm_params["top_p"] = min(0.95, self.llm_params["top_p"] + 0.02)

        if "confidence_suffix" not in prompt:
            result["prompt"] = prompt + "\n\n[Nota: Phi in crescita. Mantieni questo pattern.]"

        return result

    def _mutate_prompt(self, prompt: str, prompt_type: str, phi_history: List[Dict], result: Dict) -> Dict:
        """Genera una mutazione del prompt per contrastare il degrado"""
        result["action"] = "mutate"
        result["message"] = "Phi in calo: attivo mutazione compensativa"

        self.llm_params["temperature"] = min(1.2, self.llm_params["temperature"] + 0.1)

        mutations = [
            lambda p: p + "\n\n[CRITICAL: Verifica la coerenza con gli output precedenti prima di rispondere.]",
            lambda p: p.replace("Ragiona in modo profondo", "Ragiona in modo strutturato, step-by-step"),
            lambda p: p + "\n\n[Vincolo: Ogni risposta deve citare almeno un principio del Rigene Project.]",
            lambda p: p[:len(p)//2] + "\n[Modalita essenziale attivata per recupero coerenza.]",
        ]

        prompt_hash = int(hashlib.md5(prompt.encode()).hexdigest(), 16)
        mutation_idx = prompt_hash % len(mutations)

        new_prompt = mutations[mutation_idx](prompt)

        mutation_entry = {
            "timestamp": datetime.now().isoformat(),
            "prompt_type": prompt_type,
            "phi_before": phi_history[-1]["phi"],
            "phi_trend": self._calc_phi_trend(phi_history),
            "mutation_idx": mutation_idx,
            "prompt_hash": hashlib.md5(prompt.encode()).hexdigest()[:8]
        }
        self.mutation_history.append(mutation_entry)

        with open(self.mutation_log, 'a', encoding='utf-8') as f:
            f.write(json.dumps(mutation_entry) + "\n")

        result["prompt"] = new_prompt
        result["mutation"] = mutation_entry

        logger.info(f"Mutazione prompt applicata: tipo {mutation_idx}")
        return result

    def _consolidate_pattern(self, prompt: str, prompt_type: str, result: Dict) -> Dict:
        """Consolida pattern stabile nel DNA digitale"""
        result["action"] = "consolidate"
        result["message"] = "Phi stabile e alto: consolidamento nel DNA"

        self.prompt_templates[f"{prompt_type}_consolidated_{datetime.now().strftime('%Y%m%d')}"] = prompt

        templates_path = ROOT_DIR / "DigitalDNA" / "prompt_templates.json"
        with open(templates_path, 'w', encoding='utf-8') as f:
            json.dump(self.prompt_templates, f, indent=2)

        dna_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "prompt_consolidation",
            "prompt_type": prompt_type,
            "phi": result["phi"]
        }

        if self.dna_log.exists():
            try:
                with open(self.dna_log, encoding='utf-8') as f:
                    dna_data = json.load(f)
            except:
                dna_data = {"mutations": [], "consolidations": []}
        else:
            dna_data = {"mutations": [], "consolidations": []}

        dna_data.setdefault("consolidations", []).append(dna_entry)

        with open(self.dna_log, 'w', encoding='utf-8') as f:
            json.dump(dna_data, f, indent=2)

        return result

    def _update_llm_params(self, trend: float, phi: float) -> Dict:
        """Aggiorna parametri LLM dinamicamente"""
        if phi > 0.85:
            self.llm_params["temperature"] = max(0.3, self.llm_params["temperature"] - 0.02)
            self.llm_params["num_ctx"] = min(16384, self.llm_params["num_ctx"] + 1024)
        elif phi < 0.5:
            self.llm_params["temperature"] = min(1.5, self.llm_params["temperature"] + 0.05)
            self.llm_params["num_ctx"] = max(4096, self.llm_params["num_ctx"] - 512)

        return self.llm_params.copy()

    def get_active_prompt(self, prompt_type: str, context: Dict) -> str:
        """Restituisce il prompt attivo con variabili sostituite"""
        template = self.prompt_templates.get(prompt_type, self.prompt_templates["self_dialogue"])
        try:
            return template.format(**context)
        except KeyError:
            return template

    def get_status(self) -> Dict:
        return {
            "llm_params": self.llm_params,
            "template_count": len(self.prompt_templates),
            "mutation_count": len(self.mutation_history),
            "last_mutation": self.mutation_history[-1] if self.mutation_history else None
        }