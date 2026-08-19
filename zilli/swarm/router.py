"""L6 群智能 — Agent 间路由。

子任务 → 角色匹配 + 模型选择。复用 MOM 的 PPM 与 ModelProfile，
保证安全/成本边界不被绕过。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from zilli.routing.profile import ModelEntry, ModelProfile
from zilli.swarm.artifacts import SubTask
from zilli.swarm.roles import get_role

logger = logging.getLogger("zilli.swarm.router")


@dataclass
class RouteAssignment:
    subtask_id: str
    role: str
    model: Optional[ModelEntry]
    model_id: str
    fallback_used: bool = False


class AgentRouter:
    """子任务 → 角色 + 模型槽位。

    规则：
    1. 子任务声明角色 → 查角色表（未知角色回退 executor）
    2. 若角色模型不可用 → 用 fallback_role 重试
    3. 最终用 ModelProfile 选模型
    """

    def __init__(self, profile: Optional[ModelProfile] = None) -> None:
        self._profile = profile or ModelProfile()

    def assign(self, subtask: SubTask) -> RouteAssignment:
        role_name = subtask.role
        spec = get_role(role_name)
        if spec is None:
            logger.warning("unknown role %r, falling back to executor", role_name)
            role_name = "executor"
            spec = get_role(role_name)
            assert spec is not None

        model = self._pick_model(spec.model_profile)
        fallback_used = False
        if model is None and spec.fallback_role:
            fb = get_role(spec.fallback_role)
            if fb is not None:
                model = self._pick_model(fb.model_profile)
                fallback_used = True
                role_name = fb.role

        return RouteAssignment(
            subtask_id=subtask.id,
            role=role_name,
            model=model,
            model_id=model.model_id if model else "none",
            fallback_used=fallback_used,
        )

    def _pick_model(self, profile_slot: str) -> Optional[ModelEntry]:
        """从 ModelProfile 中按槽位名称挑一个模型。"""
        entries = self._profile.models()
        for entry in entries:
            if entry.name == profile_slot:
                return entry
        # 精确匹配落空再退到子串匹配
        for entry in entries:
            if profile_slot in entry.name:
                return entry
        # 无槽位匹配 → 任选一个模型
        return entries[0] if entries else None


__all__ = ["AgentRouter", "RouteAssignment"]
