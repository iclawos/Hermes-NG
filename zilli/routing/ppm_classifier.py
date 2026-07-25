from __future__ import annotations

import json
import logging
import re
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np

from zilli.routing.ppm_types import PPMPrediction, TaskFamily

logger = logging.getLogger("zilli.routing.ppm_classifier")


def _try_import_rust():
    """Import the Rust hotpath extension if installed."""
    try:
        import zilli_hotpath  # type: ignore[import-not-found]
        return zilli_hotpath
    except ImportError:
        return None


_SIMPLE_PATTERNS = re.compile(
    r"(?i)^(你好|hello|hi|hey|bye|thanks|yes|no|ok|good|bad|\d+\s*[+\-*/]\s*\d+)$"
)
_COMPLEX_KEYWORDS = re.compile(
    r"(?i)(复杂|分析|设计|规划|审计|合规|诊断|方案|架构|"
    r"complex|analy|design|plan|audit|compliance|diagnos|architect|strateg)"
)
_CODE_KEYWORDS = re.compile(
    r"(?i)(def |class |function|import |const |var |fn |impl |"
    r"代码|函数|实现|bug|重构|refactor|debug|compile|type |"
    r"algorithm|implement|binary|tree|sort|search|recursion|"
    r"api|endpoint|route|middleware|database|sql|query|"
    r"thread|process|异步|并发|parallel|distributed)"
)
_REASONING_KEYWORDS = re.compile(
    r"(?i)(为什么|how|why|explain|证明|推导|推理|reason|proof|compare|difference)"
)
_CREATIVE_KEYWORDS = re.compile(
    r"(?i)(写[一一个]|创作|story|poem|创意|设计[一一个]|write|draft|compose)"
)
_ANALYSIS_KEYWORDS = re.compile(
    r"(?i)(分析|audit|review|assess|evaluate|研究|research|investigate|survey|report)"
)


@dataclass
class ClassifierMetadata:
    version: str
    num_samples: int
    accuracy: float
    feature_dim: int
    exported_at: str


class PPMClassifier(ABC):
    @abstractmethod
    def classify(self, text: str, context: Optional[dict] = None) -> PPMPrediction:
        ...

    @abstractmethod
    def metadata(self) -> ClassifierMetadata:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...


class RegexClassifier(PPMClassifier):
    def __init__(
        self,
        difficulty_weights: Optional[dict[str, dict[str, float]]] = None,
    ):
        self._difficulty_weights = difficulty_weights or {
            "chat": {"length_weight": 1.0, "keyword_bonus": 0.0},
            "coding": {"length_weight": 1.0, "complex_bonus": 0.25, "arch_bonus": 0.1},
            "reasoning": {"length_weight": 1.0, "math_bonus": 0.15, "analysis_bonus": 0.1},
            "analysis": {"length_weight": 1.0, "family_bonus": 0.15},
            "creative": {"length_weight": 1.0},
            "unknown": {"length_weight": 1.0},
        }
        self._rust = _try_import_rust()

    @property
    def name(self) -> str:
        return "regex+rust" if self._rust else "regex"

    def metadata(self) -> ClassifierMetadata:
        return ClassifierMetadata(
            version="1.0.0",
            num_samples=0,
            accuracy=0.0,
            feature_dim=0,
            exported_at="",
        )

    def classify(self, text: str, context: Optional[dict] = None) -> PPMPrediction:
        if self._rust is not None:
            try:
                p = self._rust.ppm_predict(text)  # type: ignore[attr-defined]
                return PPMPrediction(
                    difficulty=p.difficulty,
                    task_family=TaskFamily(p.task_family),
                    confidence=p.confidence,
                )
            except Exception:
                pass
        family = self._predict_family(text)
        difficulty = self._predict_difficulty(text, family)
        confidence = self._estimate_confidence(text)
        return PPMPrediction(
            difficulty=difficulty,
            task_family=family,
            confidence=confidence,
        )

    def _predict_family(self, text: str) -> TaskFamily:
        if _CODE_KEYWORDS.search(text):
            return TaskFamily.CODING
        if _REASONING_KEYWORDS.search(text):
            return TaskFamily.REASONING
        if _ANALYSIS_KEYWORDS.search(text):
            return TaskFamily.ANALYSIS
        if _CREATIVE_KEYWORDS.search(text):
            return TaskFamily.CREATIVE
        if _SIMPLE_PATTERNS.match(text.strip()):
            return TaskFamily.CHAT
        return TaskFamily.UNKNOWN

    def _predict_difficulty(self, text: str, family: TaskFamily) -> float:
        if _SIMPLE_PATTERNS.match(text.strip()):
            return 0.1

        score = 0.0
        default_weights = {"length_weight": 1.0}
        w = self._difficulty_weights.get(
            family.value,
            self._difficulty_weights.get("unknown", default_weights),
        )

        score += min(len(text) / 2000, 0.3) * w["length_weight"]
        score += 0.15 * w.get("keyword_bonus", 0.0) if _COMPLEX_KEYWORDS.search(text) else 0.0

        if family == TaskFamily.CODING:
            score += 0.1
            if re.search(r"(?i)(algorithm|optimize|distributed|parallel|concurrent)", text):
                score += 0.15 * w.get("complex_bonus", 1.0)
            if re.search(r"(?i)(架构|设计模式|design pattern|architecture)", text):
                score += 0.1 * w.get("arch_bonus", 1.0)
        elif family == TaskFamily.REASONING:
            score += 0.1
            if re.search(r"(?i)(proof|theorem|推导|数学|math|calculus)", text):
                score += 0.15 * w.get("math_bonus", 1.0)
            if re.search(r"(?i)(compare|analysis|thorough|comprehensive)", text):
                score += 0.1 * w.get("analysis_bonus", 1.0)
        elif family == TaskFamily.ANALYSIS:
            score += 0.15 * w.get("family_bonus", 1.0)
        elif family == TaskFamily.CHAT:
            score -= 0.1

        return max(0.0, min(1.0, score))

    @staticmethod
    def _estimate_confidence(text: str) -> float:
        length = len(text)
        if length < 10:
            return 0.95
        if length > 500:
            return 0.6
        return 0.8


class SklearnONNXClassifier(PPMClassifier):
    """Model-based PPM classifier.

    Two runtime formats:
    - joblib: dict of sklearn Pipelines (text → tfidf → predict end-to-end)
    - onnx:   two sessions (family + difficulty) taking raw string input
    """

    def __init__(self, model_path: Optional[str] = None):
        self._model_path = model_path
        self._pipelines: Any = None
        self._fam_session: Any = None
        self._diff_session: Any = None
        self._metadata_cache: Optional[ClassifierMetadata] = None

        if model_path:
            self._load(model_path)

    @property
    def name(self) -> str:
        return "sklearn_onnx"

    def _load(self, model_path: str) -> None:
        p = Path(model_path)
        if not p.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")
        metadata_path = p.parent / f"{p.stem}_metadata.json"
        if metadata_path.exists():
            with open(metadata_path) as f:
                data = json.load(f)
            self._metadata_cache = ClassifierMetadata(**data)

        if p.suffix in (".joblib", ".pkl"):
            import joblib
            self._pipelines = joblib.load(model_path)
            return

        fam_path = p
        diff_path = p.parent / f"{p.stem.replace('_family', '')}_difficulty.onnx"
        if p.stem.endswith("_family"):
            diff_path = p.parent / f"{p.stem[:-7]}_difficulty.onnx"
        elif p.stem.endswith("_difficulty"):
            fam_path = p.parent / f"{p.stem[:-11]}_family.onnx"

        if not diff_path.exists() or not fam_path.exists():
            raise FileNotFoundError(
                f"ONNX model pair incomplete: need both *_family.onnx and *_difficulty.onnx "
                f"(checked {fam_path}, {diff_path})"
            )

        try:
            import onnxruntime as ort
        except ImportError:
            raise ImportError("onnxruntime is required for ONNX inference")
        self._fam_session = ort.InferenceSession(str(fam_path))
        self._diff_session = ort.InferenceSession(str(diff_path))

    def _ensure_loaded(self) -> None:
        if self._pipelines is None and self._fam_session is None:
            raise RuntimeError("Model not loaded. Call load() or provide model_path.")

    def metadata(self) -> ClassifierMetadata:
        if self._metadata_cache:
            return self._metadata_cache
        return ClassifierMetadata(
            version="0.0.0",
            num_samples=0,
            accuracy=0.0,
            feature_dim=0,
            exported_at="",
        )

    def classify(self, text: str, context: Optional[dict] = None) -> PPMPrediction:
        self._ensure_loaded()
        if self._pipelines is not None:
            return self._predict_joblib(text)
        return self._predict_onnx(text)

    def _predict_joblib(self, text: str) -> PPMPrediction:
        family_clf = self._pipelines["family_clf"]
        diff_reg = self._pipelines["diff_reg"]

        family = str(family_clf.predict([text])[0])
        difficulty = float(diff_reg.predict([text])[0])

        if hasattr(family_clf, "predict_proba"):
            probs = family_clf.predict_proba([text])[0]
            confidence = float(probs.max())
        else:
            confidence = 0.8

        return PPMPrediction(
            difficulty=max(0.0, min(1.0, difficulty)),
            task_family=TaskFamily(family) if family in TaskFamily._value2member_map_ else TaskFamily.UNKNOWN,
            confidence=confidence,
        )

    def _predict_onnx(self, text: str) -> PPMPrediction:
        inp_f = self._fam_session.get_inputs()[0].name
        inp_d = self._diff_session.get_inputs()[0].name
        text_arr = np.array([[text]], dtype=object)

        fam_out = self._fam_session.run(None, {inp_f: text_arr})
        diff_out = self._diff_session.run(None, {inp_d: text_arr})

        family_label = fam_out[0][0]
        family = str(family_label if not isinstance(family_label, bytes) else family_label.decode())

        difficulty_raw = diff_out[0]
        difficulty = float(np.ravel(difficulty_raw)[0])

        confidence = 0.8
        if len(fam_out) > 1:
            probs_raw = fam_out[1][0]
            if isinstance(probs_raw, dict):
                probs = np.array(list(probs_raw.values()), dtype=float)
            else:
                probs = np.ravel(probs_raw)
            if len(probs):
                confidence = float(np.max(probs))

        return PPMPrediction(
            difficulty=max(0.0, min(1.0, difficulty)),
            task_family=TaskFamily(family) if family in TaskFamily._value2member_map_ else TaskFamily.UNKNOWN,
            confidence=confidence,
        )

    @classmethod
    def train(
        cls,
        records: list[dict],
        output_path: str,
        test_size: float = 0.2,
    ) -> dict:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.linear_model import LogisticRegression, Ridge
            from sklearn.metrics import accuracy_score, mean_squared_error
            from sklearn.model_selection import train_test_split
            from sklearn.pipeline import Pipeline

            try:
                from skl2onnx import convert_sklearn
                from skl2onnx.common.data_types import StringTensorType
            except ImportError:
                logger.warning("skl2onnx not available; fallback to sklearn pipeline")
                convert_sklearn = None
        except ImportError:
            raise ImportError("sklearn and skl2onnx are required for training")

        texts = [r.get("request", r.get("text", "")) for r in records]
        family_labels = [r.get("ppm_family", "unknown") for r in records]
        difficulty_targets = [r.get("actual_difficulty", r.get("difficulty", 0.5)) for r in records]

        texts_train, texts_test, fam_train, fam_test, diff_train, diff_test = train_test_split(
            texts, family_labels, difficulty_targets, test_size=test_size, random_state=42
        )

        family_clf = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 3), max_features=5000, sublinear_tf=True)),
            ("clf", LogisticRegression(max_iter=1000, C=1.0)),
        ])
        family_clf.fit(texts_train, fam_train)
        fam_acc = accuracy_score(fam_test, family_clf.predict(texts_test))

        diff_reg = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 3), max_features=5000, sublinear_tf=True)),
            ("reg", Ridge(alpha=1.0)),
        ])
        diff_reg.fit(texts_train, diff_train)
        diff_mse = mean_squared_error(diff_test, diff_reg.predict(texts_test))

        if convert_sklearn is not None:
            initial_type = [("text", StringTensorType([1, 1]))]  # type: ignore
            family_onnx = convert_sklearn(family_clf, initial_types=initial_type)
            diff_onnx = convert_sklearn(diff_reg, initial_types=initial_type)

            with tempfile.TemporaryDirectory() as tmp:
                fam_path = Path(tmp) / "family.onnx"
                diff_path = Path(tmp) / "difficulty.onnx"
                with open(fam_path, "wb") as f:
                    f.write(family_onnx.SerializeToString())  # type: ignore[attr-defined]
                with open(diff_path, "wb") as f:
                    f.write(diff_onnx.SerializeToString())  # type: ignore[attr-defined]

                out = Path(output_path)
                out.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copy2(fam_path, out.parent / f"{out.stem}_family.onnx")
                shutil.copy2(diff_path, out.parent / f"{out.stem}_difficulty.onnx")

            metadata = ClassifierMetadata(
                version="1.0.0",
                num_samples=len(records),
                accuracy=round(float(fam_acc), 4),
                feature_dim=5000,
                exported_at=__import__("time").strftime("%Y-%m-%dT%H:%M:%S"),
            )
            meta_path = out.parent / f"{out.stem}_metadata.json"
            with open(meta_path, "w") as f:
                json.dump(metadata.__dict__, f, indent=2)
        else:
            import joblib
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump({"family_clf": family_clf, "diff_reg": diff_reg}, output_path)

        return {
            "num_samples": len(records),
            "family_accuracy": round(float(fam_acc), 4),
            "difficulty_rmse": round(float(diff_mse ** 0.5), 4),
            "output_path": output_path,
        }


def train_classifier(
    records: list[dict],
    output_path: str = "ppm_model.onnx",
    classifier_type: str = "sklearn",
) -> dict:
    if classifier_type == "sklearn":
        return SklearnONNXClassifier.train(records, output_path=output_path)
    raise ValueError(f"Unknown classifier type: {classifier_type}")
