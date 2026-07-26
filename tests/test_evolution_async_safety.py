import asyncio
from pathlib import Path

from zilli.evolution.skill_evolution import SkillEvolutionEngine


class _FakeDecision:
    model_id = "fake-model"


class _FakeMOMRouter:
    async def route(self, text: str) -> _FakeDecision:
        return _FakeDecision()

    def record_feedback(self, **kwargs):
        pass


def _make_skill(tmp_path: Path) -> str:
    skill = tmp_path / "skill_a.py"
    skill.write_text("def run():\n    return 1\n")
    return str(skill)


class TestEvolveAsyncContextSafety:
    def test_evolve_in_async_context_no_deadlock(self, tmp_path):
        """evolve() with harness mode inside a running loop must not hang.

        Regression: previously used run_coroutine_threadsafe().result() on the
        loop thread, which deadlocked until timeout.
        """
        engine = SkillEvolutionEngine(mode="harness", mom_router=_FakeMOMRouter())
        skill = _make_skill(tmp_path)

        async def run():
            return await asyncio.wait_for(
                asyncio.to_thread(engine.evolve, skill, []),
                timeout=10.0,
            )

        # evolve in a worker thread has no running loop -> asyncio.run path
        pr = asyncio.run(run())
        assert isinstance(pr, str)

    def test_evolve_on_loop_thread_no_deadlock(self, tmp_path):
        """Calling sync evolve() directly on the loop thread must skip MOM
        routing with a warning instead of deadlocking."""
        engine = SkillEvolutionEngine(mode="harness", mom_router=_FakeMOMRouter())
        skill = _make_skill(tmp_path)

        async def run():
            return engine.evolve(skill, [])

        # Direct call on loop thread: MOM routing is skipped (warning logged),
        # so this completes immediately without awaiting the loop.
        pr = asyncio.run(asyncio.wait_for(run(), timeout=10.0))
        assert isinstance(pr, str)

    def test_route_reflection_in_async_context(self, tmp_path):
        """_route_reflection must fall back to cached model in async context."""
        engine = SkillEvolutionEngine(mode="harness", mom_router=_FakeMOMRouter())
        engine.reflection_model = "cached-model"

        async def run():
            return engine._route_reflection(["some error"])

        result = asyncio.run(asyncio.wait_for(run(), timeout=10.0))
        assert result == "cached-model"
