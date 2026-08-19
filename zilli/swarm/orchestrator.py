"""L6 群智能 — SwarmOrchestrator。

编排：分解 → 路由 → 并行执行 → 产物图 → 共识 → 验证 → 反馈。
复用 MOM 的三层边界（治理/路由/反馈）与既有 Agent 执行。
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from pydantic import BaseModel, ConfigDict

from zilli.swarm.artifacts import Artifact, ArtifactGraph, SubTask
from zilli.swarm.consensus import ConsensusEngine
from zilli.swarm.decomposer import TaskDecomposer
from zilli.swarm.router import AgentRouter

logger = logging.getLogger("zilli.swarm.orchestrator")


@dataclass
class SwarmResult:
    final_text: str
    success: bool
    subtasks: list[SubTask]
    artifacts: ArtifactGraph
    consensus: list = field(default_factory=list)
    total_duration_ms: float = 0.0
    error: str = ""


class SwarmOrchestrator:
    """主协调器。

    executor_fn: (subtask, artifact_graph) -> dict（执行单个子任务）
    默认实现用 LLM 生成文本；可注入真实 Agent / HybridExecutor。
    """

    def __init__(
        self,
        decomposer: TaskDecomposer,
        router: AgentRouter,
        consensus: ConsensusEngine,
        executor_fn: Optional[Callable[[SubTask, ArtifactGraph], dict]] = None,
        verify_fn: Optional[Callable[[str], bool]] = None,
        max_concurrency: int = 4,
    ) -> None:
        self.decomposer = decomposer
        self.router = router
        self.consensus = consensus
        self._executor_fn = executor_fn or self._default_executor
        self._verify_fn = verify_fn
        self.max_concurrency = max_concurrency

    async def execute(self, request: str, industry: str = "") -> SwarmResult:
        start = time.monotonic()
        try:
            decomposition = await self.decomposer.decompose(request)
        except Exception as e:
            return SwarmResult(
                final_text="", success=False, subtasks=[], artifacts=ArtifactGraph(),
                error=f"decompose failed: {e}",
            )

        subtasks = decomposition.subtasks
        graph = ArtifactGraph()

        # 单子任务（难度低）→ 直接执行
        if len(subtasks) == 1:
            return await self._run_single(subtasks[0], graph, start)

        return await self._run_dag(subtasks, graph, start)

    async def _run_single(self, subtask: SubTask, graph: ArtifactGraph,
                          start: float) -> SwarmResult:
        try:
            payload = await self._run_one(subtask, graph)
        except Exception as e:
            return SwarmResult(
                final_text="", success=False, subtasks=[subtask],
                artifacts=graph, error=f"execution failed: {e}",
                total_duration_ms=(time.monotonic() - start) * 1000,
            )
        text = str(payload.get("text", payload.get("result", "")))
        ok = self._verify_fn(text) if self._verify_fn else bool(text)
        return SwarmResult(
            final_text=text, success=ok, subtasks=[subtask], artifacts=graph,
            total_duration_ms=(time.monotonic() - start) * 1000,
            error="" if ok else "verification failed",
        )

    async def _run_dag(self, subtasks: list[SubTask], graph: ArtifactGraph,
                       start: float) -> SwarmResult:
        pending = list(subtasks)
        sem = asyncio.Semaphore(self.max_concurrency)

        async def _worker(st: SubTask) -> None:
            async with sem:
                st.status = "running"
                try:
                    payload = await self._run_one(st, graph)
                    art = Artifact(
                        id=st.artifact_id or st.id,
                        producer_role=st.role,
                        schema=st.artifact_schema or _FreeSchema,
                        payload=payload,
                        consumer_roles=[],
                    )
                    graph.put(art)
                    art.status = "done"
                    st.status = "done"
                    st.artifact_id = art.id
                except Exception as e:
                    st.status = "rejected"
                    st.error = str(e)

        while pending:
            ready = graph.ready_subtasks(pending)
            if not ready:
                # 死锁（依赖链断裂）
                for st in pending:
                    if st.status == "pending":
                        st.status = "rejected"
                        st.error = "unresolvable dependency"
                break
            await asyncio.gather(*(_worker(st) for st in ready))
            pending = [st for st in pending if st.status == "pending"]

        rejected = [st for st in subtasks if st.status == "rejected"]
        success = not rejected
        # 最终产物：确定性取 sink 子任务（无下游依赖者）中声明顺序最后的
        # done 节点；无 sink 时退化为声明顺序最后的 done 节点。
        # 不能用完成顺序——并行分支下完成顺序由时序决定，结果不可复现。
        depended_on = {d for st in subtasks for d in st.dependencies}
        done = [st for st in subtasks if st.status == "done"]
        sinks = [st for st in done if st.id not in depended_on]
        final_text = ""
        for st in (sinks or done)[-1:]:
            art = graph.get(st.artifact_id)
            if art:
                final_text = str(art.payload.get("text", art.payload.get("result", "")))

        if success and self._verify_fn is not None and not self._verify_fn(final_text):
            success = False
            return SwarmResult(
                final_text=final_text,
                success=False,
                subtasks=subtasks,
                artifacts=graph,
                total_duration_ms=(time.monotonic() - start) * 1000,
                error="verification failed",
            )

        return SwarmResult(
            final_text=final_text,
            success=success,
            subtasks=subtasks,
            artifacts=graph,
            total_duration_ms=(time.monotonic() - start) * 1000,
            error="; ".join(st.error for st in rejected[:3]) if rejected else "",
        )

    async def _run_one(self, subtask: SubTask, graph: ArtifactGraph) -> dict:
        if asyncio.iscoroutinefunction(self._executor_fn):
            return await self._executor_fn(subtask, graph)
        return self._executor_fn(subtask, graph)

    def _default_executor(self, subtask: SubTask, graph: ArtifactGraph) -> dict:
        """无注入时的兜底：返回角色名 + 子任务描述。"""
        return {
            "text": f"[{subtask.role}] {subtask.description}",
            "role": subtask.role,
        }


class _FreeSchema(BaseModel):
    """宽松 schema：任何 dict 都通过。"""

    model_config = ConfigDict(extra="allow")


__all__ = ["SwarmOrchestrator", "SwarmResult"]
