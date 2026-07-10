"""Diversity collapse protection for evolutionary search.

Based on ShinkaEvolve (Lange et al. 2025) and Lilian Weng's
Harness Engineering for Self-Improvement (Jul 2026).

Three mechanisms:
  1. Code-novelty rejection — discard candidates too similar to population
  2. Temperature on parent selection — balance rank vs offspring count
  3. Diversity tracking — monitor population entropy over time
"""

from __future__ import annotations

import logging
import random
import re
import statistics
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("zilli.evolution.diversity")


@dataclass
class PopulationEntry:
    id: str
    fingerprint: dict[str, Any]
    score: float
    source: str = ""
    parent_id: str = ""
    generation: int = 0
    created_at: float = 0.0


def code_fingerprint(source: str) -> dict[str, Any]:
    """Extract a structural fingerprint from source code.

    Captures: function names, class names, imports, control flow keywords,
    API call patterns. Used for similarity comparison.
    """
    return {
        "functions": sorted(set(re.findall(r"def\s+(\w+)\s*\(", source))),
        "classes": sorted(set(re.findall(r"class\s+(\w+)\s*[\(:]", source))),
        "imports": sorted(set(re.findall(r"^(?:from|import)\s+(\S+)", source, re.MULTILINE))),
        "keywords": sorted(set(k for k in re.findall(r"\b(def|class|async|await|try|except|if|for|while|return|yield|raise|with)\b", source))),
        "api_calls": sorted(set(re.findall(r"\.(\w+)\(", source))),
        "n_lines": len(source.split("\n")),
    }


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def fingerprint_similarity(a: dict[str, Any], b: dict[str, Any]) -> float:
    """Weighted similarity between two code fingerprints."""
    weights = {
        "functions": 0.30,
        "classes": 0.25,
        "imports": 0.20,
        "keywords": 0.10,
        "api_calls": 0.10,
        "n_lines": 0.05,
    }
    total = 0.0
    for key, weight in weights.items():
        if key == "n_lines":
            score = 1.0 - min(abs(a.get(key, 0) - b.get(key, 0)) / max(a.get(key, 1), b.get(key, 1), 1), 1.0)
        else:
            score = jaccard_similarity(set(a.get(key, [])), set(b.get(key, [])))
        total += weight * score
    return total


def ngram_fingerprint(source: str, n: int = 3) -> set[str]:
    """Character n-gram fingerprint for fine-grained similarity."""
    cleaned = re.sub(r"\s+", " ", source)
    return {cleaned[i : i + n] for i in range(len(cleaned) - n + 1)}


class DiversityController:
    """Prevents population collapse with novelty pressure.

    Parameters
    ----------
    population_size : int
        Max population size before pruning.
    novelty_threshold : float
        Minimum fingerprint similarity distance to accept a candidate
        (1.0 = must be completely novel, 0.0 = anything accepted).
    parent_temperature : float
        Temperature for parent selection softmax (lower = more greedy).
    use_ngram : bool
        Use character n-gram as additional similarity signal.
    """

    def __init__(
        self,
        population_size: int = 50,
        novelty_threshold: float = 0.7,
        parent_temperature: float = 0.5,
        use_ngram: bool = True,
    ):
        self._max_pop = population_size
        self._threshold = novelty_threshold
        self._temperature = parent_temperature
        self._use_ngram = use_ngram
        self._population: list[PopulationEntry] = []
        self._generation = 0
        self._rejected_count = 0
        self._diversity_log: list[dict] = []

    def is_novel(self, candidate_source: str, candidate_fp: dict[str, Any]) -> bool:
        """Check if a candidate is sufficiently novel vs current population.

        Returns True if candidate should be accepted.
        """
        if not self._population:
            return True

        max_sim = 0.0
        candidate_ngram = ngram_fingerprint(candidate_source) if self._use_ngram else None
        for entry in self._population:
            sim = fingerprint_similarity(candidate_fp, entry.fingerprint)
            if self._use_ngram:
                ngram_sim = jaccard_similarity(candidate_ngram, ngram_fingerprint(entry.source))
                sim = max(sim, ngram_sim)
            if sim > max_sim:
                max_sim = sim

        if max_sim > (1.0 - self._threshold):
            self._rejected_count += 1
            return False
        return True

    def add_entry(
        self,
        entry_id: str,
        source: str,
        score: float,
        parent_id: str = "",
    ) -> bool:
        """Add an entry after novelty check. Returns True if accepted."""
        fp = code_fingerprint(source)
        if not self.is_novel(source, fp):
            return False

        self._population.append(PopulationEntry(
            id=entry_id,
            fingerprint=fp,
            score=score,
            source=source,
            parent_id=parent_id,
            generation=self._generation,
            created_at=time.time(),
        ))
        self._prune()
        return True

    def select_parent(self, scores: list[float], ids: list[str]) -> str:
        """Temperature-weighted parent selection.

        Lower temperature = more greedy toward high performers.
        Higher temperature = more exploration.
        """
        if not scores or not ids:
            return ""
        if len(scores) != len(ids):
            logger.warning("select_parent: scores (%d) and ids (%d) length mismatch", len(scores), len(ids))
            return ids[0] if ids else ""
        if len(scores) == 1:
            return ids[0]

        scaled = [max(s, 0.0) ** (1.0 / max(self._temperature, 0.01)) for s in scores]
        total = sum(scaled)
        if total == 0:
            return random.choice(ids)

        probs = [s / total for s in scaled]
        r = random.random()
        cumulative = 0.0
        for i, p in enumerate(probs):
            cumulative += p
            if r <= cumulative:
                return ids[i]
        return ids[-1]

    def _prune(self) -> None:
        """Keep only top-N entries by score, but preserve diversity.

        Uses fitness sharing: entries with similar fingerprints get
        their fitness discounted.
        """
        if len(self._population) <= self._max_pop:
            return

        sharing_threshold = 0.5
        shared_scores = []
        for i, entry in enumerate(self._population):
            sharing = 0.0
            for j, other in enumerate(self._population):
                if i == j:
                    continue
                sim = fingerprint_similarity(entry.fingerprint, other.fingerprint)
                if sim > sharing_threshold:
                    sharing += sim
            niche_count = 1.0 + sharing
            shared_scores.append((entry.score / niche_count, entry))

        shared_scores.sort(key=lambda x: x[0], reverse=True)
        self._population = [e for _, e in shared_scores[:self._max_pop]]

    def diversity_metrics(self) -> dict[str, Any]:
        """Compute population diversity statistics."""
        base = {
            "generation": self._generation,
            "rejected_count": self._rejected_count,
        }
        if len(self._population) < 2:
            base["pairwise_similarity"] = 0.0
            base["population_size"] = len(self._population)
            base["unique_functions"] = len(self._population[0].fingerprint.get("functions", [])) if self._population else 0
            return base

        similarities = []
        all_functions: set[str] = set()
        sample = random.sample(self._population, min(len(self._population), 20))
        for i in range(len(sample)):
            for j in range(i + 1, len(sample)):
                sim = fingerprint_similarity(
                    sample[i].fingerprint,
                    sample[j].fingerprint,
                )
                similarities.append(sim)
            all_functions.update(sample[i].fingerprint.get("functions", []))

        mean_sim = statistics.mean(similarities) if similarities else 0.0
        base["pairwise_similarity"] = round(mean_sim, 4)
        base["population_size"] = len(self._population)
        base["unique_functions"] = len(all_functions)
        return base

    def log_diversity(self) -> None:
        metrics = self.diversity_metrics()
        metrics["timestamp"] = time.time()
        self._diversity_log.append(metrics)
        logger.info(
            "Diversity: sim=%.3f pop=%d funcs=%d rejected=%d",
            metrics["pairwise_similarity"],
            metrics["population_size"],
            metrics["unique_functions"],
            metrics["rejected_count"],
        )

    def next_generation(self) -> None:
        self._generation += 1

    @property
    def population(self) -> list[PopulationEntry]:
        return self._population

    @property
    def diversity_log(self) -> list[dict]:
        return self._diversity_log
