"""SWEAgent 边界覆盖。

覆盖：sandbox 启用的容器初始化/清理、verbose 分支、
_narrow_scope、_grep 异常吞掉、_read_file 回退、
_AlwaysTrigger、_make_reproduce_verifier、_propose_fix 生成。
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from zilli.models.base import GenerationResult
from zilli.swe.agent import (
    SWEAgent,
    SWEConfig,
    _AlwaysTrigger,
    _make_reproduce_verifier,
)
from zilli.swe.context import CodeContext, ExploreResult


def _run(coro):
    return asyncio.run(coro)


class TestAlwaysTrigger:
    def test_wait_returns_false(self):
        assert _run(_AlwaysTrigger().wait()) is False

    def test_reset(self):
        assert _run(_AlwaysTrigger().reset()) is None


class TestMakeReproduceVerifier:
    def test_returns_verifier(self):
        v = _make_reproduce_verifier("/tmp", "true")
        assert v._command == "true"
        assert v._cwd == "/tmp"


class TestSWEEdges:
    @pytest.mark.asyncio
    async def test_run_with_sandbox(self, tmp_path, monkeypatch):
        sandbox = AsyncMock()
        sandbox.ensure_container.return_value = "cid"
        sandbox.cleanup.return_value = None
        cfg = SWEConfig(max_iterations=1, sandbox_enabled=True, test_command="true")
        agent = SWEAgent(cfg, sandbox=sandbox)
        # LoopRunner 会跑 verifier，但 patch 为空时 success=True 仍返回
        await agent.run("fix it", str(tmp_path))
        sandbox.ensure_container.assert_awaited_once()
        sandbox.cleanup.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_verbose_narrow_scope(self, tmp_path):
        agent = SWEAgent(SWEConfig(verbose=True))
        ctx = CodeContext(issue="fix", repo_path=tmp_path)
        agent._context = ctx
        out = agent._narrow_scope("fix", {}, "evidence text here")
        assert out == "fix"
        assert ctx.test_output == "evidence text here"

    @pytest.mark.asyncio
    async def test_fix_attempt_no_context(self):
        agent = SWEAgent(SWEConfig())
        assert await agent._fix_attempt("issue") == {"error": "No context"}

    @pytest.mark.asyncio
    async def test_grep_timeout_is_swallowed(self, monkeypatch):
        async def fake_exec(*args, **kwargs):
            raise asyncio.TimeoutError("grep hung")

        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
        agent = SWEAgent(SWEConfig())
        result = await agent._grep(Path("/tmp"), "somekeyword", "context")
        assert result == []

    @pytest.mark.asyncio
    async def test_read_file_oserror_fallback(self, tmp_path):
        agent = SWEAgent(SWEConfig())
        assert await agent._read_file(tmp_path / "nope.py") == ""

    @pytest.mark.asyncio
    async def test_propose_fix_generates(self, tmp_path):
        mock_model = AsyncMock()
        mock_model.generate.return_value = GenerationResult(
            text="def new():\n    return 42\n",
            model_name="mock",
        )
        agent = SWEAgent(SWEConfig(), model_backend=mock_model)
        f = tmp_path / "main.py"
        f.write_text("def old():\n    pass\n")
        explore = ExploreResult(files=["main.py"], error_context="")
        diagnosis = "Fix the logic"
        patch = await agent._propose_fix(explore, diagnosis, CodeContext(
            issue="fix", repo_path=tmp_path, explored_files={"main.py"},
        ))
        assert patch.total_changes == 2

    @pytest.mark.asyncio
    async def test_fix_attempt_applies_patch_verbose(self, tmp_path, monkeypatch):
        mock_model = AsyncMock()
        mock_model.generate.return_value = GenerationResult(
            text="def new():\n    return 42\n",
            model_name="mock",
        )
        agent = SWEAgent(SWEConfig(verbose=True), model_backend=mock_model)
        f = tmp_path / "main.py"
        f.write_text("def old():\n    pass\n")
        ctx = CodeContext(issue="fix", repo_path=tmp_path)
        ctx.test_output = ""
        agent._context = ctx
        # 直接调用 _fix_attempt，patch 会 apply 到 repo
        await agent._fix_attempt("fix")
        assert (tmp_path / "main.py").read_text() == "def new():\n    return 42"
