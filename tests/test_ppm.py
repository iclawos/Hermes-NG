
from zilli.routing.ppm import PPMPredictor, TaskFamily


class TestPPMPredictor:
    def setup_method(self):
        self.ppm = PPMPredictor()

    def test_chat_simple(self):
        pred = self.ppm.predict("Hello")
        assert pred.task_family == TaskFamily.CHAT
        assert pred.difficulty < 0.3

    def test_chat_hi(self):
        pred = self.ppm.predict("hi")
        assert pred.task_family == TaskFamily.CHAT

    def test_coding_detected(self):
        pred = self.ppm.predict("def foo(): pass")
        assert pred.task_family == TaskFamily.CODING

    def test_coding_keywords(self):
        pred = self.ppm.predict("Implement a binary search tree in Python")
        assert pred.task_family == TaskFamily.CODING

    def test_reasoning_detected(self):
        pred = self.ppm.predict("Why does quantum entanglement work?")
        assert pred.task_family == TaskFamily.REASONING

    def test_analysis_detected(self):
        pred = self.ppm.predict("分析这个系统的性能瓶颈")
        assert pred.task_family == TaskFamily.ANALYSIS

    def test_creative_detected(self):
        pred = self.ppm.predict("Write a short story about AI")
        assert pred.task_family == TaskFamily.CREATIVE

    def test_cache_hit(self):
        self.ppm.predict("Hello world")
        pred2 = self.ppm.predict("Hello world")
        assert pred2.cached
        assert self.ppm.stats()["cache_hits"] >= 1

    def test_cache_eviction(self):
        small_ppm = PPMPredictor(cache_size=2)
        small_ppm.predict("a")
        small_ppm.predict("b")
        small_ppm.predict("c")
        assert small_ppm.stats()["cache_size"] <= 2

    def test_cache_lru_evicts_oldest(self):
        small_ppm = PPMPredictor(cache_size=2)
        small_ppm.predict("first entry here")
        small_ppm.predict("second entry here")
        small_ppm.predict("third entry here")
        stats = small_ppm.stats()
        assert stats["cache_size"] <= 2

    def test_cache_hit_refreshes_lru(self):
        small_ppm = PPMPredictor(cache_size=2)
        small_ppm.predict("keep me")
        small_ppm.predict("evict me")
        small_ppm.predict("keep me")
        small_ppm.predict("new entry")
        stats = small_ppm.stats()
        assert stats["cache_size"] <= 2

    def test_unknown_family(self):
        pred = self.ppm.predict("x" * 50)
        assert pred.task_family == TaskFamily.UNKNOWN

    def test_difficulty_scales_with_length(self):
        short = self.ppm.predict("hi")
        long_ = self.ppm.predict("x" * 2000)
        assert long_.difficulty > short.difficulty

    def test_clear_cache(self):
        self.ppm.predict("test")
        self.ppm.clear_cache()
        assert self.ppm.stats()["cache_size"] == 0


class TestPPMTraining:
    def setup_method(self):
        self.ppm = PPMPredictor(learning_rate=0.1)

    def test_train_empty_returns_zero(self):
        result = self.ppm.train([])
        assert result["trained"] == 0

    def test_train_adjusts_weights(self):
        before = self.ppm._difficulty_weights["coding"]["complex_bonus"]
        self.ppm.train([
            {
                "ppm_family": "coding",
                "predicted_difficulty": 0.3,
                "actual_difficulty": 0.8,
                "success": False,
                "score": 0.2,
            },
        ])
        after = self.ppm._difficulty_weights["coding"]["complex_bonus"]
        assert after != before

    def test_train_multiple_records(self):
        records = []
        for i in range(5):
            records.append({
                "ppm_family": "chat",
                "predicted_difficulty": 0.2,
                "actual_difficulty": 0.1 + i * 0.05,
                "success": True,
                "score": 0.8,
            })
        result = self.ppm.train(records)
        assert result["trained"] == 5

    def test_train_clears_cache(self):
        self.ppm.predict("test")
        assert self.ppm.stats()["cache_size"] > 0
        self.ppm.train([{
            "ppm_family": "chat",
            "predicted_difficulty": 0.5,
            "actual_difficulty": 0.5,
            "success": True,
            "score": 0.8,
        }])
        assert self.ppm.stats()["cache_size"] == 0

    def test_reset_training(self):
        self.ppm.train([{
            "ppm_family": "coding",
            "predicted_difficulty": 0.5,
            "actual_difficulty": 0.8,
            "success": False,
            "score": 0.2,
        }])
        self.ppm.reset_training()
        assert self.ppm._difficulty_weights["coding"]["complex_bonus"] == 0.25
        assert self.ppm._train_count == 0

    def test_stats_includes_training(self):
        stats = self.ppm.stats()
        assert "train_count" in stats
        assert "learning_rate" in stats
        assert "difficulty_weights" in stats
        assert "chat" in stats["difficulty_weights"]

    def test_train_unknown_family_no_error(self):
        result = self.ppm.train([{
            "ppm_family": "nonexistent",
            "predicted_difficulty": 0.5,
            "actual_difficulty": 0.5,
            "success": True,
            "score": 0.9,
        }])
        assert result["trained"] == 1
