from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

logger = logging.getLogger("zilli.evaluation.meta_evaluator")


@dataclass
class EvaluationSample:
    task_id: str
    features: dict[str, float]
    predicted_score: float
    actual_score: float
    model_name: str = ""
    task_type: str = ""
    timestamp: float = 0.0


@dataclass
class MetaEvaluationResult:
    calibration_error: float
    confidence_interval: tuple[float, float]
    bias: float
    variance: float
    sample_count: int
    reliable: bool
    posterior_mean: float = 0.0
    posterior_std: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)


class MetaEvaluator:
    """Meta-evaluator with Bayesian posterior estimation.

    Uses a Gaussian prior and conjugate update to estimate the
    true error distribution. This replaces simple bias/variance
    statistics with a principled Bayesian approach that handles
    small sample sizes gracefully.
    """

    def __init__(
        self,
        window_size: int = 100,
        reliability_threshold: float = 0.15,
        prior_mean: float = 0.0,
        prior_std: float = 0.5,
        likelihood_std: float = 0.1,
    ):
        self.window_size = window_size
        self.reliability_threshold = reliability_threshold
        self._history: list[EvaluationSample] = []
        self._weights: dict[str, float] = {}
        self._bias_correction: float = 0.0

        self._prior_mean = prior_mean
        self._prior_std = prior_std
        self._likelihood_std = likelihood_std

    def record(self, sample: EvaluationSample) -> None:
        self._history.append(sample)
        if len(self._history) > self.window_size * 3:
            self._history = self._history[-self.window_size * 2:]

    def evaluate(self, recent_n: Optional[int] = None) -> MetaEvaluationResult:
        samples = self._history[-(recent_n or self.window_size):]
        if not samples:
            return MetaEvaluationResult(
                calibration_error=0.0,
                confidence_interval=(0.0, 0.0),
                bias=0.0,
                variance=0.0,
                sample_count=0,
                reliable=False,
                posterior_mean=self._prior_mean,
                posterior_std=self._prior_std,
            )

        predicted = np.array([s.predicted_score for s in samples])
        actual = np.array([s.actual_score for s in samples])
        errors = predicted - actual
        n = len(samples)

        sample_mean = float(np.mean(errors))
        sample_var = float(np.var(errors, ddof=1)) if n > 1 else 0.0

        posterior_mean, posterior_std = self._bayesian_update(
            sample_mean, sample_var, n
        )

        mse = float(np.mean(errors ** 2))
        calibration_error = math.sqrt(mse) if mse > 0 else 0.0

        ci_lower = posterior_mean - 1.96 * posterior_std
        ci_upper = posterior_mean + 1.96 * posterior_std

        reliable = (
            calibration_error < self.reliability_threshold
            and n >= 10
            and posterior_std < 0.3
        )

        self._bias_correction = posterior_mean

        per_model: dict[str, list[float]] = {}
        for s in samples:
            per_model.setdefault(s.model_name, []).append(
                abs(s.predicted_score - s.actual_score)
            )
        model_errors = {m: float(np.mean(errs)) for m, errs in per_model.items()}

        return MetaEvaluationResult(
            calibration_error=round(calibration_error, 4),
            confidence_interval=(round(ci_lower, 4), round(ci_upper, 4)),
            bias=round(posterior_mean, 4),
            variance=round(posterior_std ** 2, 4),
            sample_count=n,
            reliable=reliable,
            posterior_mean=round(posterior_mean, 4),
            posterior_std=round(posterior_std, 4),
            details={"model_errors": model_errors},
        )

    def _bayesian_update(
        self, sample_mean: float, sample_var: float, n: int
    ) -> tuple[float, float]:
        """Conjugate Gaussian update: prior ~ N(prior_mean, prior_std²),
        likelihood ~ N(sample_mean, sample_var/n).
        """
        prior_var = self._prior_std ** 2
        likelihood_var = sample_var / n if n > 0 else self._likelihood_std ** 2

        if likelihood_var <= 0:
            likelihood_var = self._likelihood_std ** 2

        posterior_var = 1.0 / (1.0 / prior_var + 1.0 / likelihood_var)
        posterior_mean = posterior_var * (
            self._prior_mean / prior_var + sample_mean / likelihood_var
        )

        return posterior_mean, math.sqrt(posterior_var)

    def correct_prediction(self, raw_score: float, model_name: str = "") -> float:
        return raw_score - self._bias_correction

    def detect_drift(self, threshold: float = 0.1) -> bool:
        if len(self._history) < self.window_size * 2:
            return False
        old = self._history[-self.window_size * 2:-self.window_size]
        new = self._history[-self.window_size:]
        old_err = np.mean([(s.predicted_score - s.actual_score) ** 2 for s in old])
        new_err = np.mean([(s.predicted_score - s.actual_score) ** 2 for s in new])
        return bool(new_err > old_err * (1 + threshold))

    def feature_importance(self) -> dict[str, float]:
        if len(self._history) < 20:
            return {}
        errors = [abs(s.predicted_score - s.actual_score) for s in self._history[-self.window_size:]]
        all_features: dict[str, list[float]] = {}
        for s in self._history[-self.window_size:]:
            for k, v in s.features.items():
                all_features.setdefault(k, []).append(v)

        importance: dict[str, float] = {}
        err_arr = np.array(errors)
        for feat_name, feat_vals in all_features.items():
            feat_arr = np.array(feat_vals)
            if np.std(feat_arr) > 0 and len(feat_arr) == len(err_arr):
                corr = float(np.abs(np.corrcoef(feat_arr, err_arr)[0, 1]))
                importance[feat_name] = round(corr, 4) if not math.isnan(corr) else 0.0
        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))

    def summary(self) -> dict[str, Any]:
        result = self.evaluate()
        return {
            "calibration_error": result.calibration_error,
            "bias": result.bias,
            "variance": result.variance,
            "reliable": result.reliable,
            "sample_count": result.sample_count,
            "posterior_mean": result.posterior_mean,
            "posterior_std": result.posterior_std,
            "drift_detected": self.detect_drift(),
            "feature_importance": self.feature_importance(),
        }


__all__ = ["MetaEvaluator", "EvaluationSample", "MetaEvaluationResult"]
