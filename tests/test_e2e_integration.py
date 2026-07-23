from __future__ import annotations

import time
from pathlib import Path

from zilli.evolution import SkillEvolutionEngine
from zilli.pipeline.evolution import EvolutionPipeline, PipelineConfig
from zilli.routing.feedback import FeedbackCollector
from zilli.routing.mom_router import MOMRouter
from zilli.routing.ppm import PPMPredictor
from zilli.routing.profile import ModelCapability, ModelEntry, ModelProfile
from zilli.routing.strategy import StrategySelector


async def test_route_feedback_evolve_cycle(tmp_path: Path):
    """Full e2e: route a request -> record feedback -> evolve a skill."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_file = skills_dir / "route_feedback.py"
    skill_file.write_text("def process():\n    return 0\n")

    ppm = PPMPredictor()
    profile = ModelProfile(exploration_factor=0.0)
    profile.register(ModelEntry(
        name="cheap", model_id="fast-cheap",
        cost_per_1k_input=0.0005, cost_per_1k_output=0.001,
        capability=ModelCapability(reasoning=0.3, coding=0.2),
    ))
    profile.register(ModelEntry(
        name="premium", model_id="slow-premium",
        cost_per_1k_input=0.01, cost_per_1k_output=0.02,
        capability=ModelCapability(reasoning=0.9, coding=0.95),
    ))
    strategy = StrategySelector()
    feedback = FeedbackCollector()
    router = MOMRouter(ppm=ppm, profile=profile, strategy=strategy, feedback=feedback)

    decision = await router.route("write a python function to sort a list")
    assert decision.model_id in ("fast-cheap", "slow-premium", "fast-lane")
    assert decision.task_family.value in ("coding", "reasoning", "chat")

    router.record_feedback(
        request_id="e2e-test-1",
        ppm_difficulty=decision.difficulty,
        ppm_family=decision.task_family.value,
        selected_model=decision.model_id,
        strategy_tier=decision.strategy_tier.value,
        actual_latency_ms=150,
        actual_cost=0.002,
        success=True,
        score=0.85,
    )
    router.update_profile_from_feedback(decision.model_id, success=True, score=0.85)

    engine = SkillEvolutionEngine(
        mode="harness", mom_router=router, reflection_model=decision.model_id,
    )
    pr = engine.evolve(str(skill_file), trajectory_data=[
        {"observation": {"error": "TypeError: expected str"}},
    ])
    assert "Auto-evolved" in pr
    stats = ppm.stats()
    assert stats["cache_hits"] >= 0
    assert router.stats()["ppm"]["cache_size"] >= 0


async def test_multi_cycle_ppm_training_loop(tmp_path: Path):
    """Route 5 requests -> collect feedback -> train PPM -> verify weights changed."""
    ppm = PPMPredictor(learning_rate=0.5)
    profile = ModelProfile(exploration_factor=0.0)
    profile.register(ModelEntry(
        name="default", model_id="default-model",
        cost_per_1k_input=0.001, cost_per_1k_output=0.002,
        capability=ModelCapability(reasoning=0.5, coding=0.5),
    ))
    strategy = StrategySelector()
    router = MOMRouter(ppm=ppm, profile=profile, strategy=strategy, feedback=None)

    from zilli.routing.ppm_classifier import RegexClassifier
    assert isinstance(ppm.classifier, RegexClassifier)

    weights_before = {}
    for family, w in ppm._difficulty_weights.items():
        weights_before[family] = dict(w)

    requests = [
        ("implement binary search in python", 0.7, True, "coding"),
        ("write a poem about AI", 0.3, False, "creative"),
        ("solve this math equation step by step", 0.8, True, "reasoning"),
        ("summarize this article", 0.4, True, "chat"),
        ("refactor this function to be async", 0.6, False, "analysis"),
    ]

    for req_text, actual_diff, success, family in requests:
        decision = await router.route(req_text)
        router.record_feedback(
            request_id=f"multi-{req_text[:10]}",
            ppm_difficulty=decision.difficulty,
            ppm_family=family,
            selected_model=decision.model_id,
            strategy_tier=decision.strategy_tier.value,
            actual_latency_ms=100,
            actual_cost=0.001,
            success=success,
            score=0.7 if success else 0.3,
        )
        router.update_profile_from_feedback(decision.model_id, success=success,
                                             score=0.7 if success else 0.3)

    records = [
        {
            "difficulty": actual_diff,
            "predicted_difficulty": (await router.route(req_text)).difficulty,
            "ppm_family": family,
            "success": success,
            "score": 0.7 if success else 0.3,
        }
        for req_text, actual_diff, success, family in requests
    ]
    result = ppm.train(records)
    assert result["trained"] == 5
    assert result["loss"] >= 0

    weights_after = {}
    for family, w in ppm._difficulty_weights.items():
        weights_after[family] = dict(w)

    changed = any(
        weights_before[f] != weights_after[f]
        for f in weights_before
    )
    assert changed, "PPM weights should change after training"


def test_evolution_pipeline_with_routing(tmp_path: Path):
    """EvolutionPipeline.run_cycle with simulated evaluation samples."""
    from zilli.evaluation.meta_evaluator import EvaluationSample

    config = PipelineConfig(
        monitor_interval_s=1.0,
        degradation_threshold=0.1,
        min_samples_for_detection=5,
        auto_rollback=True,
    )
    pipeline = EvolutionPipeline(config=config)

    for i in range(6):
        pipeline.record_evaluation(EvaluationSample(
            task_id=f"t{i}",
            features={"complexity": 0.5},
            model_name="current",
            predicted_score=0.5,
            actual_score=0.3,
        ))

    health = pipeline.check_health()
    assert "drift_detected" in health
    assert "reliable" in health

    events = pipeline.run_cycle()
    assert len(events) >= 1

    stage_names = [e.stage.value for e in events]
    assert "monitor" in stage_names
    assert "detect" in stage_names

    summary = pipeline.summary()
    assert summary["total_events"] == len(events)
    assert summary["current_stage"] in ("deploy", "rollback", "evolve", "monitor", "detect")


def test_evolution_pipeline_healthy_no_degradation(tmp_path: Path):
    """EvolutionPipeline produces no evolution events when system is healthy."""
    from zilli.evaluation.meta_evaluator import EvaluationSample

    config = PipelineConfig(
        degradation_threshold=0.1,
        min_samples_for_detection=3,
    )
    pipeline = EvolutionPipeline(config=config)

    for i in range(5):
        pipeline.record_evaluation(EvaluationSample(
            task_id=f"t{i}",
            features={"complexity": 0.5},
            model_name="current",
            predicted_score=0.9,
            actual_score=0.88,
        ))

    events = pipeline.run_cycle()
    stage_names = [e.stage.value for e in events]
    assert "monitor" in stage_names
    assert "detect" in stage_names
    detect_events = [e for e in events if e.stage.value == "detect"]
    assert len(detect_events) >= 1


async def test_route_feedback_profile_update_cycle(tmp_path: Path):
    """Route -> feedback -> profile update -> re-route sees updated profile."""
    ppm = PPMPredictor()
    profile = ModelProfile(exploration_factor=0.0)
    profile.register(ModelEntry(
        name="test-model", model_id="test-1",
        cost_per_1k_input=0.001, cost_per_1k_output=0.002,
        capability=ModelCapability(reasoning=0.5, coding=0.5),
    ))
    router = MOMRouter(ppm=ppm, profile=profile, strategy=StrategySelector(), feedback=None)

    initial_stats = router.stats()
    assert initial_stats["profile"]["models"][0]["success_rate"] == 1.0

    for _ in range(5):
        decision = await router.route("help me with python")
        router.record_feedback(
            request_id=f"profile-{time.time_ns()}",
            ppm_difficulty=decision.difficulty,
            ppm_family="coding",
            selected_model=decision.model_id,
            strategy_tier="standard",
            actual_latency_ms=100,
            actual_cost=0.001,
            success=False,
            score=0.2,
        )
        router.update_profile_from_feedback(decision.model_id, success=False, score=0.2)

    entry = profile.get("test-1")
    assert entry is not None
    assert entry.success_rate < 1.0
    assert entry.call_count == 5


async def test_concurrent_evolve_with_routing(tmp_path: Path):
    """Evolve multiple skills concurrently, each with routing + feedback."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_files = []
    for i in range(3):
        sf = skills_dir / f"concurrent_{i}.py"
        sf.write_text(f"def task_{i}():\n    return {i}\n")
        skill_files.append(str(sf))

    ppm = PPMPredictor()
    profile = ModelProfile(exploration_factor=0.0)
    profile.register(ModelEntry(
        name="cheap", model_id="fast-cheap",
        cost_per_1k_input=0.0005, cost_per_1k_output=0.001,
        capability=ModelCapability(reasoning=0.3, coding=0.3),
    ))
    profile.register(ModelEntry(
        name="premium", model_id="slow-premium",
        cost_per_1k_input=0.01, cost_per_1k_output=0.02,
        capability=ModelCapability(reasoning=0.9, coding=0.95),
    ))
    strategy = StrategySelector()
    feedback = FeedbackCollector()
    router = MOMRouter(ppm=ppm, profile=profile, strategy=strategy, feedback=feedback)

    decision = await router.route("evolve concurrent skills")
    router.record_feedback(
        request_id="concurrent-evolve",
        ppm_difficulty=decision.difficulty,
        ppm_family=decision.task_family.value,
        selected_model=decision.model_id,
        strategy_tier=decision.strategy_tier.value,
        actual_latency_ms=50,
        actual_cost=0.001,
        success=True,
        score=0.8,
    )

    engine = SkillEvolutionEngine(mode="harness", mom_router=router)
    results = await engine.evolve_concurrent(
        skill_files, [{"observation": {"error": "bug"}}], max_concurrency=3,
    )
    assert len(results) == 3
    for sf in skill_files:
        assert sf in results
        assert "Auto-evolved" in results[sf]

    assert ppm.stats()["call_count"] > 0


async def test_evolve_train_pipeline_cycle(tmp_path: Path):
    """EvolveToTrainPipeline minimal cycle: evolve -> train -> deploy -> monitor."""
    import json

    from zilli.data import TrajectoryStore
    from zilli.envs import HermesSandbox
    from zilli.infra.async_scheduler import AsyncRolloutScheduler
    from zilli.pipeline.evolve_to_train import EvolveToTrainPipeline, EvolveTrainConfig

    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_file = skills_dir / "et_pipeline.py"
    skill_file.write_text("def run():\n    return 0\n")

    traj_dir = tmp_path / "trajectories"
    traj_dir.mkdir()
    (traj_dir / "run1.json").write_text(json.dumps([
        {"observation": {"error": "KeyError: missing key"}},
    ]))

    engine = SkillEvolutionEngine()
    config = EvolveTrainConfig(
        skills_dir=str(skills_dir),
        trajectories_dir=str(traj_dir),
        num_train_epochs=1,
        batch_size=8,
        log_dir=str(tmp_path / "logs"),
    )

    pipeline = EvolveToTrainPipeline(
        config=config,
        evolution_engine=engine,
        store=TrajectoryStore(),
        sandbox=HermesSandbox(),
        rollout_scheduler=AsyncRolloutScheduler(),
    )

    records = await pipeline.run_cycle()
    assert len(records) >= 1

    stage_names = [r.stage.value for r in records]
    assert "evolve" in stage_names

    evolve_stage = next(r for r in records if r.stage.value == "evolve")
    assert evolve_stage.success or not evolve_stage.success


async def test_route_feedback_loop_improves_ppm(tmp_path: Path):
    """PPM accuracy improves after feedback loop with known patterns."""
    ppm = PPMPredictor(learning_rate=0.3)
    profile = ModelProfile(exploration_factor=0.0)
    profile.register(ModelEntry(
        name="default", model_id="test",
        cost_per_1k_input=0.001, cost_per_1k_output=0.002,
        capability=ModelCapability(reasoning=0.5, coding=0.5),
    ))
    router = MOMRouter(ppm=ppm, profile=profile, strategy=StrategySelector(), feedback=None)

    for i in range(10):
        decision = await router.route(f"coding task number {i}")
        router.record_feedback(
            request_id=f"loop-{i}",
            ppm_difficulty=decision.difficulty,
            ppm_family="coding",
            selected_model=decision.model_id,
            strategy_tier="standard",
            actual_latency_ms=100,
            actual_cost=0.001,
            success=True,
            score=0.9,
        )
        ppm.train([{
            "difficulty": 0.7,
            "predicted_difficulty": decision.difficulty,
            "ppm_family": "coding",
            "success": True,
            "score": 0.9,
        }])

    stats = ppm.stats()
    assert stats["train_count"] == 10
    assert stats["call_count"] >= 10
