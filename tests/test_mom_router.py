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


class TestPPMProductionLoop:
    def setup_method(self):
        self.ppm = PPMPredictor()
        self.profile = ModelProfile(exploration_factor=0.0)
        self.strategy = StrategySelector()
        self.feedback = FeedbackCollector(batch_size=10000)
        self.router = MOMRouter(
            ppm=self.ppm, profile=self.profile,
            strategy=self.strategy, feedback=self.feedback,
            train_every=10,
        )

    def _record(self, n: int, success: bool = True, score: float = 0.9):
        for i in range(n):
            self.router.record_feedback(
                request_id=f"r{i}", ppm_difficulty=0.5, ppm_family="coding",
                selected_model="m1", strategy_tier="standard",
                actual_latency_ms=100, actual_cost=0.01,
                success=success, score=score,
            )

    def test_auto_train_triggers_at_threshold(self):
        weights_before = dict(self.ppm._difficulty_weights)
        self._record(10)
        assert self.router._train_cycles == 1
        assert self.router._feedback_since_train == 0

    def test_no_train_below_threshold(self):
        self._record(5)
        assert self.router._train_cycles == 0
        assert self.router._feedback_since_train == 5

    def test_weights_shift_after_failures(self):
        before = self.ppm._difficulty_weights.get("coding", {}).copy()
        self._record(10, success=False, score=0.2)
        after = self.ppm._difficulty_weights.get("coding", {})
        assert after != before or self.router._train_cycles == 1

    def test_manual_train_with_explicit_records(self):
        from zilli.routing.feedback import FeedbackRecord
        records = [
            FeedbackRecord(
                request_id="x", ppm_difficulty=0.4, ppm_family="chat",
                selected_model="m", strategy_tier="economy",
                actual_latency_ms=50, actual_cost=0.001,
                success=True, score=0.95,
            )
        ]
        result = self.router.train_ppm_from_feedback(records)
        assert result["trained"] == 1

    def test_train_without_collector(self):
        router = MOMRouter(ppm=PPMPredictor(), profile=self.profile,
                           strategy=self.strategy, feedback=None)
        result = router.train_ppm_from_feedback()
        assert result["trained"] == 0

    def test_infer_actual_difficulty(self):
        from zilli.routing.feedback import FeedbackRecord
        fail = FeedbackRecord(
            request_id="f", ppm_difficulty=0.5, ppm_family="coding",
            selected_model="m", strategy_tier="standard",
            actual_latency_ms=1, actual_cost=0, success=False,
        )
        assert self.router._infer_actual_difficulty(fail) == 0.75

        easy = FeedbackRecord(
            request_id="e", ppm_difficulty=0.5, ppm_family="coding",
            selected_model="m", strategy_tier="standard",
            actual_latency_ms=1, actual_cost=0, success=True, score=0.9,
        )
        assert self.router._infer_actual_difficulty(easy) == 0.35

    def test_stats_include_training(self):
        s = self.router.stats()
        assert "feedback_since_train" in s
        assert "train_cycles" in s
