import asyncio
import json

from zilli.models.ollama import OllamaBackend
from zilli.models.vllm import VLLMBackend
from zilli.models.llamacpp import LlamaCppBackend


class _FakeResponse:
    def __init__(self, status=200, data=None, text=""):
        self.status_code = status
        self._data = data or {}
        self.text = text

    def json(self):
        return self._data


class _FakeClient:
    def __init__(self, response=None, raise_exc=None):
        self._response = response
        self._raise = raise_exc
        self.requests = []

    async def post(self, url, json=None, timeout=None, **kw):
        self.requests.append((url, json))
        if self._raise:
            raise self._raise
        return self._response

    async def get(self, url, **kw):
        self.requests.append((url, None))
        if self._raise:
            raise self._raise
        return self._response


def _run(coro):
    return asyncio.run(coro)


class TestOllamaGenerate:
    def test_success(self):
        b = OllamaBackend(name="t", model_id="qwen3:7b")
        resp = _FakeResponse(200, {"response": "hello world", "prompt_eval_count": 5, "eval_count": 3})
        b._client = _FakeClient(resp)
        result = _run(b.generate("hi", max_tokens=100, temperature=0.5))
        assert result.text == "hello world"
        assert result.tokens_in == 5
        assert result.tokens_out == 3
        assert result.error is None
        url, payload = b._client.requests[0]
        assert url.endswith("/api/generate")
        assert payload["model"] == "qwen3:7b"
        assert payload["options"]["num_predict"] == 100
        assert payload["options"]["temperature"] == 0.5
        assert payload["stream"] is False

    def test_http_error(self):
        b = OllamaBackend(name="t", model_id="m")
        b._client = _FakeClient(_FakeResponse(500, text="server boom"))
        result = _run(b.generate("hi"))
        assert result.error is not None
        assert "500" in result.error

    def test_exception(self):
        b = OllamaBackend(name="t", model_id="m")
        b._client = _FakeClient(raise_exc=ConnectionError("refused"))
        result = _run(b.generate("hi"))
        assert "refused" in result.error

    def test_health_ok(self):
        b = OllamaBackend(name="t", model_id="m")
        b._client = _FakeClient(_FakeResponse(200, {"models": [{"name": "m"}]}))
        assert _run(b.health_check()) is True

    def test_health_fail(self):
        b = OllamaBackend(name="t", model_id="m")
        b._client = _FakeClient(raise_exc=ConnectionError("down"))
        assert _run(b.health_check()) is False


class TestOllamaChat:
    def test_chat_success(self):
        b = OllamaBackend(name="t", model_id="m")
        resp = _FakeResponse(200, {
            "message": {"content": "chat reply"},
            "prompt_eval_count": 2, "eval_count": 4,
        })
        b._client = _FakeClient(resp)
        result = _run(b.generate_chat([{"role": "user", "content": "hi"}]))
        assert result.text == "chat reply"
        url, payload = b._client.requests[0]
        assert url.endswith("/api/chat")
        assert payload["messages"][0]["content"] == "hi"


class TestVLLMGenerate:
    def test_success(self):
        b = VLLMBackend(name="t", model_id="qwen2:7b")
        resp = _FakeResponse(200, {
            "choices": [{"text": "vllm output"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        })
        b._client = _FakeClient(resp)
        result = _run(b.generate("prompt"))
        assert result.text == "vllm output"
        assert result.tokens_in == 10
        assert result.tokens_out == 5

    def test_http_error(self):
        b = VLLMBackend(name="t", model_id="m")
        b._client = _FakeClient(_FakeResponse(503, text="busy"))
        result = _run(b.generate("x"))
        assert "503" in result.error

    def test_health(self):
        b = VLLMBackend(name="t", model_id="m")
        b._client = _FakeClient(_FakeResponse(200, {"data": [{"id": "m"}]}))
        assert _run(b.health_check()) is True


class TestLlamaCppGenerate:
    def test_success(self):
        b = LlamaCppBackend(name="t", model_id="llama3:8b")
        resp = _FakeResponse(200, {"content": "llama says hi"})
        b._client = _FakeClient(resp)
        result = _run(b.generate("hello"))
        assert result.text == "llama says hi"

    def test_http_error(self):
        b = LlamaCppBackend(name="t", model_id="m")
        b._client = _FakeClient(_FakeResponse(400, text="bad request"))
        result = _run(b.generate("x"))
        assert result.error is not None

    def test_health(self):
        b = LlamaCppBackend(name="t", model_id="m")
        b._client = _FakeClient(_FakeResponse(200, {"status": "ok"}))
        assert _run(b.health_check()) is True
