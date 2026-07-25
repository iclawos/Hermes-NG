import sys

import pytest

from zilli.cli import main


def _argv(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["zilli"] + list(args))


class TestCLIInProcess:
    def test_list_tasks(self, monkeypatch, capsys):
        _argv(monkeypatch, "list-tasks")
        main()
        out = capsys.readouterr().out
        assert "f5_memory_injection" in out

    def test_list_basic(self, monkeypatch, capsys):
        _argv(monkeypatch, "list-basic")
        main()
        assert capsys.readouterr().out

    def test_list_benchmark(self, monkeypatch, capsys):
        _argv(monkeypatch, "list-benchmark")
        main()
        assert "financial_analysis_long" in capsys.readouterr().out

    def test_sandbox_test(self, monkeypatch, capsys):
        _argv(monkeypatch, "sandbox-test")
        main()
        assert "PASSED" in capsys.readouterr().out

    def test_ppm_stats(self, monkeypatch, capsys):
        _argv(monkeypatch, "ppm", "stats")
        main()
        assert "cache_size" in capsys.readouterr().out

    def test_ppm_train_missing_records(self, monkeypatch, capsys):
        _argv(monkeypatch, "ppm", "train-model", "--records", "/nonexistent/x.json")
        main()
        assert "not found" in capsys.readouterr().out.lower()

    def test_cost_status(self, monkeypatch, capsys):
        _argv(monkeypatch, "cost", "status")
        main()
        assert "Budget" in capsys.readouterr().out

    def test_cost_reset(self, monkeypatch, capsys):
        _argv(monkeypatch, "cost", "reset-month")
        main()
        assert "reset" in capsys.readouterr().out.lower()

    def test_models_list(self, monkeypatch, capsys):
        _argv(monkeypatch, "models", "list")
        main()
        capsys.readouterr()

    def test_industry_list(self, monkeypatch, capsys):
        _argv(monkeypatch, "industry", "list")
        main()
        capsys.readouterr()

    def test_evaluate(self, monkeypatch, capsys):
        _argv(monkeypatch, "evaluate", "f5_memory_injection")
        main()
        assert "score=" in capsys.readouterr().out

    def test_train(self, monkeypatch, capsys):
        _argv(monkeypatch, "train")
        main()
        assert "Epoch" in capsys.readouterr().out

    def test_distill(self, monkeypatch, capsys, tmp_path):
        _argv(monkeypatch, "distill", "--samples", "10", "--log-dir", str(tmp_path))
        main()
        assert "loss=" in capsys.readouterr().out

    def test_unknowns_summary(self, monkeypatch, capsys, tmp_path, monkeypatch_dir=None):
        _argv(monkeypatch, "unknowns", "summary")
        main()
        assert "Unknowns" in capsys.readouterr().out

    def test_audit_export(self, monkeypatch, capsys, tmp_path):
        out = tmp_path / "report.json"
        _argv(monkeypatch, "audit", "export", "--framework", "gdpr",
              "--start", "2026-01-01", "--end", "2026-12-31",
              "--output", str(out), "--audit-dir", str(tmp_path))
        main()
        assert out.exists()

    def test_route_help_on_bad_command(self, monkeypatch, capsys):
        _argv(monkeypatch, "--version")
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
