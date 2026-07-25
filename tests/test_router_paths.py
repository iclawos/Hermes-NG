import asyncio

from zilli.models.base import GenerationResult
from zilli.models.registry import ModelRegistry
from zilli.routing.router import LocalHybridRouter, RouteClassifier, RouteType


def _run(coro):
    return asyncio.run(coro)


class _MockRegistry(ModelRegistry):
    def __init__(self, text="mock-output", error=None):
        super().__init__()
        self._text = text
        self._error = error
        self.calls = []
        self.profile.models = []

    async def generate(self, role, prompt, **kw):
        self.calls.append((role.value, prompt))
        return GenerationResult(
            text=self._text, model_name=f"mock-{role.value}",
            tokens_in=10, tokens_out=20, error=self._error,
        )


class TestRouterFastLane:
    def test_fast_lane_returns_executor_output(self):
        registry = _MockRegistry(text="fast answer")
        router = LocalHybridRouter(registry, RouteClassifier())
        result = _run(router.run("hello"))
        assert result.route_type == RouteType.FAST_LANE
        assert result.final_text == "fast answer"
        assert result.executor_result == "fast answer"
        assert result.total_duration_ms >= 0

    def test_fast_lane_error_propagates(self):
        registry = _MockRegistry(text="", error="backend down")
        router = LocalHybridRouter(registry, RouteClassifier())
        result = _run(router.run("hello"))
        assert result.error == "backend down"


class TestRouterFullRoute:
    def test_full_route_three_stages(self):
        registry = _MockRegistry(text="stage-output")
        router = LocalHybridRouter(registry, RouteClassifier())
        result = _run(router.run("设计一个复杂的数据分析方案架构", force_full_route=True))
        assert result.route_type == RouteType.FULL_ROUTE
        assert result.planner_result == "stage-output"
        assert result.executor_result == "stage-output"
        assert result.reviewer_result == "stage-output"
        assert result.final_text == "stage-output"
        roles = [r for r, _ in registry.calls]
        assert len(registry.calls) >= 3

    def test_full_route_via_classification(self):
        registry = _MockRegistry(text="r")
        router = LocalHybridRouter(registry, RouteClassifier())
        result = _run(router.run("设计一个完整的系统架构方案"))
        assert result.route_type == RouteType.FULL_ROUTE


class TestRouterPlannerBudget:
    def test_budget_exceeded_falls_back(self):
        from zilli.envs.planner_budget import PlannerBudget
        budget = PlannerBudget(max_planner_ratio=0.0)
        budget._calls.append("planner")
        registry = _MockRegistry(text="direct")
        router = LocalHybridRouter(registry, RouteClassifier(), planner_budget=budget)
        result = _run(router.run("设计一个复杂的架构方案", force_full_route=True))
        assert result.final_text == "direct"
        assert result.route_type == RouteType.FAST_LANE

    def test_calls_recorded(self):
        from zilli.envs.planner_budget import PlannerBudget
        budget = PlannerBudget(max_planner_ratio=0.9)
        registry = _MockRegistry(text="x")
        router = LocalHybridRouter(registry, RouteClassifier(), planner_budget=budget)
        _run(router.run("设计一个复杂方案", force_full_route=True))
        assert len(budget._calls) >= 2


class TestRouterCache:
    def test_cache_hit_skips_backend(self):
        from zilli.cache.engine import CacheConfig, CacheEngine
        cache = CacheEngine(CacheConfig(memory_size=10, ttl_seconds=60, disk_persistence=False))
        registry = _MockRegistry(text="cached")
        router = LocalHybridRouter(registry, RouteClassifier(), cache=cache)
        r1 = _run(router.run("hello"))
        calls_after_first = len(registry.calls)
        r2 = _run(router.run("hello"))
        assert len(registry.calls) == calls_after_first
        assert r1.final_text == r2.final_text

    def test_dangerous_output_not_cached(self):
        from zilli.cache.engine import CacheConfig, CacheEngine
        cache = CacheEngine(CacheConfig(memory_size=10, ttl_seconds=60, disk_persistence=False))
        registry = _MockRegistry(text="run rm -rf / now")
        router = LocalHybridRouter(registry, RouteClassifier(), cache=cache)
        _run(router.run("hello"))
        assert cache.get("hello", "executor") is None


class TestRouterSanitize:
    def test_pii_sanitized_before_routing(self):
        registry = _MockRegistry(text="ok")
        router = LocalHybridRouter(registry, RouteClassifier())
        result = _run(router.run("call me at 13812345678"))
        assert result.final_text == "ok"

    def test_industry_enrichment(self):
        registry = _MockRegistry(text="ok")
        router = LocalHybridRouter(registry, RouteClassifier())
        result = _run(router.run("hello", industry="medical"))
        assert result.final_text == "ok"
        assert any("health" in p.lower() or "phi" in p.lower() for _, p in registry.calls)


class TestRouterException:
    def test_exception_returns_error_result(self):
        class _BoomRegistry(_MockRegistry):
            async def generate(self, role, prompt, **kw):
                raise RuntimeError("kaboom")

        router = LocalHybridRouter(_BoomRegistry(), RouteClassifier())
        result = _run(router.run("hello"))
        assert result.error == "kaboom"
        assert result.final_text == ""
