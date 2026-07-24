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
    ):
        self.ppm = ppm
        self.profile = profile
        self.strategy = strategy
        self.feedback = feedback
        self._budget_provider = budget_provider or (lambda: 0.5)

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
        }
