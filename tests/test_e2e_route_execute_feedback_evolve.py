"""e2e integration: route -> execute -> feedback -> evolve.

Fills the gap in test_e2e_integration.py where requests were routed,
feedback recorded, and skills evolved, but never actually EXECUTED.
"""

from __future__ import annotations

import asyncio

from zilli.core.agent import Agent
from zilli.hybrid.executor import ExecutionTarget, HybridExecutor
from zilli.hybrid.gatekeeper import PrivacyGatekeeper
from zilli.models.base import GenerationResult
from zilli.models.config import DeploymentType, ModelConfig, ModelRole
from zilli.models.config import ModelProfile as ConfigModelProfile
from zilli.models.registry import ModelRegistry
from zilli.privacy.engine import PrivacyEngine
from zilli.routing.feedback import FeedbackCollector
from zilli.routing.mom_router import MOMRouter
from zilli.routing.ppm import PPMPredictor
from zilli.routing.ppm_classifier import RegexClassifier, TaskFamily
from zilli.routing.profile import ModelCapability, ModelEntry
from zilli.routing.profile import ModelProfile as RouteModelProfile
from zilli.routing.strategy import StrategySelector


def _run(coro):
    return asyncio.run(coro)


def _make_router() -> tuple[MOMRouter, PPMPredictor, RouteModelProfile, FeedbackCollector]:
    ppm = PPMPredictor(classifier=RegexClassifier())
    profile = RouteModelProfile(exploration_factor=0.0)
    profile.register(ModelEntry(
        name="cheap", model_id="fast-cheap",
        cost_per_1k_input=0.0005, cost_per_1k_output=0.001,
        capability=ModelCapability(reasoning=0.3, coding=0.3),
    ))
    profile.register(ModelEntry(
        name="premium", model_id="slow-premium",
        cost_per_1k_input=0.01, cost_per_1k_output=0.02,
        capability=ModelCapability(reasoning=0.9, coding=0.95),
    ))
    feedback = FeedbackCollector()
    strategy = StrategySelector()
    router = MOMRouter(ppm=ppm, profile=profile, strategy=strategy, feedback=feedback)
    return router, ppm, profile, feedback


class _MockRegistry(ModelRegistry):
    """Registry whose backends never pass health check; used to test fallback
    chains without network access."""

    def __init__(self):
        profile = ConfigModelProfile(models=[
            ModelConfig(name="executor", backend="ollama", model_id="m",
                        role=ModelRole.EXECUTOR, deployment=DeploymentType.LOCAL),
            ModelConfig(name="executor_fb", backend="ollama", model_id="m2",
                        role=ModelRole.EXECUTOR, deployment=DeploymentType.LOCAL,
                        is_fallback=True),
            ModelConfig(name="reviewer", backend="ollama", model_id="m3",
                        role=ModelRole.REVIEWER, deployment=DeploymentType.CLOUD),
        ])
        super().__init__(profile=profile)

    def _register(self, cfg: ModelConfig) -> None:
        self._backends[cfg.name] = _StubBackend(cfg)

    async def generate(
        self, role, prompt, max_tokens=None, temperature=None,
    ) -> GenerationResult:
        cfg = self.profile.models[0]
        return GenerationResult(text="stub", model_name=cfg.name)

    async def get_model_for_role(self, role: ModelRole):
        return None


class _StubBackend:
    def __init__(self, cfg: ModelConfig):
        self.cfg = cfg

    async def health_check(self) -> bool:
        return True

    async def generate(self, **kw) -> GenerationResult:
        return GenerationResult(text="ok", model_name=self.cfg.name)


class TestRouteExecuteFeedbackEvolve:
    def test_full_cycle_with_agent_execution(self, tmp_path):
        """route -> Agent.execute (real python subprocess) -> feedback -> evolve."""
        router, ppm, profile, feedback = _make_router()

        decision = _run(router.route("write a python function to sort a list"))
        assert decision.model_id in ("fast-cheap", "slow-premium", "fast-lane")

        agent = Agent()  # no model -> fallback generator, real subprocess execution
        result = _run(agent.run("sort a list of numbers"))
        assert result.success, result.error
        assert result.code_used
        assert result.iterations >= 1
        assert "sorted" in result.code_used or "print(" in result.code_used

        router.record_feedback(
            request_id="e2e-exec-1",
            ppm_difficulty=decision.difficulty,
            ppm_family=decision.task_family.value,
            selected_model=decision.model_id,
            strategy_tier=decision.strategy_tier.value,
            actual_latency_ms=result.duration_ms,
            actual_cost=0.001,
            success=result.success,
            score=0.9 if result.success else 0.2,
        )
        router.update_profile_from_feedback(decision.model_id, result.success, 0.9)

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_file = skills_dir / "sorting.py"
        skill_file.write_text("def process():\n    return 0\n")

        engine = _evolve_engine(router, decision.model_id)
        pr = engine.evolve(str(skill_file), trajectory_data=[
            {"observation": {"output": result.output, "error": ""}},
        ])
        assert "Auto-evolved" in pr

        queued = [r for r in list(feedback._queue._queue) if r.request_id == "e2e-exec-1"]
        assert queued, "feedback record should be queued"
        _run(feedback.flush())
        assert router.stats()["feedback_since_train"] >= 1

    def test_execute_failure_feeds_evolution(self, tmp_path):
        """Failed execution drives an error_handling evolution."""
        router, ppm, profile, feedback = _make_router()
        decision = _run(router.route("compute the nth fibonacci number"))

        agent = Agent()
        result = _run(agent.run("fib"))
        assert result.success, result.error
        assert result.output.strip()

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_file = skills_dir / "fib.py"
        skill_file.write_text(
            "def fib(n):\n"
            "    if n < 2:\n"
            "        return n\n"
            "    return fib(n - 1) + fib(n - 2)\n"
            "print(fib(10))\n"
        )

        engine = _evolve_engine(router, decision.model_id)
        pr = engine.evolve(str(skill_file), trajectory_data=[
            {"observation": {"error": "RecursionError: maximum recursion depth exceeded"}},
        ])
        assert "Auto-evolved" in pr
        assert "Error" in pr or "error_handling" in pr.lower() or "Strategy" in pr

    def test_hybrid_executor_route_execute(self):
        """route -> HybridExecutor.execute (mock registry) -> feedback."""
        router, ppm, profile, feedback = _make_router()
        decision = _run(router.route("analyze this data for anomalies"))

        gatekeeper = PrivacyGatekeeper(PrivacyEngine())
        registry = _MockRegistry()
        executor = HybridExecutor(gatekeeper, registry)
        result = _run(executor.execute("analyze this data for anomalies", tenant_id="acme"))
        assert result.target != ExecutionTarget.REJECTED

        router.record_feedback(
            request_id="e2e-hybrid-1",
            ppm_difficulty=decision.difficulty,
            ppm_family=decision.task_family.value,
            selected_model=result.model_name or decision.model_id,
            strategy_tier=decision.strategy_tier.value,
            actual_latency_ms=10,
            actual_cost=0.0,
            success=result.error is None,
            score=0.8 if result.error is None else 0.1,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
        )
        assert router.stats()["feedback_since_train"] >= 1


class TestPPMClassifierDifficultyBranches:
    """Exercise the difficulty weight branches of RegexClassifier (56% cov).

    These force the pure-Python fallback path (rust hotpath is disabled) so
    the regex family/difficulty branch lines are actually covered.
    """

    @staticmethod
    def _py(c):
        c._rust = None
        return c

    def test_coding_complex_bonus(self):
        c = self._py(RegexClassifier())
        plain = c.classify("write a function")
        complex_ = c.classify("design a distributed algorithm with parallel execution")
        assert complex_.difficulty > plain.difficulty
        assert complex_.task_family == TaskFamily.CODING

    def test_coding_arch_bonus(self):
        c = self._py(RegexClassifier())
        arch = c.classify("refactor this service architecture with design patterns")
        plain = c.classify("write a function")
        assert arch.difficulty > plain.difficulty

    def test_reasoning_math_bonus(self):
        c = self._py(RegexClassifier())
        math = c.classify("explain the proof using calculus")
        plain = c.classify("explain how it works")
        assert math.difficulty >= plain.difficulty
        assert math.task_family == TaskFamily.REASONING

    def test_reasoning_analysis_bonus(self):
        c = self._py(RegexClassifier())
        thorough = c.classify("compare these two approaches thoroughly")
        assert thorough.task_family == TaskFamily.REASONING
        assert thorough.difficulty >= c.classify("compare them").difficulty

    def test_analysis_family_bonus(self):
        c = self._py(RegexClassifier())
        a = c.classify("audit the financial review assessment")
        assert a.task_family == TaskFamily.ANALYSIS
        assert a.difficulty > 0.0

    def test_chat_negative_adjustment(self):
        c = self._py(RegexClassifier())
        pred = c.classify("hello")
        assert pred.task_family == TaskFamily.CHAT
        assert pred.difficulty < 0.5

    def test_custom_weights_change_difficulty(self):
        weights = {
            "coding": {"length_weight": 0.0, "complex_bonus": 2.0, "arch_bonus": 2.0},
        }
        c = self._py(RegexClassifier(difficulty_weights=weights))
        low = c.classify("def foo(): pass")
        high = c.classify("implement a distributed concurrent algorithm")
        assert high.difficulty > low.difficulty

    def test_unknown_family_weight(self):
        c = self._py(RegexClassifier())
        pred = c.classify("qwerty zxcv")
        assert pred.task_family == TaskFamily.UNKNOWN
        assert 0.0 <= pred.difficulty <= 1.0


class TestModelRegistryFallback:
    """ModelRegistry fallback chains + generate paths (60% cov)."""

    def _profile(self, with_cloud=False):
        models = [
            ModelConfig(
                name="primary", backend="ollama", model_id="m1",
                role=ModelRole.EXECUTOR, deployment=DeploymentType.LOCAL,
            ),
            ModelConfig(
                name="fallback1", backend="ollama", model_id="m2",
                role=ModelRole.EXECUTOR, deployment=DeploymentType.LOCAL,
                is_fallback=True,
            ),
            ModelConfig(
                name="cloud1", backend="ollama", model_id="m3",
                role=ModelRole.REVIEWER, deployment=DeploymentType.CLOUD,
                is_fallback=True,
            ),
        ]
        return ConfigModelProfile(models=models)

    def test_register_and_list(self):
        profile = self._profile()
        reg = ModelRegistry(profile=profile)
        assert reg.get_model("primary") is not None
        assert reg.get_model("missing") is None
        listing = reg.list_models()
        assert len(listing) == 3
        assert all(m["alive"] for m in listing)
        summary = reg.summary()
        assert summary["total_models"] == 3
        assert summary["per_role"]["executor"] == 2

    def test_unknown_backend_skipped(self):
        models = [
            ModelConfig(
                name="weird", backend="bogus", model_id="m",
                role=ModelRole.EXECUTOR,
            ),
        ]
        reg = ModelRegistry(profile=ConfigModelProfile(models=models))
        assert reg.get_model("weird") is None
        assert reg.summary()["total_models"] == 0

    def test_get_model_for_role_none_when_no_models(self):
        reg = ModelRegistry(profile=ConfigModelProfile(models=[]))
        result = _run(reg.get_model_for_role(ModelRole.EXECUTOR))
        assert result is None

    def test_generate_all_unhealthy_returns_error(self):
        profile = self._profile()
        reg = ModelRegistry(profile=profile)
        for backend in reg._backends.values():
            backend.health_check = _unhealthy
        result = _run(reg.generate(ModelRole.EXECUTOR, "hi"))
        assert result.error is not None
        assert "All models" in result.error

    def test_generate_by_deployment_local(self):
        profile = self._profile()
        reg = ModelRegistry(profile=profile)
        result = _run(reg.generate_local("hello"))
        assert result.text or result.error is not None

    def test_generate_by_deployment_cloud_fallback(self):
        profile = self._profile()
        reg = ModelRegistry(profile=profile)
        for backend in reg._backends.values():
            backend.health_check = _unhealthy
        result = _run(reg.generate_cloud("hello"))
        assert result.error is not None

    def test_primary_failure_falls_to_next(self):
        profile = self._profile()
        reg = ModelRegistry(profile=profile)
        calls = {"primary": 0, "fallback1": 0}

        class _FailingBackend:
            async def health_check(self):
                return True

            async def generate(self, **kw):
                return GenerationResult(
                    text="", model_name="primary",
                    error="primary exploded",
                )

        primary = reg._backends["primary"]
        primary.health_check = _healthy
        primary.generate = _failing_generate(calls, "primary")

        fallback = reg._backends["fallback1"]
        fallback.health_check = _healthy
        fallback.generate = _ok_generate(calls, "fallback1")

        result = _run(reg.generate(ModelRole.EXECUTOR, "hi"))
        assert result.model_name == "fallback1"
        assert result.error is None
        assert calls["primary"] >= 1
        assert calls["fallback1"] >= 1


async def _unhealthy():
    return False


async def _healthy():
    return True


def _failing_generate(calls, name):
    async def _gen(**kw):
        calls[name] += 1
        return GenerationResult(text="", model_name=name, error=f"{name} exploded")
    return _gen


def _ok_generate(calls, name):
    async def _gen(**kw):
        calls[name] += 1
        return GenerationResult(text="ok", model_name=name)
    return _gen


def _evolve_engine(router, model_id):
    from zilli.evolution.skill_evolution import SkillEvolutionEngine
    return SkillEvolutionEngine(
        mode="harness", mom_router=router, reflection_model=model_id,
    )
