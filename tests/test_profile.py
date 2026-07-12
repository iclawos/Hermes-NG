from zilli.routing.profile import ModelCapability, ModelEntry, ModelProfile


def _make_entry(name: str, model_id: str, cost: float = 0.01,
                reasoning: float = 0.5) -> ModelEntry:
    return ModelEntry(
        name=name,
        model_id=model_id,
        provider="test",
        cost_per_1k_input=cost,
        cost_per_1k_output=cost * 2,
        capability=ModelCapability(reasoning=reasoning),
    )


class TestModelProfile:
    def setup_method(self):
        self.profile = ModelProfile(exploration_factor=0.0)
        self.profile.register(_make_entry("cheap", "model-a", cost=0.001, reasoning=0.3))
        self.profile.register(_make_entry("good", "model-b", cost=0.01, reasoning=0.9))
        self.profile.register(_make_entry("mid", "model-c", cost=0.005, reasoning=0.6))

    def test_filter_by_cost(self):
        result = self.profile.filter(task_family="reasoning", max_cost=0.005)
        assert len(result) >= 1
        ids = [m.model_id for m in result]
        assert "model-b" not in ids

    def test_select_best_returns_high_score(self):
        candidates = [m for m in self.profile._models.values()]
        selected = self.profile.select_best("reasoning", candidates)
        assert selected is not None
        assert selected.score_for(self.profile._task_weights["reasoning"]) > 0

    def test_update_success_rate(self):
        self.profile.update_success_rate("model-b", True)
        entry = self.profile.get("model-b")
        assert entry.success_rate > 0.95

    def test_update_capability(self):
        self.profile.update_capability("model-b", {"reasoning": 1.0})
        entry = self.profile.get("model-b")
        assert entry.capability.reasoning > 0.9

    def test_stats(self):
        stats = self.profile.stats()
        assert stats["total_models"] == 3

    def test_register_and_unregister(self):
        self.profile.register(_make_entry("new", "model-d"))
        assert self.profile.get("model-d") is not None
        self.profile.unregister("model-d")
        assert self.profile.get("model-d") is None

    def test_model_entry_effective_cost(self):
        entry = _make_entry("test", "t", cost=10.0)
        cost = entry.effective_cost(1000, 500)
        assert cost == 20.0

    def test_capability_average(self):
        cap = ModelCapability(reasoning=1.0, coding=0.0, math=0.5, creativity=0.5, instruction_following=0.5)
        assert cap.average() == 0.5

    def test_select_single_candidate(self):
        entry = _make_entry("only", "only")
        result = self.profile.select_best("chat", [entry])
        assert result == entry


class TestCapabilityDot:
    def test_dot_product(self):
        cap = ModelCapability(reasoning=1.0, coding=0.5, math=0.0, creativity=1.0, instruction_following=0.5)
        weights = [1.0, 0.0, 0.0, 0.0, 0.0]
        assert cap.dot(weights) == 1.0
        weights = [0.0, 1.0, 0.0, 0.0, 0.0]
        assert cap.dot(weights) == 0.5
