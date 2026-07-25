from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional

from zilli.routing.feedback import FeedbackCollector, FeedbackRecord
from zilli.routing.ppm import PPMPredictor, TaskFamily
from zilli.routing.profile import ModelProfile
from zilli.routing.strategy import StrategySelector, StrategyTier

logger = logging.getLogger("zilli.routing.mom_router")


@dataclass
class RouteDecision:
    model_id: str
    model_name: str
    difficulty: float
    task_family: TaskFamily
    strategy_tier: StrategyTier
    confidence: float
    estimated_cost: float = 0.0


class MOMRouter:
    def __init__(
        self,
        ppm: PPMPredictor,
        profile: ModelProfile,
        strategy: StrategySelector,
        feedback: Optional[FeedbackCollector] = None,
        budget_provider: Optional[Callable[[], float]] = None,
        train_every: int = 100,
    ):
        self.ppm = ppm
        self.profile = profile
        self.strategy = strategy
        self.feedback = feedback
        self._budget_provider = budget_provider or (lambda: 0.5)
        self._train_every = train_every
        self._feedback_since_train = 0
        self._train_cycles = 0

    async def route(self, text: str, context: Optional[dict] = None) -> RouteDecision:
        prediction = self.ppm.predict(text, context)

        budget_status = self._budget_provider() if self._budget_provider else 0.5
        strategy_config = self.strategy.select(prediction.difficulty, budget_status)

        candidates = self.profile.filter(
            task_family=prediction.task_family.value,
            max_cost=strategy_config.max_cost_per_request,
            min_success_rate=0.5,
        )

        selected = self.profile.select_best(
            task_family=prediction.task_family.value,
            candidates=candidates,
        )

        model_id = selected.model_id if selected else "default"
        model_name = selected.name if selected else "default-model"

        if prediction.task_family == TaskFamily.CHAT and strategy_config.tier == StrategyTier.ECONOMY:
            model_id = "fast-lane"
            model_name = "FastLane (bypass)"

        decision = RouteDecision(
            model_id=model_id,
            model_name=model_name,
            difficulty=prediction.difficulty,
            task_family=prediction.task_family,
            strategy_tier=strategy_config.tier,
            confidence=prediction.confidence,
        )

        return decision

    def record_feedback(
        self,
        request_id: str,
        ppm_difficulty: float,
        ppm_family: str,
        selected_model: str,
        strategy_tier: str,
        actual_latency_ms: float,
        actual_cost: float,
        success: bool = True,
        score: float = 0.0,
        tokens_in: int = 0,
        tokens_out: int = 0,
    ) -> None:
        if not self.feedback:
            return

        record = FeedbackRecord(
            request_id=request_id,
            ppm_difficulty=ppm_difficulty,
            ppm_family=ppm_family,
            selected_model=selected_model,
            strategy_tier=strategy_tier,
            actual_latency_ms=actual_latency_ms,
            actual_cost=actual_cost,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            success=success,
            score=score,
        )
        self.feedback.record(record)
        self._feedback_since_train += 1
        if self._feedback_since_train >= self._train_every:
            self.train_ppm_from_feedback()

    def train_ppm_from_feedback(self, records: Optional[list] = None) -> dict:
        """Close the production loop: train PPM weights from actual outcomes.

        Converts feedback records (prediction vs actual) into PPM training
        records and applies online weight updates. Auto-triggered every
        `train_every` feedback records; can also be called manually.
        """
        if records is None:
            if not self.feedback:
                return {"trained": 0, "reason": "no_feedback_collector"}
            records = list(self.feedback._buffer) + self._drain_feedback_queue()

        training_records = [
            {
                "predicted_difficulty": r.ppm_difficulty,
                "actual_difficulty": self._infer_actual_difficulty(r),
                "ppm_family": r.ppm_family,
                "success": r.success,
            }
            for r in records
        ]

        result = self.ppm.train(training_records)
        self._feedback_since_train = 0
        self._train_cycles += 1
        logger.info(
            "PPM production training cycle %d: %d records, %d errors",
            self._train_cycles, result.get("trained", 0), len(result.get("errors", [])),
        )
        return result

    def _drain_feedback_queue(self) -> list:
        if not self.feedback:
            return []
        drained = []
        queue = self.feedback._queue
        while not queue.empty():
            try:
                drained.append(queue.get_nowait())
            except Exception:
                break
        return drained

    @staticmethod
    def _infer_actual_difficulty(record) -> float:
        """Infer true task difficulty from outcome.

        Failed tasks were harder than predicted; smooth successes were easier.
        Score (0~1 quality) modulates the adjustment.
        """
        base = record.ppm_difficulty
        if not record.success:
            return min(1.0, base + 0.25)
        if record.score >= 0.8:
            return max(0.0, base - 0.15)
        if record.score <= 0.4:
            return min(1.0, base + 0.10)
        return base

    def update_profile_from_feedback(self, model_id: str, success: bool, score: float) -> None:
        self.profile.update_success_rate(model_id, success)

        cap_update = {
            "reasoning": max(0, score - 0.2),
            "coding": score,
            "math": score * 0.8,
            "creativity": score * 0.6,
            "instruction_following": max(0, score - 0.1),
        }
        self.profile.update_capability(model_id, cap_update)

    def stats(self) -> dict:
        return {
            "ppm": self.ppm.stats(),
            "profile": self.profile.stats(),
            "strategy": {
                "tiers": [t.value for t in self.strategy.tiers],
            },
            "feedback_since_train": self._feedback_since_train,
            "train_cycles": self._train_cycles,
        }
