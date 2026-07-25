import asyncio

from zilli.hybrid.executor import HybridExecutor
from zilli.hybrid.gatekeeper import ExecutionTarget, PrivacyGatekeeper
from zilli.models.base import GenerationResult
from zilli.models.registry import ModelRegistry
from zilli.privacy.engine import PrivacyEngine


def _run(coro):
    return asyncio.run(coro)


class _MockRegistry(ModelRegistry):
    def __init__(self, local_text="local-ok", local_error=None, cloud_text="cloud-ok"):
        super().__init__()
        self._local_text = local_text
        self._local_error = local_error
        self._cloud_text = cloud_text
        self.profile.models = []

    async def generate_local(self, prompt, **kw):
        return GenerationResult(
            text=self._local_text, model_name="local-model",
            error=self._local_error,
        )

    async def generate_cloud(self, prompt, provider=None, **kw):
        return GenerationResult(text=self._cloud_text, model_name="cloud-model")


def _make(local_text="local-ok", local_error=None):
    engine = PrivacyEngine()
    gatekeeper = PrivacyGatekeeper(engine)
    registry = _MockRegistry(local_text=local_text, local_error=local_error)
    return HybridExecutor(gatekeeper, registry)


class TestHybridExecutor:
    def test_public_text_goes_local(self):
        ex = _make(local_text="local-ok")
        result = _run(ex.execute("hello world", tenant_id="default"))
        assert result.text == "local-ok"
        assert result.target in (ExecutionTarget.LOCAL, ExecutionTarget.LOCAL_WITH_CLOUD_FALLBACK)
        assert result.error is None

    def test_local_failure_falls_back_to_cloud(self):
        ex = _make(local_text="", local_error="connection refused")
        result = _run(ex.execute("hello world", tenant_id="default"))
        if result.target == ExecutionTarget.LOCAL_WITH_CLOUD_FALLBACK:
            assert result.text == "cloud-ok"

    def test_restricted_data_stays_local(self):
        ex = _make(local_text="safe")
        result = _run(ex.execute("my SSN is 123-45-6789", tenant_id="default"))
        assert result.target in (ExecutionTarget.LOCAL, ExecutionTarget.REJECTED)
        if result.target == ExecutionTarget.LOCAL:
            assert result.text == "safe"

    def test_result_contains_verdict(self):
        ex = _make()
        result = _run(ex.execute("test input"))
        assert result.verdict is not None
        assert isinstance(result.warnings, list)


class TestGatekeeperDecide:
    def test_public_allowed(self):
        gk = PrivacyGatekeeper(PrivacyEngine())
        d = gk.decide("hello", tenant_id="default")
        assert d.target != ExecutionTarget.REJECTED

    def test_decision_has_reason(self):
        gk = PrivacyGatekeeper(PrivacyEngine())
        d = gk.decide("hello world", tenant_id="default")
        assert d.reason
