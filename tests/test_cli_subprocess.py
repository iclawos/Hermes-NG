import os
import subprocess
import sys

import pytest

CLI = [sys.executable, "-m", "zilli.cli"]

_run_cli_env = os.environ.copy()


@pytest.fixture(autouse=True)
def _isolate_budget(tmp_path):
    """Never touch the real ~/.zilli_budget.json during subprocess CLI tests."""
    global _run_cli_env
    _run_cli_env = dict(os.environ, ZILLI_BUDGET_FILE=str(tmp_path / "budget.json"))
    yield _run_cli_env


def _run_cli(*args, timeout=60):
    return subprocess.run(
        CLI + list(args),
        capture_output=True, text=True, timeout=timeout,
        env=_run_cli_env,
    )


class TestCLIBasics:
    def test_version(self):
        r = _run_cli("--version")
        assert r.returncode == 0
        assert "1.0.0" in r.stdout

    def test_no_args_shows_help(self):
        r = _run_cli()
        assert "zilli" in r.stdout.lower() or "usage" in r.stdout.lower()

    def test_list_tasks(self):
        r = _run_cli("list-tasks")
        assert r.returncode == 0
        assert "f5_memory_injection" in r.stdout

    def test_list_basic(self):
        r = _run_cli("list-basic")
        assert r.returncode == 0

    def test_list_benchmark(self):
        r = _run_cli("list-benchmark")
        assert r.returncode == 0
        assert "financial_analysis_long" in r.stdout

    def test_sandbox_test(self):
        r = _run_cli("sandbox-test")
        assert r.returncode == 0
        assert "PASSED" in r.stdout

    def test_ppm_stats(self):
        r = _run_cli("ppm", "stats")
        assert r.returncode == 0
        assert "cache_size" in r.stdout
        assert "difficulty_weights" in r.stdout

    def test_ppm_train_model_missing_records(self):
        r = _run_cli("ppm", "train-model", "--records", "/nonexistent/x.json")
        assert "not found" in r.stdout.lower()

    def test_cost_status(self):
        r = _run_cli("cost", "status")
        assert r.returncode == 0
        assert "Budget" in r.stdout

    def test_cost_reset(self):
        r = _run_cli("cost", "reset-month")
        assert r.returncode == 0
        assert "reset" in r.stdout.lower()

    def test_models_list(self):
        r = _run_cli("models", "list")
        assert r.returncode == 0

    def test_industry_list(self):
        r = _run_cli("industry", "list")
        assert r.returncode == 0

    def test_evaluate_single_task(self):
        r = _run_cli("evaluate", "f5_memory_injection", timeout=120)
        assert r.returncode == 0

    def test_train_dry(self):
        r = _run_cli("train", timeout=120)
        assert r.returncode == 0
        assert "Epoch" in r.stdout

    def test_distill_small(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            r = _run_cli("distill", "--samples", "10", "--log-dir", tmp, timeout=120)
            assert r.returncode == 0
            assert "loss=" in r.stdout

    def test_unknowns_summary(self):
        import tempfile
        r = subprocess.run(
            CLI + ["unknowns", "summary"],
            capture_output=True, text=True, timeout=60,
            cwd=tempfile.mkdtemp(),
        )
        assert r.returncode == 0
        assert "Unknowns" in r.stdout

    def test_audit_export(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "report.json")
            r = _run_cli("audit", "export", "--framework", "gdpr",
                         "--start", "2026-01-01", "--end", "2026-12-31",
                         "--output", out, "--audit-dir", tmp)
            assert r.returncode == 0
            assert Path(out).exists()
