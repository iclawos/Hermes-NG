import asyncio

from zilli.routing.feedback import FeedbackCollector
from zilli.routing.mom_router import MOMRouter
from zilli.routing.ppm import PPMPredictor, TaskFamily
from zilli.routing.profile import ModelCapability, ModelEntry, ModelProfile
from zilli.routing.strategy import StrategySelector, StrategyTier


class TestMOMRouter:
    def setup_method(self):
        self.ppm = PPMPredictor()
        self.profile = ModelProfile(exploration_factor=0.0)
        self.profile.register(ModelEntry(
            name="cheap", model_id="fast-cheap",
            cost_per_1k_input=0.0005, cost_per_1k_output=0.001,
            capability=ModelCapability(reasoning=0.3, coding=0.2),
        ))
        self.profile.register(ModelEntry(
            name="powerful", model_id="gpt-4",
            cost_per_1k_input=0.01, cost_per_1k_output=0.03,
            capability=ModelCapability(reasoning=0.9, coding=0.9),
        ))
        self.strategy = StrategySelector()
        self.feedback = FeedbackCollector()
        self.router = MOMRouter(
            ppm=self.ppm,
            profile=self.profile,
            strategy=self.strategy,
            feedback=self.feedback,
        )

    def test_route_simple_chat_goes_cheap(self):
        decision = asyncio.run(self.router.route("Hello"))
        assert decision.task_family == TaskFamily.CHAT
        assert decision.strategy_tier == StrategyTier.ECONOMY

    def test_route_complex_coding(self):
        decision = asyncio.run(self.router.route(
            "Design a distributed system architecture for real-time data processing"
        ))
        assert decision.task_family in (TaskFamily.CODING, TaskFamily.ANALYSIS)

    def test_route_returns_decision(self):
        decision = asyncio.run(self.router.route("hi"))
        assert decision.model_id is not None
        assert decision.confidence > 0

    def test_record_feedback(self):
        self.router.record_feedback(
            request_id="r1", ppm_difficulty=0.5, ppm_family="chat",
            selected_model="fast-cheap", strategy_tier="economy",
            actual_latency_ms=100, actual_cost=0.001, success=True, score=0.8,
        )

    def test_update_profile_from_feedback(self):
        self.router.update_profile_from_feedback("fast-cheap", success=True, score=0.9)
        entry = self.profile.get("fast-cheap")
        assert entry.success_rate > 0.9

    def test_stats(self):
        stats = self.router.stats()
        assert "ppm" in stats
        assert "profile" in stats
        assert "strategy" in stats
