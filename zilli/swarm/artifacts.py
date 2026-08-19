"""L6 群智能 — 产物图（Artifact Graph）。

子任务交接的唯一通道是产物（非共享内存）。产物是 DAG，带严格
schema 校验、状态机与生命周期管理。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal, Optional

from pydantic import BaseModel

ArtifactStatus = Literal["pending", "done", "rejected", "consumed"]


@dataclass
class Artifact:
    id: str
    producer_role: str
    schema: type[BaseModel]
    payload: dict
    consumer_roles: list[str] = field(default_factory=list)
    status: ArtifactStatus = "pending"
    created_at: float = field(default_factory=time.time)

    def validate_payload(self) -> bool:
        try:
            self.schema(**self.payload)
            return True
        except Exception:
            return False


@dataclass
class SubTask:
    id: str
    description: str
    role: str
    dependencies: list[str] = field(default_factory=list)
    parallel: bool = False
    artifact_schema: Optional[type[BaseModel]] = None
    max_retries: int = 2
    status: Literal["pending", "running", "done", "rejected"] = "pending"
    artifact_id: str = ""
    error: str = ""


class ArtifactGraph:
    """产物 DAG：按 ID 存取，跟踪消费关系，支持 GC。"""

    def __init__(self) -> None:
        self._artifacts: dict[str, Artifact] = {}
        self._consumed_by: dict[str, set[str]] = {}

    def put(self, artifact: Artifact) -> None:
        if not artifact.validate_payload():
            raise ValueError(
                f"Artifact {artifact.id} payload does not match schema "
                f"{artifact.schema.__name__}"
            )
        self._artifacts[artifact.id] = artifact

    def get(self, artifact_id: str) -> Artifact | None:
        return self._artifacts.get(artifact_id)

    def consumers_of(self, artifact_id: str) -> list[str]:
        return list(self._consumed_by.get(artifact_id, set()))

    def consume(self, artifact_id: str, consumer_role: str) -> Artifact | None:
        art = self._artifacts.get(artifact_id)
        if art is None:
            return None
        self._consumed_by.setdefault(artifact_id, set()).add(consumer_role)
        art.status = "consumed"
        return art

    def reject(self, artifact_id: str, reason: str = "") -> None:
        art = self._artifacts.get(artifact_id)
        if art is not None:
            art.status = "rejected"

    def pending_dependencies(self, subtask: SubTask) -> list[str]:
        # consumed 也算已满足：产物已成功产出，只是被消费方读过
        return [
            d for d in subtask.dependencies
            if (self._artifacts.get(d) is None
                or self._artifacts[d].status not in ("done", "consumed"))
        ]

    def is_runnable(self, subtask: SubTask) -> bool:
        return not self.pending_dependencies(subtask)

    def ready_subtasks(self, subtasks: list[SubTask]) -> list[SubTask]:
        return [s for s in subtasks
                if s.status == "pending" and self.is_runnable(s)]

    def gc_unconsumed(self, max_age_sec: float = 3600) -> int:
        """回收超过存活期的产物。返回回收数量。"""
        now = time.time()
        stale = [
            aid for aid, art in self._artifacts.items()
            if art.status in ("done", "consumed")
            and now - art.created_at > max_age_sec
        ]
        for aid in stale:
            del self._artifacts[aid]
        return len(stale)

    def __len__(self) -> int:
        return len(self._artifacts)


__all__ = ["Artifact", "ArtifactGraph", "SubTask"]
