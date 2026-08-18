"""L6 群智能 — 共识引擎。

四级共识链：多数共识 → 权重投票 → 指定仲裁 → 人工升级。
从廉价到昂贵，按分歧程度自动升级。
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger("zilli.swarm.consensus")


class ConsensusLevel(str, Enum):
    MAJORITY = "majority"
    WEIGHTED = "weighted"
    ARBITER = "arbiter"
    HUMAN = "human"


@dataclass
class ConsensusRecord:
    topic: str
    options: list[str]
    votes: dict[str, float] = field(default_factory=dict)
    level: ConsensusLevel = ConsensusLevel.MAJORITY
    arbiter: str = ""
    human_escalated: bool = False
    resolution: str = ""
    reason: str = ""
    created_at: float = field(default_factory=time.time)


class ConsensusEngine:
    """对多个 Agent 的意见做收敛。

    vote_fn: (topic, options, level) -> list[(option, weight, agent_id)]
    默认走规则多数（每 option 一票）。arbiter_fn 可选。
    """

    def __init__(
        self,
        vote_fn: Optional[Callable[[str, list[str], ConsensusLevel], list[tuple[str, float, str]]]] = None,
        arbiter_fn: Optional[Callable[[str, list[str], list[str]], str]] = None,
        timeout_sec: float = 60.0,
    ) -> None:
        self._vote_fn = vote_fn
        self._arbiter_fn = arbiter_fn
        self.timeout_sec = timeout_sec

    def reach(
        self,
        topic: str,
        options: list[str],
        level: ConsensusLevel = ConsensusLevel.MAJORITY,
    ) -> ConsensusRecord:
        votes: dict[str, float] = {}
        if self._vote_fn is not None:
            for option, weight, _agent in self._vote_fn(topic, options, level):
                votes[option] = votes.get(option, 0.0) + weight
        else:
            for opt in options:
                votes[opt] = votes.get(opt, 0.0) + 1.0

        record = ConsensusRecord(
            topic=topic, options=list(options), votes=votes, level=level,
        )

        winner = self._decide(topic, options, votes, level)
        record.resolution = winner
        record.reason = f"{level.value} consensus on {winner!r}"
        return record

    def _decide(
        self,
        topic: str,
        options: list[str],
        votes: dict[str, float],
        level: ConsensusLevel,
    ) -> str:
        if not options:
            raise ValueError("consensus requires at least one option")

        winner = max(options, key=lambda o: votes.get(o, 0.0))

        if level == ConsensusLevel.MAJORITY:
            return winner

        if level == ConsensusLevel.WEIGHTED:
            return winner

        if level == ConsensusLevel.ARBITER:
            if self._arbiter_fn is None:
                logger.warning("arbiter_fn not configured; falling back to weighted winner")
                return winner
            losers = [o for o in options if o != winner]
            return self._arbiter_fn(topic, [winner, *losers], [winner])

        # HUMAN：不自动裁决，交给人工（返回当前领先者并标记升级）
        self._human_escalated = True
        return winner

    @property
    def human_escalated(self) -> bool:
        return getattr(self, "_human_escalated", False)


__all__ = ["ConsensusEngine", "ConsensusRecord", "ConsensusLevel"]
