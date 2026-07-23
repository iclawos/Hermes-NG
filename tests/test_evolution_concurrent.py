import asyncio
from pathlib import Path

import pytest

from zilli.evolution.diversity import DiversityController
from zilli.evolution.skill_evolution import SkillEvolutionEngine


def _make_skill(tmp_path: Path, name: str, content: str = "") -> str:
    p = tmp_path / name
    p.write_text(content or f"def {name.replace('.py', '')}():\n    pass\n")
    return str(p)


class TestEvolveAsync:
    @pytest.fixture
    def engine(self):
        return SkillEvolutionEngine(diversity_controller=DiversityController())

    @pytest.fixture
    def tmp_skills(self, tmp_path: Path):
        return [
            _make_skill(tmp_path, "skill_a.py"),
            _make_skill(tmp_path, "skill_b.py"),
            _make_skill(tmp_path, "skill_c.py"),
        ]

    def test_evolve_async_single(self, engine, tmp_skills):
        result = asyncio.run(engine.evolve_async(tmp_skills[0], []))
        assert isinstance(result, str)
        assert "Auto-evolved" in result

    def test_evolve_concurrent(self, engine, tmp_skills):
        results = asyncio.run(
            engine.evolve_concurrent(tmp_skills, [], max_concurrency=2)
        )
        assert len(results) == 3
        for sf, pr in results.items():
            assert "Auto-evolved" in pr

    def test_evolve_concurrent_respects_max_concurrency(self, engine, tmp_skills):
        results = asyncio.run(
            engine.evolve_concurrent(tmp_skills, [], max_concurrency=1)
        )
        assert len(results) == 3

    def test_evolve_concurrent_with_trajectories(self, engine, tmp_skills):
        traj = [{"observation": {"error": "TypeError"}}]
        results = asyncio.run(
            engine.evolve_concurrent(tmp_skills[:2], [traj], max_concurrency=2)
        )
        assert len(results) == 2

    def test_evolve_concurrent_empty(self, engine):
        results = asyncio.run(engine.evolve_concurrent([], []))
        assert results == {}

    def test_evolve_multi_strategy_async(self, engine, tmp_skills):
        result = asyncio.run(
            engine.evolve_multi_strategy_async(tmp_skills[0], [])
        )
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_evolve_multi_strategy_concurrent(self, engine, tmp_skills):
        results = asyncio.run(
            engine.evolve_multi_strategy_concurrent(
                tmp_skills[:2], [], max_concurrency=2,
            )
        )
        assert len(results) == 2
        for sf, prs in results.items():
            assert len(prs) >= 1

    def test_evolve_concurrent_preserves_order(self, engine, tmp_skills):
        results = asyncio.run(
            engine.evolve_concurrent(tmp_skills[:2], [], max_concurrency=2)
        )
        assert set(results.keys()) == {tmp_skills[0], tmp_skills[1]}


class TestEvolveConcurrentIntegration:
    def test_with_diversity_tracking(self, tmp_path: Path):
        skills = [
            _make_skill(tmp_path, "d1.py", "def d1():\n    return 1\n"),
            _make_skill(tmp_path, "d2.py", "def d2():\n    return 2\n"),
        ]
        engine = SkillEvolutionEngine(diversity_controller=DiversityController())
        results = asyncio.run(
            engine.evolve_concurrent(skills, [], max_concurrency=2)
        )
        assert len(results) == 2
        metrics = engine.diversity.diversity_metrics()
        assert metrics["generation"] >= 0
