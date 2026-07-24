from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


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


__all__ = ["TaskFamily", "PPMPrediction"]
