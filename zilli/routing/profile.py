from __future__ import annotations

import json
import logging
import math
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("zilli.routing.profile")


@dataclass
class ModelCapability:
    reasoning: float = 0.5
    coding: float = 0.5
    math: float = 0.5
    creativity: float = 0.5
    instruction_following: float = 0.5

    def average(self) -> float:
        return (self.reasoning + self.coding + self.math
                + self.creativity + self.instruction_following) / 5.0

    def dot(self, weights: list[float]) -> float:
        return (
            self.reasoning * weights[0]
            + self.coding * weights[1]
            + self.math * weights[2]
            + self.creativity * weights[3]
            + self.instruction_following * weights[4]
        )


@dataclass
class ModelEntry:
    name: str
    model_id: str
    provider: str = ""
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    latency_p50_ms: float = 500.0
    capability: ModelCapability = field(default_factory=ModelCapability)
    success_rate: float = 1.0
    call_count: int = 0
    last_used: float = 0.0

    def effective_cost(self, input_tokens: int, output_tokens: int) -> float:
        return (
            self.cost_per_1k_input * input_tokens / 1000
            + self.cost_per_1k_output * output_tokens / 1000
        )

    def score_for(self, task_weights: list[float]) -> float:
        cap = self.capability.dot(task_weights)
        return cap * self.success_rate


class ModelProfile:
    def __init__(
        self,
        persist_path: Optional[str] = None,
        exploration_factor: float = 0.1,
    ):
        self._models: dict[str, ModelEntry] = {}
        self._task_weights: dict[str, list[float]] = {
            "chat": [0.1, 0.1, 0.1, 0.5, 0.2],
            "reasoning": [0.4, 0.1, 0.3, 0.05, 0.15],
            "coding": [0.2, 0.4, 0.1, 0.05, 0.25],
            "analysis": [0.3, 0.1, 0.1, 0.1, 0.4],
            "creative": [0.05, 0.05, 0.0, 0.7, 0.2],
            "unknown": [0.2, 0.2, 0.2, 0.2, 0.2],
        }
        self._exploration_factor = exploration_factor
        self._path = Path(persist_path) if persist_path else None
        self._load()

    def register(self, entry: ModelEntry) -> None:
        self._models[entry.model_id] = entry
        self._save()

    def unregister(self, model_id: str) -> None:
        self._models.pop(model_id, None)
        self._save()

    def get(self, model_id: str) -> Optional[ModelEntry]:
        return self._models.get(model_id)

    def filter(
        self,
        task_family: str,
        max_cost: float = float("inf"),
        min_success_rate: float = 0.0,
    ) -> list[ModelEntry]:
        candidates = []
        for m in self._models.values():
            if m.cost_per_1k_input > max_cost and m.cost_per_1k_output > max_cost:
                continue
            if m.success_rate < min_success_rate:
                continue
            candidates.append(m)

        weights = self._task_weights.get(task_family, self._task_weights["unknown"])

        if self._exploration_factor > 0 and random.random() < self._exploration_factor:
            random.shuffle(candidates)
            return candidates[:max(1, len(candidates) // 2)]

        candidates.sort(key=lambda m: m.score_for(weights), reverse=True)
        return candidates

    def select_best(self, task_family: str, candidates: list[ModelEntry]) -> Optional[ModelEntry]:
        if not candidates:
            return None

        weights = self._task_weights.get(task_family, self._task_weights["unknown"])

        if len(candidates) == 1:
            return candidates[0]

        scores = [m.score_for(weights) for m in candidates]

        temp = 0.5 + max(0, 1.0 - max(scores))
        probs = [math.exp(s / temp) for s in scores]
        total = sum(probs)
        probs = [p / total for p in probs]

        r = random.random()
        cumulative = 0.0
        for i, p in enumerate(probs):
            cumulative += p
            if r <= cumulative:
                chosen = candidates[i]
                chosen.call_count += 1
                chosen.last_used = time.time()
                self._save()
                return candidates[i]

        chosen = candidates[-1]
        chosen.call_count += 1
        chosen.last_used = time.time()
        self._save()
        return chosen

    def update_capability(
        self,
        model_id: str,
        dimensions: dict[str, float],
    ) -> None:
        entry = self._models.get(model_id)
        if not entry:
            return
        for key, value in dimensions.items():
            if hasattr(entry.capability, key):
                current = getattr(entry.capability, key)
                updated = current * 0.7 + value * 0.3
                setattr(entry.capability, key, max(0.0, min(1.0, updated)))
        self._save()

    def update_success_rate(self, model_id: str, success: bool) -> None:
        entry = self._models.get(model_id)
        if not entry:
            return
        alpha = 0.1
        entry.success_rate = entry.success_rate * (1 - alpha) + (1.0 if success else 0.0) * alpha
        entry.call_count += 1
        entry.last_used = time.time()
        self._save()

    def _load(self) -> None:
        if not self._path or not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
            for item in data:
                cap = ModelCapability(**item.pop("capability", {}))
                entry = ModelEntry(capability=cap, **item)
                self._models[entry.model_id] = entry
        except Exception as e:
            logger.debug("Failed to load model profile: %s", e)

    def _save(self) -> None:
        if not self._path:
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            data = []
            for m in self._models.values():
                d = {
                    "name": m.name,
                    "model_id": m.model_id,
                    "provider": m.provider,
                    "cost_per_1k_input": m.cost_per_1k_input,
                    "cost_per_1k_output": m.cost_per_1k_output,
                    "latency_p50_ms": m.latency_p50_ms,
                    "capability": {
                        "reasoning": m.capability.reasoning,
                        "coding": m.capability.coding,
                        "math": m.capability.math,
                        "creativity": m.capability.creativity,
                        "instruction_following": m.capability.instruction_following,
                    },
                    "success_rate": m.success_rate,
                    "call_count": m.call_count,
                    "last_used": m.last_used,
                }
                data.append(d)
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2))
            tmp.replace(self._path)
        except Exception as e:
            logger.debug("Failed to save model profile: %s", e)

    def stats(self) -> dict:
        return {
            "total_models": len(self._models),
            "models": [
                {
                    "name": m.name,
                    "model_id": m.model_id,
                    "success_rate": round(m.success_rate, 3),
                    "call_count": m.call_count,
                    "avg_capability": round(m.capability.average(), 3),
                }
                for m in self._models.values()
            ],
        }
