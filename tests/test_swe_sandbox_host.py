import asyncio

from zilli.swe.sandbox import Sandbox, SandboxConfig


def _run(coro):
    return asyncio.run(coro)


class TestSandboxHostMode:
    def test_ensure_container_no_docker(self, tmp_path):
        sb = Sandbox(SandboxConfig())
        cid = _run(sb.ensure_container(tmp_path))
        assert cid == ""
        assert sb._container_id is None

    def test_run_command_success(self):
        sb = Sandbox()
        result = _run(sb.run_command("echo hello"))
        assert result.returncode == 0
        assert "hello" in result.stdout
        assert result.duration_ms >= 0

    def test_run_command_failure(self):
        sb = Sandbox()
        result = _run(sb.run_command("ls /nonexistent_path_xyz_abc"))
        assert result.returncode != 0

    def test_run_command_with_cwd(self, tmp_path):
        sb = Sandbox()
        result = _run(sb.run_command("pwd", cwd=str(tmp_path)))
        assert str(tmp_path) in result.stdout

    def test_run_command_shell_operators(self):
        sb = Sandbox()
        result = _run(sb.run_command("echo a && echo b"))
        assert "a" in result.stdout
        assert "b" in result.stdout

    def test_run_command_timeout(self):
        sb = Sandbox()
        result = _run(sb.run_command("sleep 5", timeout=0.2))
        assert result.returncode == -1
        assert "Timed out" in result.stderr

    def test_copy_no_container_is_noop(self, tmp_path):
        sb = Sandbox()
        f = tmp_path / "x.txt"
        f.write_text("data")
        _run(sb.copy_to(str(f), "/tmp/y"))
        _run(sb.copy_from("/tmp/y", str(tmp_path / "z.txt")))

    def test_cleanup(self):
        sb = Sandbox()
        _run(sb.cleanup())

    def test_config_defaults(self):
        cfg = SandboxConfig()
        assert cfg.image
        assert cfg.memory_limit
        assert cfg.workdir
