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

    def test_batch_size_triggers_early_flush(self):
        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                path = str(Path(tmp) / "feedback.jsonl")
                collector = FeedbackCollector(persist_path=path, batch_size=5,
                                              flush_interval_seconds=3600)
                for i in range(5):
                    collector.record(FeedbackRecord(
                        request_id=f"r{i}", ppm_difficulty=0.3, ppm_family="chat",
                        selected_model="m1", strategy_tier="economy",
                        actual_latency_ms=50, actual_cost=0.001,
                    ))
                deadline = asyncio.get_event_loop().time() + 5.0
                while not Path(path).exists():
                    if asyncio.get_event_loop().time() > deadline:
                        raise TimeoutError("flush did not persist in 5s")
                    await asyncio.sleep(0.05)
                lines = Path(path).read_text().strip().split("\n")
                assert len(lines) == 5

        asyncio.run(run())

    def test_record_without_running_loop_no_crash(self):
        collector = FeedbackCollector(batch_size=2)
        for i in range(3):
            collector.record(FeedbackRecord(
                request_id=f"r{i}", ppm_difficulty=0.3, ppm_family="chat",
                selected_model="m1", strategy_tier="economy",
                actual_latency_ms=50, actual_cost=0.001,
            ))
        asyncio.run(collector.flush())


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


class TestFeedbackEvaluatorLLMScore:
    def test_llm_score_parses_rating(self):
        ev = FeedbackEvaluator()

        async def fake_llm(prompt):
            return type("FakeResult", (), {"text": "Rating: 0.85"})()

        score = asyncio.run(ev.llm_score("hi", "hello world", fake_llm))
        assert score == 0.85

    def test_llm_score_fallback_on_no_match(self):
        ev = FeedbackEvaluator()

        async def fake_llm(prompt):
            return type("FakeResult", (), {"text": "This is a great response"})()

        score = asyncio.run(ev.llm_score("Q", "A nice answer", fake_llm))
        assert score >= 0.0

    def test_llm_score_fallback_on_exception(self):
        ev = FeedbackEvaluator()

        async def broken_llm(prompt):
            raise RuntimeError("LLM unavailable")

        score = asyncio.run(ev.llm_score("Q", "A", broken_llm))
        assert score >= 0.0
        assert ev.stats()["llm_fallbacks"] >= 1

    def test_llm_score_parses_string_return(self):
        ev = FeedbackEvaluator()

        async def fake_llm(prompt):
            return "Rating: 0.92"

        score = asyncio.run(ev.llm_score("Q", "A", fake_llm))
        assert score == 0.92

    def test_llm_score_clamps_range(self):
        ev = FeedbackEvaluator()

        async def fake_llm(prompt):
            return type("FakeResult", (), {"text": "Rating: 99.0"})()

        score = asyncio.run(ev.llm_score("Q", "A", fake_llm))
        assert score == 1.0

    def test_llm_score_stats(self):
        ev = FeedbackEvaluator()
        assert "llm_calls" in ev.stats()
        assert "llm_fallbacks" in ev.stats()
        assert "llm_cache_size" in ev.stats()

    def test_llm_score_cache_hit(self):
        ev = FeedbackEvaluator()

        async def fake_llm(prompt):
            return "Rating: 0.75"

        score1 = asyncio.run(ev.llm_score("hello", "world", fake_llm))
        score2 = asyncio.run(ev.llm_score("hello", "world", fake_llm))
        assert score1 == score2 == 0.75
        assert ev.stats()["llm_cache_size"] >= 1

    def test_llm_score_cache_eviction(self):
        ev = FeedbackEvaluator(llm_score_cache_size=2)

        async def fake_llm(prompt):
            return "Rating: 0.5"

        for i in range(5):
            asyncio.run(ev.llm_score(f"q{i}", f"a{i}", fake_llm))
        assert ev.stats()["llm_cache_size"] <= 2

    def test_start_record_stop_single_loop_persists(self):
        async def run():
            with tempfile.TemporaryDirectory() as tmp:
                path = str(Path(tmp) / "fb.jsonl")
                collector = FeedbackCollector(persist_path=path,
                                              flush_interval_seconds=0.05)
                await collector.start()
                collector.record(FeedbackRecord(
                    request_id="x1", ppm_difficulty=0.3, ppm_family="chat",
                    selected_model="m1", strategy_tier="economy",
                    actual_latency_ms=50, actual_cost=0.001,
                ))
                await asyncio.sleep(0.15)
                await collector.stop()
                assert collector._flush_task is None
                assert "x1" in Path(path).read_text()

        asyncio.run(run())

    def test_persist_failure_does_not_crash(self):
        async def run():
            collector = FeedbackCollector(persist_path="/proc/impossible-dir/fb.jsonl")
            collector.record(FeedbackRecord(
                request_id="p1", ppm_difficulty=0.3, ppm_family="chat",
                selected_model="m1", strategy_tier="economy",
                actual_latency_ms=50, actual_cost=0.001,
            ))
            await collector.flush()  # persist fails silently

        asyncio.run(run())

    def test_llm_score_fallback_on_non_text_result(self):
        ev = FeedbackEvaluator()

        async def fake_llm(prompt):
            return 42

        score = asyncio.run(ev.llm_score("Q", "A decent answer here", fake_llm))
        assert 0.0 <= score <= 1.0
        assert ev._llm_fallback_count == 1
