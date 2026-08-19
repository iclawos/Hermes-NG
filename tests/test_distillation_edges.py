"""DistillationScheduler 边界覆盖。

覆盖：空 buffer 损失、GPU→CPU 回退、full-SFT/LoRA 回调异常、
should_distill 空 buffer、不可序列化指标值。
"""



from zilli.training.distillation import DistillationSample, DistillationScheduler


def _s(exec_reward=0.5, plan_reward=0.8):
    return DistillationSample(
        executor_action={"tool": "write"},
        planner_action={"tool": "write"},
        executor_log_prob=-1.0,
        planner_log_prob=-1.5,
        executor_reward=exec_reward,
        planner_reward=plan_reward,
        executor_embedding=[0.1, 0.2],
        planner_embedding=[0.3, 0.4],
    )


class TestDistillationEdges:
    def test_bc_loss_empty_returns_zero(self):
        sched = DistillationScheduler()
        bc, kl = sched.compute_bc_loss([], [])
        assert bc == 0.0
        assert kl == 0.0

    def test_rl_loss_empty_returns_zero(self):
        sched = DistillationScheduler()
        assert sched.compute_rl_loss([], []) == 0.0

    def test_should_distill_empty_buffer_false(self):
        sched = DistillationScheduler()
        assert sched.should_distill() is False

    def test_gpu_fallback_to_cpu(self, monkeypatch):
        sched = DistillationScheduler()
        sched.compute_loss_torch = lambda buf: None
        sched.add_batch([_s() for _ in range(5)])
        cycle = sched.run_cycle()
        assert cycle is not None
        assert isinstance(cycle.total_loss, float)

    def test_full_sft_callback_error_is_swallowed(self, tmp_path):
        def boom(buf):
            raise RuntimeError("full sft blew up")

        sched = DistillationScheduler(
            log_dir=str(tmp_path),
            full_sft_interval_days=0,
            lora_threshold=10**9,
            full_sft_callback=boom,
        )
        sched.add_batch([_s() for _ in range(5)])
        cycle = sched.run_cycle()
        assert "full_sft_error" in cycle.metrics
        assert cycle.metrics["full_sft_error"].startswith("full sft blew up")
        assert sched._full_sft_events == 1

    def test_lora_callback_error_is_swallowed(self, tmp_path):
        def boom(buf):
            raise RuntimeError("lora blew up")

        sched = DistillationScheduler(
            log_dir=str(tmp_path),
            lora_threshold=1,
            distill_interval_hours=0,
            lora_callback=boom,
        )
        sched.add_batch([_s() for _ in range(3)])
        cycle = sched.run_cycle()
        assert "lora_error" in cycle.metrics
        assert cycle.metrics["lora_error"].startswith("lora blew up")
        assert sched._lora_events == 1

    def test_cycle_with_both_callbacks_success(self, tmp_path):
        captured = {}

        def full_cb(buf):
            captured["full"] = len(buf)

        def lora_cb(buf):
            captured["lora"] = len(buf)

        sched = DistillationScheduler(
            log_dir=str(tmp_path),
            full_sft_interval_days=0,
            lora_threshold=1,
            distill_interval_hours=0,
            full_sft_callback=full_cb,
            lora_callback=lora_cb,
        )
        sched.add_batch([_s() for _ in range(3)])
        cycle = sched.run_cycle()
        assert cycle.lora_triggered is True
        assert "full_sft_result" in cycle.metrics
        assert captured == {"full": 3, "lora": 3}
        assert sched._full_sft_events == 1
        assert sched._lora_events == 1

    def test_save_checkpoint_with_unsafe_sample_value(self, tmp_path):
        sched = DistillationScheduler(log_dir=str(tmp_path))
        s = _s()
        s.executor_embedding = object()
        sched.add_batch([s])
        path = sched.save_checkpoint(str(tmp_path / "unsafe.json"))
        import json

        with open(path) as f:
            data = json.load(f)
        assert data["state"]["buffer"][0]["executor_embedding"].startswith("<")

    def test_add_batch_empty_is_noop(self, tmp_path):
        sched = DistillationScheduler(log_dir=str(tmp_path))
        sched.add_batch([])
        assert sched.run_cycle() is None
