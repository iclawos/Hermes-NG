import asyncio
import json
import tempfile
from pathlib import Path

from zilli.routing.feedback import FeedbackCollector, FeedbackEvaluator, FeedbackRecord


class TestFeedbackRecord:
    def test_default_timestamp(self):
        r = FeedbackRecord(request_id="test", ppm_difficulty=0.5, ppm_family="chat",
                           selected_model="m", strategy_tier="standard",
                           actual_latency_ms=100, actual_cost=0.01)
        assert r.timestamp > 0


class TestFeedbackCollector:
    def test_record_and_flush(self):
        collector = FeedbackCollector(batch_size=100, flush_interval_seconds=60)
        collector.record(FeedbackRecord(
            request_id="r1", ppm_difficulty=0.3, ppm_family="chat",
            selected_model="m1", strategy_tier="economy",
            actual_latency_ms=50, actual_cost=0.001,
        ))
        asyncio.run(collector.flush())

    def test_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "feedback.jsonl")
            collector = FeedbackCollector(persist_path=path)
            collector.record(FeedbackRecord(
                request_id="r1", ppm_difficulty=0.3, ppm_family="chat",
                selected_model="m1", strategy_tier="economy",
                actual_latency_ms=50, actual_cost=0.001,
            ))
            asyncio.run(collector.flush())
            lines = Path(path).read_text().strip().split("\n")
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data["request_id"] == "r1"

    def test_start_stop(self):
        collector = FeedbackCollector()
        asyncio.run(collector.start())
        asyncio.run(collector.stop())


class TestFeedbackEvaluator:
    def test_empty_response_scores_low(self):
        ev = FeedbackEvaluator()
        score = ev.auto_score("Hello", "")
        assert score < 0.3

    def test_good_response_scores_higher(self):
        ev = FeedbackEvaluator()
        score = ev.auto_score("Hi", "I am doing well, thank you for asking!")
        assert score > 0.3

    def test_long_response_higher(self):
        ev = FeedbackEvaluator()
        short = ev.auto_score("Q", "A")
        long_ = ev.auto_score("Q", "A" * 1000)
        assert long_ > short
