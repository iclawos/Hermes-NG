from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import yaml

from zilli.audit import AuditEvent, AuditLevel, AuditLogger

if TYPE_CHECKING:
    from zilli.configs import ZilliConfig
from zilli.models.registry import ModelRegistry
from zilli.routing import LocalHybridRouter, RouteClassifier
from zilli.routing.router import RouteResult
from zilli.security.isolation import AccessLevel, DataIsolation, IsolationPolicy
from zilli.security.pii import Sanitizer

logger = logging.getLogger("zilli.industry")


class IndustryType(str, Enum):
    LEGAL = "legal"
    MEDICAL = "medical"
    FINANCIAL = "financial"
    EDUCATION = "education"

    def __str__(self) -> str:
        return self.value


@dataclass
class IndustryWorkflow:
    industry: IndustryType
    compliance_rules: list[str] = field(default_factory=list)
    access_level: AccessLevel = AccessLevel.CONFIDENTIAL
    require_audit: bool = True
    require_sanitization: bool = True
    retention_days: int = 90
    template_name: str = ""
    source_file: str = ""
    mtime: float = 0.0

    def sanitize_input(self, text: str, sanitizer: Optional[Sanitizer] = None) -> str:
        s = sanitizer or Sanitizer()
        result = s.sanitize(text)
        if result.findings:
            logger.info(
                "Sanitized %d PII items from %s input",
                len(result.findings), self.industry.value,
            )
        return result.sanitized

    def audit_call(self, audit_logger: AuditLogger, request: str, result: RouteResult, tenant: str = "default"):
        if not self.require_audit:
            return
        audit_logger.route_decision(
            route_type=result.route_type.value,
            request=request,
            reason=result.decision.reason,
            tenant_id=tenant,
        )
        if result.error:
            audit_logger.log(AuditEvent(
                event_type="industry_error",
                level=AuditLevel.ERROR,
                message=f"{self.industry.value} workflow error: {result.error}",
                tenant_id=tenant,
            ))


LEGAL = IndustryWorkflow(
    industry=IndustryType.LEGAL,
    access_level=AccessLevel.RESTRICTED,
    compliance_rules=[
        "attorney-client privilege must be preserved",
        "no client confidential information outside local server",
        "all model calls must be audited",
        "output must cite applicable legal standards",
    ],
)

MEDICAL = IndustryWorkflow(
    industry=IndustryType.MEDICAL,
    access_level=AccessLevel.RESTRICTED,
    compliance_rules=[
        "HIPAA compliance required",
        "all PHI must be detected and handled per policy",
        "no patient data outside local server",
        "diagnostic suggestions must include disclaimer",
    ],
)

FINANCIAL = IndustryWorkflow(
    industry=IndustryType.FINANCIAL,
    access_level=AccessLevel.CONFIDENTIAL,
    compliance_rules=[
        "SOX compliance required",
        "all financial data must be audited",
        "no PII in audit logs",
        "risk assessments must clearly label confidence levels",
    ],
)

EDUCATION = IndustryWorkflow(
    industry=IndustryType.EDUCATION,
    access_level=AccessLevel.CONFIDENTIAL,
    compliance_rules=[
        "FERPA compliance required",
        "student PII must be removed from model inputs",
        "grades and assessments must be anonymized",
    ],
)


class WorkflowRegistry:
    _WORKFLOWS: dict[IndustryType, IndustryWorkflow] = {
        IndustryType.LEGAL: LEGAL,
        IndustryType.MEDICAL: MEDICAL,
        IndustryType.FINANCIAL: FINANCIAL,
        IndustryType.EDUCATION: EDUCATION,
    }

    _INDUSTRY_BY_FRAMEWORK: dict[str, IndustryType] = {
        "hipaa": IndustryType.MEDICAL,
        "sox": IndustryType.FINANCIAL,
        "aba": IndustryType.LEGAL,
        "ferpa": IndustryType.EDUCATION,
        "legal": IndustryType.LEGAL,
        "medical": IndustryType.MEDICAL,
        "financial": IndustryType.FINANCIAL,
        "education": IndustryType.EDUCATION,
    }

    def __init__(
        self,
        model_registry: Optional[ModelRegistry] = None,
        audit_logger: Optional[AuditLogger] = None,
        data_isolation: Optional[DataIsolation] = None,
        config: Optional["ZilliConfig"] = None,
        templates_dir: Optional[str | Path] = None,
    ):
        self.model_registry = model_registry or ModelRegistry(config=config)
        self.config = config

        audit_cfg = getattr(config, "audit", None) if config else None
        log_dir = audit_cfg.log_dir if audit_cfg else "./audit_logs"
        sanitize = audit_cfg.sanitize if audit_cfg else True
        self.audit_logger = audit_logger or AuditLogger(log_dir=log_dir, sanitize=sanitize)

        self.data_isolation = data_isolation or DataIsolation()
        self._classifier = RouteClassifier(model_registry=self.model_registry)
        self._router = LocalHybridRouter(
            registry=self.model_registry,
            classifier=self._classifier,
        )
        self._workflows: dict[IndustryType, IndustryWorkflow] = dict(self._WORKFLOWS)

        if templates_dir is None:
            env_dir = os.environ.get("ZILLI_INDUSTRY_CONFIG", "")
            if env_dir:
                templates_dir = env_dir
        self._templates_dir: Optional[Path] = (
            Path(templates_dir) if templates_dir else None
        )
        if self._templates_dir is not None:
            self.reload_templates()

    def get_workflow(self, industry: IndustryType) -> IndustryWorkflow | None:
        return self._workflows.get(industry)

    def register_workflow(self, workflow: IndustryWorkflow) -> None:
        """Register or replace a workflow at runtime (no restart required)."""
        self._workflows[workflow.industry] = workflow

    def unregister_workflow(self, industry: IndustryType) -> bool:
        return self._workflows.pop(industry, None) is not None

    def reset_to_builtin(self) -> None:
        """Restore the built-in workflow templates."""
        self._workflows = dict(self._WORKFLOWS)

    def reload_templates(self) -> dict[str, Any]:
        """Hot-reload industry templates from the configured directory.

        Returns a report of loaded / skipped / removed templates. Template
        files are YAML; the industry is derived from the ``framework`` or
        ``industry`` key, falling back to the file stem.
        """
        report: dict[str, Any] = {"loaded": [], "skipped": [], "removed": [], "dir": None}
        if self._templates_dir is None:
            return report
        templates_dir = self._templates_dir
        report["dir"] = str(templates_dir)
        if not templates_dir.exists():
            logger.warning("Industry templates dir not found: %s", templates_dir)
            return report

        loaded: dict[IndustryType, IndustryWorkflow] = {}
        yaml_files = list(templates_dir.glob("*.yaml")) + list(templates_dir.glob("*.yml"))
        for f in sorted(yaml_files):
            try:
                data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError) as e:
                logger.warning("Skipping industry template %s: %s", f, e)
                report["skipped"].append(str(f))
                continue

            industry = self._industry_from_template(data, f)
            if industry is None:
                report["skipped"].append(str(f))
                continue

            workflow = self._workflow_from_template(industry, data, f)
            loaded[industry] = workflow
            report["loaded"].append({
                "file": f.name,
                "industry": industry.value,
                "template_name": workflow.template_name,
            })

        removed = [ind.value for ind in self._workflows if ind not in loaded]
        self._workflows = loaded
        report["removed"] = removed
        logger.info(
            "Reloaded industry templates from %s: %d loaded, %d skipped, %d removed",
            templates_dir, len(loaded), len(report["skipped"]), len(removed),
        )
        return report

    def _industry_from_template(
        self, data: dict[str, Any], path: Path
    ) -> IndustryType | None:
        raw = str(data.get("industry", "")).lower()
        if not raw:
            raw = str(data.get("framework", "")).lower()
        if raw and raw in self._INDUSTRY_BY_FRAMEWORK:
            return self._INDUSTRY_BY_FRAMEWORK[raw]
        stem = path.stem.lower()
        if stem in self._INDUSTRY_BY_FRAMEWORK:
            return self._INDUSTRY_BY_FRAMEWORK[stem]
        logger.warning(
            "Industry template %s has no recognized industry/framework (got %r)",
            path, data.get("framework"),
        )
        return None

    def _workflow_from_template(
        self, industry: IndustryType, data: dict[str, Any], path: Path
    ) -> IndustryWorkflow:
        access_raw = str(data.get("access_level", "")).lower()
        try:
            access_level = AccessLevel(access_raw) if access_raw else AccessLevel.CONFIDENTIAL
        except ValueError:
            access_level = AccessLevel.CONFIDENTIAL
        try:
            mtime = path.stat().st_mtime
        except OSError:
            mtime = 0.0
        audit = data.get("audit") or {}
        retention_days = data.get("retention_days")
        if not retention_days and isinstance(audit, dict):
            retention_years = audit.get("retention_years")
            if retention_years:
                retention_days = int(retention_years) * 365
        rules = data.get("compliance_rules", [])
        if not isinstance(rules, list):
            rules = [str(rules)]
        return IndustryWorkflow(
            industry=industry,
            compliance_rules=[str(r) for r in rules],
            access_level=access_level,
            require_audit=bool(data.get("require_audit", True)),
            require_sanitization=bool(data.get("require_sanitization", True)),
            retention_days=int(retention_days or 90),
            template_name=str(data.get("name", path.stem)),
            source_file=path.name,
            mtime=mtime,
        )

    def list_industries(self) -> list[dict]:
        return [
            {
                "id": ind.value,
                "compliance_rules": wf.compliance_rules,
                "access_level": wf.access_level.value,
                "require_audit": wf.require_audit,
                "retention_days": wf.retention_days,
                "template_name": wf.template_name,
                "source_file": wf.source_file,
            }
            for ind, wf in self._workflows.items()
        ]

    async def run(
        self,
        request: str,
        industry: IndustryType,
        tenant_id: str = "default",
        force_full_route: bool = False,
        sanitize: bool = True,
    ) -> RouteResult:
        workflow = self.get_workflow(industry)
        if workflow is None:
            raise ValueError(f"Unknown industry: {industry}")

        policy = IsolationPolicy(
            tenant_id=tenant_id,
            access_level=workflow.access_level,
            require_sanitization=workflow.require_sanitization,
            audit_required=workflow.require_audit,
            retention_days=workflow.retention_days,
        )
        self.data_isolation.register_tenant(tenant_id, policy)

        processed_request = request
        if sanitize and workflow.require_sanitization:
            processed_request = workflow.sanitize_input(request)

        router = self._router

        result = await router.run(
            request=processed_request,
            industry=industry.value,
            force_full_route=force_full_route,
        )

        if workflow.require_audit:
            workflow.audit_call(self.audit_logger, processed_request, result, tenant_id)

        return result
