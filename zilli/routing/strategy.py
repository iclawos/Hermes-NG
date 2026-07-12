from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("zilli.routing.strategy")


class StrategyTier(str, Enum):
    ECONOMY = "economy"
    STANDARD = "standard"
    ENHANCED = "enhanced"

    def __str__(self) -> str:
        return self.value


@dataclass
class StrategyConfig:
    tier: StrategyTier
    sota_call_ratio: float
    max_cost_per_request: float
    cost_control_target: str
    description: str


_STRATEGY_DEFS: dict[StrategyTier, StrategyConfig] = {
    StrategyTier.ECONOMY: StrategyConfig(
        tier=StrategyTier.ECONOMY,
        sota_call_ratio=0.01,
        max_cost_per_request=0.001,
        cost_control_target="extreme cost saving",
        description="Distilled models or rule engine only",
    ),
    StrategyTier.STANDARD: StrategyConfig(
        tier=StrategyTier.STANDARD,
        sota_call_ratio=0.05,
        max_cost_per_request=0.01,
        cost_control_target="cost < 10% of budget",
        description="PPM prediction + MOM standard routing",
    ),
    StrategyTier.ENHANCED: StrategyConfig(
        tier=StrategyTier.ENHANCED,
        sota_call_ratio=0.2,
        max_cost_per_request=0.05,
        cost_control_target="allow moderate overspend",
        description="Multi-model协同推理 (MoE activation)",
    ),
}


class StrategySelector:
    def __init__(
        self,
        economy_threshold: float = 0.2,
        enhanced_threshold: float = 0.7,
        budget_ratio_threshold: float = 0.8,
    ):
        self.economy_threshold = economy_threshold
        self.enhanced_threshold = enhanced_threshold
        self.budget_ratio_threshold = budget_ratio_threshold

    def select(
        self,
        difficulty: float,
        budget_status: float,
    ) -> StrategyConfig:
        if difficulty <= self.economy_threshold or budget_status >= self.budget_ratio_threshold:
            return _STRATEGY_DEFS[StrategyTier.ECONOMY]

        if difficulty >= self.enhanced_threshold and budget_status < 0.5:
            return _STRATEGY_DEFS[StrategyTier.ENHANCED]

        return _STRATEGY_DEFS[StrategyTier.STANDARD]

    def get_config(self, tier: StrategyTier) -> StrategyConfig:
        return _STRATEGY_DEFS[tier]

    @property
    def tiers(self) -> list[StrategyTier]:
        return [StrategyTier.ECONOMY, StrategyTier.STANDARD, StrategyTier.ENHANCED]
