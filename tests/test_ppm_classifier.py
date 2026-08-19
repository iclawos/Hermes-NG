import json
import tempfile
from pathlib import Path

import pytest

from zilli.routing.ppm import TaskFamily
from zilli.routing.ppm_classifier import (
    ClassifierMetadata,
    PPMClassifier,
    RegexClassifier,
    SklearnONNXClassifier,
    train_classifier,
)


class TestPPMClassifierABC:
    def test_abc_cannot_instantiate(self):
        with pytest.raises(TypeError):
            PPMClassifier()  # type: ignore[abstract]


class TestRegexClassifier:
    def test_name(self):
        c = RegexClassifier()
        assert c.name in ("regex", "regex+rust")

    def test_simple_chat(self):
        c = RegexClassifier()
        pred = c.classify("hello")
        assert pred.task_family == TaskFamily.CHAT
        assert pred.difficulty < 0.5

    def test_coding_detected(self):
        c = RegexClassifier()
        pred = c.classify("def fibonacci(n):")
        assert pred.task_family == TaskFamily.CODING

    def test_reasoning_detected(self):
        c = RegexClassifier()
        pred = c.classify("explain why this happens")
        assert pred.task_family == TaskFamily.REASONING

    def test_analysis_detected(self):
        c = RegexClassifier()
        pred = c.classify("analyze the audit results")
        assert pred.task_family == TaskFamily.ANALYSIS

    def test_creative_detected(self):
        c = RegexClassifier()
        pred = c.classify("write a poem about AI")
        assert pred.task_family == TaskFamily.CREATIVE

    def test_unknown_family(self):
        c = RegexClassifier()
        pred = c.classify("")
        assert pred.task_family == TaskFamily.UNKNOWN

    def test_difficulty_scales_with_length(self):
        c = RegexClassifier()
        short = c.classify("hi")
        long_text = c.classify("this is a very long text " * 100)
        assert long_text.difficulty >= short.difficulty

    def test_confidence_high_for_short(self):
        c = RegexClassifier()
        pred = c.classify("hi")
        assert pred.confidence > 0.9

    def test_confidence_lower_for_long(self):
        c = RegexClassifier()
        pred = c.classify("x" * 600)
        assert pred.confidence < 0.7

    def test_metadata(self):
        c = RegexClassifier()
        meta = c.metadata()
        assert isinstance(meta, ClassifierMetadata)
        assert meta.version == "1.0.0"

    def test_custom_difficulty_weights(self):
        weights = {
            "chat": {"length_weight": 2.0, "keyword_bonus": 0.5},
        }
        c = RegexClassifier(difficulty_weights=weights)
        pred = c.classify("hello there")
        assert pred.difficulty > 0.0


class TestSklearnONNXClassifier:
    @pytest.fixture
    def sample_records(self):
        return [
            {"request": "def hello(): pass", "ppm_family": "coding", "actual_difficulty": 0.3},
            {"request": "what is the meaning", "ppm_family": "reasoning", "actual_difficulty": 0.7},
            {"request": "hello", "ppm_family": "chat", "actual_difficulty": 0.1},
            {"request": "write a story", "ppm_family": "creative", "actual_difficulty": 0.5},
            {"request": "analyze this data", "ppm_family": "analysis", "actual_difficulty": 0.6},
            {"request": "hi how are you", "ppm_family": "chat", "actual_difficulty": 0.1},
            {"request": "implement bst", "ppm_family": "coding", "actual_difficulty": 0.8},
            {"request": "compare theories", "ppm_family": "reasoning", "actual_difficulty": 0.6},
            {"request": "audit finances", "ppm_family": "analysis", "actual_difficulty": 0.7},
            {"request": "design a logo", "ppm_family": "creative", "actual_difficulty": 0.4},
        ]

    def test_train_sklearn_pipeline(self, sample_records):
        with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as f:
            result = SklearnONNXClassifier.train(sample_records, output_path=f.name)
            assert result["num_samples"] == 10
            assert result["family_accuracy"] >= 0.0

    def test_train_sklearn_onnx(self, sample_records):
        with tempfile.TemporaryDirectory() as d:
            output = str(Path(d) / "ppm_model.onnx")
            result = SklearnONNXClassifier.train(sample_records, output_path=output)
            assert result["num_samples"] == 10
            # char_wb analyzer is not ONNX-convertible: expect joblib fallback
            family_path = Path(d) / "ppm_model_family.onnx"
            joblib_path = Path(d) / "ppm_model.joblib"
            meta_path = Path(d) / "ppm_model_metadata.json"
            assert family_path.exists() or joblib_path.exists()
            assert meta_path.exists()
            with open(meta_path) as f:
                meta = json.load(f)
            assert meta["version"] == "1.0.0"
            assert meta["num_samples"] == 10

    def test_load_and_classify(self, sample_records):
        with tempfile.TemporaryDirectory() as d:
            output = str(Path(d) / "ppm_model.joblib")
            SklearnONNXClassifier.train(sample_records, output_path=output)

            classifier = SklearnONNXClassifier(output)
            assert classifier.name == "sklearn_onnx"
            pred = classifier.classify("hello")
            assert pred.task_family is not None
            assert 0.0 <= pred.difficulty <= 1.0

    def test_train_classifier_function(self, sample_records):
        with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as f:
            result = train_classifier(sample_records, output_path=f.name)
            assert result["num_samples"] == 10

    def test_train_classifier_unknown_type(self, sample_records):
        with pytest.raises(ValueError, match="Unknown classifier type"):
            train_classifier(sample_records, classifier_type="unknown")


class TestClassifierIntegration:
    def test_ppm_with_regex_classifier(self):
        from zilli.routing.ppm import PPMPredictor

        p = PPMPredictor(classifier=RegexClassifier())
        pred = p.predict("def foo(): return 1")
        assert pred.task_family == TaskFamily.CODING
        assert p.stats()["classifier"] in ("regex", "regex+rust")

    def test_ppm_default_uses_regex(self):
        from zilli.routing.ppm import PPMPredictor

        p = PPMPredictor()
        pred = p.predict("hello")
        assert pred.task_family == TaskFamily.CHAT
        assert p.stats()["classifier"] in ("regex", "regex+rust", "sklearn_onnx")


class TestRustHotpathParity:
    """zilli_hotpath PyO3 binding must be functionally identical to the
    pure-Python RegexClassifier (family / difficulty / confidence)."""

    SAMPLES = [
        "hello", "hi there", "refactor the auth module",
        "why does this algorithm have O(n^2)?",
        "audit financial compliance",
        "write a story about a robot",
        "2 + 2", "ok",
        "设计微服务架构方案", "请帮我分析这份财报", "写一首诗",
        "异步并发并行分布式系统设计", "prove the theorem using calculus",
        "thanks", "def fibonacci(n):", "explain why this happens",
        "analyze the audit results", "write a poem about AI",
        "生成一份合规审计报告并评估风险", "compare A vs B thoroughly",
    ]

    def test_rust_module_importable(self):
        try:
            import zilli_hotpath
        except ImportError:
            pytest.skip("zilli_hotpath not installed")
        assert hasattr(zilli_hotpath, "ppm_predict")

    def test_rust_parity_with_python(self):
        try:
            import zilli_hotpath
        except ImportError:
            pytest.skip("zilli_hotpath not installed")

        c = RegexClassifier()
        for sample in self.SAMPLES:
            p = zilli_hotpath.ppm_predict(sample)
            fam = c._predict_family(sample)
            diff = c._predict_difficulty(sample, fam)
            conf = c._estimate_confidence(sample)
            assert p.task_family == fam.value, f"{sample!r}: family {p.task_family} != {fam.value}"
            assert abs(p.difficulty - diff) < 1e-9, (
                f"{sample!r}: difficulty {p.difficulty} != {diff}"
            )
            assert abs(p.confidence - conf) < 1e-9, (
                f"{sample!r}: confidence {p.confidence} != {conf}"
            )

    def test_rust_faster_than_python(self):
        try:
            import zilli_hotpath
        except ImportError:
            pytest.skip("zilli_hotpath not installed")
        import random
        import string
        import time

        rng = random.Random(42)
        samples = [
            "".join(rng.choices(string.ascii_letters, k=rng.randint(5, 200)))
            for _ in range(500)
        ]

        c = RegexClassifier()

        t0 = time.perf_counter()
        for s in samples:
            zilli_hotpath.ppm_predict(s)
        rust_ms = (time.perf_counter() - t0) / len(samples) * 1000

        t0 = time.perf_counter()
        for s in samples:
            fam = c._predict_family(s)
            c._predict_difficulty(s, fam)
            c._estimate_confidence(s)
        py_ms = (time.perf_counter() - t0) / len(samples) * 1000

        # Rust hotpath must be ≥ 5x faster than pure-Python (measured ~20x)
        assert rust_ms < py_ms / 5, f"rust {rust_ms:.3f}ms not 5x faster than py {py_ms:.3f}ms"
