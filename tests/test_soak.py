import asyncio
import json

from zilli.soak import SoakHealth, SoakRunner


class _FakePipeline:
    def __init__(self, fail_times: int = 0):
        self._fail_times = fail_times
        self._calls = 0

    async def run_cycle(self):
        self._calls += 1
        if self._calls <= self._fail_times:
            raise RuntimeError(f"boom {self._calls}")
        from zilli.pipeline.evolve_to_train import CycleRecord, EvolveTrainStage
        return [CycleRecord(stage=EvolveTrainStage.EVOLVE, success=True, message="ok")]

    def summary(self):
        return {"champion_model": "fake-v1"}


def _run(coro):
    return asyncio.run(coro)


class TestSoakRunner:
    def test_completes_cycles(self, tmp_path):
        runner = SoakRunner(_FakePipeline(), interval_sec=0.01,
                            status_path=str(tmp_path / "s.json"),
                            metrics_path=str(tmp_path / "m.jsonl"))
        health = _run(runner.run(max_duration_sec=0.05))
        assert health.cycles_completed >= 1
        assert health.cycles_failed == 0
        assert health.healthy

    def test_recovers_from_failures(self, tmp_path):
        runner = SoakRunner(_FakePipeline(fail_times=2), interval_sec=0.01,
                            status_path=str(tmp_path / "s.json"),
                            metrics_path=str(tmp_path / "m.jsonl"),
                            backoff_base_sec=0.01)
        health = _run(runner.run(max_duration_sec=1.0))
        assert health.cycles_failed == 2
        assert health.consecutive_failures == 0

    def test_stops_after_max_consecutive_failures(self, tmp_path):
        runner = SoakRunner(_FakePipeline(fail_times=100), interval_sec=0.01,
                            status_path=str(tmp_path / "s.json"),
                            metrics_path=str(tmp_path / "m.jsonl"),
                            max_consecutive_failures=2,
                            backoff_base_sec=0.01)
        health = _run(runner.run(max_duration_sec=30))
        assert health.consecutive_failures == 2
        assert not health.healthy
        assert health.last_error.startswith("boom")

    def test_status_file_written(self, tmp_path):
        status = tmp_path / "status.json"
        runner = SoakRunner(_FakePipeline(), interval_sec=0.01,
                            status_path=str(status),
                            metrics_path=str(tmp_path / "m.jsonl"))
        _run(runner.run(max_duration_sec=0.05))
        data = json.loads(status.read_text())
        assert data["cycles_completed"] >= 1
        assert data["healthy"] is True

    def test_metrics_appended(self, tmp_path):
        metrics = tmp_path / "metrics.jsonl"
        runner = SoakRunner(_FakePipeline(fail_times=1), interval_sec=0.01,
                            status_path=str(tmp_path / "s.json"),
                            metrics_path=str(metrics),
                            backoff_base_sec=0.01)
        _run(runner.run(max_duration_sec=0.3))
        lines = metrics.read_text().strip().split("\n")
        events = [json.loads(line)["event"] for line in lines]
        assert "cycle_error" in events
        assert "cycle_ok" in events

    def test_stop_file_terminates(self, tmp_path):
        stop = tmp_path / "STOP"
        stop.touch()
        runner = SoakRunner(_FakePipeline(), interval_sec=0.01,
                            status_path=str(tmp_path / "s.json"),
                            metrics_path=str(tmp_path / "m.jsonl"))
        health = _run(runner.run(stop_file=str(stop)))
        assert health.cycles_completed == 0

    def test_champion_tracked(self, tmp_path):
        runner = SoakRunner(_FakePipeline(), interval_sec=0.01,
                            status_path=str(tmp_path / "s.json"),
                            metrics_path=str(tmp_path / "m.jsonl"))
        health = _run(runner.run(max_duration_sec=0.05))
        assert health.last_champion == "fake-v1"


class TestSoakHealth:
    def test_defaults(self):
        h = SoakHealth()
        assert h.healthy
        assert h.cycles_completed == 0
        d = h.to_dict()
        assert d["consecutive_failures"] == 0

    def test_unhealthy_after_3_failures(self):
        h = SoakHealth(consecutive_failures=3)
        assert not h.healthy
