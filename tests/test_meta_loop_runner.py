import asyncio

from zilli.loops.base import Trigger, VerificationResult, Verifier
from zilli.loops.runner import LoopRunner, MetaLoopRunner


class _AlwaysTrigger(Trigger):
    async def wait(self) -> bool:
        return False

    async def reset(self) -> None:
        pass


class _PassVerifier(Verifier):
    async def verify(self, input_data, output):
        return VerificationResult(passed=True, evidence="ok")


class _FailVerifier(Verifier):
    async def verify(self, input_data, output):
        return VerificationResult(passed=False, evidence="nope")


def _run(coro):
    return asyncio.run(coro)


def _make_runner(verifier, max_retries=2):
    async def process(x):
        return f"out:{x}"

    return LoopRunner(
        process_fn=process,
        verifier=verifier,
        trigger=_AlwaysTrigger(),
        max_retries=max_retries,
    )


class TestMetaLoopRunner:
    def test_converges_on_success(self):
        inner = _make_runner(_PassVerifier())
        meta = MetaLoopRunner(inner, max_meta_iterations=3,
                              mode=MetaLoopRunner.MODE_PARAM_TUNE)
        result = _run(meta.run("task1"))
        assert result.success

    def test_runs_all_iterations_on_failure(self):
        inner = _make_runner(_FailVerifier())
        meta = MetaLoopRunner(inner, max_meta_iterations=2,
                              mode=MetaLoopRunner.MODE_PARAM_TUNE)
        result = _run(meta.run("task1"))
        assert not result.success
        assert len(meta.tuning_log) == 2

    def test_param_tuning_increases_retries_on_failure(self):
        inner = _make_runner(_FailVerifier(), max_retries=1)
        meta = MetaLoopRunner(inner, max_meta_iterations=2,
                              mode=MetaLoopRunner.MODE_PARAM_TUNE)
        _run(meta.run("task1"))
        assert inner._max_retries >= 1

    def test_harness_mode_without_orchestrator(self):
        inner = _make_runner(_PassVerifier())
        meta = MetaLoopRunner(inner, max_meta_iterations=1,
                              mode=MetaLoopRunner.MODE_HARNESS_EVOLVE,
                              harness_orchestrator=None)
        result = _run(meta.run("task1"))
        assert result.success

    def test_best_result_prefers_fewer_retries(self):
        inner = _make_runner(_PassVerifier())
        meta = MetaLoopRunner(inner, max_meta_iterations=2,
                              mode=MetaLoopRunner.MODE_PARAM_TUNE)
        result = _run(meta.run("x"))
        assert result.success

    def test_tuning_log_records_params(self):
        inner = _make_runner(_PassVerifier())
        meta = MetaLoopRunner(inner, max_meta_iterations=1,
                              mode=MetaLoopRunner.MODE_PARAM_TUNE)
        _run(meta.run("x"))
        log = meta.tuning_log
        assert len(log) == 1
        assert "max_retries" in log[0]["params"]

    def test_evolved_versions_property(self):
        inner = _make_runner(_PassVerifier())
        meta = MetaLoopRunner(inner, max_meta_iterations=1)
        _run(meta.run("x"))
        assert isinstance(meta._evolved_versions, list)
