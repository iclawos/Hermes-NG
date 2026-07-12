
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
