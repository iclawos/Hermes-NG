from __future__ import annotations

import json
from pathlib import Path

from zilli.evolution import SkillEvolutionEngine
from zilli.evolution.diversity import DiversityController


def test_cli_integration_single_strategy(tmp_path: Path):
    """Simulate CLI workflow: load trajectories, evolve skill files, print PRs."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_file = skills_dir / "test_skill.py"
    skill_file.write_text("def hello():\n    \"\"\"Greet.\"\"\"\n    pass\n")

    traj_dir = tmp_path / "trajectories"
    traj_dir.mkdir()
    (traj_dir / "run1.json").write_text(json.dumps([
        {"observation": {"error": "TypeError: expected str"}},
        {"observation": {"error": ""}},
    ]))

    engine = SkillEvolutionEngine()
    pr = engine.evolve(str(skill_file), trajectory_data=[
        {"observation": {"error": "TypeError"}},
    ])
    assert "Auto-evolved" in pr
    assert "Strategy:" in pr


def test_cli_integration_multi_strategy(tmp_path: Path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_file = skills_dir / "multi.py"
    skill_file.write_text("def process():\n    return 42\n")

    traj_dir = tmp_path / "trajectories"
    traj_dir.mkdir()
    (traj_dir / "run.json").write_text(json.dumps([
        {"observation": {"error": "KeyError"}},
    ]))

    engine = SkillEvolutionEngine(
        diversity_controller=DiversityController(
            population_size=20, novelty_threshold=0.2,
        ),
    )
    prs = engine.evolve_multi_strategy(str(skill_file), trajectory_data=[
        {"observation": {"error": "KeyError"}},
    ])
    assert len(prs) == 4
    assert any("Auto-evolved" in p for p in prs)


def test_cli_integration_markdown_skill(tmp_path: Path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_file = skills_dir / "prompt.md"
    skill_file.write_text("# My Skill\n\n```python\ndef run():\n    pass\n```\n")

    engine = SkillEvolutionEngine()
    pr = engine.evolve(str(skill_file), trajectory_data=[])
    assert "Auto-evolved" in pr


def test_cli_integration_diversity_rejection(tmp_path: Path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_file = skills_dir / "dup.py"
    skill_file.write_text("def fn():\n    return 1\n")

    dc = DiversityController(population_size=10, novelty_threshold=0.9)
    dc.add_entry("existing", "def fn():\n    return 1\n", score=1.0)

    engine = SkillEvolutionEngine(diversity_controller=dc)
    pr = engine.evolve(str(skill_file), trajectory_data=[])
    assert "Diversity Rejected" in pr
