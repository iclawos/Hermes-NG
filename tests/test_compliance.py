import json
import tempfile
from pathlib import Path

from zilli.audit.compliance import ComplianceFramework, ComplianceReport, ComplianceReporter


def _write_log(audit_dir: Path, events: list[dict], date: str = "2026-07-26"):
    log_file = audit_dir / f"audit_{date}.jsonl"
    with open(log_file, "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


class TestComplianceGenerate:
    def test_empty_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = ComplianceReporter(audit_dir=tmp)
            report = r.generate("gdpr", "t1", "2026-01-01", "2026-12-31")
            assert report.total_requests == 0
            assert report.passed

    def test_counts_routes(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_log(Path(tmp), [
                {"tenant_id": "t1", "route_type": "cloud", "sanitized": True},
                {"tenant_id": "t1", "route_type": "local"},
                {"tenant_id": "t1", "route_type": "cloud", "sanitized": True},
            ])
            r = ComplianceReporter(audit_dir=tmp)
            report = r.generate("gdpr", "t1", "2026-01-01", "2026-12-31")
            assert report.total_requests == 3
            assert report.cloud_requests == 2
            assert report.local_requests == 1
            assert report.sanitized_requests == 2

    def test_tenant_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_log(Path(tmp), [
                {"tenant_id": "t1", "route_type": "cloud"},
                {"tenant_id": "t2", "route_type": "cloud"},
            ])
            r = ComplianceReporter(audit_dir=tmp)
            report = r.generate("gdpr", "t1", "2026-01-01", "2026-12-31")
            assert report.total_requests == 1

    def test_pii_and_consent(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_log(Path(tmp), [
                {"tenant_id": "t1", "pii_count": 3, "consent_violation": True},
                {"tenant_id": "t1", "pii_count": 2},
            ])
            r = ComplianceReporter(audit_dir=tmp)
            report = r.generate("gdpr", "t1", "2026-01-01", "2026-12-31")
            assert report.pii_detected_count == 5
            assert report.consent_violations == 1
            assert not report.passed

    def test_rejected_requests(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_log(Path(tmp), [{"tenant_id": "t1", "rejected": True} for _ in range(15)])
            r = ComplianceReporter(audit_dir=tmp)
            report = r.generate("soc2", "t1", "2026-01-01", "2026-12-31")
            assert report.rejected_requests == 15

    def test_hipaa_unsanitized_cloud_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_log(Path(tmp), [
                {"tenant_id": "t1", "route_type": "cloud", "sanitized": False},
            ])
            r = ComplianceReporter(audit_dir=tmp)
            report = r.generate(ComplianceFramework.HIPAA, "t1", "2026-01-01", "2026-12-31")
            assert not report.passed
            assert any(f["check"] == "cloud_sanitization" for f in report.findings)

    def test_gdpr_pii_without_violation_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_log(Path(tmp), [{"tenant_id": "t1", "pii_count": 1}])
            r = ComplianceReporter(audit_dir=tmp)
            report = r.generate(ComplianceFramework.GDPR, "t1", "2026-01-01", "2026-12-31")
            assert any(f["check"] == "pii_processing_basis" for f in report.findings)
            assert report.passed

    def test_date_range_filtering(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_log(Path(tmp), [{"tenant_id": "t1"}], date="2026-03-15")
            _write_log(Path(tmp), [{"tenant_id": "t1"}, {"tenant_id": "t1"}], date="2026-06-01")
            r = ComplianceReporter(audit_dir=tmp)
            report = r.generate("gdpr", "t1", "2026-04-01", "2026-12-31")
            assert report.total_requests == 2

    def test_invalid_date_includes_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_log(Path(tmp), [{"tenant_id": "t1"}])
            r = ComplianceReporter(audit_dir=tmp)
            report = r.generate("gdpr", "t1", "bad-date", "also-bad")
            assert report.total_requests == 1

    def test_malformed_jsonl_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_file = Path(tmp) / "audit_2026-07-26.jsonl"
            log_file.write_text('{"tenant_id": "t1"}\nnot-json\n\n{"tenant_id": "t1"}\n')
            r = ComplianceReporter(audit_dir=tmp)
            report = r.generate("gdpr", "t1", "2026-01-01", "2026-12-31")
            assert report.total_requests == 2


class TestComplianceExport:
    def test_export_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_log(Path(tmp), [{"tenant_id": "t1", "route_type": "local"}])
            r = ComplianceReporter(audit_dir=tmp)
            report = r.generate("soc2", "t1", "2026-01-01", "2026-12-31")
            out = str(Path(tmp) / "report.json")
            r.export_json(report, out)
            data = json.loads(Path(out).read_text())
            assert data["framework"] == "soc2"
            assert data["summary"]["total_requests"] == 1
            assert data["passed"] is True


class TestComplianceReport:
    def test_defaults(self):
        r = ComplianceReport(framework="gdpr", tenant_id="t", generated_at=0,
                             period_start="", period_end="")
        assert r.passed
        assert r.data_retention_ok
