import asyncio
import json
from pathlib import Path

from zilli.data import TrajectoryStore
from zilli.learner.continuous_learner import ContinuousLearner


def _run(coro):
    return asyncio.run(coro)


class TestCollectProductionTrajectories:
    def test_reads_list_and_dict_files(self, tmp_path):
        store = TrajectoryStore()
        learner = ContinuousLearner(store, data_dir=str(tmp_path),
                                    archive_dir=str(tmp_path / "arch"))
        (tmp_path / "a.json").write_text(json.dumps([{"trajectory": [1], "reward": 0.9}]))
        (tmp_path / "b.json").write_text(json.dumps({"trajectory": [2], "reward": 0.5}))
        trajs, files = _run(learner._collect_production_trajectories())
        assert len(trajs) == 2
        assert len(files) == 2

    def test_bad_json_skipped(self, tmp_path):
        store = TrajectoryStore()
        learner = ContinuousLearner(store, data_dir=str(tmp_path),
                                    archive_dir=str(tmp_path / "arch"))
        (tmp_path / "bad.json").write_text("not json{")
        (tmp_path / "ok.json").write_text(json.dumps({"trajectory": []}))
        trajs, files = _run(learner._collect_production_trajectories())
        assert len(trajs) == 1
        assert len(files) == 1
        assert learner._recent_errors[-1] == ("error", "bad.json") or \
               ("error", "bad.json") in list(learner._recent_errors)

    def test_missing_dir_created(self, tmp_path):
        store = TrajectoryStore()
        target = tmp_path / "newdir"
        learner = ContinuousLearner(store, data_dir=str(target),
                                    archive_dir=str(tmp_path / "arch"))
        trajs, files = _run(learner._collect_production_trajectories())
        assert trajs == [] and files == []
        assert target.exists()


class TestSFTTrigger:
    def test_no_callback_never_triggers(self):
        learner = ContinuousLearner(TrajectoryStore())
        assert learner._should_trigger_sft() is False

    def test_triggers_at_threshold(self, tmp_path):
        store = TrajectoryStore()
        for i in range(5):
            store.add_trajectory([{"step": i}, {"step": i + 1}], 0.9)
        learner = ContinuousLearner(store, sft_threshold=5,
                                    sft_callback=lambda stats: {"ok": True},
                                    data_dir=str(tmp_path),
                                    archive_dir=str(tmp_path / "arch"))
        assert learner._should_trigger_sft() is True

    def test_below_threshold(self):
        learner = ContinuousLearner(TrajectoryStore(), sft_threshold=100,
                                    sft_callback=lambda s: None)
        assert learner._should_trigger_sft() is False

    def test_trigger_writes_log(self, tmp_path):
        store = TrajectoryStore()
        store.add_trajectory([{"step": 1}, {"step": 2}], 0.9)
        learner = ContinuousLearner(store, sft_threshold=1,
                                    sft_callback=lambda stats: {"loss": 0.5},
                                    data_dir=str(tmp_path),
                                    archive_dir=str(tmp_path / "arch"))
        metrics = _run(learner._trigger_online_sft())
        assert metrics["loss"] == 0.5
        log = tmp_path / "sft_events.jsonl"
        assert log.exists()
        entry = json.loads(log.read_text().strip().split("\n")[0])
        assert entry["golden"] >= 1

    def test_callback_error_captured(self, tmp_path):
        def boom(stats):
            raise RuntimeError("callback exploded")

        learner = ContinuousLearner(TrajectoryStore(), sft_threshold=1,
                                    sft_callback=boom,
                                    data_dir=str(tmp_path),
                                    archive_dir=str(tmp_path / "arch"))
        metrics = _run(learner._trigger_online_sft())
        assert "error" in metrics
        assert "exploded" in metrics["error"]

    def test_async_callback_supported(self, tmp_path):
        async def cb(stats):
            return {"async": True}

        learner = ContinuousLearner(TrajectoryStore(), sft_threshold=1,
                                    sft_callback=cb,
                                    data_dir=str(tmp_path),
                                    archive_dir=str(tmp_path / "arch"))
        metrics = _run(learner._trigger_online_sft())
        assert metrics.get("async") is True


class TestArchive:
    def test_moves_files(self, tmp_path):
        arch = tmp_path / "arch"
        learner = ContinuousLearner(TrajectoryStore(),
                                    data_dir=str(tmp_path),
                                    archive_dir=str(arch))
        f = tmp_path / "done.json"
        f.write_text("{}")
        learner._archive_processed_data([f])
        assert not f.exists()
        assert (arch / "done.json").exists()

    def test_missing_file_ignored(self, tmp_path):
        learner = ContinuousLearner(TrajectoryStore(),
                                    data_dir=str(tmp_path),
                                    archive_dir=str(tmp_path / "arch"))
        learner._archive_processed_data([tmp_path / "ghost.json"])
        learner._archive_processed_data([])


class TestStats:
    def test_stats_fields(self, tmp_path):
        learner = ContinuousLearner(TrajectoryStore(), interval_hours=12,
                                    sft_threshold=42,
                                    data_dir=str(tmp_path),
                                    archive_dir=str(tmp_path / "arch"))
        s = learner.stats()
        assert s["interval_hours"] == 12
        assert s["sft_threshold"] == 42
        assert s["running"] is False
        assert s["cycle_count"] == 0

    def test_stop(self):
        learner = ContinuousLearner(TrajectoryStore())
        learner._running = True
        _run(learner.stop())
        assert learner._running is False
