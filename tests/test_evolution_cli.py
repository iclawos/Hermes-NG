from __future__ import annotations

import json
from pathlib import Path

from zilli.evolution.cli import _collect_skill_files, _load_trajectories


def test_load_trajectories_empty_dir(tmp_path: Path):
    data = _load_trajectories(tmp_path)
    assert data == []


def test_load_trajectories_single(tmp_path: Path):
    f = tmp_path / "traj.json"
    f.write_text(json.dumps([{"step": 1}, {"step": 2}]))
    data = _load_trajectories(tmp_path)
    assert len(data) == 2


def test_load_trajectories_skips_bad_json(tmp_path: Path, capsys):
    f = tmp_path / "bad.json"
    f.write_text("not json")
    data = _load_trajectories(tmp_path)
    assert data == []
    captured = capsys.readouterr()
    assert "Warning" in captured.err


def test_collect_skill_files_finds_py_and_md(tmp_path: Path):
    (tmp_path / "foo.py").write_text("")
    (tmp_path / "bar.md").write_text("")
    (tmp_path / "__init__.py").write_text("")
    (tmp_path / "_internal.py").write_text("")
    (tmp_path / "readme.md").write_text("")
    files = _collect_skill_files(tmp_path)
    names = [f.name for f in files]
    assert "foo.py" in names
    assert "bar.md" in names
    assert "__init__.py" not in names
    assert "_internal.py" not in names


def test_collect_skill_files_empty_dir(tmp_path: Path):
    assert _collect_skill_files(tmp_path) == []


def test_collect_skill_files_sorts(tmp_path: Path):
    (tmp_path / "z.py").write_text("")
    (tmp_path / "a.py").write_text("")
    (tmp_path / "m.py").write_text("")
    names = [f.name for f in _collect_skill_files(tmp_path)]
    assert names == ["a.py", "m.py", "z.py"]
