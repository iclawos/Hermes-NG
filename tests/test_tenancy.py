import pytest

from zilli.security.isolation import AccessLevel
from zilli.tenancy import TenantConfig, TenantContext, TenantManager, validate_tenant_id


class TestValidateTenantId:
    def test_valid_ids(self):
        assert validate_tenant_id("acme") == "acme"
        assert validate_tenant_id("acme-corp_2") == "acme-corp_2"
        assert validate_tenant_id("A1") == "A1"

    def test_rejects_bad_ids(self):
        for bad in ["", "with space", "../evil", "a/b", "-lead", "x" * 65]:
            with pytest.raises(ValueError):
                validate_tenant_id(bad)


class TestTenantConfig:
    def test_defaults(self):
        cfg = TenantConfig(tenant_id="t1")
        assert cfg.monthly_budget_usd == 500.0
        assert cfg.planner_ratio_limit == 0.05
        assert cfg.policy.access_level == AccessLevel.INTERNAL

    def test_from_dict(self):
        cfg = TenantConfig.from_dict("acme", {
            "monthly_budget_usd": 1000.0,
            "planner_ratio_limit": 0.10,
            "industry": "medical",
            "policy": {
                "access_level": "restricted",
                "allowed_roles": ["executor"],
                "retention_days": 30,
            },
        })
        assert cfg.tenant_id == "acme"
        assert cfg.monthly_budget_usd == 1000.0
        assert cfg.planner_ratio_limit == 0.10
        assert cfg.industry == "medical"
        assert cfg.policy.access_level == AccessLevel.RESTRICTED
        assert cfg.policy.allowed_roles == ["executor"]
        assert cfg.policy.retention_days == 30


class TestTenantContext:
    def test_isolated_data_dir(self, tmp_path):
        cfg = TenantConfig(tenant_id="acme")
        ctx = TenantContext(cfg, base_dir=tmp_path)
        d = ctx.data_dir
        assert d.exists()
        assert "acme" in str(d)

    def test_storage_path_namespaced(self, tmp_path):
        ctx = TenantContext(TenantConfig(tenant_id="acme"), base_dir=tmp_path)
        p = ctx.storage_path("feedback.jsonl")
        assert p.parent == ctx.data_dir
        assert p.name == "feedback.jsonl"

    def test_storage_path_strips_traversal(self, tmp_path):
        ctx = TenantContext(TenantConfig(tenant_id="acme"), base_dir=tmp_path)
        p = ctx.storage_path("../../etc/passwd")
        assert p.parent == ctx.data_dir
        assert p.name == "passwd"

    def test_planner_budget_uses_config_ratio(self, tmp_path):
        cfg = TenantConfig(tenant_id="acme", planner_ratio_limit=0.20)
        ctx = TenantContext(cfg, base_dir=tmp_path)
        assert ctx.planner_budget._max_ratio == 0.20

    def test_check_role(self, tmp_path):
        cfg = TenantConfig.from_dict("acme", {"policy": {"allowed_roles": ["executor"]}})
        ctx = TenantContext(cfg, base_dir=tmp_path)
        assert ctx.check_role("executor") is True
        assert ctx.check_role("planner") is False

    def test_summary(self, tmp_path):
        ctx = TenantContext(TenantConfig(tenant_id="acme"), base_dir=tmp_path)
        s = ctx.summary()
        assert s["tenant_id"] == "acme"
        assert s["access_level"] == "internal"


class TestTenantManager:
    def test_register_and_get(self, tmp_path):
        mgr = TenantManager(base_dir=tmp_path)
        ctx = mgr.register(TenantConfig(tenant_id="acme"))
        assert mgr.get("acme") is ctx
        assert "acme" in mgr
        assert len(mgr) == 1

    def test_get_default_auto_registers(self, tmp_path):
        mgr = TenantManager(base_dir=tmp_path)
        ctx = mgr.get("default")
        assert ctx.tenant_id == "default"
        assert len(mgr) == 1

    def test_get_unknown_auto_registers_with_defaults(self, tmp_path):
        mgr = TenantManager(base_dir=tmp_path)
        ctx = mgr.get("new-tenant")
        assert ctx.tenant_id == "new-tenant"
        assert ctx.config.monthly_budget_usd == 500.0

    def test_register_rejects_invalid_id(self, tmp_path):
        mgr = TenantManager(base_dir=tmp_path)
        with pytest.raises(ValueError):
            mgr.register(TenantConfig(tenant_id="../evil"))

    def test_remove(self, tmp_path):
        mgr = TenantManager(base_dir=tmp_path)
        mgr.register(TenantConfig(tenant_id="acme"))
        assert mgr.remove("acme") is True
        assert mgr.remove("acme") is False
        assert len(mgr) == 0

    def test_list_tenants(self, tmp_path):
        mgr = TenantManager(base_dir=tmp_path)
        mgr.register(TenantConfig(tenant_id="a"))
        mgr.register(TenantConfig(tenant_id="b"))
        tenants = mgr.list_tenants()
        assert len(tenants) == 2
        ids = {t["tenant_id"] for t in tenants}
        assert ids == {"a", "b"}

    def test_data_isolation_between_tenants(self, tmp_path):
        mgr = TenantManager(base_dir=tmp_path)
        a = mgr.register(TenantConfig(tenant_id="a"))
        b = mgr.register(TenantConfig(tenant_id="b"))
        assert a.data_dir != b.data_dir
        assert a.storage_path("feedback.jsonl") != b.storage_path("feedback.jsonl")


class TestTenantPersistence:
    def test_save_and_load_roundtrip(self, tmp_path):
        mgr = TenantManager(base_dir=tmp_path / "data")
        mgr.register(TenantConfig.from_dict("acme", {
            "monthly_budget_usd": 1000.0,
            "planner_ratio_limit": 0.10,
            "industry": "medical",
            "policy": {"access_level": "restricted", "allowed_roles": ["executor"]},
        }))
        cfg_file = tmp_path / "tenants.yaml"
        mgr.save_yaml(cfg_file)

        mgr2 = TenantManager.from_yaml(cfg_file, base_dir=tmp_path / "data2")
        ctx = mgr2.get("acme")
        assert ctx.config.monthly_budget_usd == 1000.0
        assert ctx.config.planner_ratio_limit == 0.10
        assert ctx.config.industry == "medical"
        assert ctx.config.policy.access_level == AccessLevel.RESTRICTED
        assert ctx.config.policy.allowed_roles == ["executor"]

    def test_from_yaml_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            TenantManager.from_yaml(tmp_path / "ghost.yaml")

    def test_from_yaml_empty_tenants(self, tmp_path):
        cfg = tmp_path / "t.yaml"
        cfg.write_text("base_dir: ./data\ntenants: {}\n")
        mgr = TenantManager.from_yaml(cfg)
        assert len(mgr) == 0

    def test_from_yaml_multiple_tenants(self, tmp_path):
        cfg = tmp_path / "t.yaml"
        cfg.write_text(
            "tenants:\n"
            "  a:\n    monthly_budget_usd: 100\n"
            "  b:\n    monthly_budget_usd: 200\n"
        )
        mgr = TenantManager.from_yaml(cfg, base_dir=tmp_path)
        assert len(mgr) == 2
        assert mgr.get("a").config.monthly_budget_usd == 100
        assert mgr.get("b").config.monthly_budget_usd == 200
