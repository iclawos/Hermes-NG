from __future__ import annotations

import logging
import time
from collections import OrderedDict
from typing import TYPE_CHECKING, Optional

from zilli.routing.ppm_types import PPMPrediction, TaskFamily

if TYPE_CHECKING:
    from zilli.routing.ppm_classifier import PPMClassifier

logger = logging.getLogger("zilli.routing.ppm")


class PPMPredictor:
    def __init__(
        self,
        cache_size: int = 1024,
        timeout_ms: float = 10.0,
        learning_rate: float = 0.1,
        classifier: Optional[PPMClassifier] = None,
    ):
        self._cache: OrderedDict[int, PPMPrediction] = OrderedDict()
        self._cache_size = cache_size
        self._timeout_ms = timeout_ms
        self._call_count = 0
        self._cache_hits = 0
        self._learning_rate = learning_rate
        self._train_count = 0
        self._difficulty_weights: dict[str, dict[str, float]] = {
            "chat": {"length_weight": 1.0, "keyword_bonus": 0.0},
            "coding": {"length_weight": 1.0, "complex_bonus": 0.25, "arch_bonus": 0.1},
            "reasoning": {"length_weight": 1.0, "math_bonus": 0.15, "analysis_bonus": 0.1},
            "analysis": {"length_weight": 1.0, "family_bonus": 0.15},
            "creative": {"length_weight": 1.0},
            "unknown": {"length_weight": 1.0},
        }
        self._classifier: Optional[PPMClassifier] = classifier

    @property
    def classifier(self) -> PPMClassifier:
        if self._classifier is None:
            from zilli.routing.ppm_classifier import RegexClassifier
            self._classifier = RegexClassifier(difficulty_weights=self._difficulty_weights)
        return self._classifier

    def _feature_hash(self, text: str) -> int:
        return hash(text[:200].lower().strip())

    def predict(self, text: str, context: Optional[dict] = None) -> PPMPrediction:
        start = time.monotonic()
        key = self._feature_hash(text)
        cached = self._cache.get(key)
        if cached is not None:
            self._cache_hits += 1
            self._cache.move_to_end(key)
            elapsed = (time.monotonic() - start) * 1000
            cached.latency_ms = elapsed
            cached.cached = True
            return cached

        self._call_count += 1

        pred = self.classifier.classify(text, context)
        elapsed = (time.monotonic() - start) * 1000
        pred.latency_ms = elapsed

        if len(self._cache) < self._cache_size:
            self._cache[key] = pred
        else:
            self._evict()
            self._cache[key] = pred

        return pred

    def _evict(self) -> None:
        if not self._cache:
            return
        self._cache.popitem(last=False)

    def train(self, records: list[dict]) -> dict:
        if not records:
            return {"trained": 0, "errors": []}

        lr = self._learning_rate
        loss_sum = 0.0

        for r in records:
            actual_difficulty = r.get("actual_difficulty", r.get("difficulty", 0.5))
            predicted_difficulty = r.get("predicted_difficulty", actual_difficulty)
            family = r.get("ppm_family", "unknown")
            success = r.get("success", True)
            score = r.get("score", 0.5)

            error = actual_difficulty - predicted_difficulty
            loss_sum += error ** 2

            if family not in self._difficulty_weights:
                continue

            w = self._difficulty_weights[family]

            if "length_weight" in w:
                w["length_weight"] = w["length_weight"] + lr * error * 0.1
                w["length_weight"] = max(0.1, min(3.0, w["length_weight"]))

            if success and score > 0.7 and predicted_difficulty > 0.3:
                for k in w:
                    if k != "length_weight":
                        w[k] = w[k] * (1 - lr * 0.5)

            if not success and score < 0.3:
                for k in w:
                    if k != "length_weight":
                        w[k] = w[k] + lr * 0.1

            self._train_count += 1

        self.clear_cache()

        return {
            "trained": len(records),
            "loss": round(loss_sum / max(len(records), 1), 4),
        }

    def reset_training(self) -> None:
        self._difficulty_weights = {
            "chat": {"length_weight": 1.0, "keyword_bonus": 0.0},
            "coding": {"length_weight": 1.0, "complex_bonus": 0.25, "arch_bonus": 0.1},
            "reasoning": {"length_weight": 1.0, "math_bonus": 0.15, "analysis_bonus": 0.1},
            "analysis": {"length_weight": 1.0, "family_bonus": 0.15},
            "creative": {"length_weight": 1.0},
            "unknown": {"length_weight": 1.0},
        }
        self._train_count = 0
        self.clear_cache()

    def stats(self) -> dict:
        from zilli.routing.ppm_classifier import ClassifierMetadata
        meta = self.classifier.metadata() if self._classifier else ClassifierMetadata(
            version="0.0.0", num_samples=0, accuracy=0.0, feature_dim=0, exported_at="",
        )
        return {
            "cache_size": len(self._cache),
            "cache_hits": self._cache_hits,
            "call_count": self._call_count,
            "hit_rate": round(self._cache_hits / max(self._call_count, 1), 4),
            "train_count": self._train_count,
            "learning_rate": self._learning_rate,
            "difficulty_weights": {
                k: dict(v) for k, v in self._difficulty_weights.items()
            },
            "classifier": self.classifier.name,
            "classifier_accuracy": meta.accuracy,
        }

    def clear_cache(self) -> None:
        self._cache.clear()
