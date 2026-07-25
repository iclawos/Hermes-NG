from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from zilli.envs.planner_budget import PlannerBudget
from zilli.security.isolation import AccessLevel, IsolationPolicy

logger = logging.getLogger("zilli.tenancy")

_TENANT_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_\-]{0,63}$")


def validate_tenant_id(tenant_id: str) -> str:
    """Validate and normalize a tenant id. Raises ValueError on bad input."""
    if not _TENANT_ID_RE.match(tenant_id):
        raise ValueError(f"Invalid tenant id: {tenant_id!r}")
    return tenant_id


@dataclass
class TenantConfig:
    """Per-tenant configuration overrides."""
    tenant_id: str
    policy: IsolationPolicy = field(default_factory=IsolationPolicy)
    monthly_budget_usd: float = 500.0
    planner_ratio_limit: float = 0.05
    max_sota_ratio: float = 0.05
    industry: str = ""
    data_retention_days: int = 90

    @classmethod
    def from_dict(cls, tenant_id: str, data: dict[str, Any]) -> "TenantConfig":
        policy_data = data.get("policy", {})
        policy = IsolationPolicy(
            tenant_id=tenant_id,
            access_level=AccessLevel(policy_data.get("access_level", "internal")),
            allowed_roles=policy_data.get("allowed_roles", ["planner", "executor", "reviewer"]),
            max_input_length=policy_data.get("max_input_length", 32768),
            require_sanitization=policy_data.get("require_sanitization", True),
            audit_required=policy_data.get("audit_required", True),
            retention_days=policy_data.get("retention_days", data.get("data_retention_days", 90)),
        )
        return cls(
            tenant_id=tenant_id,
            policy=policy,
            monthly_budget_usd=data.get("monthly_budget_usd", 500.0),
            planner_ratio_limit=data.get("planner_ratio_limit", 0.05),
            max_sota_ratio=data.get("max_sota_ratio", 0.05),
            industry=data.get("industry", ""),
            data_retention_days=data.get("data_retention_days", 90),
        )


class TenantContext:
    """Runtime context for one tenant: config + isolated state."""

    def __init__(self, config: TenantConfig, base_dir: str | Path = "./tenant_data"):
        self.config = config
        self.tenant_id = config.tenant_id
        self._base_dir = Path(base_dir) / config.tenant_id
        self._planner_budget: Optional[PlannerBudget] = None

    @property
    def data_dir(self) -> Path:
        """Tenant-isolated data directory (created lazily)."""
        self._base_dir.mkdir(parents=True, exist_ok=True)
        return self._base_dir

    def storage_path(self, name: str) -> Path:
        """Namespaced storage path, e.g. feedback.jsonl, audit logs."""
        safe = Path(name).name
        return self.data_dir / safe

    @property
    def planner_budget(self) -> PlannerBudget:
        if self._planner_budget is None:
            self._planner_budget = PlannerBudget(
                max_planner_ratio=self.config.planner_ratio_limit,
            )
        return self._planner_budget

    def check_role(self, role: str) -> bool:
        return role in self.config.policy.allowed_roles

    def summary(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "access_level": self.config.policy.access_level.value,
            "monthly_budget_usd": self.config.monthly_budget_usd,
            "planner_ratio_limit": self.config.planner_ratio_limit,
            "max_sota_ratio": self.config.max_sota_ratio,
            "industry": self.config.industry,
            "data_dir": str(self._base_dir),
        }


class TenantManager:
    """Registry and factory for tenant contexts."""

    def __init__(self, base_dir: str | Path = "./tenant_data",
                 default_config: Optional[TenantConfig] = None):
        self._base_dir = Path(base_dir)
        self._contexts: dict[str, TenantContext] = {}
        self._default_config = default_config or TenantConfig(tenant_id="default")

    def register(self, config: TenantConfig) -> TenantContext:
        validate_tenant_id(config.tenant_id)
        ctx = TenantContext(config, base_dir=self._base_dir)
        self._contexts[config.tenant_id] = ctx
        logger.info("Tenant registered: %s (budget=$%.0f, planner≤%.0f%%)",
                    config.tenant_id, config.monthly_budget_usd,
                    config.planner_ratio_limit * 100)
        return ctx

    def get(self, tenant_id: str = "default") -> TenantContext:
        if tenant_id not in self._contexts:
            if tenant_id == "default":
                return self.register(self._default_config)
            config = TenantConfig(tenant_id=tenant_id)
            return self.register(config)
        return self._contexts[tenant_id]

    def remove(self, tenant_id: str) -> bool:
        return self._contexts.pop(tenant_id, None) is not None

    def list_tenants(self) -> list[dict[str, Any]]:
        return [ctx.summary() for ctx in self._contexts.values()]

    def __contains__(self, tenant_id: str) -> bool:
        return tenant_id in self._contexts

    def __len__(self) -> int:
        return len(self._contexts)

    @classmethod
    def from_yaml(cls, path: str | Path,
                  base_dir: str | Path = "./tenant_data") -> "TenantManager":
        """Load tenant definitions from a YAML file.

        Format:
            base_dir: ./tenant_data          # optional
            tenants:
              acme:
                monthly_budget_usd: 1000
                planner_ratio_limit: 0.10
                industry: medical
                policy:
                  access_level: restricted
                  allowed_roles: [executor]
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Tenant config not found: {path}")
        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        mgr = cls(base_dir=data.get("base_dir", base_dir))
        for tenant_id, tenant_data in (data.get("tenants") or {}).items():
            cfg = TenantConfig.from_dict(tenant_id, tenant_data or {})
            mgr.register(cfg)
        return mgr

    def save_yaml(self, path: str | Path) -> None:
        """Persist current tenant registry to YAML."""
        data: dict[str, Any] = {"base_dir": str(self._base_dir), "tenants": {}}
        for ctx in self._contexts.values():
            c = ctx.config
            data["tenants"][c.tenant_id] = {
                "monthly_budget_usd": c.monthly_budget_usd,
                "planner_ratio_limit": c.planner_ratio_limit,
                "max_sota_ratio": c.max_sota_ratio,
                "industry": c.industry,
                "data_retention_days": c.data_retention_days,
                "policy": {
                    "access_level": c.policy.access_level.value,
                    "allowed_roles": c.policy.allowed_roles,
                    "max_input_length": c.policy.max_input_length,
                    "require_sanitization": c.policy.require_sanitization,
                    "audit_required": c.policy.audit_required,
                    "retention_days": c.policy.retention_days,
                },
            }
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


__all__ = [
    "TenantConfig",
    "TenantContext",
    "TenantManager",
    "validate_tenant_id",
]
