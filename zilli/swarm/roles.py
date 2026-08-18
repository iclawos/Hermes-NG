"""L6 群智能 — Agent 角色注册表。

角色按工具集、上下文预算、模型槽位、评估标准与回退角色定义。
"""

from __future__ import annotations

from dataclasses import dataclass

_ROLE_SPECS: dict[str, "AgentRoleSpec"] = {}


@dataclass(frozen=True)
class AgentRoleSpec:
    role: str
    tools: tuple[str, ...] = ()
    max_context: int = 8000
    model_profile: str = "executor"
    eval_criteria: tuple[str, ...] = ()
    fallback_role: str = ""

    def __post_init__(self) -> None:
        if not self.role:
            raise ValueError("role must not be empty")


def register_role(spec: AgentRoleSpec) -> AgentRoleSpec:
    """Register a role spec (idempotent by role name)."""
    _ROLE_SPECS[spec.role] = spec
    return spec


def get_role(role: str) -> AgentRoleSpec | None:
    return _ROLE_SPECS.get(role)


def list_roles() -> list[str]:
    return sorted(_ROLE_SPECS.keys())


def _register_builtins() -> None:
    # 内置角色：与 multi_agent.tasks.yaml 对齐
    _ROLE_SPECS.update({
        spec.role: spec for spec in (
            AgentRoleSpec(
                role="researcher",
                tools=("web_search", "file_read", "memory_write"),
                max_context=8000,
                model_profile="planner",
                eval_criteria=("information_gathered",),
            ),
            AgentRoleSpec(
                role="architect",
                tools=("file_read", "file_write", "memory_write"),
                max_context=12000,
                model_profile="planner",
                eval_criteria=("decision_clear",),
                fallback_role="researcher",
            ),
            AgentRoleSpec(
                role="writer",
                tools=("memory_read", "file_write"),
                max_context=8000,
                model_profile="executor",
                eval_criteria=("report_generated", "report_quality"),
                fallback_role="executor",
            ),
            AgentRoleSpec(
                role="verifier",
                tools=("file_read", "code_interpreter", "bash_run"),
                max_context=12000,
                model_profile="reviewer",
                eval_criteria=("behavior_correct",),
                fallback_role="reviewer",
            ),
            AgentRoleSpec(
                role="reviewer",
                tools=("file_read", "memory_read"),
                max_context=8000,
                model_profile="reviewer",
                eval_criteria=("quality_approved",),
            ),
            AgentRoleSpec(
                role="executor",
                tools=("file_read", "file_write", "memory_write", "memory_read"),
                max_context=8000,
                model_profile="executor",
                eval_criteria=("task_completed",),
            ),
        )
    })


def reset_role_registry() -> None:
    """清空并恢复内置角色。"""
    _ROLE_SPECS.clear()
    _register_builtins()


_register_builtins()

__all__ = ["AgentRoleSpec", "register_role", "get_role", "list_roles", "reset_role_registry"]
