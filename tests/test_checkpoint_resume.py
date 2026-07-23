from pathlib import Path

import pytest

from zilli.run_training import TrainingExperiment


class TestTrainingExperimentCheckpoint:
    def test_save_and_load_checkpoint(self, tmp_path: Path):
        exp = TrainingExperiment("test_exp", {"lr": 0.001}, str(tmp_path))
        exp.log_epoch(0, {"loss": 0.5, "reward": 0.8})
        exp.best_reward = 0.8

        ckpt_path = str(tmp_path / "test_exp_ckpt_epoch_0.json")
        exp.save_checkpoint("epoch_0")
        assert Path(ckpt_path).exists()

        loaded = TrainingExperiment.load_checkpoint(ckpt_path)
        assert loaded["experiment"] == "test_exp"
        assert loaded["epoch"] == 1
        assert loaded["best_reward"] == 0.8

    def test_save_checkpoint_multiple_epochs(self, tmp_path: Path):
        exp = TrainingExperiment("multi_epoch", {}, str(tmp_path))
        for i in range(5):
            exp.log_epoch(i, {"loss": 0.5 - i * 0.1, "reward": i * 0.2})

        exp.save_checkpoint("final")
        ckpt = TrainingExperiment.load_checkpoint(
            str(tmp_path / "multi_epoch_ckpt_final.json")
        )
        assert ckpt["epoch"] == 5
        assert len(ckpt["metrics"]) == 5

    def test_resume_from_checkpoint(self, tmp_path: Path):
        exp = TrainingExperiment("resume_test", {"epochs": 10}, str(tmp_path))
        for i in range(3):
            exp.log_epoch(i, {"loss": 0.5, "reward": i * 0.3})
        exp.best_reward = 0.6
        exp.save_checkpoint("interrupt")

        ckpt_path = str(tmp_path / "resume_test_ckpt_interrupt.json")
        resumed, start_epoch = TrainingExperiment.resume_from(
            ckpt_path, {"epochs": 10}, str(tmp_path)
        )
        assert start_epoch == 3
        assert resumed.best_reward == 0.6
        assert len(resumed.metrics) == 4  # 3 original + 1 resume marker

    def test_resume_and_continue_training(self, tmp_path: Path):
        exp = TrainingExperiment("continue_test", {"epochs": 5}, str(tmp_path))
        for i in range(2):
            exp.log_epoch(i, {"loss": 0.5, "reward": float(i)})
        exp.best_reward = 1.0
        exp.save_checkpoint("part1")

        ckpt_path = str(tmp_path / "continue_test_ckpt_part1.json")
        resumed, start_epoch = TrainingExperiment.resume_from(
            ckpt_path, {"epochs": 5}, str(tmp_path)
        )
        assert start_epoch == 2
        assert resumed.best_reward == 1.0

        for i in range(start_epoch, 5):
            resumed.log_epoch(i, {"loss": 0.3, "reward": float(i + 1)})
            if float(i + 1) > resumed.best_reward:
                resumed.best_reward = float(i + 1)

        assert resumed.best_reward == 5.0
        assert len(resumed.metrics) == 6  # 2 original + 1 resume marker + 3 new

    def test_load_checkpoint_not_found(self):
        with pytest.raises(FileNotFoundError):
            TrainingExperiment.load_checkpoint("/nonexistent/path.json")

    def test_checkpoint_includes_config_hash(self, tmp_path: Path):
        exp = TrainingExperiment("hash_test", {"a": 1, "b": 2}, str(tmp_path))
        exp.log_epoch(0, {"loss": 0.1})
        exp.save_checkpoint("v1")

        ckpt = TrainingExperiment.load_checkpoint(
            str(tmp_path / "hash_test_ckpt_v1.json")
        )
        assert "config_hash" in ckpt
        assert len(ckpt["config_hash"]) == 12

    def test_save_with_extra_data(self, tmp_path: Path):
        exp = TrainingExperiment("extra_test", {}, str(tmp_path))
        exp.log_epoch(0, {"loss": 0.1})
        exp.save_checkpoint("extra", extra={"custom_field": "hello", "epoch_state": 42})

        ckpt = TrainingExperiment.load_checkpoint(
            str(tmp_path / "extra_test_ckpt_extra.json")
        )
        assert ckpt["custom_field"] == "hello"
        assert ckpt["epoch_state"] == 42

    def test_resume_preserves_all_metrics(self, tmp_path: Path):
        exp = TrainingExperiment("full_metrics", {}, str(tmp_path))
        original = []
        for i in range(10):
            m = {"loss": round(1.0 - i * 0.1, 2), "reward": round(i * 0.5, 2)}
            exp.log_epoch(i, m)
            original.append(m)
        exp.save_checkpoint("full")

        ckpt = TrainingExperiment.load_checkpoint(
            str(tmp_path / "full_metrics_ckpt_full.json")
        )
        assert len(ckpt["metrics"]) == 10
        for i, m in enumerate(original):
            assert ckpt["metrics"][i]["loss"] == m["loss"]

    def test_summary_after_resume(self, tmp_path: Path):
        exp = TrainingExperiment("summary_resume", {}, str(tmp_path))
        exp.log_epoch(0, {"loss": 0.5})
        exp.save_checkpoint("epoch_0")

        ckpt_path = str(tmp_path / "summary_resume_ckpt_epoch_0.json")
        resumed, _ = TrainingExperiment.resume_from(ckpt_path, {}, str(tmp_path))
        s = resumed.summary()
        assert s["epochs"] >= 1
        assert "latest_metrics" in s
