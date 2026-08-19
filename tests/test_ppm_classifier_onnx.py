"""SklearnONNXClassifier 加载/预测错误路径测试（mock onnxruntime）。

覆盖纯 joblib 分支以外的 ONNX 路径：模型对缺失、onnxruntime 缺失、
_predict_onnx 的 dict/list probs、joblib 无 predict_proba 回退等。
"""

import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from zilli.routing.ppm import TaskFamily
from zilli.routing.ppm_classifier import SklearnONNXClassifier


class FakeInput:
    name = "text"


class FakeSession:
    def __init__(self, family_label="coding", diff=0.4, probs=None):
        self._family = family_label
        self._diff = diff
        self._probs = probs

    def get_inputs(self):
        return [FakeInput()]

    def run(self, _, feed):
        if self._probs is not None:
            return [[self._family], [self._probs]]
        return [[self._family]]


class FakeDiffSession(FakeSession):
    def run(self, _, feed):
        return [[self._diff]]


def _write_onnx_pair(d: Path, family="coding", diff=0.4, probs=None):
    fam_path = d / "model_family.onnx"
    diff_path = d / "model_difficulty.onnx"
    (d / "model.onnx").write_bytes(b"base")
    fam_path.write_bytes(b"family")
    diff_path.write_bytes(b"difficulty")
    sessions = {
        str(fam_path): FakeSession(family_label=family, diff=diff, probs=probs),
        str(diff_path): FakeDiffSession(diff=diff),
    }

    def _install():
        fake = ModuleType("onnxruntime")
        fake.InferenceSession = lambda path: sessions.get(
            path, FakeSession(family_label=family, diff=diff, probs=probs))
        sys.modules["onnxruntime"] = fake

    return fam_path, diff_path, _install


def test_missing_model_file():
    with pytest.raises(FileNotFoundError, match="Model not found"):
        SklearnONNXClassifier("/nonexistent/model.onnx")


def test_onnx_pair_incomplete(tmp_path):
    (tmp_path / "model_family.onnx").write_bytes(b"f")
    fam_path, _, install = _write_onnx_pair(tmp_path)
    install()
    # 只保留 family，删除 difficulty
    (tmp_path / "model_difficulty.onnx").unlink()
    with pytest.raises(FileNotFoundError, match="pair incomplete"):
        SklearnONNXClassifier(str(tmp_path / "model.onnx"))


def test_onnxruntime_missing(tmp_path, monkeypatch):
    fam_path, _, _ = _write_onnx_pair(tmp_path)
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "onnxruntime":
            raise ImportError("onnxruntime not installed (simulated)")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ImportError, match="onnxruntime"):
        SklearnONNXClassifier(str(tmp_path / "model.onnx"))


def test_onnx_load_predict_plain(tmp_path):
    fam_path, _, install = _write_onnx_pair(tmp_path, family="coding", diff=0.4)
    install()
    c = SklearnONNXClassifier(str(tmp_path / "model.onnx"))
    pred = c.classify("def foo(): pass")
    assert pred.task_family == TaskFamily.CODING
    assert pred.difficulty == pytest.approx(0.4)


def test_onnx_predict_unknown_family(tmp_path):
    fam_path, _, install = _write_onnx_pair(tmp_path, family="nonsense", diff=0.4)
    install()
    c = SklearnONNXClassifier(str(tmp_path / "model.onnx"))
    pred = c.classify("anything")
    assert pred.task_family == TaskFamily.UNKNOWN


def test_onnx_predict_bytes_label(tmp_path):
    fam_path, _, install = _write_onnx_pair(tmp_path, family=b"creative", diff=0.2)
    install()
    c = SklearnONNXClassifier(str(tmp_path / "model.onnx"))
    pred = c.classify("write a poem")
    assert pred.task_family == TaskFamily.CREATIVE


def test_onnx_predict_probs_dict_confidence(tmp_path):
    fam_path, _, install = _write_onnx_pair(
        tmp_path, probs={"coding": 0.1, "reasoning": 0.9})
    install()
    c = SklearnONNXClassifier(str(tmp_path / "model.onnx"))
    pred = c.classify("why does x")
    assert pred.confidence == pytest.approx(0.9)


def test_onnx_predict_probs_list_confidence(tmp_path):
    fam_path, _, install = _write_onnx_pair(tmp_path, probs=[0.2, 0.8])
    install()
    c = SklearnONNXClassifier(str(tmp_path / "model.onnx"))
    pred = c.classify("why does x")
    assert pred.confidence == pytest.approx(0.8)


def test_onnx_metadata_from_sidecar(tmp_path):
    fam_path, _, install = _write_onnx_pair(tmp_path)
    meta = {"version": "9.9.9", "num_samples": 5, "accuracy": 0.99,
            "feature_dim": 128, "exported_at": "2026-01-01"}
    (tmp_path / "model_metadata.json").write_text(json.dumps(meta))
    install()
    c = SklearnONNXClassifier(str(tmp_path / "model.onnx"))
    assert c.metadata().version == "9.9.9"


def test_onnx_metadata_default(tmp_path):
    fam_path, _, install = _write_onnx_pair(tmp_path)
    install()
    c = SklearnONNXClassifier(str(tmp_path / "model.onnx"))
    m = c.metadata()
    assert m.version == "0.0.0"
    assert m.num_samples == 0


def test_classify_before_load_raises():
    c = SklearnONNXClassifier(None)
    with pytest.raises(RuntimeError, match="not loaded"):
        c.classify("hello")


class _NoProbaClf:
    def predict(self, texts):
        return ["chat"]


class _NoProbaReg:
    def predict(self, texts):
        return [0.3]


def test_joblib_without_predict_proba_uses_default_confidence(tmp_path):
    """joblib 管道无 predict_proba 时置信度回退 0.8。"""
    import joblib

    model_path = str(tmp_path / "m.joblib")
    joblib.dump({"family_clf": _NoProbaClf(), "diff_reg": _NoProbaReg()}, model_path)
    c = SklearnONNXClassifier(model_path)
    pred = c.classify("hi")
    assert pred.task_family == TaskFamily.CHAT
    assert pred.confidence == 0.8
