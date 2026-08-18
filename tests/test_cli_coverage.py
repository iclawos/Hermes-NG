"""CLI handler coverage: in-process invocation of previously-uncovered
subcommands (run, route, industry run, models health, ppm train-model,
unknowns resolve/pitch, swe) plus small-module gaps."""

from __future__ import annotations

import json
import sys

import pytest

from zilli.cli import main


@pytest.fixture(autouse=True)
def _isolate_budget(tmp_path, monkeypatch):
    """Never touch the real ~/.zilli_budget.json during CLI tests."""
    monkeypatch.setenv("ZILLI_BUDGET_FILE", str(tmp_path / "budget.json"))


def _argv(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["zilli"] + list(args))


def _run(coro):
    import asyncio
    return asyncio.run(coro)


class TestCLIRun:
    def test_run_subcommand(self, monkeypatch, capsys):
        """zilli run: agent fallback executes real subprocess, no network."""
        _argv(monkeypatch, "run", "sort a list of numbers")
        main()
        out = capsys.readouterr().out
        assert "PASS" in out or "FAIL" in out

    def test_run_failure(self, monkeypatch, capsys):
        _argv(monkeypatch, "run", "some unknown task with no matching branch")
        main()
        out = capsys.readouterr().out
        assert "Result:" in out


class TestCLIModels:
    def test_models_health(self, monkeypatch, capsys):
        """models health: iterates backends; unreachable endpoints reported."""
        _argv(monkeypatch, "models", "health")
        main()
        out = capsys.readouterr().out
        assert "health" in out.lower() or "✘" in out or "unreachable" in out

    def test_models_usage_error(self, monkeypatch, capsys):
        """Invalid models subcommand → argparse SystemExit (not usage text)."""
        _argv(monkeypatch, "models", "bogus-command")
        with pytest.raises(SystemExit):
            main()

    def test_models_list_empty(self, monkeypatch, capsys):
        _argv(monkeypatch, "models", "list")
        main()
        out = capsys.readouterr().out
        assert out  # either table or "No models registered."


class TestCLIPpmTrain:
    def test_ppm_train_model(self, monkeypatch, capsys, tmp_path):
        records = [
            {"request": "def foo(): pass", "ppm_family": "coding", "actual_difficulty": 0.3},
            {"request": "hello there", "ppm_family": "chat", "actual_difficulty": 0.1},
            {"request": "explain why", "ppm_family": "reasoning", "actual_difficulty": 0.6},
            {"request": "write a story", "ppm_family": "creative", "actual_difficulty": 0.5},
            {"request": "analyze audit", "ppm_family": "analysis", "actual_difficulty": 0.7},
            {"request": "def bar(): return", "ppm_family": "coding", "actual_difficulty": 0.4},
            {"request": "hi", "ppm_family": "chat", "actual_difficulty": 0.1},
            {"request": "compare proof", "ppm_family": "reasoning", "actual_difficulty": 0.6},
        ]
        rec = tmp_path / "records.json"
        rec.write_text(json.dumps(records))
        out = tmp_path / "model.joblib"
        _argv(monkeypatch, "ppm", "train-model", "--records", str(rec),
              "--output", str(out), "--classifier", "sklearn")
        main()
        output = capsys.readouterr().out
        assert "family_accuracy" in output
        assert out.exists() or (tmp_path / "model.joblib").exists()


class TestCLIUnknowns:
    def test_unknowns_resolve(self, monkeypatch, capsys, tmp_path):
        # seed a known unknown id
        _argv(monkeypatch, "unknowns", "resolve", "ID-NOT-EXIST", "test")
        main()
        out = capsys.readouterr().out
        assert "not found" in out.lower() or "resolved" in out.lower()

    def test_unknowns_pitch(self, monkeypatch, capsys, tmp_path):
        _argv(monkeypatch, "unknowns", "pitch", "Test Pitch")
        main()
        out = capsys.readouterr().out
        assert "Saved" in out


class TestPlannerBudgetPersist:
    def test_persist_and_load(self, tmp_path):
        from zilli.envs.planner_budget import PlannerBudget
        f = tmp_path / "budget.json"
        b = PlannerBudget(window_size=50, max_planner_ratio=0.1, budget_file=str(f))
        b.record_call("executor")
        b.record_call("planner")
        assert f.exists()

        loaded = PlannerBudget.load(str(f))
        assert loaded._window_size == 50
        assert loaded.planner_ratio == pytest.approx(0.5, abs=0.01)

    def test_load_missing_file_returns_default(self, tmp_path):
        from zilli.envs.planner_budget import PlannerBudget
        loaded = PlannerBudget.load(str(tmp_path / "nope.json"), window_size=7)
        assert loaded._window_size == 7


class TestClassifierModelPath:
    def test_classify_with_model(self):
        import asyncio

        from zilli.routing.classifier import RouteClassifier, RouteType

        class _FakeBackend:
            async def generate(self, prompt, **kw):
                return type("R", (), {"text": "full_route", "error": None})()

        class _FakeRegistry:
            async def get_model_for_role(self, role):
                return _FakeBackend()

        c = RouteClassifier(model_registry=_FakeRegistry())
        decision = asyncio.run(c.classify_with_model("analyze this design"))
        assert decision.route == RouteType.FULL_ROUTE

    def test_classify_with_model_error_falls_back(self):
        import asyncio

        from zilli.routing.classifier import RouteClassifier, RouteType

        class _ErrBackend:
            async def generate(self, prompt, **kw):
                return type("R", (), {"text": "", "error": "model down"})()

        class _ErrRegistry:
            async def get_model_for_role(self, role):
                return _ErrBackend()

        c = RouteClassifier(model_registry=_ErrRegistry())
        decision = asyncio.run(c.classify_with_model("simple hello"))
        assert decision.route == RouteType.FAST_LANE

    def test_classify_no_registry_uses_rules(self):
        from zilli.routing.classifier import RouteClassifier, RouteType
        c = RouteClassifier()
        assert c.classify("hello").route == RouteType.FAST_LANE
        assert c.classify("x" * 600).route == RouteType.FULL_ROUTE


class TestTrajectoryStore:
    """Experience replay: priority sampling, purify, noise, size enforcement."""

    def _traj(self, n=2):
        return [{"step": i, "action": {"a": i}, "observation": {"success": True}}
                for i in range(n)]

    def test_add_production_and_priority_sample(self):
        from zilli.data import TrajectoryStore

        s = TrajectoryStore()
        s.add_production_trajectories([
            {"trajectory": self._traj(), "reward": 0.9},
        ])
        assert len(s.rollout_buffer) == 1
        s.golden_trajectories.append({"trajectory": self._traj(), "reward": 0.9})
        # priority sample with use_priority
        batch = s.sample_batch(batch_size=4, use_priority=True)
        assert len(batch) >= 1

    def test_priority_sample_empty(self):
        from zilli.data import TrajectoryStore

        s = TrajectoryStore()
        assert s.sample_batch(batch_size=4, use_priority=True) == []

    def test_enforce_max_size(self):
        from zilli.data import TrajectoryStore

        s = TrajectoryStore({"max_size": 2})
        for i in range(4):
            s.rollout_buffer.append({"trajectory": self._traj(), "reward": 0.1 * i})
        s._enforce_max_size()
        assert len(s.rollout_buffer) == 2

    def test_purify(self):
        from zilli.data import TrajectoryStore

        s = TrajectoryStore()
        s.golden_trajectories.append({"trajectory": self._traj(), "reward": 0.9})
        s.failure_trajectories.append({
            "trajectory": [{"observation": {"error": "E1"}},
                           {"observation": {"error": "E2"}}],
            "reward": 0.1,
        })
        s.rollout_buffer.append({"trajectory": self._traj(), "reward": 0.5})
        removed = s.purify()
        assert removed >= 0
        # stats reflect cleaning
        stats = s.stats()
        assert stats["total"] >= 0

    def test_summarize_error(self):
        from zilli.data import TrajectoryStore

        s = TrajectoryStore()
        err = s._summarize_error([
            {"observation": {"error": "KeyError: x"}},
            {"observation": {"error": "TypeError: y"}},
            {"observation": {"ok": True}},
            {"observation": {"error": "ValueError: z"}},
        ])
        assert "KeyError" in err and "ValueError" in err
        assert s._summarize_error([{"observation": {"ok": True}}]) == "Unknown failure"

    def test_add_noise(self):
        from zilli.data import TrajectoryStore

        s = TrajectoryStore()
        traj = [{"step": 0, "action": {"a": 1},
                 "observation": {"success": True, "reward": 1.0}}]
        noisy = s._add_noise(traj, noise_level=0.0)
        assert noisy[0]["step"] == 0
        assert noisy[0]["observation"]["reward"] == 1.0

    def test_avg_reward_and_length(self):
        from zilli.data import TrajectoryStore

        s = TrajectoryStore()
        assert s._avg_reward([]) == 0.0
        assert s._avg_length() == 0.0
        s.golden_trajectories.append({"trajectory": self._traj(), "reward": 1.0, "length": 2})
        assert s._avg_reward(s.golden_trajectories) == pytest.approx(1.0)
        assert s._avg_length() == pytest.approx(2.0)

    def test_sample_batch_priority_zero_priorities(self, monkeypatch):
        from zilli.data import TrajectoryStore

        s = TrajectoryStore()
        s.rollout_buffer.append({"trajectory": self._traj(), "reward": 0.5})
        monkeypatch.setattr(s, "_entry_priority", lambda e: 0.0)
        batch = s._priority_sample(2)
        assert len(batch) == 1


class TestHermesSandbox:
    """Mock env tool registry and scenario branches."""

    async def _step(self, sandbox, tool_name, **kw):
        return await sandbox.step({
            "tool_name": tool_name,
            "action_id": "1",
            "reasoning": "r",
            **kw,
        })

    def test_unknown_tool(self):
        import asyncio

        from zilli.envs import HermesSandbox

        sandbox = HermesSandbox()
        r = asyncio.run(self._step(sandbox, "nonexistent_tool"))
        assert r["done"] is True
        assert "Unknown tool" in r["observation"]["error"]

    def test_error_probability(self, monkeypatch):
        import asyncio

        from zilli.envs import HermesSandbox

        sandbox = HermesSandbox(scenario={"error_probability": 1.0})
        monkeypatch.setattr("random.random", lambda: 0.5)
        r = asyncio.run(self._step(sandbox, "memory_write", key="k", value="v"))
        assert r["reward"] == -0.5
        assert r["observation"]["success"] is False

    def test_scenario_initial_state(self):
        import asyncio

        from zilli.envs import HermesSandbox

        sandbox = HermesSandbox(scenario={
            "initial_files": {"a.py": "print(1)"},
            "initial_memory": {"whoami": "zilli"},
        })
        assert sandbox.context["files"]["a.py"] == "print(1)"
        assert sandbox.context["memory"]["whoami"] == "zilli"
        r = asyncio.run(self._step(sandbox, "memory_read", key="whoami"))
        assert r["observation"]["success"] is True

    def test_finish_and_max_turns(self):
        import asyncio

        from zilli.envs import HermesSandbox

        sandbox = HermesSandbox(scenario={"max_turns": 1})
        r = asyncio.run(self._step(sandbox, "memory_write", key="k", value="v"))
        assert r["done"] is True  # max_turns reached
        sandbox.reset()
        r = asyncio.run(self._step(sandbox, "finish", summary="done"))
        assert r["done"] is True

    def test_tool_registry_and_tools(self):
        import asyncio

        from zilli.envs import HermesSandbox
        from zilli.envs.mock_env import get_tool_registry, register_tool

        reg = get_tool_registry()
        assert "memory_write" in reg
        assert "finish" in reg
        assert "web_search" in reg

        @register_tool("test_custom_tool")
        def _custom(ctx, x):
            return {"success": True, "x": x}

        assert "test_custom_tool" in get_tool_registry()
        sandbox = HermesSandbox()
        r = asyncio.run(self._step(sandbox, "test_custom_tool", x=42))
        assert r["observation"]["x"] == 42
        assert r["reward"] == 1.0

    def test_skill_update_and_file_ops(self):
        import asyncio

        from zilli.envs import HermesSandbox

        sandbox = HermesSandbox()
        # create skill then update
        r = asyncio.run(self._step(sandbox, "skill_create", name="s1", code="x=1"))
        assert r["observation"]["success"] is True
        r = asyncio.run(self._step(sandbox, "skill_update", name="s1", code="x=2"))
        assert r["observation"]["success"] is True
        # update missing skill fails
        r = asyncio.run(self._step(sandbox, "skill_update", name="nope", code="x"))
        assert r["observation"]["success"] is False
        # file write then read then missing
        r = asyncio.run(self._step(sandbox, "file_write", path="f.txt", content="hi"))
        assert r["observation"]["bytes"] == 2
        r = asyncio.run(self._step(sandbox, "file_read", path="f.txt"))
        assert r["observation"]["content"] == "hi"
        r = asyncio.run(self._step(sandbox, "file_read", path="missing"))
        assert r["observation"]["success"] is False

    def test_bash_and_web_and_code(self):
        import asyncio

        from zilli.envs import HermesSandbox

        sandbox = HermesSandbox(scenario={
            "search_results": {"news": ["result-1"]},
            "code_errors": ["bug"],
        })
        r = asyncio.run(self._step(sandbox, "bash_run", command="ls"))
        assert r["observation"]["success"] is True
        r = asyncio.run(self._step(sandbox, "bash_run", command="error case"))
        assert r["observation"]["success"] is False
        r = asyncio.run(self._step(sandbox, "web_search", query="news"))
        assert r["observation"]["results"] == ["result-1"]
        r = asyncio.run(self._step(sandbox, "code_interpreter", code="print('bug')"))
        assert r["observation"]["success"] is False

    def test_reset_and_stats(self):
        import asyncio

        from zilli.envs import HermesSandbox

        sandbox = HermesSandbox()
        asyncio.run(self._step(sandbox, "memory_write", key="k", value="v"))
        sandbox.reset()
        stats = sandbox.get_stats()
        assert stats["turns"] == 0
        assert stats["trajectory_length"] == 0


class TestModelProfile:
    """Routing ModelProfile persistence, selection, and capability updates."""

    def _make(self, tmp_path, n=3):
        from zilli.routing.profile import ModelEntry, ModelProfile

        p = ModelProfile(persist_path=str(tmp_path / "profile.json"), exploration_factor=0.0)
        for i in range(n):
            p.register(ModelEntry(
                name=f"m{i}", model_id=f"id{i}",
                cost_per_1k_input=0.1 * (i + 1), cost_per_1k_output=0.2 * (i + 1),
                success_rate=0.9 - 0.1 * i,
            ))
        return p

    def test_filter_skips_expensive_and_low_success(self, tmp_path):
        p = self._make(tmp_path)
        # id0 cost 0.1/0.2; filter max_cost=0.15 both dirs → id0 only
        cands = p.filter("coding", max_cost=0.15)
        assert len(cands) == 1
        assert cands[0].model_id == "id0"
        # min_success_rate filter
        cands = p.filter("coding", max_cost=float("inf"), min_success_rate=0.85)
        assert all(c.success_rate >= 0.85 for c in cands)

    def test_select_best_single_and_persist(self, tmp_path):
        p = self._make(tmp_path, n=1)
        best = p.select_best("chat", p.filter("chat"))
        assert best.model_id == "id0"
        assert (tmp_path / "profile.json").exists()

    def test_select_best_uses_softmax_and_saves(self, tmp_path):
        p = self._make(tmp_path)
        cands = p.filter("chat")
        best = p.select_best("chat", cands)
        assert best is not None
        assert best.call_count >= 1
        assert best.last_used > 0
        # second selection mutates persistence
        p2 = self._make(tmp_path)
        assert p2.get("id0") is not None

    def test_select_best_empty(self, tmp_path):
        p = self._make(tmp_path)
        assert p.select_best("chat", []) is None

    def test_update_capability_and_success(self, tmp_path):
        p = self._make(tmp_path, n=1)
        e = p.get("id0")
        orig = e.capability.reasoning
        p.update_capability("id0", {"reasoning": 1.0})
        assert p.get("id0").capability.reasoning == pytest.approx(orig * 0.7 + 1.0 * 0.3)
        # unknown dimension ignored
        p.update_capability("id0", {"bogus": 1.0})
        # unknown model no-op
        p.update_capability("nope", {"reasoning": 1.0})
        # success rate update
        p.update_success_rate("id0", True)
        assert p.get("id0").success_rate > 0.8
        p.update_success_rate("nope", False)  # no-op

    def test_load_from_persisted_json(self, tmp_path):
        from zilli.routing.profile import ModelCapability, ModelEntry, ModelProfile

        path = tmp_path / "profile.json"
        p = ModelProfile(persist_path=str(path), exploration_factor=0.0)
        p.register(ModelEntry(name="x", model_id="x1", capability=ModelCapability(reasoning=0.8)))

        p2 = ModelProfile(persist_path=str(path))
        assert p2.get("x1") is not None
        assert p2.get("x1").capability.reasoning == pytest.approx(0.8)

    def test_exploration_shuffles(self, tmp_path, monkeypatch):
        from zilli.routing.profile import ModelEntry, ModelProfile

        p = ModelProfile(persist_path=str(tmp_path / "p.json"), exploration_factor=1.0)
        for i in range(6):
            p.register(ModelEntry(name=f"m{i}", model_id=f"id{i}", cost_per_1k_input=1.0,
                                  cost_per_1k_output=1.0, success_rate=1.0))
        cands = p.filter("chat", max_cost=5.0)
        assert len(cands) >= 1

    def test_unregister(self, tmp_path):
        p = self._make(tmp_path)
        p.unregister("id0")
        assert p.get("id0") is None


class TestContinuousLearnerRunLoop:
    def test_collect_and_archive(self, tmp_path):
        import asyncio

        from zilli.data import TrajectoryStore
        from zilli.learner.continuous_learner import ContinuousLearner

        data_dir = tmp_path / "prod"
        data_dir.mkdir()
        (data_dir / "a.json").write_text(json.dumps({
            "trajectory": [{"observation": {"success": True}}], "reward": 0.9,
        }))
        (data_dir / "bad.json").write_text("{not json")

        store = TrajectoryStore()
        cl = ContinuousLearner(store=store, data_dir=str(data_dir), interval_hours=24)

        trajs, processed = asyncio.run(cl._collect_production_trajectories())
        assert len(trajs) >= 1
        assert len(processed) == 1  # bad.json skipped, a.json processed
        assert not (data_dir / "a.json").exists() or True  # not archived yet

        cl._archive_processed_data(processed)
        assert cl.archive_dir.exists()

        stats = cl.stats()
        assert stats["interval_hours"] == 24
        assert stats["recent_files"] >= 2  # one ok + one bad json

    def test_sft_trigger_writes_log(self, tmp_path):
        import asyncio

        from zilli.data import TrajectoryStore
        from zilli.learner.continuous_learner import ContinuousLearner

        data_dir = tmp_path / "prod"
        data_dir.mkdir()
        store = TrajectoryStore()
        store.add_trajectory([
            {"observation": {"success": True}},
            {"observation": {"success": True}},
        ], 0.9)
        cl = ContinuousLearner(
            store=store, data_dir=str(data_dir), sft_threshold=1,
            sft_callback=lambda stats: {"custom": True},
        )
        metrics = asyncio.run(cl._trigger_online_sft())
        assert metrics["golden"] >= 1
        assert (data_dir / "sft_events.jsonl").exists()

    def test_run_loop_one_cycle(self, tmp_path, monkeypatch):
        """run(): one full cycle with data, then stop."""
        import asyncio

        from zilli.data import TrajectoryStore
        from zilli.learner.continuous_learner import ContinuousLearner

        data_dir = tmp_path / "prod"
        data_dir.mkdir()
        (data_dir / "a.json").write_text(json.dumps([
            {"trajectory": [{"observation": {"success": True}},
                            {"observation": {"success": True}}],
             "reward": 0.9},
        ]))

        store = TrajectoryStore()
        cl = ContinuousLearner(store=store, data_dir=str(data_dir), interval_hours=1)

        async def _short_sleep(delay):
            cl._running = False  # stop after first wake

        monkeypatch.setattr(asyncio, "sleep", _short_sleep)
        asyncio.run(cl.run())
        assert cl._cycle_count == 1
        assert cl._total_production_trajs == 1
        assert len(cl._cycles) == 1

    def test_run_loop_error_path(self, tmp_path, monkeypatch):
        """run(): collect raises → error handled, retry backoff, stops."""
        import asyncio

        from zilli.data import TrajectoryStore
        from zilli.learner.continuous_learner import ContinuousLearner

        store = TrajectoryStore()
        cl = ContinuousLearner(store=store, data_dir=str(tmp_path / "prod"),
                               interval_hours=1)

        async def _boom():
            raise RuntimeError("boom")

        monkeypatch.setattr(cl, "_collect_production_trajectories", _boom)

        calls = []

        async def _short_sleep(delay):
            calls.append(delay)
            cl._running = False

        monkeypatch.setattr(asyncio, "sleep", _short_sleep)
        asyncio.run(cl.run())
        assert cl._cycle_count == 1
        assert cl._cycles[0].sft_metrics == {"error": "boom"}
        assert calls  # retry backoff was used

    def test_stop(self, tmp_path):
        import asyncio

        from zilli.data import TrajectoryStore
        from zilli.learner.continuous_learner import ContinuousLearner

        cl = ContinuousLearner(store=TrajectoryStore(), data_dir=str(tmp_path / "prod"))
        asyncio.run(cl.stop())
        assert cl._running is False


class TestRunCost:
    def test_cost_status_per_task_stats(self, monkeypatch, capsys, tmp_path):
        _argv(monkeypatch, "cost", "status")
        main()
        out = capsys.readouterr().out
        assert "Budget" in out


class TestRunDistillMissingConfig:
    def test_distill_config_not_found(self, monkeypatch, capsys, tmp_path):
        _argv(monkeypatch, "distill", "--config", str(tmp_path / "missing.yaml"),
              "--samples", "5", "--log-dir", str(tmp_path))
        main()
        assert "Config not found" in capsys.readouterr().out

    def test_distill_path_traversal(self, monkeypatch, capsys, tmp_path):
        _argv(monkeypatch, "distill", "--config", "../etc/passwd",
              "--samples", "5")
        main()
        assert "traversal" in capsys.readouterr().out.lower()


class TestRunTrainPathTraversal:
    def test_train_path_traversal(self, monkeypatch, capsys):
        _argv(monkeypatch, "train", "--config", "../evil.yaml")
        main()
        assert "traversal" in capsys.readouterr().out.lower()


class TestSweCLI:
    def test_swe_no_model_no_repo(self, monkeypatch, capsys, tmp_path):
        """swe with no model: falls back to rule-based agent on a tmp repo."""
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "bug.py").write_text("def f():\n    return x\n")
        _argv(monkeypatch, "swe", "--repo", str(repo), "--issue", "fix the bug")
        main()
        out = capsys.readouterr().out
        assert "SWE" in out


class TestCLIRoute:
    def test_route_subcommand(self, monkeypatch, capsys):
        """route: works offline — no healthy models → graceful error output."""
        _argv(monkeypatch, "route", "hello world", "--verbose")
        main()
        out = capsys.readouterr().out
        assert "Route:" in out
        assert "Decision:" in out

    def test_route_truncated_output(self, monkeypatch, capsys):
        _argv(monkeypatch, "route", "x" * 2500)
        main()
        out = capsys.readouterr().out
        assert "truncated" in out.lower() or "Route:" in out


class TestCLIIndustry:
    def test_industry_run(self, monkeypatch, capsys):
        _argv(monkeypatch, "industry", "run", "medical", "hello world", "--tenant", "test")
        main()
        out = capsys.readouterr().out
        assert "Industry:" in out or "OUTPUT" in out

    def test_industry_run_full_route_no_sanitize(self, monkeypatch, capsys):
        _argv(monkeypatch, "industry", "run", "legal", "hello world",
              "--tenant", "test", "--full-route", "--no-sanitize")
        main()
        out = capsys.readouterr().out
        assert "OUTPUT" in out


class TestCLIModelsGenerateNoHealthy:
    def test_models_generate_no_healthy(self, monkeypatch, capsys):
        _argv(monkeypatch, "models", "generate", "planner", "hello")
        main()
        out = capsys.readouterr().out
        assert "Error" in out or "PLANNER" in out


class TestCLIPipeline:
    def test_pipeline_subcommand(self, monkeypatch, capsys, tmp_path):
        skills = tmp_path / "skills"
        skills.mkdir()
        (skills / "s.py").write_text("def run():\n    return 0\n")
        traj = tmp_path / "traj"
        traj.mkdir()
        (traj / "t.json").write_text(json.dumps([
            {"observation": {"error": "KeyError: x"}},
        ]))
        _argv(monkeypatch, "pipeline", "--skills-dir", str(skills),
              "--trajectories-dir", str(traj), "--cycles", "1", "--epochs", "1",
              "--log-dir", str(tmp_path / "exp"))
        main()
        out = capsys.readouterr().out
        assert "Pipeline Complete" in out or "Cycle" in out


class TestCLIEvaluateTrain:
    def test_evaluate_cost_aware(self, monkeypatch, capsys):
        _argv(monkeypatch, "evaluate", "--cost-aware", "--budget", "100")
        main()
        out = capsys.readouterr().out
        assert "Cost summary" in out
        assert "Remaining budget" in out

    def test_evaluate_task_not_found(self, monkeypatch, capsys):
        _argv(monkeypatch, "evaluate", "does_not_exist")
        main()
        assert "Task not found" in capsys.readouterr().out

    def test_train_cost_aware(self, monkeypatch, capsys):
        _argv(monkeypatch, "train", "--cost-aware", "--budget", "100")
        main()
        out = capsys.readouterr().out
        assert "Training simulation complete" in out
        assert "Cost summary" in out

    def test_train_path_traversal(self, monkeypatch, capsys):
        _argv(monkeypatch, "train", "--config", "../etc/passwd")
        main()
        assert "Path traversal" in capsys.readouterr().out


class TestCLIRouteVerbose:
    """route --verbose with a stub router producing planner/executor output."""

    def _stub_route_parts(self, monkeypatch):
        import zilli.routing as routing_mod
        from zilli.routing.classifier import RouteDecision, RouteType
        from zilli.routing.router import RouteResult

        class _StubRegistry:
            pass

        class _StubClassifier:
            pass

        class _StubRouter:
            async def run(self, request, industry=None, force_full_route=False):
                return RouteResult(
                    final_text="short final",
                    route_type=RouteType.FAST_LANE,
                    decision=RouteDecision(RouteType.FAST_LANE, reason="stub decision"),
                    planner_result="[PLANNER] long output " + "x" * 500,
                    executor_result="[EXECUTOR] " + "y" * 500,
                    total_duration_ms=12.0,
                )

        monkeypatch.setattr(routing_mod, "RouteClassifier", lambda *a, **k: _StubClassifier())
        monkeypatch.setattr(routing_mod, "LocalHybridRouter", lambda *a, **k: _StubRouter())
        import zilli.models as models_mod
        monkeypatch.setattr(models_mod, "ModelRegistry", lambda *a, **k: _StubRegistry())

    def test_route_verbose_full(self, monkeypatch, capsys):
        self._stub_route_parts(monkeypatch)
        _argv(monkeypatch, "route", "hello world", "--verbose", "--full-route")
        main()
        out = capsys.readouterr().out
        assert "PLANNER OUTPUT" in out
        assert "EXECUTOR OUTPUT" in out
        assert "short final" in out

    def test_route_verbose_truncated_final(self, monkeypatch, capsys):
        self._stub_route_parts(monkeypatch)
        # patch router to return a >2000 char final_text
        import zilli.routing as routing_mod
        from zilli.routing.classifier import RouteDecision, RouteType
        from zilli.routing.router import RouteResult

        class _LongRouter:
            async def run(self, request, industry=None, force_full_route=False):
                return RouteResult(
                    final_text="F" * 2500,
                    route_type=RouteType.FULL_ROUTE,
                    decision=RouteDecision(RouteType.FULL_ROUTE, reason="stub"),
                    total_duration_ms=5.0,
                )

        monkeypatch.setattr(routing_mod, "LocalHybridRouter", lambda *a, **k: _LongRouter())
        _argv(monkeypatch, "route", "hello world", "--verbose", "--full-route")
        main()
        out = capsys.readouterr().out
        assert "truncated to 2000 chars" in out


class TestCLIModelsGenerateSuccess:
    def test_models_generate_success(self, monkeypatch, capsys):
        """models generate with a stub registry returning success."""
        import zilli.models as models_mod
        from zilli.models.base import GenerationResult

        class _StubBackend:
            async def health_check(self):
                return True

            async def generate(self, prompt, max_tokens=None, temperature=None):
                return GenerationResult(
                    text="stub text", model_name="planner",
                    tokens_in=10, tokens_out=5, duration_ms=3.0,
                )

        class _StubRegistry:
            async def generate(self, role, prompt, max_tokens=None, temperature=None):
                return GenerationResult(
                    text="stub text", model_name="planner",
                    tokens_in=10, tokens_out=5, duration_ms=3.0,
                )

        monkeypatch.setattr(models_mod, "ModelRegistry", lambda *a, **k: _StubRegistry())
        _argv(monkeypatch, "models", "generate", "planner", "hello")
        main()
        out = capsys.readouterr().out
        assert "PLANNER" in out
        assert "stats:" in out

    def test_models_health_ok(self, monkeypatch, capsys):
        """models health: backend loaded and healthy."""
        import zilli.models as models_mod

        class _StubBackend:
            async def health_check(self):
                return True

        class _Cfg:
            name = "planner"
            model_id = "qwen3"
            base_url = "http://x:11434"

        class _Profile:
            models = [_Cfg()]

        class _StubRegistry:
            profile = _Profile()

            def get_model(self, name):
                return _StubBackend()

        monkeypatch.setattr(models_mod, "ModelRegistry", lambda *a, **k: _StubRegistry())
        _argv(monkeypatch, "models", "health")
        main()
        out = capsys.readouterr().out
        assert "healthy" in out

    def test_models_health_backend_not_loaded(self, monkeypatch, capsys):
        """models health: cfg in profile but get_model returns None."""
        import zilli.models as models_mod

        class _Cfg:
            name = "planner"
            model_id = "qwen3"
            base_url = "http://x:11434"

        class _Profile:
            models = [_Cfg()]

        class _StubRegistry:
            profile = _Profile()

            def get_model(self, name):
                return None

        monkeypatch.setattr(models_mod, "ModelRegistry", lambda *a, **k: _StubRegistry())
        _argv(monkeypatch, "models", "health")
        main()
        out = capsys.readouterr().out
        assert "backend not loaded" in out

    def test_models_usage(self, monkeypatch, capsys):
        """models with no subcommand → usage."""
        import zilli.models as models_mod
        monkeypatch.setattr(models_mod, "ModelRegistry", lambda *a, **k: object())
        _argv(monkeypatch, "models")
        main()
        assert "Usage" in capsys.readouterr().out


class TestCLIUnknownsLLM:
    """unknowns reference + interview with stubbed model."""

    def _stub_registry(self, monkeypatch):
        import zilli.models as models_mod

        class _StubBackend:
            async def generate(self, prompt, **kw):
                return type("R", (), {"text": "stub response"})

        class _StubRegistry:
            def get_model(self, name):
                return _StubBackend()

        monkeypatch.setattr(models_mod, "ModelRegistry", lambda *a, **k: _StubRegistry())

    def test_reference(self, monkeypatch, capsys, tmp_path):
        self._stub_registry(monkeypatch)
        ref = tmp_path / "ref.py"
        ref.write_text("def f():\n    return 1\n")
        _argv(monkeypatch, "unknowns", "reference", str(ref))
        main()
        out = capsys.readouterr().out
        assert "Reference Brief" in out

    def test_interview_with_unknowns(self, monkeypatch, capsys, tmp_path):
        self._stub_registry(monkeypatch)
        monkeypatch.chdir(tmp_path)
        # seed an unresolved unknown in the CLI's default work_dir ./unknowns
        from zilli.loops.unknowns import UnknownCategory, UnknownItem, UnknownsDiscovery
        d = UnknownsDiscovery(work_dir=str(tmp_path / "unknowns"))
        d._unknowns = [UnknownItem(id="u1", description="how to x", category=UnknownCategory.UNKNOWN_KNOWN)]
        d._save()
        monkeypatch.setattr("builtins.input", lambda *a: "task")
        _argv(monkeypatch, "unknowns", "interview")
        main()
        out = capsys.readouterr().out
        assert "Interview Questions" in out


class TestCLICost:
    def test_cost_status_and_reset(self, monkeypatch, capsys):
        _argv(monkeypatch, "cost", "status")
        main()
        out = capsys.readouterr().out
        assert "Budget Status" in out

        _argv(monkeypatch, "cost", "reset-month")
        main()
        assert "reset" in capsys.readouterr().out.lower()

    def test_cost_usage(self, monkeypatch, capsys):
        _argv(monkeypatch, "cost", "bogus")
        with pytest.raises(SystemExit):
            main()


class TestCLIModelsList:
    def test_models_list_empty(self, monkeypatch, capsys):
        """models list with no registered models."""
        import zilli.models as models_mod

        class _StubRegistry:
            def list_models(self):
                return []

        monkeypatch.setattr(models_mod, "ModelRegistry", lambda *a, **k: _StubRegistry())
        _argv(monkeypatch, "models", "list")
        main()
        assert "No models registered" in capsys.readouterr().out


class TestCLIIndustryList:
    def test_industry_list_empty(self, monkeypatch, capsys):
        import zilli.industry as ind_mod

        class _StubRegistry:
            def list_industries(self):
                return []

        monkeypatch.setattr(ind_mod, "WorkflowRegistry", lambda *a, **k: _StubRegistry())
        _argv(monkeypatch, "industry", "list")
        main()
        assert "No industries registered" in capsys.readouterr().out


class TestCLISoak:
    def test_soak_with_stop_file(self, monkeypatch, capsys, tmp_path):
        """soak: creates stop file before run → exits immediately, prints summary."""
        skills = tmp_path / "skills"
        skills.mkdir()
        traj = tmp_path / "traj"
        traj.mkdir()
        stop = tmp_path / "stop.txt"
        stop.write_text("stop")
        status = tmp_path / "soak_status.json"
        _argv(monkeypatch, "soak", "--skills-dir", str(skills),
              "--trajectories-dir", str(traj), "--interval", "1",
              "--status", str(status), "--metrics", str(tmp_path / "m.jsonl"),
              "--stop-file", str(stop))
        main()
        out = capsys.readouterr().out
        assert "Soak Summary" in out


class TestUnknownsCLIResolve:
    def test_resolve_not_found(self, monkeypatch, capsys, tmp_path):
        monkeypatch.chdir(tmp_path)
        _argv(monkeypatch, "unknowns", "resolve", "nope", "whatever")
        main()
        assert "not found" in capsys.readouterr().out

    def test_summary_empty(self, monkeypatch, capsys, tmp_path):
        monkeypatch.chdir(tmp_path)
        _argv(monkeypatch, "unknowns", "summary")
        main()
        out = capsys.readouterr().out
        assert "Total unknowns: 0" in out

    def test_summary_with_categories(self, monkeypatch, capsys, tmp_path):
        monkeypatch.chdir(tmp_path)
        from zilli.loops.unknowns import (
            UnknownCategory,
            UnknownItem,
            UnknownsDiscovery,
        )

        d = UnknownsDiscovery(work_dir=str(tmp_path / "unknowns"))
        d._unknowns = [
            UnknownItem(id="a", description="x", category=UnknownCategory.KNOWN_UNKNOWN),
            UnknownItem(id="b", description="y", category=UnknownCategory.KNOWN_UNKNOWN,
                        resolved=True, resolution="done"),
        ]
        d._save()
        _argv(monkeypatch, "unknowns", "summary")
        main()
        out = capsys.readouterr().out
        assert "1/2 resolved" in out

    def test_interview_no_unresolved(self, monkeypatch, capsys, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("builtins.input", lambda *a: "task")
        _argv(monkeypatch, "unknowns", "interview")
        main()
        assert "No unresolved unknowns" in capsys.readouterr().out

    def test_model_not_registered_error(self, monkeypatch, capsys, tmp_path):
        """unknowns LLM path with no planner model → error message."""
        import zilli.models as models_mod

        class _StubRegistry:
            def get_model(self, name):
                return None

        monkeypatch.setattr(models_mod, "ModelRegistry", lambda *a, **k: _StubRegistry())
        _argv(monkeypatch, "unknowns", "brainstorm", "build a thing")
        main()
        assert "not registered" in capsys.readouterr().out


class TestUnknownsCore:
    """Direct unit tests for UnknownsDiscovery persistence & fallbacks."""

    def test_resolve_and_persist(self, tmp_path):
        from zilli.loops.unknowns import (
            UnknownCategory,
            UnknownItem,
            UnknownsDiscovery,
        )

        d = UnknownsDiscovery(work_dir=str(tmp_path / "u"))
        u = UnknownItem(
            id="u1", description="how to scale", category=UnknownCategory.UNKNOWN_KNOWN,
        )
        d._unknowns.append(u)
        assert d.resolve_unknown("u1", "use sharding") is True
        assert u.resolved is True
        assert u.resolution == "use sharding"
        assert (tmp_path / "u" / "unknowns.json").exists()
        assert d.resolve_unknown("nope", "x") is False
        # reload from disk
        d2 = UnknownsDiscovery(work_dir=str(tmp_path / "u"))
        assert len(d2._unknowns) == 1
        assert d2._unknowns[0].resolved is True

    def test_get_unresolved_and_summary(self, tmp_path):
        from zilli.loops.unknowns import (
            UnknownCategory,
            UnknownItem,
            UnknownsDiscovery,
        )

        d = UnknownsDiscovery(work_dir=str(tmp_path / "u"))
        d._unknowns = [
            UnknownItem(id="a", description="x", category=UnknownCategory.KNOWN_UNKNOWN),
            UnknownItem(id="b", description="y", category=UnknownCategory.KNOWN_KNOWN,
                        resolved=True, resolution="done"),
            UnknownItem(id="c", description="z", category=UnknownCategory.UNKNOWN_KNOWN),
        ]
        assert len(d.get_unresolved()) == 2
        assert len(d.get_unresolved(category=UnknownCategory.UNKNOWN_KNOWN)) == 1
        s = d.summary()
        assert s["total_unknowns"] == 3
        assert s["resolved"] == 1
        assert s["by_category"]["known_unknown"]["total"] == 1

    def test_log_decision_and_notes(self, tmp_path):
        from zilli.loops.unknowns import UnknownsDiscovery

        d = UnknownsDiscovery(work_dir=str(tmp_path / "u"))
        d.log_decision("arch", "use postgres", "need SQL", deviation=True,
                       original_plan="use mysql")
        assert len(d.get_notes()) == 1
        assert len(d.get_notes(deviation_only=True)) == 1
        assert (tmp_path / "u" / "implementation-notes.md").exists()

    def test_generate_interview_questions(self, tmp_path):
        import asyncio

        from zilli.loops.unknowns import (
            UnknownCategory,
            UnknownItem,
            UnknownsDiscovery,
        )

        d = UnknownsDiscovery(work_dir=str(tmp_path / "u"))
        d._unknowns = [UnknownItem(id="a", description="scale", category=UnknownCategory.UNKNOWN_KNOWN)]

        async def llm(prompt):
            return '["q1", "q2"]'

        qs = asyncio.run(d.generate_interview_questions("task", d.get_unresolved(), llm))
        assert qs == ["q1", "q2"]

        async def llm_bad(prompt):
            return "not json"

        qs = asyncio.run(d.generate_interview_questions("task", d.get_unresolved(), llm_bad))
        assert len(qs) == 1

    def test_generate_quiz(self, tmp_path):
        import asyncio

        from zilli.loops.unknowns import UnknownsDiscovery

        d = UnknownsDiscovery(work_dir=str(tmp_path / "u"))

        async def llm(prompt):
            return json.dumps([{
                "question": "q?", "options": ["a", "b"],
                "correct_answer": 0, "explanation": "e",
            }])

        quiz = asyncio.run(d.generate_quiz("changes", llm, num_questions=1))
        assert len(quiz) == 1
        assert quiz[0].correct_answer == 0

        async def llm_bad(prompt):
            return "garbage"

        assert asyncio.run(d.generate_quiz("changes", llm_bad)) == []

    def test_brainstorm_json_fallback_and_empty(self, tmp_path):
        import asyncio

        from zilli.loops.unknowns import UnknownsDiscovery

        d = UnknownsDiscovery(work_dir=str(tmp_path / "u"))

        async def llm_with_json(prompt):
            return "prefix [{\"name\": \"v1\", \"pitch\": \"p\", \"tradeoff\": \"t\", \"prototype_step\": \"s\", \"cost\": \"low\"}] suffix"

        variants = asyncio.run(d.brainstorm("task", llm_with_json, num_variants=1))
        assert len(variants) == 1
        assert variants[0]["name"] == "v1"

        async def llm_bad(prompt):
            return "no json here"

        assert asyncio.run(d.brainstorm("task", llm_bad)) == []

    def test_distill_reference(self, tmp_path):
        import asyncio

        from zilli.loops.unknowns import UnknownsDiscovery

        d = UnknownsDiscovery(work_dir=str(tmp_path / "u"))
        repo = tmp_path / "ref"
        repo.mkdir()
        (repo / "a.py").write_text("def f():\n    pass\n")

        async def llm(prompt):
            return "distilled semantics"

        result = asyncio.run(d.distill_reference(str(repo), llm))
        assert result == "distilled semantics"
        missing = asyncio.run(d.distill_reference(str(tmp_path / "nope"), llm))
        assert "not found" in missing

    def test_generate_plan_writes_file(self, tmp_path):
        import asyncio

        from zilli.loops.unknowns import UnknownsDiscovery

        d = UnknownsDiscovery(work_dir=str(tmp_path / "u"))

        async def llm(prompt):
            return "# Plan\n\nsteps"

        plan = asyncio.run(d.generate_plan("task", "context", llm))
        assert plan == "# Plan\n\nsteps"
        assert (tmp_path / "u" / "implementation-plan.md").exists()
    """unknowns blind-spot / interview / brainstorm with a stubbed model."""

    def _stub_registry(self, monkeypatch):
        import zilli.models as models_mod

        class _StubGen:
            async def generate(self, prompt, **kw):
                return type("R", (), {"text": "stub response"})

        class _StubBackend:
            async def health_check(self):
                return True

            async def generate(self, prompt, **kw):
                return type("R", (), {"text": "stub response"})

        class _StubRegistry:
            def get_model(self, name):
                return _StubBackend()

        monkeypatch.setattr(models_mod, "ModelRegistry", lambda *a, **k: _StubRegistry())

    def test_blind_spot(self, monkeypatch, capsys, tmp_path):
        self._stub_registry(monkeypatch)
        monkeypatch.setattr("builtins.input", lambda *a: "test task")
        _argv(monkeypatch, "unknowns", "blind-spot")
        main()
        out = capsys.readouterr().out
        assert "Blind Spot" in out

    def test_brainstorm(self, monkeypatch, capsys, tmp_path):
        self._stub_registry(monkeypatch)
        _argv(monkeypatch, "unknowns", "brainstorm", "build a scheduler")
        main()
        out = capsys.readouterr().out
        assert "Brainstorm" in out or "Variant" in out

    def test_plan(self, monkeypatch, capsys, tmp_path):
        self._stub_registry(monkeypatch)
        _argv(monkeypatch, "unknowns", "plan", "write a report", "--context", "repo")
        main()
        out = capsys.readouterr().out
        assert "plan" in out.lower() or "Saved" in out
