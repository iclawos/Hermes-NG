import json
import sys
from pathlib import Path

from zilli.evolution.cli import (
    _collect_skill_files,
    _load_trajectories,
    _print_summary,
    _write_json_report,
    main,
)


class TestLoadTrajectories:
    def test_loads_list_and_dict(self, tmp_path):
        (tmp_path / "a.json").write_text(json.dumps([{"r": 1}, {"r": 2}]))
        (tmp_path / "b.json").write_text(json.dumps({"r": 3}))
        result = _load_trajectories(tmp_path)
        assert len(result) == 3

    def test_bad_json_warns_continues(self, tmp_path, capsys):
        (tmp_path / "bad.json").write_text("oops{")
        (tmp_path / "ok.json").write_text(json.dumps({"r": 1}))
        result = _load_trajectories(tmp_path)
        assert len(result) == 1
        assert "skipping" in capsys.readouterr().err

    def test_empty_dir(self, tmp_path):
        assert _load_trajectories(tmp_path) == []


class TestCollectSkillFiles:
    def test_collects_py_and_md(self, tmp_path):
        (tmp_path / "skill_a.py").write_text("x = 1")
        (tmp_path / "skill_b.md").write_text("# doc")
        files = _collect_skill_files(tmp_path)
        assert len(files) == 2

    def test_skips_underscore_and_init(self, tmp_path):
        (tmp_path / "__init__.py").write_text("")
        (tmp_path / "_private.py").write_text("")
        (tmp_path / "public.py").write_text("")
        files = _collect_skill_files(tmp_path)
        assert len(files) == 1
        assert files[0].name == "public.py"

    def test_skips_directories(self, tmp_path):
        (tmp_path / "subdir.py").mkdir()
        files = _collect_skill_files(tmp_path)
        assert files == []


class TestPrintSummary:
    def test_prints_all_fields(self, capsys):
        summary = {
            "total_skills": 3, "accepted": 2, "rejected": 1,
            "diversity": {
                "population_size": 2, "pairwise_similarity": 0.42,
                "unique_functions": 7, "generation": 1, "rejected_count": 1,
            },
            "config": {"mode": "evolve", "multi_strategy": False},
        }
        _print_summary(summary)
        out = capsys.readouterr().out
        assert "Skills processed:    3" in out
        assert "0.420" in out
        assert "evolve" in out


class TestWriteJsonReport:
    def test_writes_file(self, tmp_path):
        out = str(tmp_path / "report.json")
        assert _write_json_report(out, {"a": 1}) is True
        assert json.loads(Path(out).read_text()) == {"a": 1}

    def test_bad_path_returns_false(self, capsys):
        assert _write_json_report("/nonexistent_dir_xyz/deep/report.json", {}) is False
        assert "Error" in capsys.readouterr().err


class TestEvolveCLIMain:
    def _setup(self, tmp_path, monkeypatch, extra_args=None):
        traj_dir = tmp_path / "trajs"
        skill_dir = tmp_path / "skills"
        traj_dir.mkdir()
        skill_dir.mkdir()
        (traj_dir / "t1.json").write_text(json.dumps([{"error": "boom", "reward": 0.1}]))
        (skill_dir / "skill_a.py").write_text("def run():\n    return 1\n")
        args = ["--input", str(traj_dir), "--target-skills", str(skill_dir)]
        if extra_args:
            args += extra_args
        monkeypatch.setattr(sys, "argv", ["zilli-evolve"] + args)
        return traj_dir, skill_dir

    def test_main_evolve_mode(self, tmp_path, monkeypatch, capsys):
        self._setup(tmp_path, monkeypatch)
        main()
        out = capsys.readouterr().out
        assert "Evolution Summary" in out

    def test_main_multi_strategy(self, tmp_path, monkeypatch, capsys):
        self._setup(tmp_path, monkeypatch, ["--multi-strategy"])
        main()
        out = capsys.readouterr().out
        assert "Evolution Summary" in out

    def test_main_with_output_report(self, tmp_path, monkeypatch):
        report = tmp_path / "out.json"
        self._setup(tmp_path, monkeypatch, ["--output", str(report)])
        main()
        data = json.loads(report.read_text())
        assert data["total_skills"] == 1

    def test_main_harness_mode(self, tmp_path, monkeypatch, capsys):
        self._setup(tmp_path, monkeypatch, ["--mode", "harness"])
        main()
        out = capsys.readouterr().out
        assert "Evolution Summary" in out

    def test_main_verbose(self, tmp_path, monkeypatch, capsys):
        self._setup(tmp_path, monkeypatch, ["--verbose"])
        main()
        capsys.readouterr()

    def test_main_quiet(self, tmp_path, monkeypatch, capsys):
        self._setup(tmp_path, monkeypatch, ["--quiet"])
        main()
        capsys.readouterr()

    def test_main_custom_threshold(self, tmp_path, monkeypatch, capsys):
        self._setup(tmp_path, monkeypatch, ["--diversity-threshold", "0.9"])
        main()
        capsys.readouterr()
