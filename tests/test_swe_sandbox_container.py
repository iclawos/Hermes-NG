"""Sandbox Docker 容器分支测试（mock 容器就绪状态）。

不依赖真实 docker 守护进程：把 HAS_DOCKER 置真并 mock _run_host /
run_command 的容器路径。
"""

import asyncio

from zilli.swe.sandbox import Sandbox


def _run(coro):
    return asyncio.run(coro)


def _async_ret(value=""):
    async def _f(cmd):
        return value
    return _f


def _async_ret_calls(calls):
    async def _f(cmd):
        calls.append(cmd)
        return ""
    return _f


def _async_raise(exc):
    async def _f(cmd):
        raise exc
    return _f


class TestSandboxContainerMode:
    def test_ensure_container_cached(self, monkeypatch, tmp_path):
        sb = Sandbox()
        sb._container_id = "abc123"
        assert _run(sb.ensure_container(tmp_path)) == "abc123"

    def test_ensure_container_docker_branch(self, monkeypatch, tmp_path):
        from zilli.swe import sandbox as sb_mod

        monkeypatch.setattr(sb_mod, "HAS_DOCKER", True)
        sb = Sandbox()
        sb._run_host = _async_ret("cont_xyz\n")
        cid = _run(sb.ensure_container(tmp_path))
        assert cid == "cont_xyz"
        assert sb._container_id == "cont_xyz"

    def test_run_command_container_branch(self, monkeypatch):
        class FakeProc:
            returncode = 0

            async def communicate(self):
                return (b"docker exec ran\n", b"")

        async def fake_exec(*args, **kwargs):
            return FakeProc()

        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
        sb = Sandbox()
        sb._container_id = "cid"
        result = _run(sb.run_command("echo hi"))
        assert result.returncode == 0
        assert "docker exec ran" in result.stdout

    def test_run_command_container_with_cwd(self, monkeypatch):
        class FakeProc:
            returncode = 0

            async def communicate(self):
                return (b"pwd out\n", b"")

        async def fake_exec(*args, **kwargs):
            return FakeProc()

        monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
        sb = Sandbox()
        sb._container_id = "cid"
        result = _run(sb.run_command("pwd", cwd="/repo/src"))
        assert result.returncode == 0
        assert "pwd out" in result.stdout

    def test_copy_to_container(self, monkeypatch, tmp_path):
        sb = Sandbox()
        sb._container_id = "cid"
        calls = []
        sb._run_host = _async_ret_calls(calls)
        f = tmp_path / "x.txt"
        f.write_text("d")
        _run(sb.copy_to(str(f), "/tmp/y"))
        assert calls, "docker cp should be called when container present"

    def test_copy_from_container(self, monkeypatch, tmp_path):
        sb = Sandbox()
        sb._container_id = "cid"
        calls = []
        sb._run_host = _async_ret_calls(calls)
        _run(sb.copy_from("/tmp/y", str(tmp_path / "z.txt")))
        assert calls, "docker cp should be called when container present"

    def test_cleanup_container_error(self, monkeypatch, tmp_path):
        sb = Sandbox()
        sb._container_id = "cid"
        sb._tmp_dir = tmp_path
        sb._run_host = _async_raise(RuntimeError("rm failed"))
        _run(sb.cleanup())
        assert sb._container_id is None

    def test_cleanup_container_success(self, monkeypatch, tmp_path):
        sb = Sandbox()
        sb._container_id = "cid"
        sb._tmp_dir = tmp_path
        sb._run_host = _async_ret("")
        _run(sb.cleanup())
        assert sb._container_id is None
        assert not tmp_path.exists()
