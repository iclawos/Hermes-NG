"""L6 群智能 — 任务分解器。

将复杂任务分解为子任务 DAG：显式依赖、产物 schema、并行标记。
分解受扇出上限约束，且必须无环。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional, Union

from zilli.swarm.artifacts import SubTask
from zilli.swarm.roles import get_role

logger = logging.getLogger("zilli.swarm.decomposer")

DecomposeFn = Callable[[str, str, float], Union[list[SubTask], Awaitable[list[SubTask]]]]


@dataclass
class DecomposeResult:
    subtasks: list[SubTask]
    decomposition_reason: str
    ppm_family: str
    difficulty: float


class DecomposeError(ValueError):
    pass


class TaskDecomposer:
    """由 PPM 分类驱动，调用 LLM 或规则策略生成子任务 DAG。

    `decompose_fn` 可注入（测试/离线场景）；默认走规则启发式。
    """

    MAX_FANOUT = 8
    # 依赖深度上限，防止退化成脆弱的深链
    MAX_DEPTH = 6

    def __init__(
        self,
        decompose_fn: Optional[DecomposeFn] = None,
        min_difficulty: float = 0.7,
        max_fanout: int = MAX_FANOUT,
    ) -> None:
        self._decompose_fn = decompose_fn
        self.min_difficulty = min_difficulty
        self.max_fanout = max_fanout

    async def decompose(
        self,
        task: str,
        ppm_family: str = "coding",
        difficulty: float = 0.8,
    ) -> DecomposeResult:
        if difficulty < self.min_difficulty:
            return DecomposeResult(
                subtasks=[SubTask(
                    id="st-0",
                    description=task,
                    role="executor",
                    artifact_schema=None,
                )],
                decomposition_reason=f"difficulty {difficulty:.2f} below threshold {self.min_difficulty:.2f}",
                ppm_family=ppm_family,
                difficulty=difficulty,
            )

        if self._decompose_fn is not None:
            out = self._decompose_fn(task, ppm_family, difficulty)
            subtasks = await out if isinstance(out, Awaitable) else out
        else:
            subtasks = self._rule_based(task, ppm_family)

        self._validate(subtasks)
        return DecomposeResult(
            subtasks=subtasks,
            decomposition_reason=f"decomposed via {ppm_family} rules",
            ppm_family=ppm_family,
            difficulty=difficulty,
        )

    def _rule_based(self, task: str, ppm_family: str) -> list[SubTask]:
        """内置启发式：research → write → verify 三阶段。"""
        return [
            SubTask(id="st-1", description="gather information", role="researcher",
                    parallel=True, artifact_schema=None),
            SubTask(id="st-2", description="produce deliverable", role="writer",
                    dependencies=["st-1"], artifact_schema=None),
            SubTask(id="st-3", description="verify deliverable", role="verifier",
                    dependencies=["st-2"], artifact_schema=None),
        ]

    def _validate(self, subtasks: list[SubTask]) -> None:
        if not subtasks:
            raise DecomposeError("decompose produced zero subtasks")
        if len(subtasks) > self.max_fanout:
            raise DecomposeError(
                f"fanout {len(subtasks)} exceeds max_fanout {self.max_fanout}"
            )

        seen: set[str] = set()
        for st in subtasks:
            if st.id in seen:
                raise DecomposeError(f"duplicate subtask id {st.id!r}")
            seen.add(st.id)
            role = get_role(st.role)
            if role is None:
                raise DecomposeError(f"unknown role {st.role!r}")
            for dep in st.dependencies:
                if dep not in seen and dep not in {s.id for s in subtasks}:
                    raise DecomposeError(f"subtask {st.id} depends on unknown {dep!r}")

        # 环检测（DFS）
        by_id = {s.id: s for s in subtasks}
        visiting: set[str] = set()
        visited: set[str] = set()

        def _acyclic(sid: str) -> bool:
            if sid in visited:
                return True
            if sid in visiting:
                return False
            visiting.add(sid)
            for dep in by_id[sid].dependencies:
                if dep in by_id and not _acyclic(dep):
                    return False
            visiting.discard(sid)
            visited.add(sid)
            return True

        for sid in by_id:
            if not _acyclic(sid):
                raise DecomposeError(f"cycle detected involving {sid!r}")


__all__ = ["TaskDecomposer", "DecomposeResult", "DecomposeError"]
