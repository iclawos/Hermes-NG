from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger("zilli.routing.ppm")


class TaskFamily(str, Enum):
    CHAT = "chat"
    REASONING = "reasoning"
    CODING = "coding"
    ANALYSIS = "analysis"
    CREATIVE = "creative"
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        return self.value


@dataclass
class PPMPrediction:
    difficulty: float
    task_family: TaskFamily
    confidence: float
    latency_ms: float = 0.0
    cached: bool = False


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


class PPMPredictor:
    def __init__(
        self,
        cache_size: int = 1024,
        timeout_ms: float = 10.0,
    ):
        self._cache: dict[int, PPMPrediction] = {}
        self._cache_size = cache_size
        self._timeout_ms = timeout_ms
        self._call_count = 0
        self._cache_hits = 0

    def _feature_hash(self, text: str) -> int:
        return hash(text[:200].lower().strip())

    def predict(self, text: str, context: Optional[dict] = None) -> PPMPrediction:
        start = time.monotonic()
        key = self._feature_hash(text)
        cached = self._cache.get(key)
        if cached is not None:
            self._cache_hits += 1
            elapsed = (time.monotonic() - start) * 1000
            cached.latency_ms = elapsed
            cached.cached = True
            return cached

        self._call_count += 1

        family = self._predict_family(text)
        difficulty = self._predict_difficulty(text, family)
        confidence = self._estimate_confidence(text)

        pred = PPMPrediction(
            difficulty=difficulty,
            task_family=family,
            confidence=confidence,
        )
        elapsed = (time.monotonic() - start) * 1000
        pred.latency_ms = elapsed

        if len(self._cache) < self._cache_size:
            self._cache[key] = pred
        else:
            self._evict()
            self._cache[key] = pred

        return pred

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

        score += min(len(text) / 2000, 0.3)
        score += 0.15 if _COMPLEX_KEYWORDS.search(text) else 0.0

        if family == TaskFamily.CODING:
            score += 0.1
            if re.search(r"(?i)(algorithm|optimize|distributed|parallel|concurrent)", text):
                score += 0.15
            if re.search(r"(?i)(架构|设计模式|design pattern|architecture)", text):
                score += 0.1
        elif family == TaskFamily.REASONING:
            score += 0.1
            if re.search(r"(?i)(proof|theorem|推导|数学|math|calculus)", text):
                score += 0.15
            if re.search(r"(?i)(compare|analysis|thorough|comprehensive)", text):
                score += 0.1
        elif family == TaskFamily.ANALYSIS:
            score += 0.15
        elif family == TaskFamily.CHAT:
            score -= 0.1

        return max(0.0, min(1.0, score))

    def _estimate_confidence(self, text: str) -> float:
        length = len(text)
        if length < 10:
            return 0.95
        if length > 500:
            return 0.6
        return 0.8

    def _evict(self) -> None:
        if not self._cache:
            return
        oldest = min(self._cache.keys(), key=lambda k: k)
        del self._cache[oldest]

    def stats(self) -> dict:
        return {
            "cache_size": len(self._cache),
            "cache_hits": self._cache_hits,
            "call_count": self._call_count,
            "hit_rate": round(self._cache_hits / max(self._call_count, 1), 4),
        }

    def clear_cache(self) -> None:
        self._cache.clear()


_ANALYSIS_KEYWORDS = re.compile(
    r"(?i)(分析|audit|review|assess|evaluate|研究|research|investigate|survey|report)"
)
