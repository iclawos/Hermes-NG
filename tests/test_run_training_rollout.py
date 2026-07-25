import asyncio

from zilli.envs import HermesSandbox
from zilli.run_training import TrainingExperiment, _wrap_step, run_rollout


class TestWrapStep:
    def test_wraps_all_fields(self):
        result = _wrap_step(
            {"tool": "write"},
            {"observation": {"ok": True}, "reward": 0.5, "done": True},
        )
        assert result["action"] == {"tool": "write"}
        assert result["observation"] == {"ok": True}
        assert result["reward"] == 0.5
        assert result["done"] is True

    def test_defaults_on_missing(self):
        result = _wrap_step({"tool": "read"}, {})
        assert result["reward"] == 0.0
        assert result["done"] is False


class TestRunRollout:
    def test_basic_rollout(self):
        sandbox = HermesSandbox()
        result = asyncio.run(run_rollout(sandbox, {"id": "t1", "max_steps": 3}))
        assert "trajectory" in result
        assert result["reward"] != 0 or len(result["trajectory"]) > 0
        assert result["tokens"] >= 256
        assert len(result["trajectory"]) <= 4

    def test_rollout_with_scenario_filtered(self):
        sandbox = HermesSandbox()
        task = {
            "id": "t2", "max_steps": 2,
            "initial_context": {
                "scenario": {"env": "test"},
                "malicious_key": "should_be_dropped",
            },
        }
        result = asyncio.run(run_rollout(sandbox, task))
        assert "trajectory" in result

    def test_rollout_max_steps_floor(self):
        sandbox = HermesSandbox()
        result = asyncio.run(run_rollout(sandbox, {"id": "t3", "max_steps": 0}))
        assert result["tokens"] >= 256


class TestExperimentBestReward:
    def test_summary_defaults(self, tmp_path):
        exp = TrainingExperiment("e1", {}, log_dir=str(tmp_path))
        s = exp.summary()
        assert s["epochs"] == 0
        assert s["latest_metrics"] is None
        assert s["best_reward"] == float("-inf")


class TestMainConfigFiltering:
    def test_main_with_full_default_config(self, tmp_path, monkeypatch):
        """Regression: main() must not crash on the shipped default config
        which contains non-TrainingConfig keys (store_config, distillation, arena)."""
        import yaml
        cfg = {
            "training": {
                "algorithm": "CISPO",
                "num_epochs": 1,
                "batch_size": 4,
                "checkpoint_interval": 1,
                "log_dir": str(tmp_path),
                "store_config": {"max_size": 100},
                "distillation": {"lambda_bc": 1.0},
                "arena": {"min_win_gap": 0.05},
            }
        }
        cfg_path = tmp_path / "cfg.yaml"
        cfg_path.write_text(yaml.safe_dump(cfg))

        from zilli.run_training import main
        exp = asyncio.run(main(str(cfg_path), "filter_test"))
        assert exp.summary()["epochs"] >= 1
