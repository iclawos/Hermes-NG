from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from zilli.evolution import SkillEvolutionEngine

from zilli.adaptive.sota_scheduler import DynamicSOTAScheduler
from zilli.data import TrajectoryStore
from zilli.envs import HermesSandbox
from zilli.evaluation.meta_evaluator import EvaluationSample, MetaEvaluator
from zilli.infra.async_scheduler import AsyncRolloutScheduler
from zilli.tasks import load_tasks
from zilli.training.champion_challenger import ArenaStatus, ChampionChallenger
from zilli.training.rl_trainer import RLTrainer

logger = logging.getLogger("zilli.pipeline.evolve_to_train")


class EvolveTrainStage(str, Enum):
    EVOLVE = "evolve"
    TRAIN = "train"
    DEPLOY = "deploy"
    MONITOR = "monitor"
    ROLLBACK = "rollback"


@dataclass
class CycleRecord:
    stage: EvolveTrainStage
    success: bool
    message: str
    metrics: dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


@dataclass
class EvolveTrainConfig:
    skills_dir: str = ""
    trajectories_dir: str = ""
    num_train_epochs: int = 5
    batch_size: int = 32
    checkpoint_interval: int = 20
    log_dir: str = "./experiments"
    min_arena_matches: int = 3
    warmup_rounds: int = 2
    degradation_threshold: float = 0.1
    diversity_threshold: float = 0.5
    max_cycles: int = 10


class EvolveToTrainPipeline:
    def __init__(
        self,
        config: Optional[EvolveTrainConfig] = None,
        evolution_engine: Optional[SkillEvolutionEngine] = None,
        trainer: Optional[RLTrainer] = None,
        arena: Optional[ChampionChallenger] = None,
        meta_evaluator: Optional[MetaEvaluator] = None,
        store: Optional[TrajectoryStore] = None,
        sandbox: Optional[HermesSandbox] = None,
        sota_scheduler: Optional[DynamicSOTAScheduler] = None,
        rollout_scheduler: Optional[AsyncRolloutScheduler] = None,
    ):
        self.config = config or EvolveTrainConfig()
        self._evolution_engine = evolution_engine
        self._trainer = trainer
        self._arena = arena
        self._meta_evaluator = meta_evaluator or MetaEvaluator()
        self._store = store or TrajectoryStore()
        self._sandbox = sandbox or HermesSandbox()
        self._sota_scheduler = sota_scheduler or DynamicSOTAScheduler()
        self._rollout_scheduler = rollout_scheduler or AsyncRolloutScheduler()
        self._cycle_count = 0
        self._history: list[CycleRecord] = []
        self._deployed_version: Optional[str] = None
        self._rollback_versions: list[str] = []
        self._champion_model = "base-v1"

    async def run_cycle(self, skill_files: Optional[list[str]] = None) -> list[CycleRecord]:
        self._cycle_count += 1
        cycle_records: list[CycleRecord] = []

        evolve_record = await self._stage_evolve(skill_files)
        cycle_records.append(evolve_record)

        if evolve_record.success:
            train_record = await self._stage_train()
            cycle_records.append(train_record)

            if train_record.success:
                deploy_record = await self._stage_deploy()
                cycle_records.append(deploy_record)
            else:
                deploy_record = CycleRecord(
                    stage=EvolveTrainStage.DEPLOY,
                    success=False,
                    message="Training failed, skipping deploy",
                )
                cycle_records.append(deploy_record)

        monitor_record = await self._stage_monitor()
        cycle_records.append(monitor_record)

        if not monitor_record.success and self.config.degradation_threshold > 0:
            rollback_record = await self._stage_rollback()
            cycle_records.append(rollback_record)

        self._history.extend(cycle_records)
        return cycle_records

    async def _stage_evolve(self, skill_files: Optional[list[str]] = None) -> CycleRecord:
        if not self._evolution_engine:
            return CycleRecord(
                stage=EvolveTrainStage.EVOLVE, success=False,
                message="No evolution engine configured",
            )

        files_to_evolve = skill_files
        if not files_to_evolve:
            skills_dir = Path(self.config.skills_dir)
            if skills_dir.exists():
                files_to_evolve = [
                    str(f) for f in sorted(skills_dir.glob("*.py"))
                    if f.is_file() and f.name != "__init__.py"
                ]

        if not files_to_evolve:
            return CycleRecord(
                stage=EvolveTrainStage.EVOLVE, success=False,
                message="No skill files to evolve",
            )

        trajectories = self._load_trajectories()
        accepted = 0
        rejected = 0
        prs: list[str] = []

        for skill_file in files_to_evolve:
            try:
                pr = self._evolution_engine.evolve(skill_file, trajectories)
                if "# Diversity rejected" in pr:
                    rejected += 1
                else:
                    accepted += 1
                prs.append(pr)
            except Exception as e:
                logger.warning("Evolution failed for %s: %s", skill_file, e)
                rejected += 1

        return CycleRecord(
            stage=EvolveTrainStage.EVOLVE,
            success=accepted > 0,
            message=f"Evolved {len(files_to_evolve)} files: {accepted} accepted, {rejected} rejected",
            metrics={
                "files_processed": len(files_to_evolve),
                "accepted": accepted,
                "rejected": rejected,
                "generated_prs": len(prs),
            },
        )

    async def _stage_train(self) -> CycleRecord:
        if not self._trainer:
            return CycleRecord(
                stage=EvolveTrainStage.TRAIN, success=False,
                message="No trainer configured",
            )

        tasks = load_tasks()
        if not tasks:
            tasks = [{"id": "dummy", "max_steps": 5}]

        for epoch in range(self.config.num_train_epochs):
            batch_tasks = tasks[:8] if len(tasks) > 8 else tasks

            rollout_results = await self._rollout_scheduler.schedule(
                self._sota_aware_rollout,
                batch_tasks,
                timeout_per_task=300,
            )

            for result in rollout_results:
                if result.completed:
                    self._store.add_trajectory(result.trajectory, result.reward)

            batch = self._store.sample_batch(batch_size=self.config.batch_size)
            if batch:
                self._trainer.update(batch)
                store_stats = self._store.stats()
                avg_reward = store_stats.get("avg_golden_reward", 0.0)
                self._meta_evaluator.record(EvaluationSample(
                    task_id=f"train_epoch_{epoch}",
                    model_name="trainer",
                    features={},
                    predicted_score=0.5,
                    actual_score=float(avg_reward),
                ))

        store_stats = self._store.stats()
        return CycleRecord(
            stage=EvolveTrainStage.TRAIN,
            success=True,
            message=f"Training complete: {self.config.num_train_epochs} epochs",
            metrics={
                "epochs": self.config.num_train_epochs,
                "golden": store_stats.get("golden", 0),
                "failure": store_stats.get("failure", 0),
                "avg_reward": store_stats.get("avg_golden_reward", 0.0),
            },
        )

    async def _stage_deploy(self) -> CycleRecord:
        if not self._arena:
            self._champion_model = f"evolved-v{self._cycle_count}"
            self._deployed_version = self._champion_model
            return CycleRecord(
                stage=EvolveTrainStage.DEPLOY, success=True,
                message=f"Deployed (no arena): {self._champion_model}",
            )

        def eval_fn(model_name: str) -> list[float]:
            store_stats = self._store.stats()
            return [store_stats.get("avg_golden_reward", 0.0)]

        scores = []
        for i in range(self.config.min_arena_matches):
            match = self._arena.run_match(self._champion_model, eval_fn)
            if match:
                scores.append({
                    "match": i,
                    "champion_score": match.champion_score,
                    "challenger_score": match.challenger_score,
                    "winner": match.winner or "",
                })

        challenger_wins = sum(1 for s in scores if s.get("winner") == "challenger")
        is_promoted = challenger_wins >= self.config.min_arena_matches // 2 + 1

        if is_promoted:
            self._rollback_versions.append(self._champion_model)
            self._champion_model = f"evolved-v{self._cycle_count}"
            self._arena.register_model(self._champion_model, self._champion_model, ArenaStatus.CHAMPION)
            self._deployed_version = self._champion_model

        return CycleRecord(
            stage=EvolveTrainStage.DEPLOY,
            success=is_promoted,
            message=(
                f"Promoted: {self._champion_model}" if is_promoted
                else f"Challenger lost ({challenger_wins}/{self.config.min_arena_matches} wins)"
            ),
            metrics={
                "champion": self._champion_model if is_promoted else self._champion_model,
                "matches": len(scores),
                "challenger_wins": challenger_wins,
                "promoted": is_promoted,
            },
        )

    async def _stage_monitor(self) -> CycleRecord:
        meta_result = self._meta_evaluator.evaluate()
        drift = self._meta_evaluator.detect_drift()

        is_healthy = meta_result.reliable and not drift
        return CycleRecord(
            stage=EvolveTrainStage.MONITOR,
            success=is_healthy,
            message=(
                "System healthy" if is_healthy
                else f"Degradation detected: drift={drift}, reliable={meta_result.reliable}"
            ),
            metrics={
                "reliable": meta_result.reliable,
                "drift": drift,
                "calibration_error": meta_result.calibration_error,
                "sample_count": meta_result.sample_count,
                "total_cycles": self._cycle_count,
            },
        )

    async def _stage_rollback(self) -> CycleRecord:
        if self._rollback_versions:
            prev = self._rollback_versions.pop()
            self._champion_model = prev
            self._deployed_version = prev
            return CycleRecord(
                stage=EvolveTrainStage.ROLLBACK, success=True,
                message=f"Rolled back to {prev}",
            )
        return CycleRecord(
            stage=EvolveTrainStage.ROLLBACK, success=False,
            message="No rollback version available",
        )

    async def _sota_aware_rollout(self, task: dict) -> Any:
        task_type = task.get("type", "default")
        difficulty = task.get("difficulty", 0.5)
        use_sota = self._sota_scheduler.should_call_sota(
            task_type, {"max_prob": difficulty},
        )

        self._sandbox.reset()
        traj = []
        total_reward = 0.0
        max_steps = task.get("max_steps", 10)

        from zilli.schema.actions import FinishAction, MemoryWriteAction

        for step_num in range(max_steps):
            action = MemoryWriteAction(
                action_id=f"{task.get('id', 'task')}_{step_num}",
                reasoning=f"Step {step_num}",
                key=f"step_{step_num}",
                value=f"progress_{step_num}",
            )
            result = await self._sandbox.step(action)
            traj.append({
                "action": action.model_dump(),
                "observation": result.get("observation", {}),
                "reward": result.get("reward", 0.0),
            })
            total_reward += result.get("reward", 0.0)
            if result.get("done", False):
                break

        finish = FinishAction(
            action_id=f"{task.get('id', 'task')}_finish",
            reasoning="Complete",
            summary=f"Finished in {step_num + 1} steps",
        )
        final = await self._sandbox.step(finish)
        traj.append({
            "action": finish.model_dump(),
            "observation": final.get("observation", {}),
            "reward": final.get("reward", 0.0),
        })
        total_reward += final.get("reward", 0.0)
        task_success = total_reward > 0

        if use_sota:
            self._sota_scheduler.record_call("default", task_type, task_success)
        else:
            self._sota_scheduler.record_without_sota(task_type, task_success)

        class RolloutResult:
            def __init__(self, traj, reward, completed=True):
                self.trajectory = traj
                self.reward = reward
                self.completed = completed
                self.tokens = len(traj) * 256

        return RolloutResult(traj, total_reward)

    def _load_trajectories(self) -> list[dict]:
        traj_dir = Path(self.config.trajectories_dir)
        if not traj_dir.exists():
            return []
        trajectories = []
        for f in sorted(traj_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text())
                if isinstance(data, list):
                    trajectories.extend(data)
                else:
                    trajectories.append(data)
            except (json.JSONDecodeError, IOError):
                pass
        return trajectories

    def summary(self) -> dict[str, Any]:
        return {
            "cycle_count": self._cycle_count,
            "total_events": len(self._history),
            "deployed_version": self._deployed_version,
            "champion_model": self._champion_model,
            "rollback_versions": self._rollback_versions,
            "history": [
                {
                    "stage": r.stage.value,
                    "success": r.success,
                    "message": r.message,
                }
                for r in self._history[-20:]
            ],
        }
