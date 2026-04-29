"""
SPEACE SMFOI-KERNEL v0.3
Schema Minimo Fondamentale di Orientamento dell'Intelligenza

Ciclo adattivo ricorsivo a 6 step:
  1. Self-Location        → Dove si trova SPEACE nel SEA
  2. Constraint Mapping   → Vincoli attuali
  3. Push Detection       → Forze esterne
  4. Survival & Evolution Stack (Lv0–3)
  5. Output Action
  6. Outcome Evaluation & Learning  [NUOVO in v0.3]

Versione: 0.3 | 2026-04-17
"""

import os
import sys
import json
import time
import yaml
import datetime
import traceback
from pathlib import Path
from typing import Optional, Dict, Any, List

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Importa il modulo Consciousness (ACF Integration)
try:
    from cortex.consciousness import ConsciousnessIndex
    _CONSCIOUSNESS_AVAILABLE = True
except ImportError:
    _CONSCIOUSNESS_AVAILABLE = False

# Importa DriveExecutive (M7.0 — ponte causale Drive→Comportamento)
try:
    from cortex.cognitive_autonomy.executive import DriveExecutive, DriveSnapshot
    from cortex.cognitive_autonomy.homeostasis.controller import HomeostaticController
    _DRIVE_EXECUTIVE_AVAILABLE = True
except ImportError:
    _DRIVE_EXECUTIVE_AVAILABLE = False
STATE_FILE = ROOT_DIR / "state.json"
EPIGENOME_PATH = ROOT_DIR / "digitaldna" / "epigenome.yaml"
GENOME_PATH = ROOT_DIR / "digitaldna" / "genome.yaml"
LOGS_DIR = ROOT_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
KERNEL_LOG = LOGS_DIR / "smfoi_kernel.log"

sys.path.insert(0, str(ROOT_DIR))


class SMFOIKernel:
    """
    Kernel di orientamento ricorsivo di SPEACE.
    Ogni ciclo esegue i 6 step e produce un Output Action.
    """

    VERSION = "0.3"

    def __init__(self, agent_name: str = "SPEACE-CORE", recursion_level: int = 1):
        self.agent_name = agent_name
        self.recursion_level = recursion_level  # 1=normale, 2=meta, 3=kernel-modifica
        self.cycle_count = 0
        self.genome = self._load_yaml(GENOME_PATH)
        self.epigenome = self._load_yaml(EPIGENOME_PATH)
        self.state = self._load_state()

        # ACF Integration: Consciousness Index
        if _CONSCIOUSNESS_AVAILABLE:
            self.consciousness = ConsciousnessIndex(
                phi_mode="fast",
                workspace_capacity=4,
                log_dir=LOGS_DIR
            )
            self._log("ACF Consciousness Index attivato ✓")
        else:
            self.consciousness = None
            self._log("ACF Consciousness Index non disponibile (import fallito)")

        # M7.0: DriveExecutive (ponte causale Drive→BehavioralState)
        if _DRIVE_EXECUTIVE_AVAILABLE:
            self._drive_executive = DriveExecutive()
            self._homeostatic_ctrl = HomeostaticController()
            self._log("DriveExecutive M7.0 attivato ✓")
        else:
            self._drive_executive = None
            self._homeostatic_ctrl = None

        self._log(f"SMFOI-KERNEL v{self.VERSION} inizializzato | Agent: {agent_name} | Level: {recursion_level}")

    # =========================================================
    # CICLO PRINCIPALE
    # =========================================================

    def run_cycle(self, external_push: Optional[Dict] = None) -> Dict:
        """
        Esegue un ciclo completo SMFOI a 6 step.
        Restituisce il risultato dell'azione e le metriche di outcome.
        """
        self.cycle_count += 1
        cycle_id = f"CYCLE-{self.agent_name}-{self.cycle_count:04d}"
        start_time = time.time()

        self._log(f"\n{'='*60}")
        self._log(f"CICLO {cycle_id} | {datetime.datetime.now().isoformat()}")
        self._log(f"{'='*60}")

        context = {"cycle_id": cycle_id, "timestamp": datetime.datetime.now().isoformat()}

        try:
            # STEP 1: Self-Location
            sea_state = self._step1_self_location()
            context["sea_state"] = sea_state

            # STEP 2: Constraint Mapping
            constraints = self._step2_constraint_mapping(sea_state)
            context["constraints"] = constraints

            # STEP 3: Push Detection
            push = self._step3_push_detection(external_push)
            context["push"] = push

            # STEP 3.bis (M4.15, OPT-IN): Needs Check via Continuous Neural Mesh.
            # Attivo solo se `epigenome.mesh.enabled` (default OFF, abilitato in EPI-004).
            # Fail-soft: qualunque errore non interrompe il ciclo SMFOI.
            try:
                from cortex.mesh.smfoi_bridge import is_enabled as _mesh_enabled
                from cortex.mesh.smfoi_bridge import step3bis_needs_check as _mesh_needs_check
                if _mesh_enabled(self.epigenome):
                    runtime_snap = {
                        "cycles": self.cycle_count,
                        "agent": self.agent_name,
                        "recursion_level": self.recursion_level,
                    }
                    needs_res = _mesh_needs_check(
                        push=push,
                        epigenome=self.epigenome,
                        runtime_snapshot=runtime_snap,
                    )
                    context["mesh_step3bis"] = needs_res.to_dict()
                    if needs_res.promoted:
                        push = needs_res.push
                        context["push"] = push
                        self._log(
                            f"[STEP 3.bis] Mesh needs check → promoted "
                            f"(verdict={needs_res.verdict}, drv={needs_res.driving_need}, "
                            f"props={needs_res.proposals_count})"
                        )
                    else:
                        self._log(
                            f"[STEP 3.bis] Mesh needs check → no-op "
                            f"(verdict={needs_res.verdict or '—'})"
                        )
            except Exception as _mesh_err:
                # Difensivo extra: il bridge è già fail-soft, ma blindiamo il kernel
                context["mesh_step3bis_error"] = str(_mesh_err)

            # STEP 4: Survival & Evolution Stack
            response_level, action_plan = self._step4_survival_evolution(sea_state, constraints, push)
            context["response_level"] = response_level
            context["action_plan"] = action_plan

            # STEP 5: Output Action
            action_result = self._step5_output_action(action_plan, context)
            context["action_result"] = action_result

            # STEP 5.bis (OPT-IN, M3L.2): Neural Flow tra i comparti
            # Attivo solo se flags.neural_flow_enabled=True in epigenome.
            # Non altera action_result (già consolidato) ma arricchisce
            # il context con lo state del flusso neurale per diagnostica e
            # fitness downstream. Behavioural safety: se Safety blocca il
            # neural state, il blocco viene loggato ma NON modifica le
            # decisioni già prese nello step 5 (retrocompatibile).
            try:
                from cortex import neural_flow as _nf, state_bus as _sb
                if _nf.is_enabled(self.epigenome):
                    sensory_hint = {}
                    if isinstance(external_push, dict):
                        sensory_hint["text"] = str(
                            external_push.get("text")
                            or external_push.get("message")
                            or ""
                        )
                    neural_state = _sb.new_state(cycle_id, sensory_input=sensory_hint)
                    neural_state = _nf.NeuralFlow().run(neural_state)
                    context["neural_state"] = neural_state
                    context["neural_flow_blocked"] = _sb.is_blocked(neural_state)
            except Exception as _nf_err:
                context["neural_flow_error"] = str(_nf_err)

            # STEP 6: Outcome Evaluation & Learning
            outcome = self._step6_outcome_evaluation(action_result, context)
            context["outcome"] = outcome

            # Aggiorna stato
            elapsed = time.time() - start_time
            context["elapsed_seconds"] = round(elapsed, 3)
            self._update_state(cycle_id, context)

            self._log(f"CICLO {cycle_id} COMPLETATO in {elapsed:.2f}s | Fitness: {outcome.get('fitness_delta', 0):+.3f}")
            return context

        except Exception as e:
            self._log(f"ERRORE nel ciclo {cycle_id}: {e}\n{traceback.format_exc()}")
            context["error"] = str(e)
            context["success"] = False
            return context

    # =========================================================
    # COMPARTMENT DISPATCH (M1 – PROP-CORTEX-COMPLETE-M1)
    # =========================================================

    # Mappa comparto → (modulo, classe, metodo di default)
    _COMPARTMENT_MAP = {
        "prefrontal_cortex":      ("cortex.comparti.prefrontal",            "PrefrontalCortex",    "plan"),
        "hippocampus":            ("cortex.comparti.hippocampus",           "Hippocampus",         "get_recent_fitness_trend"),
        "safety_module":          ("cortex.comparti.safety_module",         "SafetyModule",        "self_report"),
        "temporal_lobe":          ("cortex.comparti.temporal_lobe",         "TemporalLobe",        "self_report"),
        "parietal_lobe":          ("cortex.comparti.parietal_lobe",         "ParietalLobe",        "self_report"),
        "cerebellum":             ("cortex.comparti.cerebellum",            "Cerebellum",          "self_report"),
        "default_mode_network":   ("cortex.comparti.default_mode_network",  "DefaultModeNetwork",  "reflect"),
        "curiosity_module":       ("cortex.comparti.curiosity_module",      "CuriosityModule",     "self_report"),
        "world_model":            ("cortex.world_model",                    "WorldModel",          "get_summary"),
    }

    def call_compartment(self, name: str, payload: Optional[Dict] = None,
                         method: Optional[str] = None) -> Dict:
        """
        Dispatch verso uno dei 9 comparti del Cortex.
        Import lazy per tolleranza: se un modulo manca, non rompe il kernel.

        Args:
            name:    chiave del comparto (vedi _COMPARTMENT_MAP)
            payload: dict passato al metodo chiamato (best-effort, opzionale)
            method:  override del metodo da invocare; se None usa quello di default

        Returns:
            {"compartment": ..., "method": ..., "status": "ok"|"error"|"unknown",
             "result": ...}
        """
        payload = payload or {}
        if name not in self._COMPARTMENT_MAP:
            return {"compartment": name, "status": "unknown",
                    "reason": "not_in_compartment_map"}

        module_path, class_name, default_method = self._COMPARTMENT_MAP[name]
        target_method = method or default_method

        try:
            import importlib
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            instance = cls()
            fn = getattr(instance, target_method, None)
            if fn is None:
                return {"compartment": name, "method": target_method,
                        "status": "error", "reason": "method_not_found"}

            # Best-effort argument passing
            try:
                if payload:
                    result = fn(**payload) if isinstance(payload, dict) else fn(payload)
                else:
                    result = fn()
            except TypeError:
                # Fallback: chiamata senza argomenti
                result = fn()

            return {"compartment": name, "method": target_method,
                    "status": "ok", "result": result}

        except Exception as e:
            return {"compartment": name, "method": target_method,
                    "status": "error", "reason": str(e)}

    def list_compartments(self) -> List[str]:
        """Ritorna la lista delle chiavi comparto registrate."""
        return list(self._COMPARTMENT_MAP.keys())

    # =========================================================
    # STEP 1 – SELF-LOCATION
    # =========================================================

    def _step1_self_location(self) -> Dict:
        """
        Dove si trova SPEACE nel suo spazio evolutivo (SEA)?
        Analizza fase, obiettivi attivi, stato corrente.
        """
        self._log("\n[STEP 1] Self-Location")

        sea_state = {
            "phase": self.genome.get("identity", {}).get("phase", 1),
            "phase_name": self.genome.get("identity", {}).get("phase_name", "Embrionale"),
            "agent": self.agent_name,
            "cycle": self.cycle_count,
            "recursion_level": self.recursion_level,
            "active_objectives": [
                obj["id"] for obj in self.genome.get("core_objectives", [])
                if not obj.get("immutable", False) or True
            ],
            "fitness_current": self.epigenome.get("fitness_metrics", {}).get("current_fitness", 0.0),
            "flags": self.epigenome.get("flags", {}),
            "last_mutation": self.epigenome.get("meta", {}).get("last_mutation_id", "none"),
        }

        self._log(f"  Fase: {sea_state['phase']} – {sea_state['phase_name']}")
        self._log(f"  Fitness corrente: {sea_state['fitness_current']:.3f}")
        self._log(f"  Obiettivi attivi: {len(sea_state['active_objectives'])}")
        return sea_state

    # =========================================================
    # STEP 2 – CONSTRAINT MAPPING
    # =========================================================

    def _step2_constraint_mapping(self, sea_state: Dict) -> Dict:
        """
        Mappa i vincoli attuali: risorse, policy, flag di sicurezza.
        """
        self._log("\n[STEP 2] Constraint Mapping")

        import psutil
        ram = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)
        disk = psutil.disk_usage(str(ROOT_DIR))

        constraints = {
            "hardware": {
                "ram_total_gb": round(ram.total / 1e9, 1),
                "ram_available_gb": round(ram.available / 1e9, 1),
                "ram_used_pct": ram.percent,
                "cpu_pct": cpu,
                "disk_free_gb": round(disk.free / 1e9, 1),
            },
            "policy": {
                "safe_mode": sea_state["flags"].get("safe_mode", True),
                "auto_replication_locked": self.genome.get("safety_rules", {}).get("auto_replication_locked", True),
                "max_risk_auto": self.genome.get("safety_rules", {}).get("max_risk_without_approval", "low"),
                "rollback_active": sea_state["flags"].get("rollback_system_active", True),
            },
            "resource_budget": {
                "ram_budget_pct": 80,   # max 80% RAM
                "ram_ok": ram.percent < 80,
                "cpu_ok": cpu < 85,
            }
        }

        self._log(f"  RAM: {ram.percent:.0f}% usata | CPU: {cpu:.0f}%")
        self._log(f"  Safe mode: {constraints['policy']['safe_mode']}")
        self._log(f"  RAM budget OK: {constraints['resource_budget']['ram_ok']}")
        return constraints

    # =========================================================
    # STEP 3 – PUSH DETECTION
    # =========================================================

    def _step3_push_detection(self, external_push: Optional[Dict]) -> Dict:
        """
        Rileva forze esterne: richieste utente, eventi, dati ambientali.
        """
        self._log("\n[STEP 3] Push Detection")

        push = {
            "type": "none",
            "priority": 0,
            "content": None,
            "source": "internal",
        }

        if external_push:
            push.update(external_push)
            self._log(f"  Push esterno rilevato: type={push.get('type')} | priority={push.get('priority')}")
        else:
            # Controlla trigger interni
            pending_proposals = (ROOT_DIR / "safeproactive" / "PROPOSALS.md").read_text()
            pending_count = pending_proposals.count("**Status:** pending")
            if pending_count > 0:
                push = {"type": "pending_proposals", "priority": 2, "content": {"count": pending_count}, "source": "safeproactive"}
                self._log(f"  Proposte pending rilevate: {pending_count}")
            else:
                self._log("  Nessun push esterno. Sistema in modalità heartbeat.")

        return push

    # =========================================================
    # STEP 4 – SURVIVAL & EVOLUTION STACK
    # =========================================================

    def _step4_survival_evolution(self, sea_state: Dict, constraints: Dict, push: Dict):
        """
        Determina il livello di risposta e pianifica l'azione.

        Lv0: Survival (sistema in pericolo → stabilizzare)
        Lv1: Maintenance (operazioni ordinarie)
        Lv2: Optimization (miglioramento parametri)
        Lv3: Evolution (modifica strutturale, solo con approvazione)
        """
        self._log("\n[STEP 4] Survival & Evolution Stack")

        # M7.0: Calcola BehavioralState da DriveExecutive
        behavioral_state = None
        if self._drive_executive is not None and self._homeostatic_ctrl is not None:
            try:
                # Leggi receptor readings dal sea_state / constraints
                receptor_readings = {
                    "energy":    constraints.get("resource_budget", {}).get("ram_pct", 0.8),
                    "safety":    1.0 if constraints.get("resource_budget", {}).get("ram_ok", True) else 0.2,
                    "coherence": sea_state.get("fitness_current", 0.7),
                }
                hc_result = self._homeostatic_ctrl.update(receptor_readings)
                # Phi da ConsciousnessIndex se disponibile (altrimenti 0.5)
                phi_val = 0.5
                behavioral_state = self._drive_executive.compute_from_homeostasis(
                    hc_result, phi=phi_val
                )
                self._log(
                    f"  [DriveExec] repair={behavioral_state.self_repair_mode} "
                    f"parallel={behavioral_state.max_parallel_tasks} "
                    f"explore_bonus={behavioral_state.exploration_bonus:.2f} "
                    f"rules={behavioral_state.triggered_rules}"
                )
                # Propaga in context per step 5 e outcome evaluation
                sea_state["behavioral_state"] = behavioral_state.to_dict()
            except Exception as _de_err:
                self._log(f"  [DriveExec] WARNING: {_de_err}")

        # Usa BehavioralState per modulare il livello di risposta
        _repair_override = behavioral_state is not None and behavioral_state.self_repair_mode

        # Determina livello
        if _repair_override or not constraints["resource_budget"]["ram_ok"]:
            level = 0
            action_plan = {"action": "stabilize", "target": "ram", "reason": "RAM critica"}
        elif push["type"] == "pending_proposals":
            level = 1
            action_plan = {"action": "review_proposals", "count": push["content"]["count"]}
        elif sea_state["fitness_current"] < 0.5 and self.cycle_count > 5:
            level = 2
            action_plan = {"action": "optimize_epigenome", "target": "learning_rate"}
        elif self.recursion_level >= 3 and sea_state["fitness_current"] > 0.8:
            level = 3
            action_plan = {"action": "propose_evolution", "type": "structural"}
        else:
            level = 1
            action_plan = {"action": "heartbeat", "status": "nominal"}

        self._log(f"  Livello risposta: {level} | Azione: {action_plan['action']}")
        return level, action_plan

    # =========================================================
    # STEP 5 – OUTPUT ACTION
    # =========================================================

    def _step5_output_action(self, action_plan: Dict, context: Dict) -> Dict:
        """
        Esegue l'azione pianificata (con SafeProactive se necessario).
        """
        self._log("\n[STEP 5] Output Action")

        action = action_plan.get("action", "heartbeat")
        result = {"action": action, "success": True, "output": None}

        if action == "heartbeat":
            result["output"] = f"Heartbeat OK | Ciclo {self.cycle_count}"
            self._log(f"  ✓ {result['output']}")

        elif action == "stabilize":
            result["output"] = "Stabilizzazione: riduco attività background"
            self._log(f"  ⚠️ {result['output']}")

        elif action == "review_proposals":
            count = action_plan.get("count", 0)
            result["output"] = f"{count} proposte in attesa di revisione → vedi safeproactive/PROPOSALS.md"
            self._log(f"  📋 {result['output']}")

        elif action == "optimize_epigenome":
            result["output"] = "Proposta mutazione epigenome generata → SafeProactive"
            self._log(f"  🧬 {result['output']}")

        elif action == "propose_evolution":
            result["output"] = "Proposta evoluzione strutturale → SafeProactive HIGH"
            self._log(f"  🚀 {result['output']}")

        else:
            result["output"] = f"Azione '{action}' eseguita"

        return result

    # =========================================================
    # STEP 6 – OUTCOME EVALUATION & LEARNING
    # =========================================================

    def _step6_outcome_evaluation(self, action_result: Dict, context: Dict) -> Dict:
        """
        Misura l'esito dell'azione, calcola fitness delta con C-index integrato,
        aggiorna epigenome e World Model.

        FITNESS v2 (ACF Integration):
          fitness = (alignment*0.25) + (task_success*0.20) + (stability*0.15) +
                    (efficiency*0.10) + (ethics*0.05) + (c_index*0.25)
        """
        self._log("\n[STEP 6] Outcome Evaluation & Learning [ACF v2]")

        success = action_result.get("success", False)
        metrics = self.epigenome.get("fitness_metrics", {})

        # ── Aggiorna task_success_rate ───────────────────────────────────────
        prev_success_rate = metrics.get("task_success_rate", 0.0)
        new_success_rate = (
            prev_success_rate * (self.cycle_count - 1) +
            (1.0 if success else 0.0)
        ) / self.cycle_count

        # ── Calcola C-index (ACF Integration) ───────────────────────────────
        c_index_result = None
        c_index_value = 0.0
        evolution_suggestion = None

        if self.consciousness is not None:
            # Arricchisce il contesto con snapshot epigenome per phi_calculator
            context["epigenome_snapshot"] = {
                "exploration_rate": self.epigenome.get("learning", {}).get("exploration_rate", 0.15),
                "reflection_depth": self.epigenome.get("learning", {}).get("reflection_depth", 2),
            }
            c_index_result = self.consciousness.compute(context)
            c_index_value = c_index_result["c_index"]
            evolution_suggestion = self.consciousness.suggest_evolution()

            self._log(f"  C-index: {c_index_value:.4f} | "
                      f"Φ={c_index_result['components']['phi']:.3f} | "
                      f"W={c_index_result['components']['w_activation']:.3f} | "
                      f"A={c_index_result['components']['a_complexity']:.3f}")
            self._log(f"  Livello coscienza: {c_index_result['level_icon']} {c_index_result['level']}")

        # ── FITNESS v2: 6 componenti con C-index ────────────────────────────
        weights_v2 = {
            "speace_alignment_score": 0.25,
            "task_success_rate":      0.20,
            "system_stability":       0.15,
            "resource_efficiency":    0.10,
            "ethical_compliance":     0.05,
            "c_index":                0.25,   # ← nuovo componente ACF
        }

        fitness = (
            metrics.get("speace_alignment_score", 0.5) * weights_v2["speace_alignment_score"] +
            new_success_rate                            * weights_v2["task_success_rate"] +
            metrics.get("system_stability", 1.0)       * weights_v2["system_stability"] +
            metrics.get("resource_efficiency", 0.8)    * weights_v2["resource_efficiency"] +
            metrics.get("ethical_compliance", 1.0)     * weights_v2["ethical_compliance"] +
            c_index_value                               * weights_v2["c_index"]
        )

        prev_fitness = metrics.get("current_fitness", 0.0)
        fitness_delta = fitness - prev_fitness

        # ── Aggiorna metriche in memoria ─────────────────────────────────────
        metrics["task_success_rate"] = round(new_success_rate, 4)
        metrics["current_fitness"]   = round(fitness, 4)
        if c_index_result:
            metrics["c_index"]           = round(c_index_value, 4)
            metrics["phi"]               = round(c_index_result["components"]["phi"], 4)
            metrics["w_activation"]      = round(c_index_result["components"]["w_activation"], 4)
            metrics["a_complexity"]      = round(c_index_result["components"]["a_complexity"], 4)
            metrics["consciousness_level"] = c_index_result["level"]

        outcome = {
            "success": success,
            "fitness_before": round(prev_fitness, 4),
            "fitness_after":  round(fitness, 4),
            "fitness_delta":  round(fitness_delta, 4),
            "task_success_rate": round(new_success_rate, 4),
            "learning_applied": True,
            "mutation_suggested": fitness_delta < -0.05,
            "c_index": c_index_result,
            "evolution_suggestion": evolution_suggestion,
        }

        self._log(f"  Successo: {success}")
        self._log(f"  Fitness v2: {prev_fitness:.4f} → {fitness:.4f} ({fitness_delta:+.4f})")
        if outcome["mutation_suggested"]:
            self._log("  ⚠️ Fitness in calo: mutazione epigenetica suggerita")
        if evolution_suggestion:
            self._log(f"  💡 Suggerimento evolutivo: {evolution_suggestion}")

        return outcome

    # =========================================================
    # UTILITÀ
    # =========================================================

    def _load_yaml(self, path: Path) -> Dict:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _load_state(self) -> Dict:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
        return {"cycles": [], "last_fitness": 0.0}

    def _update_state(self, cycle_id: str, context: Dict):
        self.state["last_cycle"] = cycle_id
        self.state["last_run"] = context.get("timestamp")
        self.state["last_fitness"] = context.get("outcome", {}).get("fitness_after", 0.0)
        # Mantieni solo ultimi 100 cicli
        cycles = self.state.get("cycles", [])
        cycles.append({"id": cycle_id, "ts": context.get("timestamp"), "fitness": self.state["last_fitness"]})
        self.state["cycles"] = cycles[-100:]
        STATE_FILE.write_text(json.dumps(self.state, indent=2))

    def _log(self, msg: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = f"[{ts}] {msg}"
        print(line)
        with open(KERNEL_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def get_status(self) -> Dict:
        return {
            "version": self.VERSION,
            "agent": self.agent_name,
            "cycles_run": self.cycle_count,
            "last_fitness": self.state.get("last_fitness", 0.0),
            "recursion_level": self.recursion_level,
        }


# -------------------------------------------------------
# ESECUZIONE DIRETTA (test)
# -------------------------------------------------------
if __name__ == "__main__":
    print("\n=== TEST SMFOI-KERNEL v0.3 ===\n")
    kernel = SMFOIKernel(agent_name="SPEACE-TEST")

    # Ciclo 1: heartbeat normale
    result1 = kernel.run_cycle()

    # Ciclo 2: push esterno simulato
    result2 = kernel.run_cycle(external_push={
        "type": "user_request",
        "priority": 3,
        "content": {"request": "Genera Daily Brief"},
        "source": "roberto"
    })

    print(f"\n=== STATO FINALE ===")
    print(json.dumps(kernel.get_status(), indent=2))
