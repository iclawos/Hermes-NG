from zilli.industry.workflows import IndustryType, WorkflowRegistry


class TestIndustryType:
    def test_enum_values(self):
        assert IndustryType.LEGAL.value == "legal"
        assert IndustryType.MEDICAL.value == "medical"
        assert IndustryType.FINANCIAL.value == "financial"
        assert IndustryType.EDUCATION.value == "education"

    def test_enum_str(self):
        assert str(IndustryType.MEDICAL) == "medical"


class TestIndustryWorkflow:
    def test_legal_workflow(self):
        from zilli.industry.workflows import LEGAL
        assert LEGAL.industry == IndustryType.LEGAL
        assert len(LEGAL.compliance_rules) > 0
        assert any("attorney-client" in r for r in LEGAL.compliance_rules)

    def test_medical_workflow(self):
        from zilli.industry.workflows import MEDICAL
        assert MEDICAL.industry == IndustryType.MEDICAL
        assert any("HIPAA" in r for r in MEDICAL.compliance_rules)

    def test_financial_workflow(self):
        from zilli.industry.workflows import FINANCIAL
        assert FINANCIAL.industry == IndustryType.FINANCIAL
        assert any("SOX" in r for r in FINANCIAL.compliance_rules)

    def test_education_workflow(self):
        from zilli.industry.workflows import EDUCATION
        assert EDUCATION.industry == IndustryType.EDUCATION
        assert any("FERPA" in r for r in EDUCATION.compliance_rules)


class TestWorkflowRegistry:
    def test_list_industries(self):
        registry = WorkflowRegistry()
        industries = registry.list_industries()
        assert len(industries) == 4
        ids = {ind["id"] for ind in industries}
        assert ids == {"legal", "medical", "financial", "education"}

    def test_get_workflow(self):
        registry = WorkflowRegistry()
        legal = registry.get_workflow(IndustryType.LEGAL)
        assert legal is not None
        assert legal.industry == IndustryType.LEGAL

    def test_get_unknown(self):
        registry = WorkflowRegistry()
        result = registry.get_workflow("unknown")  # type: ignore
        assert result is None

    def test_sanitize_input_removes_pii(self):
        from zilli.industry.workflows import MEDICAL
        result = MEDICAL.sanitize_input("Patient email: test@hospital.com")
        assert "test@hospital.com" not in result
        assert "***" in result

    def test_sanitize_input_clean(self):
        from zilli.industry.workflows import LEGAL
        result = LEGAL.sanitize_input("Standard legal question")
        assert result == "Standard legal question"


class TestIndustryTemplateLoading:
    def test_reload_templates_from_dir(self, tmp_path):
        (tmp_path / "hipaa.yaml").write_text(
            "framework: hipaa\n"
            "name: HIPAA Custom\n"
            "compliance_rules:\n"
            "  - HIPAA rule one\n"
            "  - HIPAA rule two\n"
            "access_level: restricted\n"
            "retention_days: 3650\n"
        )
        registry = WorkflowRegistry(templates_dir=tmp_path)
        report = registry.reload_templates()
        assert len(report["loaded"]) == 1
        med = registry.get_workflow(IndustryType.MEDICAL)
        assert med is not None
        assert med.template_name == "HIPAA Custom"
        assert len(med.compliance_rules) == 2
        assert med.access_level.value == "restricted"
        assert med.retention_days == 3650

    def test_hot_reload_updates_workflow(self, tmp_path):
        cfg = tmp_path / "sox.yaml"
        cfg.write_text("framework: sox\ncompliance_rules:\n  - v1 rule\n")
        registry = WorkflowRegistry(templates_dir=tmp_path)
        fin_v1 = registry.get_workflow(IndustryType.FINANCIAL)
        assert fin_v1 is not None
        assert fin_v1.compliance_rules == ["v1 rule"]

        cfg.write_text("framework: sox\ncompliance_rules:\n  - v2 rule\n")
        report = registry.reload_templates()
        assert report["loaded"]
        fin_v2 = registry.get_workflow(IndustryType.FINANCIAL)
        assert fin_v2.compliance_rules == ["v2 rule"]

    def test_register_unregister_workflow(self, tmp_path):
        from zilli.industry.workflows import IndustryWorkflow
        registry = WorkflowRegistry()
        custom = IndustryWorkflow(
            industry=IndustryType.LEGAL,
            compliance_rules=["custom legal rule"],
            template_name="custom",
        )
        registry.register_workflow(custom)
        assert registry.get_workflow(IndustryType.LEGAL).compliance_rules == ["custom legal rule"]
        assert registry.unregister_workflow(IndustryType.LEGAL) is True
        assert registry.get_workflow(IndustryType.LEGAL) is None

    def test_reload_removes_missing_templates(self, tmp_path):
        (tmp_path / "hipaa.yaml").write_text("framework: hipaa\nname: H1\n")
        (tmp_path / "sox.yaml").write_text("framework: sox\nname: S1\n")
        registry = WorkflowRegistry(templates_dir=tmp_path)
        assert registry.get_workflow(IndustryType.MEDICAL) is not None
        assert registry.get_workflow(IndustryType.FINANCIAL) is not None

        (tmp_path / "hipaa.yaml").unlink()
        report = registry.reload_templates()
        assert "medical" in report["removed"]
        assert registry.get_workflow(IndustryType.MEDICAL) is None
        assert registry.get_workflow(IndustryType.FINANCIAL) is not None

    def test_unknown_framework_skipped(self, tmp_path):
        (tmp_path / "mystery.yaml").write_text("framework: unknown_thing\nname: X\n")
        registry = WorkflowRegistry(templates_dir=tmp_path)
        report = registry.reload_templates()
        assert len(report["skipped"]) == 1
        assert len(report["loaded"]) == 0

    def test_missing_dir_returns_empty_report(self, tmp_path):
        registry = WorkflowRegistry(templates_dir=tmp_path / "nope")
        report = registry.reload_templates()
        assert report["loaded"] == []

    def test_env_var_templates_dir(self, tmp_path, monkeypatch):
        (tmp_path / "ferpa.yaml").write_text("framework: ferpa\nname: F1\n")
        monkeypatch.setenv("ZILLI_INDUSTRY_CONFIG", str(tmp_path))
        registry = WorkflowRegistry()
        edu = registry.get_workflow(IndustryType.EDUCATION)
        assert edu is not None
        assert edu.template_name == "F1"

    def test_industry_from_framework_key(self):
        registry = WorkflowRegistry()
        ind = registry._industry_from_template({"framework": "aba"}, __import__("pathlib").Path("x.yaml"))
        assert ind == IndustryType.LEGAL

    def test_retention_days_from_audit_years(self, tmp_path):
        (tmp_path / "hipaa.yaml").write_text(
            "framework: hipaa\n"
            "audit:\n"
            "  retention_years: 6\n"
        )
        registry = WorkflowRegistry(templates_dir=tmp_path)
        med = registry.get_workflow(IndustryType.MEDICAL)
        assert med.retention_days == 6 * 365
