import asyncio
import json

from zilli.loops.unknowns import UnknownsDiscovery


async def _fake_llm(prompt: str) -> str:
    if "WILDLY DIFFERENT" in prompt:
        return json.dumps([
            {"name": "CLI tool", "pitch": "Minimal terminal app", "tradeoff": "fast but limited",
             "prototype_step": "argparse skeleton", "cost": "low"},
            {"name": "Web dashboard", "pitch": "Browser UI", "tradeoff": "rich but slower",
             "prototype_step": "single HTML mock", "cost": "medium"},
        ])
    if "KEY SEMANTICS" in prompt:
        return "Implementation brief: token bucket with triple-limit cascade."
    if "implementation plan" in prompt.lower():
        return "## 1. Decisions You'll Want to Tweak\n- Data model: flat vs nested"
    return "ok"


def _run(coro):
    return asyncio.run(coro)


class TestBrainstorm:
    def test_returns_variants(self, tmp_path):
        d = UnknownsDiscovery(work_dir=str(tmp_path))
        variants = _run(d.brainstorm("build a rate limiter", _fake_llm))
        assert len(variants) == 2
        assert variants[0]["name"] == "CLI tool"
        assert variants[1]["cost"] == "medium"

    def test_handles_malformed_json(self, tmp_path):
        async def bad_llm(prompt: str) -> str:
            return "not json at all"

        d = UnknownsDiscovery(work_dir=str(tmp_path))
        variants = _run(d.brainstorm("task", bad_llm))
        assert variants == []


class TestDistillReference:
    def test_reads_file(self, tmp_path):
        ref = tmp_path / "ref.py"
        ref.write_text("def token_bucket(): pass")
        d = UnknownsDiscovery(work_dir=str(tmp_path / "work"))
        brief = _run(d.distill_reference(str(ref), _fake_llm, goal="replicate"))
        assert "token bucket" in brief

    def test_missing_path(self, tmp_path):
        d = UnknownsDiscovery(work_dir=str(tmp_path))
        brief = _run(d.distill_reference(str(tmp_path / "nope.py"), _fake_llm))
        assert "not found" in brief.lower()

    def test_reads_directory(self, tmp_path):
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "a.py").write_text("x = 1")
        (pkg / "b.md").write_text("# docs")
        d = UnknownsDiscovery(work_dir=str(tmp_path / "work"))
        brief = _run(d.distill_reference(str(pkg), _fake_llm))
        assert "token bucket" in brief


class TestGeneratePlan:
    def test_saves_plan_file(self, tmp_path):
        d = UnknownsDiscovery(work_dir=str(tmp_path))
        plan = _run(d.generate_plan("build feature", "some context", _fake_llm))
        assert "Decisions" in plan
        assert (tmp_path / "implementation-plan.md").exists()


class TestPackagePitch:
    def test_pitch_contains_sections(self, tmp_path):
        d = UnknownsDiscovery(work_dir=str(tmp_path))
        d.log_decision("arch", "use flat model", "simpler", deviation=True, original_plan="nested")
        pitch = _run(d.package_pitch("My Feature"))
        assert "# My Feature" in pitch
        assert "DEVIATION" in pitch
        assert "use flat model" in pitch
        assert (tmp_path / "pitch.md").exists()

    def test_pitch_includes_plan(self, tmp_path):
        d = UnknownsDiscovery(work_dir=str(tmp_path))
        _run(d.generate_plan("build feature", "ctx", _fake_llm))
        pitch = _run(d.package_pitch("With Plan"))
        assert "Data model: flat vs nested" in pitch
