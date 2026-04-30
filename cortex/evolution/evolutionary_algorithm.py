"""
cortex.evolution.evolutionary_algorithm
=========================================
M14.2 — EvolutionaryAlgorithm: algoritmo genetico reale per l'evoluzione
multi-generazionale dei parametri epigenetici di SPEACE.

A differenza delle mutazioni epigenetiche singole (EPI-001→017) approvate
manualmente via SafeProactive, il GA opera su una **popolazione di varianti**
dell'epigenome in sandbox e seleziona automaticamente il migliore candidato
da proporre via SafeProactive — implementando la vera selezione darwiniana.

Architettura:
  Individual (genome dict, fitness, generation)
       ↓
  EvolutionaryAlgorithm (population_size, mutation_rate, crossover_rate)
       ↓
  evolve(N generations):
    1. Evaluate fitness (fitness_function.yaml weights)
    2. Select top-50% parents
    3. Crossover (uniform binary)
    4. Mutate ±rate (proporzionale al valore)
    5. Nuovo Individual con generation++
       ↓
  best_individual → MutationProposal (SafeProactive)

Fitness function: usa i pesi da digitaldna/fitness_function.yaml
  fitness = alignment*0.35 + task_success*0.25 + stability*0.20
          + efficiency*0.15 + ethics*0.05

Ispirato a GROK SPEACE v4.3 EvolutionaryAlgorithm.
M14.2 | 2026-04-29
"""

from __future__ import annotations

import copy
import logging
import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("speace.evolution.ga")

# ── Pesi fitness function (da fitness_function.yaml) ─────────────────────────
DEFAULT_FITNESS_WEIGHTS: Dict[str, float] = {
    "speace_alignment_score": 0.35,
    "task_success_rate":      0.25,
    "system_stability":       0.20,
    "resource_efficiency":    0.15,
    "ethical_compliance":     0.05,
}

# Soglie fitness
FITNESS_MIN_TO_SURVIVE = 0.50
FITNESS_MIN_TO_APPLY   = 0.60
FITNESS_EXCELLENT      = 0.85


# ─────────────────────────────────────────────────────────────────────────────
# Individual
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Individual:
    """
    Un individuo della popolazione GA — variante di parametri epigenetici.

    Attributi:
        genome:     dict {param_name: float} dei parametri epigenetici
        fitness:    score fitness [0.0, 1.0] dopo valutazione
        generation: numero di generazione in cui è nato
        parent_ids: ID dei genitori (per tracciabilità)
        id:         identificativo univoco (timestamp + random)
        age:        numero di generazioni sopravvissute
    """
    genome:     Dict[str, float]
    fitness:    float = 0.0
    generation: int   = 0
    parent_ids: List[str] = field(default_factory=list)
    id:         str   = field(default_factory=lambda: f"ind_{int(time.time()*1000) % 1_000_000}_{random.randint(0,999):03d}")
    age:        int   = 0

    def clone(self) -> "Individual":
        """Crea una copia profonda."""
        return Individual(
            genome     = copy.deepcopy(self.genome),
            fitness    = self.fitness,
            generation = self.generation,
            parent_ids = list(self.parent_ids),
            id         = f"ind_{int(time.time()*1000) % 1_000_000}_{random.randint(0,999):03d}",
            age        = self.age,
        )

    def summary(self) -> str:
        top3 = sorted(self.genome.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
        params = " | ".join(f"{k}={v:.4f}" for k, v in top3)
        return (
            f"[Individual] id={self.id} gen={self.generation} "
            f"fitness={self.fitness:.4f} age={self.age} | {params}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# EvolutionaryResult
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EvolutionaryResult:
    """
    Risultato di una run evolutiva.

    Attributi:
        best_individual:    migliore individuo finale
        final_population:   popolazione finale (ordinata per fitness)
        generations_run:    numero di generazioni completate
        fitness_history:    [(gen, best_fitness, avg_fitness)] per generazione
        converged:          True se la fitness ha smesso di migliorare
        elapsed_s:          tempo impiegato in secondi
    """
    best_individual:  Individual
    final_population: List[Individual]
    generations_run:  int
    fitness_history:  List[Tuple[int, float, float]]
    converged:        bool = False
    elapsed_s:        float = 0.0

    def summary(self) -> str:
        best = self.best_individual
        last_gen, best_fit, avg_fit = self.fitness_history[-1] if self.fitness_history else (0, 0, 0)
        return (
            f"[EvolutionaryResult] gens={self.generations_run} "
            f"best_fitness={best_fit:.4f} avg_fitness={avg_fit:.4f} "
            f"converged={self.converged} elapsed={self.elapsed_s:.2f}s\n"
            f"  Best: {best.summary()}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# EvolutionaryAlgorithm
# ─────────────────────────────────────────────────────────────────────────────

class EvolutionaryAlgorithm:
    """
    M14.2 — Algoritmo genetico reale per l'evoluzione di parametri SPEACE.

    Implementa un GA canonico con:
      - Inizializzazione da un genome base (copia dell'epigenome corrente)
      - Selezione top-50% (elitismo + variabilità)
      - Crossover uniforme binario tra due genitori
      - Mutazione proporzionale ±rate
      - Fitness function da fitness_function.yaml (pesi configurabili)
      - Convergenza automatica (plateau detection)

    Uso semplice:
        # Genome base = slice dei parametri epigenetici da ottimizzare
        base_genome = {
            "learning_rate": 0.01,
            "exploration_rate": 0.3,
            "homeostasis_threshold": 0.4,
            "plasticity_rate": 0.05,
            "mutation_rate_epi": 0.1,
        }

        ga = EvolutionaryAlgorithm(population_size=10)
        result = ga.evolve(base_genome, n_generations=5)
        print(result.summary())
        # → best_individual con fitness ottimizzata

    Per usare fitness function reale (runtime SPEACE):
        ga = EvolutionaryAlgorithm(
            population_size=10,
            fitness_fn=lambda genome: speace_runtime.evaluate_genome(genome)
        )

    Proposta SafeProactive automatica al termine:
        proposal = ga.propose_best(result, file_path="digitaldna/epigenome.yaml")
        proposal.approved = True   # dopo approvazione Roberto
        # → CodeMutationLab applica le modifiche

    Nota: Il GA opera SEMPRE in sandbox — non modifica mai l'epigenome
    direttamente. Produce solo una MutationProposal.
    """

    def __init__(
        self,
        population_size:   int   = 10,
        mutation_rate:     float = 0.20,   # ±20% del valore corrente
        crossover_rate:    float = 0.70,   # probabilità di crossover vs cloning
        elite_fraction:    float = 0.50,   # top-50% sopravvivono
        fitness_weights:   Optional[Dict[str, float]] = None,
        fitness_fn:        Optional[Callable[[Dict[str, float]], float]] = None,
        convergence_patience: int = 5,     # generazioni senza miglioramento → stop
        rng_seed:          Optional[int] = None,
    ) -> None:
        """
        Args:
            population_size:      numero di individui per generazione
            mutation_rate:        ±rate proporzionale al valore (es. 0.20 = ±20%)
            crossover_rate:       probabilità crossover; altrimenti cloning
            elite_fraction:       frazione top sopravviventi (0.5 = top-50%)
            fitness_weights:      pesi fitness (default: da fitness_function.yaml)
            fitness_fn:           funzione fitness esterna (sostituisce quella interna)
            convergence_patience: generazioni senza miglioramento prima di fermarsi
            rng_seed:             seed per riproducibilità
        """
        self._pop_size      = max(4, population_size)   # minimo 4 per crossover
        self._mutation_rate = max(0.0, min(1.0, mutation_rate))
        self._crossover_rate = max(0.0, min(1.0, crossover_rate))
        self._elite_n       = max(1, int(self._pop_size * elite_fraction))
        self._weights       = fitness_weights or dict(DEFAULT_FITNESS_WEIGHTS)
        self._fitness_fn    = fitness_fn
        self._patience      = convergence_patience
        self._rng           = random.Random(rng_seed)

        # Statistiche run
        self._runs: int = 0
        self._total_evaluations: int = 0

    # ── Evoluzione ────────────────────────────────────────────────────────────

    def evolve(
        self,
        base_genome:   Dict[str, float],
        n_generations: int = 10,
        verbose:       bool = False,
    ) -> EvolutionaryResult:
        """
        Esegui il ciclo evolutivo partendo da `base_genome`.

        Args:
            base_genome:   genome di partenza (slice di parametri epigenetici)
            n_generations: numero massimo di generazioni
            verbose:       stampa progress per generazione

        Returns:
            EvolutionaryResult con best_individual e fitness_history.
        """
        t0 = time.time()
        self._runs += 1

        # Validazione
        if not base_genome:
            raise ValueError("base_genome non può essere vuoto")
        if n_generations < 1:
            raise ValueError("n_generations deve essere >= 1")

        # Inizializza popolazione
        population = self._initialize_population(base_genome)
        fitness_history: List[Tuple[int, float, float]] = []
        best_ever: Optional[Individual] = None
        plateau_count = 0
        prev_best_fitness = -1.0

        for gen in range(n_generations):
            # 1. Valuta fitness per tutti
            for ind in population:
                if ind.fitness == 0.0:  # già valutato = skip
                    ind.fitness = self._evaluate(ind.genome)
                    self._total_evaluations += 1
                ind.age += 1

            # 2. Ordina per fitness decrescente
            population.sort(key=lambda x: x.fitness, reverse=True)

            best_gen    = population[0].fitness
            avg_gen     = sum(i.fitness for i in population) / len(population)
            fitness_history.append((gen, round(best_gen, 5), round(avg_gen, 5)))

            if verbose:
                logger.info(
                    "[GA] gen=%d best=%.4f avg=%.4f pop=%d",
                    gen, best_gen, avg_gen, len(population),
                )

            # Aggiorna best_ever
            if best_ever is None or population[0].fitness > best_ever.fitness:
                best_ever = population[0].clone()
                plateau_count = 0
            else:
                if abs(best_gen - prev_best_fitness) < 1e-5:
                    plateau_count += 1
                else:
                    plateau_count = 0

            prev_best_fitness = best_gen

            # Convergenza anticipata
            if plateau_count >= self._patience:
                logger.info("[GA] Convergenza anticipata a gen=%d (plateau=%d)", gen, plateau_count)
                break

            # 3. Selezione + riproduzione → nuova generazione
            if gen < n_generations - 1:
                population = self._reproduce(population, gen + 1)

        elapsed = time.time() - t0
        converged = plateau_count >= self._patience

        assert best_ever is not None
        logger.info("[GA] Run #%d completata: %s", self._runs, best_ever.summary())

        return EvolutionaryResult(
            best_individual  = best_ever,
            final_population = sorted(population, key=lambda x: x.fitness, reverse=True),
            generations_run  = len(fitness_history),
            fitness_history  = fitness_history,
            converged        = converged,
            elapsed_s        = round(elapsed, 3),
        )

    # ── Inizializzazione ──────────────────────────────────────────────────────

    def _initialize_population(self, base_genome: Dict[str, float]) -> List[Individual]:
        """
        Crea una popolazione di `pop_size` individui.

        Il primo individuo è la copia esatta del base_genome (elitismo iniziale).
        Gli altri sono perturbazioni casuali del base_genome.
        """
        population: List[Individual] = []

        # Individuo base (genotipo originale)
        base = Individual(genome=copy.deepcopy(base_genome), generation=0)
        population.append(base)

        # Varianti perturbate
        for _ in range(self._pop_size - 1):
            mutated_genome = self._perturb(base_genome, rate=self._mutation_rate * 1.5)
            ind = Individual(genome=mutated_genome, generation=0)
            population.append(ind)

        return population

    def _perturb(self, genome: Dict[str, float], rate: float) -> Dict[str, float]:
        """Perturba casualmente tutti i parametri del genome di ±rate."""
        result = {}
        for k, v in genome.items():
            delta = v * rate * (self._rng.random() * 2.0 - 1.0)
            result[k] = self._clamp(v + delta, k)
        return result

    # ── Selezione e riproduzione ──────────────────────────────────────────────

    def _reproduce(
        self,
        population: List[Individual],  # già ordinata per fitness desc
        next_gen:   int,
    ) -> List[Individual]:
        """
        Genera la popolazione della prossima generazione.

        1. Elitismo: i top-elite_n sopravvivono intatti (fitness conservata)
        2. Fill: pop_size - elite_n nuovi figli da crossover/mutation
        """
        # Elitismo: i migliori sopravvivono
        elites = [ind.clone() for ind in population[:self._elite_n]]
        for e in elites:
            e.generation = next_gen

        # Fill con figli
        children: List[Individual] = []
        parents = population[:self._elite_n]   # pool genitori = elite

        while len(children) < self._pop_size - self._elite_n:
            # Scegli 2 genitori (con rimpiazzo, permette autopair solo se pop piccola)
            p1, p2 = self._rng.choices(parents, k=2)

            if self._rng.random() < self._crossover_rate:
                child_genome = self._crossover(p1.genome, p2.genome)
            else:
                child_genome = copy.deepcopy(p1.genome)

            # Mutazione proporzionale
            child_genome = self._mutate(child_genome)

            child = Individual(
                genome     = child_genome,
                generation = next_gen,
                parent_ids = [p1.id, p2.id],
            )
            children.append(child)

        return elites + children

    def _crossover(
        self,
        g1: Dict[str, float],
        g2: Dict[str, float],
    ) -> Dict[str, float]:
        """Crossover uniforme binario: ogni gene da g1 o g2 con p=0.5."""
        result = {}
        for k in g1:
            result[k] = g1[k] if self._rng.random() < 0.5 else g2.get(k, g1[k])
        # Aggiungi geni presenti solo in g2 (se i genomi differiscono)
        for k in g2:
            if k not in result:
                result[k] = g2[k]
        return result

    def _mutate(self, genome: Dict[str, float]) -> Dict[str, float]:
        """
        Mutazione proporzionale ±rate su ogni gene con probabilità 1/n_genes.
        (Probabilità adattiva: ogni run muta in media 1 gene per individuo.)
        """
        result = copy.deepcopy(genome)
        n = max(1, len(genome))
        p_mutate = 1.0 / n   # probabilità per-gene: in media 1 mutazione
        for k, v in result.items():
            if self._rng.random() < p_mutate:
                delta = v * self._mutation_rate * (self._rng.random() * 2.0 - 1.0)
                result[k] = self._clamp(v + delta, k)
        return result

    # ── Fitness ───────────────────────────────────────────────────────────────

    def _evaluate(self, genome: Dict[str, float]) -> float:
        """
        Valuta la fitness di un genome.

        Se è disponibile una fitness_fn esterna, la usa.
        Altrimenti usa la formula interna basata sui pesi di fitness_function.yaml.

        La fitness interna normalizza i valori del genome usando i nomi dei pesi:
        - Se il genome contiene chiavi che corrispondono ai pesi → usa direttamente
        - Altrimenti usa una media normalizzata dei valori del genome

        Returns:
            float in [0.0, 1.0]
        """
        if self._fitness_fn is not None:
            try:
                raw = float(self._fitness_fn(genome))
                return max(0.0, min(1.0, raw))
            except Exception as e:
                logger.warning("[GA] fitness_fn error: %s — fallback interno", e)

        return self._internal_fitness(genome)

    def _internal_fitness(self, genome: Dict[str, float]) -> float:
        """
        Fitness interna: weighted sum dei valori del genome che corrispondono
        ai nomi dei pesi di fitness_function.yaml.

        Se il genome non ha chiavi corrispondenti, usa la media normalizzata
        dei valori (tutti i parametri contribuiscono equalmente).
        """
        w = self._weights
        total_weight = sum(w.values())

        # Tentativo 1: matching diretto sui nomi dei pesi
        matched_score = 0.0
        matched_weight = 0.0
        for weight_key, weight_val in w.items():
            if weight_key in genome:
                v = max(0.0, min(1.0, genome[weight_key]))
                matched_score  += v * weight_val
                matched_weight += weight_val

        if matched_weight >= total_weight * 0.5:
            # Almeno metà dei pesi trovati → usa questa misura
            return round(matched_score / max(1e-9, matched_weight), 5)

        # Tentativo 2: media normalizzata di tutti i valori del genome
        values = list(genome.values())
        if not values:
            return 0.0

        # Normalizza i valori in [0, 1] assumendo che il range sia [0, 1]
        normalized = [max(0.0, min(1.0, v)) for v in values]
        avg = sum(normalized) / len(normalized)

        # Bonus per valori "ottimali" intorno a 0.5-0.7 (zona target epigenetica)
        target = 0.6
        variance = sum((v - target) ** 2 for v in normalized) / len(normalized)
        coherence_bonus = max(0.0, 0.1 * (1.0 - math.sqrt(variance)))

        return round(min(1.0, avg + coherence_bonus), 5)

    # ── Utility ───────────────────────────────────────────────────────────────

    def _clamp(self, value: float, key: str = "") -> float:
        """
        Clamp di un valore nel range [min, max] appropriato.
        Per parametri epigenetici SPEACE, il range standard è [0.0, 1.0]
        con alcune eccezioni.
        """
        # Parametri con range speciale
        _RANGES: Dict[str, Tuple[float, float]] = {
            "learning_rate":       (0.0001, 0.5),
            "temperature":         (0.1, 2.0),
            "max_parallel_tasks":  (1.0, 8.0),
            "heartbeat_frequency": (10.0, 3600.0),
            "mutation_rate_epi":   (0.01, 0.5),
        }
        if key in _RANGES:
            lo, hi = _RANGES[key]
        else:
            lo, hi = 0.0, 1.0
        return max(lo, min(hi, value))

    # ── SafeProactive integration ─────────────────────────────────────────────

    def propose_best(
        self,
        result:      EvolutionaryResult,
        description: str = "",
    ) -> Dict[str, Any]:
        """
        Produce una proposta SafeProactive per il best_individual.

        Non usa CodeMutationLab (che opera su codice Python), ma genera
        un dict strutturato pronto per essere serializzato in PROPOSALS.md
        come proposta di aggiornamento dell'epigenome.

        Args:
            result:      risultato della run evolutiva
            description: descrizione aggiuntiva

        Returns:
            Dict con tutti i campi della proposta SafeProactive.
        """
        best    = result.best_individual
        ts      = datetime.now(timezone.utc).isoformat()
        quality = "EXCELLENT" if best.fitness >= FITNESS_EXCELLENT else (
                  "GOOD" if best.fitness >= FITNESS_MIN_TO_APPLY else
                  "LOW — NON RACCOMANDATO")

        genome_str = "\n".join(
            f"    {k}: {v:.6f}" for k, v in sorted(best.genome.items())
        )
        history_str = " → ".join(
            f"gen{g}:{bf:.4f}" for g, bf, _ in result.fitness_history
        )

        proposal = {
            "id":          f"PROP-GA-{ts[:10].replace('-','')}-GEN{result.generations_run}",
            "timestamp":   ts,
            "action":      "epigenome_update",
            "risk_level":  "MEDIUM",
            "source":      "EvolutionaryAlgorithm GA — M14.2",
            "title":       f"M14.2 — GA Best Individual (fitness={best.fitness:.4f}, {quality})",
            "description": description or (
                f"Proposta di aggiornamento epigenome basata su {result.generations_run} "
                f"generazioni GA con population_size={self._pop_size}.\n"
                f"Fitness: {history_str}\n"
                f"Best genome:\n{genome_str}"
            ),
            "genome_update": best.genome,
            "fitness_score": best.fitness,
            "generations":   result.generations_run,
            "converged":     result.converged,
            "quality":       quality,
            "status":        "PENDING_APPROVAL",
            "approval":      "Roberto De Biase (human-in-the-loop — Medium risk)",
        }

        logger.info("[GA] Proposta generata: %s fitness=%.4f", proposal["id"], best.fitness)
        return proposal

    def format_proposal_markdown(self, proposal: Dict[str, Any]) -> str:
        """Formatta la proposta come blocco Markdown per PROPOSALS.md."""
        genome_lines = "\n".join(
            f"      {k}: {v:.6f}"
            for k, v in sorted(proposal.get("genome_update", {}).items())
        )
        return (
            f"## {proposal['id']}\n"
            f"- **Timestamp:** {proposal['timestamp']}\n"
            f"- **Azione:** {proposal['action']}\n"
            f"- **Risk Level:** {proposal['risk_level']}\n"
            f"- **Sorgente:** {proposal['source']}\n"
            f"- **Titolo:** {proposal['title']}\n"
            f"- **Descrizione:**\n"
            f"  {proposal['description'].replace(chr(10), chr(10)+'  ')}\n"
            f"- **Genome proposto:**\n"
            f"  ```yaml\n{genome_lines}\n  ```\n"
            f"- **Fitness:** {proposal['fitness_score']:.4f} ({proposal['quality']})\n"
            f"- **Generazioni:** {proposal['generations']} "
            f"(converged={proposal['converged']})\n"
            f"- **Status:** {proposal['status']}\n"
            f"- **Approvazione richiesta:** {proposal['approval']}\n"
        )

    # ── Diagnostica ───────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        return {
            "population_size":     self._pop_size,
            "mutation_rate":       self._mutation_rate,
            "crossover_rate":      self._crossover_rate,
            "elite_n":             self._elite_n,
            "convergence_patience": self._patience,
            "runs":                self._runs,
            "total_evaluations":   self._total_evaluations,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Helper: carica base_genome da epigenome.yaml
# ─────────────────────────────────────────────────────────────────────────────

def load_epigenome_genome_slice(
    epigenome_path: Optional[Path] = None,
    keys:           Optional[List[str]] = None,
) -> Dict[str, float]:
    """
    Carica uno slice di parametri float dall'epigenome.yaml come base_genome.

    Se `keys` è specificato, estrae solo quei parametri.
    Altrimenti cerca tutti i parametri float nei blocchi di primo livello.

    Args:
        epigenome_path: path del file epigenome.yaml
        keys:           lista di chiavi da estrarre (None = auto-detect float)

    Returns:
        Dict {param_name: float_value}
    """
    if epigenome_path is None:
        epigenome_path = Path(__file__).parent.parent.parent / "digitaldna" / "epigenome.yaml"

    if not epigenome_path.exists():
        logger.warning("[GA] epigenome.yaml non trovato: %s", epigenome_path)
        return _default_genome_slice()

    try:
        # Import yaml opzionale — usa parser semplice se non disponibile
        try:
            import yaml
            with open(epigenome_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except ImportError:
            data = _parse_yaml_floats(epigenome_path)

        genome = {}
        _extract_floats(data, genome, prefix="")

        if keys:
            genome = {k: v for k, v in genome.items() if any(key in k for key in keys)}

        if not genome:
            return _default_genome_slice()

        return genome

    except Exception as e:
        logger.warning("[GA] Errore parsing epigenome.yaml: %s", e)
        return _default_genome_slice()


def _extract_floats(obj: Any, result: Dict[str, float], prefix: str, depth: int = 0) -> None:
    """Ricava ricorsivamente tutti i valori float da un dict YAML."""
    if depth > 4:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                key = f"{prefix}.{k}" if prefix else k
                result[key] = float(v)
            elif isinstance(v, dict):
                _extract_floats(v, result, f"{prefix}.{k}" if prefix else k, depth + 1)


def _default_genome_slice() -> Dict[str, float]:
    """Genome di default se l'epigenome.yaml non è leggibile."""
    return {
        "learning_rate":           0.01,
        "exploration_rate":        0.30,
        "homeostasis_threshold":   0.40,
        "plasticity_rate":         0.05,
        "mutation_rate_epi":       0.10,
        "speace_alignment_score":  0.70,
        "task_success_rate":       0.65,
        "system_stability":        0.80,
        "resource_efficiency":     0.60,
        "ethical_compliance":      0.90,
    }


def _parse_yaml_floats(path: Path) -> dict:
    """Parser YAML minimale (solo chiave: valore float/int) senza dipendenze."""
    result: dict = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("#") or ":" not in stripped:
                continue
            parts = stripped.split(":", 1)
            if len(parts) == 2:
                k = parts[0].strip()
                v_str = parts[1].strip().split("#")[0].strip()
                try:
                    result[k] = float(v_str)
                except ValueError:
                    pass
    return result


__all__ = [
    "EvolutionaryAlgorithm",
    "Individual",
    "EvolutionaryResult",
    "load_epigenome_genome_slice",
    "DEFAULT_FITNESS_WEIGHTS",
    "FITNESS_EXCELLENT",
    "FITNESS_MIN_TO_APPLY",
]
