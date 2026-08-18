import asyncio
import json
from pathlib import Path

from zilli.evolution.diversity import DiversityController
from zilli.evolution.skill_evolution import SkillEvolutionEngine
from zilli.pipeline.evolve_to_train import (
    EvolveToTrainPipeline,
    EvolveTrainConfig,
    EvolveTrainStage,
)
from zilli.training.rl_trainer import RLTrainer


class TestEvolveToTrainPipeline:
    def test_config_defaults(self):
        config = EvolveTrainConfig()
        assert config.num_train_epochs == 5
        assert config.batch_size == 32
        assert config.max_cycles == 10

    def test_cycle_without_engine(self):
        pipeline = EvolveToTrainPipeline()
        records = asyncio.run(pipeline.run_cycle())
        assert len(records) >= 2
        assert records[0].stage == EvolveTrainStage.EVOLVE
        assert not records[0].success

    def test_cycle_with_evolution(self, tmp_path: Path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_file = skills_dir / "test_skill.py"
        skill_file.write_text("def hello():\n    return 'hello'\n")

        config = EvolveTrainConfig(skills_dir=str(skills_dir))
        engine = SkillEvolutionEngine(diversity_controller=DiversityController())
        pipeline = EvolveToTrainPipeline(config=config, evolution_engine=engine)

        records = asyncio.run(pipeline.run_cycle(skill_files=[str(skill_file)]))
        evolve_record = next(r for r in records if r.stage == EvolveTrainStage.EVOLVE)
        assert evolve_record.success
        assert evolve_record.metrics.get("accepted", 0) >= 1

    def test_cycle_with_trainer(self, tmp_path: Path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skill_file = skills_dir / "train_skill.py"
        skill_file.write_text("def process():\n    return 0\n")

        config = EvolveTrainConfig(
            skills_dir=str(skills_dir),
            num_train_epochs=2,
            batch_size=4,
        )
        engine = SkillEvolutionEngine(diversity_controller=DiversityController())
        trainer = RLTrainer({})
        pipeline = EvolveToTrainPipeline(
            config=config,
            evolution_engine=engine,
            trainer=trainer,
        )

        records = asyncio.run(pipeline.run_cycle(skill_files=[str(skill_file)]))
        stages = {r.stage for r in records}
        assert EvolveTrainStage.EVOLVE in stages
        assert EvolveTrainStage.TRAIN in stages or EvolveTrainStage.MONITOR in stages

    def test_summary_format(self):
        pipeline = EvolveToTrainPipeline()
        summary = pipeline.summary()
        assert "cycle_count" in summary
        assert "deployed_version" in summary
        assert "champion_model" in summary

    def test_rollback_with_history(self):
        pipeline = EvolveToTrainPipeline()
        pipeline._rollback_versions.append("base-v1")
        record = asyncio.run(pipeline._stage_rollback())
        assert record.success
        assert "base-v1" in record.message

    def test_rollback_empty(self):
        pipeline = EvolveToTrainPipeline()
        record = asyncio.run(pipeline._stage_rollback())
        assert not record.success

    def test_load_trajectories(self, tmp_path: Path):
        traj_dir = tmp_path / "trajectories"
        traj_dir.mkdir()
        (traj_dir / "run1.json").write_text(json.dumps([
            {"observation": {"error": "TypeError"}},
        ]))

        config = EvolveTrainConfig(trajectories_dir=str(traj_dir))
        pipeline = EvolveToTrainPipeline(config=config)
        trajs = pipeline._load_trajectories()
        assert len(trajs) == 1

    def test_deploy_promotes_on_arena_wins(self):
        pipeline = EvolveToTrainPipeline()
        record = asyncio.run(pipeline._stage_deploy())
        assert record.success
        assert pipeline._deployed_version is not None


class TestEvolveConcurrency:
    def test_parallel_evolution_max_concurrency(self):
        import threading

        active = 0
        peak = 0
        lock = threading.Lock()

        class TrackingEngine:
            def evolve(self, skill_file, trajectory_data):
                nonlocal active, peak
                with lock:
                    active += 1
                    peak = max(peak, active)
                import time
                time.sleep(0.02)
                with lock:
                    active -= 1
                return f"PR for {skill_file}"

        config = EvolveTrainConfig(evolution_concurrency=2)
        pipeline = EvolveToTrainPipeline(config=config, evolution_engine=TrackingEngine())
        record = asyncio.run(pipeline._stage_evolve(
            skill_files=[f"skill_{i}.py" for i in range(6)],
        ))
        assert record.success
        assert record.metrics["accepted"] == 6
        assert peak <= 2, f"expected peak concurrency <= 2, got {peak}"

    def test_async_evolve_engine_supported(self):
        class AsyncEngine:
            async def evolve(self, skill_file, trajectory_data):
                return f"PR for {skill_file}"

        config = EvolveTrainConfig(evolution_concurrency=2)
        pipeline = EvolveToTrainPipeline(config=config, evolution_engine=AsyncEngine())
        record = asyncio.run(pipeline._stage_evolve(skill_files=["a.py", "b.py"]))
        assert record.success
        assert record.metrics["accepted"] == 2

    def test_failed_evolution_counts_as_rejected(self):
        class FailingEngine:
            def evolve(self, skill_file, trajectory_data):
                if "bad" in skill_file:
                    raise RuntimeError("boom")
                return "PR ok"

        pipeline = EvolveToTrainPipeline(evolution_engine=FailingEngine())
        record = asyncio.run(pipeline._stage_evolve(
            skill_files=["good.py", "bad.py", "also_bad.py"],
        ))
        assert record.success
        assert record.metrics["accepted"] == 1
        assert record.metrics["rejected"] == 2

    def test_diversity_rejection_marks_accepted(self):
        class DiversityEngine:
            def evolve(self, skill_file, trajectory_data):
                if "dup" in skill_file:
                    return "# Diversity rejected: duplicate\n"
                return "PR new"

        pipeline = EvolveToTrainPipeline(evolution_engine=DiversityEngine())
        record = asyncio.run(pipeline._stage_evolve(
            skill_files=["new.py", "dup.py"],
        ))
        assert record.metrics["accepted"] == 1
        assert record.metrics["rejected"] == 1
