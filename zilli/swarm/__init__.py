"""L6 群智能（Swarm Intelligence）包。

多 Agent 协作：任务分解 → Agent 间路由 → 并行执行 → 共识仲裁。
复用 MOM 三层边界（治理/路由/反馈）与既有 Agent 执行。

RFC: docs/rfc-006-l6-swarm-intelligence.md
"""

from zilli.swarm.artifacts import Artifact, ArtifactGraph, SubTask
from zilli.swarm.consensus import (
    ConsensusEngine,
    ConsensusLevel,
    ConsensusRecord,
)
from zilli.swarm.decomposer import (
    DecomposeError,
    DecomposeResult,
    TaskDecomposer,
)
from zilli.swarm.orchestrator import SwarmOrchestrator, SwarmResult
from zilli.swarm.roles import (
    AgentRoleSpec,
    get_role,
    list_roles,
    register_role,
    reset_role_registry,
)
from zilli.swarm.router import AgentRouter, RouteAssignment

__all__ = [
    "Artifact",
    "ArtifactGraph",
    "SubTask",
    "ConsensusEngine",
    "ConsensusLevel",
    "ConsensusRecord",
    "DecomposeError",
    "DecomposeResult",
    "TaskDecomposer",
    "SwarmOrchestrator",
    "SwarmResult",
    "AgentRoleSpec",
    "get_role",
    "list_roles",
    "register_role",
    "reset_role_registry",
    "AgentRouter",
    "RouteAssignment",
]
