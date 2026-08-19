"""Model 后端 HTTP 路径测试（mock httpx）。

覆盖 Ollama / vLLM / llama.cpp 的 generate 成功/HTTP 错误/异常、
generate_stream 各分支、generate_chat、health_check 各分支。
"""

import asyncio
import json

from zilli.models.llamacpp import LlamaCppBackend
from zilli.models.ollama import OllamaBackend
from zilli.models.vllm import VLLMBackend


def _run(coro):
    return asyncio.run(coro)


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    def json(self):
        return self._json


class _FakeClient:
    def __init__(self, responses=None):
        self.posts = []
        self.gets = []
        self.streams = []
        self._responses = responses or {}

    async def post(self, url, json=None, timeout=None):
        self.posts.append((url, json))
        return self._responses.get("post", _FakeResponse())

    async def get(self, url, timeout=None):
        self.gets.append(url)
        return self._responses.get("get", _FakeResponse())


def _make_backend(cls):
    backend = cls("test", "test-model")
    client = _FakeClient()
    backend._client = client
    return backend, client


# ---------- Ollama ----------

class TestOllamaHTTP:
    def test_generate_success(self):
        b, c = _make_backend(OllamaBackend)
        c._responses["post"] = _FakeResponse(json_data={
            "response": "hello world", "prompt_eval_count": 5, "eval_count": 3,
        })
        r = _run(b.generate("hi"))
        assert r.text == "hello world"
        assert r.tokens_in == 5
        assert r.tokens_out == 3
        assert c.posts[0][0].endswith("/api/generate")

    def test_generate_http_error(self):
        b, c = _make_backend(OllamaBackend)
        c._responses["post"] = _FakeResponse(status_code=500, text="boom")
        r = _run(b.generate("hi"))
        assert r.error and "500" in r.error

    def test_generate_exception(self):
        b, c = _make_backend(OllamaBackend)
        async def boom(url, json=None, timeout=None):
            raise RuntimeError("network down")
        c.post = boom
        r = _run(b.generate("hi"))
        assert "network down" in r.error

    def test_generate_chat_success(self):
        b, c = _make_backend(OllamaBackend)
        c._responses["post"] = _FakeResponse(json_data={
            "message": {"content": "chat reply"}, "eval_count": 7,
        })
        r = _run(b.generate_chat([{"role": "user", "content": "q"}]))
        assert r.text == "chat reply"
        assert c.posts[0][0].endswith("/api/chat")

    def test_generate_chat_http_error(self):
        b, c = _make_backend(OllamaBackend)
        c._responses["post"] = _FakeResponse(status_code=503, text="unavailable")
        r = _run(b.generate_chat([{"role": "user", "content": "q"}]))
        assert r.error and "503" in r.error

    def test_health_check_ok(self):
        b, c = _make_backend(OllamaBackend)
        c._responses["get"] = _FakeResponse(json_data={
            "models": [{"name": "test-model"}, {"name": "other"}],
        })
        assert _run(b.health_check()) is True

    def test_health_check_model_missing(self):
        b, c = _make_backend(OllamaBackend)
        c._responses["get"] = _FakeResponse(json_data={"models": [{"name": "x"}]})
        assert _run(b.health_check()) is False

    def test_health_check_http_error(self):
        b, c = _make_backend(OllamaBackend)
        c._responses["get"] = _FakeResponse(status_code=500)
        assert _run(b.health_check()) is False


# ---------- vLLM ----------

class TestVLLMHTTP:
    def test_generate_success(self):
        b, c = _make_backend(VLLMBackend)
        c._responses["post"] = _FakeResponse(json_data={
            "choices": [{"text": "vllm out"}],
            "usage": {"prompt_tokens": 4, "completion_tokens": 2},
        })
        r = _run(b.generate("hi"))
        assert r.text == "vllm out"
        assert r.tokens_in == 4

    def test_generate_http_error(self):
        b, c = _make_backend(VLLMBackend)
        c._responses["post"] = _FakeResponse(status_code=429, text="rate limited")
        r = _run(b.generate("hi"))
        assert r.error and "429" in r.error

    def test_generate_exception(self):
        b, c = _make_backend(VLLMBackend)
        async def boom(url, json=None, timeout=None):
            raise RuntimeError("vllm down")
        c.post = boom
        r = _run(b.generate("hi"))
        assert "vllm down" in r.error

    def test_generate_chat_success(self):
        b, c = _make_backend(VLLMBackend)
        c._responses["post"] = _FakeResponse(json_data={
            "choices": [{"message": {"content": "chat out"}}],
            "usage": {"prompt_tokens": 2, "completion_tokens": 3},
        })
        r = _run(b.generate_chat([{"role": "user", "content": "q"}]))
        assert r.text == "chat out"

    def test_health_check_ok(self):
        b, c = _make_backend(VLLMBackend)
        c._responses["get"] = _FakeResponse(json_data={"data": [{"id": "test-model"}]})
        assert _run(b.health_check()) is True

    def test_health_check_missing(self):
        b, c = _make_backend(VLLMBackend)
        c._responses["get"] = _FakeResponse(json_data={"data": []})
        assert _run(b.health_check()) is False

    def test_health_check_error(self):
        b, c = _make_backend(VLLMBackend)
        async def boom(url, timeout=None):
            raise RuntimeError("health fail")
        c.get = boom
        assert _run(b.health_check()) is False


# ---------- llama.cpp ----------

class TestLlamaCppHTTP:
    def test_generate_success(self):
        b, c = _make_backend(LlamaCppBackend)
        c._responses["post"] = _FakeResponse(json_data={
            "content": "llama out", "tokens_evaluated": 3, "tokens_predicted": 1,
        })
        r = _run(b.generate("hi"))
        assert r.text == "llama out"
        assert r.tokens_in == 3

    def test_generate_http_error(self):
        b, c = _make_backend(LlamaCppBackend)
        c._responses["post"] = _FakeResponse(status_code=500, text="err")
        r = _run(b.generate("hi"))
        assert r.error and "500" in r.error

    def test_generate_exception(self):
        b, c = _make_backend(LlamaCppBackend)
        async def boom(url, json=None, timeout=None):
            raise RuntimeError("llama fail")
        c.post = boom
        r = _run(b.generate("hi"))
        assert "llama fail" in r.error

    def test_health_check_ok(self):
        b, c = _make_backend(LlamaCppBackend)
        c._responses["get"] = _FakeResponse(status_code=200)
        assert _run(b.health_check()) is True

    def test_health_check_error(self):
        b, c = _make_backend(LlamaCppBackend)
        c._responses["get"] = _FakeResponse(status_code=500)
        assert _run(b.health_check()) is False


# ---------- stream 分支（三后端共用 FakeStream） ----------

class _FakeStreamContext:
    def __init__(self, status_code, lines):
        self.status_code = status_code
        self._lines = lines
        self.response = _FakeResponse(status_code=status_code)
        self.response.aiter_lines = lambda: _ALines(list(lines))

    async def __aenter__(self):
        return self.response

    async def __aexit__(self, *a):
        return False


class _ALines:
    def __init__(self, lines):
        self._lines = lines

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._lines:
            raise StopAsyncIteration
        return self._lines.pop(0)


def _attach_stream(backend, status=200, lines=None):
    class _SC:
        def stream(self, method, url, json=None):
            return _FakeStreamContext(status, lines or [])
    client = _FakeClient()
    client.stream = _SC().stream
    backend._client = client
    return client


class TestStreams:
    def test_ollama_stream_ok(self):
        b = OllamaBackend("t", "m")
        _attach_stream(b, lines=['{"response": "hi"}', '{"response": "!"}', ""])
        chunks = [c for c in _run(_collect(b.generate_stream("x")))]
        assert chunks == ["hi", "!"]

    def test_ollama_stream_http_error(self):
        b = OllamaBackend("t", "m")
        _attach_stream(b, status=500)
        chunks = [c for c in _run(_collect(b.generate_stream("x")))]
        assert chunks == []

    def test_ollama_stream_json_error_skipped(self):
        b = OllamaBackend("t", "m")
        _attach_stream(b, lines=["not json", '{"response": "ok"}'])
        chunks = [c for c in _run(_collect(b.generate_stream("x")))]
        assert chunks == ["ok"]

    def test_vllm_stream_ok(self):
        b = VLLMBackend("t", "m")
        _attach_stream(b, lines=[
            "data: " + json.dumps({"choices": [{"text": "v"}]}),
            "data: [DONE]",
        ])
        chunks = [c for c in _run(_collect(b.generate_stream("x")))]
        assert chunks == ["v"]

    def test_vllm_stream_bad_delta_skipped(self):
        b = VLLMBackend("t", "m")
        _attach_stream(b, lines=[
            "data: not json",
            "data: " + json.dumps({"choices": [{"text": "z"}]}),
        ])
        chunks = [c for c in _run(_collect(b.generate_stream("x")))]
        assert chunks == ["z"]

    def test_llamacpp_stream_stop_break(self):
        b = LlamaCppBackend("t", "m")
        _attach_stream(b, lines=[
            '{"content": "a"}',
            '{"content": "b", "stop": true}',
            '{"content": "c"}',
        ])
        chunks = [c for c in _run(_collect(b.generate_stream("x")))]
        assert chunks == ["a", "b"]

    def test_llamacpp_stream_http_error(self):
        b = LlamaCppBackend("t", "m")
        _attach_stream(b, status=500)
        chunks = [c for c in _run(_collect(b.generate_stream("x")))]
        assert chunks == []


async def _collect(agen):
    out = []
    async for x in agen:
        out.append(x)
    return out
