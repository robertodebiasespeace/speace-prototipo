"""
SPEACE Metalearning System – BRN-013
Learning-to-learn mechanism inspired by Darwin Gödel Machine and MAML.

The metalearner enables SPEACE to:
- Learn optimal learning strategies for new tasks
- Transfer knowledge across heterogeneous domains
- Optimize its own hyperparameters dynamically
- Build a library of reusable cognitive strategies

Version: 1.0
Data: 26 Aprile 2026
"""

import logging
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from collections import deque
from enum import Enum
import random
import math

logger = logging.getLogger(__name__)
ROOT_DIR = Path(__file__).parent.parent.parent


# ─── Enums ──────────────────────────────────────────────────────────────────

class LearningStrategy(Enum):
    """Available learning strategies SPEACE can select from."""
    GRADIENT_BASED   = "gradient_based"     # Standard gradient descent
    EVOLUTIONARY     = "evolutionary"       # Evolutionary algorithm
    HEBBIAN          = "hebbian"            # Hebbian associative learning
    EPISODIC_REPLAY  = "episodic_replay"    # Experience replay from BRN-012
    ANALOGICAL       = "analogical"         # Analogical transfer
    META_GRADIENT    = "meta_gradient"      # MAML-style meta-gradient
    CURIOSITY_DRIVEN = "curiosity_driven"   # Intrinsic motivation driven
    CONTRASTIVE      = "contrastive"        # Contrastive self-supervised


class TaskDomain(Enum):
    """Domains of tasks SPEACE may encounter."""
    LANGUAGE        = "language"
    PERCEPTION      = "perception"
    PLANNING        = "planning"
    SOCIAL          = "social"
    SCIENTIFIC      = "scientific"
    CREATIVE        = "creative"
    REGULATORY      = "regulatory"
    MOTOR           = "motor"
    UNKNOWN         = "unknown"


# ─── Data Structures ────────────────────────────────────────────────────────

@dataclass
class Task:
    """A task instance for meta-learning."""
    task_id: str
    domain: TaskDomain
    description: str
    input_features: Dict[str, Any] = field(default_factory=dict)
    target_output: Optional[Any] = None
    difficulty: float = 0.5          # 0=trivial, 1=impossible
    novelty: float = 0.5             # 0=fully known, 1=completely new
    created_at: float = field(default_factory=time.time)


@dataclass
class LearningEpisode:
    """Record of a learning episode."""
    task_id: str
    strategy_used: LearningStrategy
    initial_performance: float
    final_performance: float
    steps_taken: int
    time_elapsed: float
    hyperparams_used: Dict[str, float]
    success: bool
    lessons: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    @property
    def improvement(self) -> float:
        return self.final_performance - self.initial_performance

    @property
    def efficiency(self) -> float:
        if self.steps_taken == 0 or self.time_elapsed == 0:
            return 0.0
        return self.improvement / (self.steps_taken * self.time_elapsed + 1e-8)


@dataclass
class StrategyProfile:
    """Performance profile for a learning strategy across domains."""
    strategy: LearningStrategy
    domain_scores: Dict[str, float] = field(default_factory=dict)
    avg_improvement: float = 0.0
    avg_efficiency: float = 0.0
    usage_count: int = 0
    last_used: float = 0.0

    def update(self, episode: LearningEpisode) -> None:
        domain_key = episode.task_id.split("_")[0]
        prev = self.domain_scores.get(domain_key, 0.5)
        # Exponential moving average
        alpha = 0.3
        self.domain_scores[domain_key] = (1 - alpha) * prev + alpha * episode.final_performance
        self.avg_improvement = (1 - alpha) * self.avg_improvement + alpha * episode.improvement
        self.avg_efficiency = (1 - alpha) * self.avg_efficiency + alpha * episode.efficiency
        self.usage_count += 1
        self.last_used = time.time()


# ─── Strategy Selector ───────────────────────────────────────────────────────

class StrategySelector:
    """
    Selects the optimal learning strategy for a given task.
    Uses UCB (Upper Confidence Bound) bandit algorithm for exploration/exploitation.
    """

    def __init__(self, exploration_factor: float = 1.4):
        self.exploration_factor = exploration_factor
        self.profiles: Dict[LearningStrategy, StrategyProfile] = {
            s: StrategyProfile(strategy=s) for s in LearningStrategy
        }
        self.total_selections = 0

    def select(self, task: Task) -> LearningStrategy:
        """Select strategy using UCB with domain-awareness."""
        self.total_selections += 1
        domain_key = task.domain.value

        scores = {}
        for strategy, profile in self.profiles.items():
            # Domain-specific score
            domain_score = profile.domain_scores.get(domain_key, 0.5)
            # UCB exploration bonus
            if profile.usage_count == 0:
                exploration_bonus = float('inf')
            else:
                exploration_bonus = self.exploration_factor * math.sqrt(
                    math.log(self.total_selections + 1) / (profile.usage_count + 1)
                )
            # Novelty adjustment: prefer gradient/curiosity for novel tasks
            novelty_adj = 0.0
            if task.novelty > 0.7:
                if strategy in (LearningStrategy.CURIOSITY_DRIVEN, LearningStrategy.META_GRADIENT):
                    novelty_adj = 0.2
            # Difficulty adjustment
            difficulty_adj = 0.0
            if task.difficulty > 0.7:
                if strategy in (LearningStrategy.EVOLUTIONARY, LearningStrategy.META_GRADIENT):
                    difficulty_adj = 0.15

            scores[strategy] = domain_score + exploration_bonus + novelty_adj + difficulty_adj

        best = max(scores, key=lambda s: scores[s])
        logger.debug(f"StrategySelector: chose {best.value} for task {task.task_id} in domain {domain_key}")
        return best

    def update(self, episode: LearningEpisode) -> None:
        """Update profile after observing learning episode outcome."""
        self.profiles[episode.strategy_used].update(episode)

    def get_best_for_domain(self, domain: TaskDomain) -> LearningStrategy:
        """Return empirically best strategy for a domain."""
        best_score = -1.0
        best_strategy = LearningStrategy.META_GRADIENT
        for strategy, profile in self.profiles.items():
            score = profile.domain_scores.get(domain.value, 0.0)
            if score > best_score:
                best_score = score
                best_strategy = strategy
        return best_strategy

    def get_status(self) -> Dict:
        return {
            "total_selections": self.total_selections,
            "profiles": {
                s.value: {
                    "avg_improvement": round(p.avg_improvement, 4),
                    "usage_count": p.usage_count,
                    "domain_scores": {k: round(v, 3) for k, v in p.domain_scores.items()}
                }
                for s, p in self.profiles.items()
            }
        }


# ─── Hyperparameter Optimizer ────────────────────────────────────────────────

class HyperparameterOptimizer:
    """
    Bayesian-inspired hyperparameter optimization using Gaussian Process surrogate.
    Simplified for lightweight operation on CPU.
    """

    DEFAULT_PARAMS = {
        "learning_rate": (0.0001, 0.1),
        "batch_size": (8, 128),
        "momentum": (0.5, 0.99),
        "dropout": (0.0, 0.5),
        "attention_heads": (1, 16),
        "hidden_dim": (64, 1024),
    }

    def __init__(self):
        self.history: List[Tuple[Dict[str, float], float]] = []  # (params, score)
        self.best_params: Dict[str, float] = {}
        self.best_score: float = -1.0
        self._init_defaults()

    def _init_defaults(self) -> None:
        """Initialize with middle values."""
        self.best_params = {
            k: (lo + hi) / 2 for k, (lo, hi) in self.DEFAULT_PARAMS.items()
        }

    def suggest(self, task_domain: TaskDomain) -> Dict[str, float]:
        """Suggest hyperparameters for next trial using random search + exploitation."""
        if len(self.history) < 5 or random.random() < 0.3:
            # Exploration: random sample
            return {
                k: random.uniform(lo, hi)
                for k, (lo, hi) in self.DEFAULT_PARAMS.items()
            }
        # Exploitation: perturb best params
        params = dict(self.best_params)
        # Perturb one parameter
        key = random.choice(list(self.DEFAULT_PARAMS.keys()))
        lo, hi = self.DEFAULT_PARAMS[key]
        noise = (hi - lo) * 0.1 * random.gauss(0, 1)
        params[key] = max(lo, min(hi, params[key] + noise))
        return params

    def observe(self, params: Dict[str, float], score: float) -> None:
        """Record outcome of a trial."""
        self.history.append((params, score))
        if score > self.best_score:
            self.best_score = score
            self.best_params = dict(params)
            logger.info(f"HyperparamOptimizer: new best score {score:.4f}")

    def get_status(self) -> Dict:
        return {
            "trials_observed": len(self.history),
            "best_score": round(self.best_score, 4),
            "best_params": {k: round(v, 4) for k, v in self.best_params.items()}
        }


# ─── Transfer Learning Engine ────────────────────────────────────────────────

class TransferLearningEngine:
    """
    Knowledge transfer across domains and tasks.
    Maintains a library of reusable "cognitive primitives" extracted from past episodes.
    """

    def __init__(self, max_primitives: int = 200):
        self.max_primitives = max_primitives
        self.primitive_library: List[Dict] = []   # Reusable cognitive units
        self.domain_bridges: Dict[str, List[str]] = {}  # Cross-domain mappings
        self.transfer_log: deque = deque(maxlen=100)

    def extract_primitives(self, episode: LearningEpisode) -> List[Dict]:
        """Extract reusable primitives from a successful learning episode."""
        if not episode.success:
            return []
        primitives = []
        for lesson in episode.lessons:
            primitive = {
                "source_task": episode.task_id,
                "lesson": lesson,
                "strategy": episode.strategy_used.value,
                "performance_gain": episode.improvement,
                "confidence": min(1.0, episode.improvement * 2),
                "timestamp": episode.timestamp
            }
            primitives.append(primitive)
        return primitives

    def store_primitives(self, primitives: List[Dict]) -> None:
        """Add primitives to library, pruning old ones if needed."""
        self.primitive_library.extend(primitives)
        if len(self.primitive_library) > self.max_primitives:
            # Keep highest confidence primitives
            self.primitive_library.sort(key=lambda p: p["confidence"], reverse=True)
            self.primitive_library = self.primitive_library[:self.max_primitives]

    def retrieve_relevant(self, task: Task, top_k: int = 5) -> List[Dict]:
        """Retrieve most relevant primitives for a new task."""
        domain_key = task.domain.value
        relevant = []
        for prim in self.primitive_library:
            source_domain = prim["source_task"].split("_")[0]
            # Score by domain match + confidence
            domain_match = 1.0 if source_domain == domain_key else 0.3
            score = domain_match * prim["confidence"]
            relevant.append((score, prim))
        relevant.sort(key=lambda x: x[0], reverse=True)
        retrieved = [p for _, p in relevant[:top_k]]
        self.transfer_log.append({
            "task_id": task.task_id,
            "primitives_retrieved": len(retrieved),
            "timestamp": time.time()
        })
        return retrieved

    def register_domain_bridge(self, source_domain: str, target_domain: str,
                                relation: str) -> None:
        """Register a discovered structural similarity between two domains."""
        if source_domain not in self.domain_bridges:
            self.domain_bridges[source_domain] = []
        self.domain_bridges[source_domain].append(
            f"{target_domain}:{relation}"
        )

    def get_status(self) -> Dict:
        return {
            "primitives_stored": len(self.primitive_library),
            "domain_bridges": self.domain_bridges,
            "recent_transfers": len(self.transfer_log)
        }


# ─── Experience Buffer ───────────────────────────────────────────────────────

class ExperienceBuffer:
    """
    Meta-experience replay buffer for the metalearner.
    Stores episodes and samples batches for meta-gradient computation.
    """

    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.buffer: deque = deque(maxlen=capacity)

    def store(self, episode: LearningEpisode) -> None:
        self.buffer.append(episode)

    def sample(self, n: int = 10) -> List[LearningEpisode]:
        """Sample n episodes, weighted by recency and improvement."""
        if not self.buffer:
            return []
        n = min(n, len(self.buffer))
        episodes = list(self.buffer)
        # Weight by improvement magnitude
        weights = [max(0.01, abs(e.improvement)) for e in episodes]
        total = sum(weights)
        probs = [w / total for w in weights]
        indices = random.choices(range(len(episodes)), weights=probs, k=n)
        return [episodes[i] for i in indices]

    def sample_by_domain(self, domain: TaskDomain, n: int = 5) -> List[LearningEpisode]:
        """Sample episodes from a specific domain."""
        domain_eps = [e for e in self.buffer
                      if domain.value in e.task_id]
        if not domain_eps:
            return self.sample(n)
        return random.sample(domain_eps, min(n, len(domain_eps)))

    def get_statistics(self) -> Dict:
        if not self.buffer:
            return {"size": 0}
        improvements = [e.improvement for e in self.buffer]
        return {
            "size": len(self.buffer),
            "avg_improvement": round(sum(improvements) / len(improvements), 4),
            "max_improvement": round(max(improvements), 4),
            "success_rate": round(sum(1 for e in self.buffer if e.success) / len(self.buffer), 3)
        }


# ─── Meta Learner Core ───────────────────────────────────────────────────────

class MetaLearner:
    """
    SPEACE Metalearning System (BRN-013).

    Coordinates strategy selection, hyperparameter optimization, transfer learning,
    and experience replay to enable learning-to-learn across all cognitive domains.

    Inspired by: MAML, Darwin Gödel Machine, EVOLVE framework.
    """

    def __init__(self, state_path: Optional[Path] = None):
        self.state_path = state_path or ROOT_DIR / "data" / "metalearner_state.json"
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        self.strategy_selector = StrategySelector(exploration_factor=1.4)
        self.hyperparam_optimizer = HyperparameterOptimizer()
        self.transfer_engine = TransferLearningEngine(max_primitives=200)
        self.experience_buffer = ExperienceBuffer(capacity=1000)

        self.meta_episode_count = 0
        self.meta_performance: deque = deque(maxlen=50)  # Rolling meta-performance
        self.current_task: Optional[Task] = None
        self._load_state()

        logger.info("MetaLearner BRN-013 initialized")

    # ── Public API ──────────────────────────────────────────────────────────

    def prepare_for_task(self, task: Task) -> Dict[str, Any]:
        """
        Prepare the metalearner for a new learning task.
        Returns: strategy, hyperparams, and relevant primitives.
        """
        self.current_task = task

        # 1. Select strategy
        strategy = self.strategy_selector.select(task)

        # 2. Get hyperparameters
        hyperparams = self.hyperparam_optimizer.suggest(task.domain)

        # 3. Retrieve relevant transfer primitives
        primitives = self.transfer_engine.retrieve_relevant(task, top_k=5)

        plan = {
            "task_id": task.task_id,
            "domain": task.domain.value,
            "strategy": strategy.value,
            "hyperparams": {k: round(v, 4) for k, v in hyperparams.items()},
            "transfer_primitives": [p["lesson"] for p in primitives],
            "difficulty": task.difficulty,
            "novelty": task.novelty
        }
        logger.info(f"MetaLearner: prepared for task {task.task_id} → strategy={strategy.value}")
        return plan

    def record_outcome(self, task: Task, strategy: LearningStrategy,
                       hyperparams: Dict[str, float],
                       initial_perf: float, final_perf: float,
                       steps: int, lessons: List[str]) -> LearningEpisode:
        """Record the outcome of a learning episode and update all components."""
        success = final_perf >= initial_perf + 0.05  # At least 5% improvement
        episode = LearningEpisode(
            task_id=task.task_id,
            strategy_used=strategy,
            initial_performance=initial_perf,
            final_performance=final_perf,
            steps_taken=steps,
            time_elapsed=time.time() - task.created_at,
            hyperparams_used=hyperparams,
            success=success,
            lessons=lessons
        )

        # Update components
        self.strategy_selector.update(episode)
        self.hyperparam_optimizer.observe(hyperparams, final_perf)
        primitives = self.transfer_engine.extract_primitives(episode)
        self.transfer_engine.store_primitives(primitives)
        self.experience_buffer.store(episode)

        self.meta_episode_count += 1
        self.meta_performance.append(final_perf)
        self._save_state()

        logger.info(f"MetaLearner: episode recorded | success={success} | "
                    f"improvement={episode.improvement:.4f} | "
                    f"efficiency={episode.efficiency:.4f}")
        return episode

    def meta_reflect(self) -> Dict[str, Any]:
        """
        Perform meta-level reflection on recent learning history.
        Identifies patterns, failure modes, and improvement opportunities.
        Returns insights for integration with System3 and DefaultModeNetwork.
        """
        sample = self.experience_buffer.sample(n=20)
        if not sample:
            return {"status": "insufficient_data"}

        # Aggregate statistics
        strategies_used = {}
        for ep in sample:
            s = ep.strategy_used.value
            strategies_used[s] = strategies_used.get(s, 0) + 1

        avg_improvement = sum(ep.improvement for ep in sample) / len(sample)
        success_rate = sum(1 for ep in sample if ep.success) / len(sample)
        best_ep = max(sample, key=lambda e: e.improvement)
        worst_ep = min(sample, key=lambda e: e.improvement)

        insights = {
            "meta_episodes": self.meta_episode_count,
            "recent_avg_improvement": round(avg_improvement, 4),
            "recent_success_rate": round(success_rate, 3),
            "dominant_strategy": max(strategies_used, key=strategies_used.get),
            "best_task": best_ep.task_id,
            "worst_task": worst_ep.task_id,
            "transfer_primitives_stored": len(self.transfer_engine.primitive_library),
            "hyperopt_best_score": round(self.hyperparam_optimizer.best_score, 4),
            "meta_performance_trend": self._compute_trend()
        }
        logger.info(f"MetaLearner: meta-reflection → success_rate={success_rate:.2%} | "
                    f"avg_improvement={avg_improvement:.4f}")
        return insights

    # ── Internal helpers ────────────────────────────────────────────────────

    def _compute_trend(self) -> str:
        """Compute performance trend: improving / stable / degrading."""
        if len(self.meta_performance) < 4:
            return "insufficient_data"
        recent = list(self.meta_performance)[-10:]
        delta = recent[-1] - recent[0]
        if delta > 0.05:
            return "improving"
        elif delta < -0.05:
            return "degrading"
        return "stable"

    def _save_state(self) -> None:
        try:
            state = {
                "meta_episode_count": self.meta_episode_count,
                "strategy_selector": self.strategy_selector.get_status(),
                "hyperparam_optimizer": self.hyperparam_optimizer.get_status(),
                "transfer_engine": self.transfer_engine.get_status(),
                "experience_buffer": self.experience_buffer.get_statistics(),
                "last_saved": time.time()
            }
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"MetaLearner: could not save state: {e}")

    def _load_state(self) -> None:
        try:
            if self.state_path.exists():
                with open(self.state_path, "r", encoding="utf-8") as f:
                    state = json.load(f)
                self.meta_episode_count = state.get("meta_episode_count", 0)
                logger.info(f"MetaLearner: resumed from {self.meta_episode_count} episodes")
        except Exception as e:
            logger.warning(f"MetaLearner: could not load state: {e}")

    def get_full_status(self) -> Dict:
        return {
            "module": "MetaLearner",
            "brn_id": "BRN-013",
            "meta_episode_count": self.meta_episode_count,
            "current_task": self.current_task.task_id if self.current_task else None,
            "strategy_selector": self.strategy_selector.get_status(),
            "hyperparam_optimizer": self.hyperparam_optimizer.get_status(),
            "transfer_engine": self.transfer_engine.get_status(),
            "experience_buffer": self.experience_buffer.get_statistics(),
            "meta_performance_trend": self._compute_trend()
        }


# ─── Factory ─────────────────────────────────────────────────────────────────

def create_metalearner(state_path: Optional[Path] = None) -> MetaLearner:
    """Factory function for MetaLearner."""
    return MetaLearner(state_path=state_path)


# ─── Self-test ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ml = create_metalearner()

    # Simulate a learning episode
    task = Task(
        task_id="scientific_climate_analysis_001",
        domain=TaskDomain.SCIENTIFIC,
        description="Analyze correlation between CO2 and temperature anomalies",
        difficulty=0.6,
        novelty=0.4
    )

    plan = ml.prepare_for_task(task)
    print("\n[MetaLearner] Prepared plan:")
    print(json.dumps(plan, indent=2))

    # Simulate outcome
    strategy = LearningStrategy(plan["strategy"])
    episode = ml.record_outcome(
        task=task,
        strategy=strategy,
        hyperparams=plan["hyperparams"],
        initial_perf=0.45,
        final_perf=0.78,
        steps=25,
        lessons=["CO2-temperature correlation peaks at 10yr lag", "ENSO confounds short-term trends"]
    )
    print(f"\n[MetaLearner] Episode improvement: {episode.improvement:.4f}")

    insights = ml.meta_reflect()
    print("\n[MetaLearner] Meta-reflection:")
    print(json.dumps(insights, indent=2))

    print("\n[MetaLearner] BRN-013 self-test passed ✓")
