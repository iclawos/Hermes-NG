"""L6 群智能 — swarm 包测试。"""

import asyncio
import time

import pytest

from zilli.swarm.artifacts import Artifact, ArtifactGraph, SubTask
from zilli.swarm.consensus import (
    ConsensusEngine,
    ConsensusLevel,
    ConsensusRecord,
)
from zilli.swarm.decomposer import DecomposeError, TaskDecomposer
from zilli.swarm.orchestrator import SwarmOrchestrator, SwarmResult
from zilli.swarm.roles import (
    AgentRoleSpec,
    get_role,
    list_roles,
    register_role,
    reset_role_registry,
)
from zilli.swarm.router import AgentRouter, RouteAssignment

# ── roles ────────────────────────────────────────────────────────────

def test_builtin_roles_registered():
    roles = list_roles()
    assert "researcher" in roles
    assert "writer" in roles
    assert "verifier" in roles
    assert "architect" in roles
    assert "reviewer" in roles


def test_get_role_returns_spec():
    spec = get_role("writer")
    assert spec is not None
    assert spec.max_context == 8000
    assert "file_write" in spec.tools


def test_get_role_unknown_returns_none():
    assert get_role("nonexistent") is None


def test_register_role_duplicate_is_idempotent():
    register_role(AgentRoleSpec(role="executor"))
    assert get_role("executor") is not None


def test_register_role_empty_name_rejected():
    with pytest.raises(ValueError):
        register_role(AgentRoleSpec(role=""))


def test_reset_role_registry_restores_builtins():
    reset_role_registry()
    assert "researcher" in list_roles()
    assert len(list_roles()) == 6


# ── artifacts ────────────────────────────────────────────────────────

class FakeSchema:
    def __init__(self, **kwargs):
        self._data = kwargs


def test_artifact_graph_put_get():
    g = ArtifactGraph()
    art = Artifact(
        id="a1",
        producer_role="writer",
        schema=FakeSchema,
        payload={"text": "hello"},
        consumer_roles=["verifier"],
    )
    g.put(art)
    assert g.get("a1") is not None
    assert len(g) == 1


def test_artifact_graph_missing_get_returns_none():
    g = ArtifactGraph()
    assert g.get("nope") is None


def test_artifact_consume_marks_consumed():
    g = ArtifactGraph()
    art = Artifact(id="a1", producer_role="writer", schema=FakeSchema, payload={})
    g.put(art)
    g.consume("a1", "verifier")
    assert g.get("a1").status == "consumed"
    assert g.consumers_of("a1") == ["verifier"]


def test_artifact_reject_sets_status():
    g = ArtifactGraph()
    art = Artifact(id="a1", producer_role="writer", schema=FakeSchema, payload={})
    g.put(art)
    g.reject("a1", "bad schema")
    assert g.get("a1").status == "rejected"


def test_artifact_validate_payload_ok():
    art = Artifact(id="a1", producer_role="w", schema=dict, payload={"k": 1})
    assert art.validate_payload() is True


def test_artifact_graph_gc_stale_consumed():
    g = ArtifactGraph()
    art = Artifact(id="a1", producer_role="w", schema=FakeSchema, payload={})
    art.created_at = time.time() - 9999
    g.put(art)
    g.consume("a1", "verifier")
    assert g.gc_unconsumed(max_age_sec=100) == 1
    assert g.get("a1") is None


def test_subtask_dependencies():
    st = SubTask(id="s1", description="x", role="writer", dependencies=["dep"])
    g = ArtifactGraph()
    assert g.pending_dependencies(st) == ["dep"]
    assert g.is_runnable(st) is False


def test_ready_subtasks_filters():
    g = ArtifactGraph()
    a = SubTask(id="a", description="x", role="researcher")
    b = SubTask(id="b", description="y", role="writer", dependencies=["a"])
    art = Artifact(id="a", producer_role="researcher", schema=FakeSchema, payload={})
    art.status = "done"
    g.put(art)
    assert {s.id for s in g.ready_subtasks([a, b])} == {"a", "b"}


# ── decomposer ───────────────────────────────────────────────────────

def test_decompose_below_threshold_single_task():
    d = TaskDecomposer()
    result = asyncio.run(d.decompose("simple", difficulty=0.5))
    assert len(result.subtasks) == 1
    assert result.subtasks[0].role == "executor"


def test_decompose_rule_based_three_stage():
    d = TaskDecomposer()
    result = asyncio.run(d.decompose("complex", difficulty=0.9))
    roles = [s.role for s in result.subtasks]
    assert roles == ["researcher", "writer", "verifier"]


def test_decompose_custom_fn_used():
    async def custom(task, family, difficulty):
        return [SubTask(id="c1", description=task, role="architect")]

    d = TaskDecomposer(decompose_fn=custom)
    result = asyncio.run(d.decompose("x", difficulty=0.9))
    assert result.subtasks[0].role == "architect"


def test_decompose_unknown_role_rejected():
    async def bad(task, family, difficulty):
        return [SubTask(id="x", description="x", role="alien")]

    d = TaskDecomposer(decompose_fn=bad)
    with pytest.raises(DecomposeError):
        asyncio.run(d.decompose("x", difficulty=0.9))


def test_decompose_cycle_rejected():
    async def cyclic(task, family, difficulty):
        return [
            SubTask(id="x", description="x", role="writer", dependencies=["y"]),
            SubTask(id="y", description="y", role="writer", dependencies=["x"]),
        ]

    d = TaskDecomposer(decompose_fn=cyclic)
    with pytest.raises(DecomposeError):
        asyncio.run(d.decompose("x", difficulty=0.9))


def test_decompose_fanout_limit_rejected():
    async def too_many(task, family, difficulty):
        return [
            SubTask(id=f"t{i}", description="x", role="writer")
            for i in range(9)
        ]

    d = TaskDecomposer(decompose_fn=too_many)
    with pytest.raises(DecomposeError):
        asyncio.run(d.decompose("x", difficulty=0.9))


def test_decompose_empty_rejected():
    async def empty(task, family, difficulty):
        return []

    d = TaskDecomposer(decompose_fn=empty)
    with pytest.raises(DecomposeError):
        asyncio.run(d.decompose("x", difficulty=0.9))


# ── consensus ────────────────────────────────────────────────────────

def test_consensus_majority():
    eng = ConsensusEngine()
    rec = eng.reach("which model", ["a", "b", "c"], ConsensusLevel.MAJORITY)
    assert isinstance(rec, ConsensusRecord)
    assert rec.resolution in ("a", "b", "c")


def test_consensus_weighted_uses_vote_fn():
    def votes(topic, options, level):
        return [("b", 3.0, "agent1"), ("a", 1.0, "agent2")]

    eng = ConsensusEngine(vote_fn=votes)
    rec = eng.reach("topic", ["a", "b"], ConsensusLevel.WEIGHTED)
    assert rec.resolution == "b"
    assert rec.votes["b"] == 3.0


def test_consensus_arbiter_decides():
    def arbiter(topic, options, candidates):
        return options[0]

    eng = ConsensusEngine(arbiter_fn=arbiter)
    rec = eng.reach("topic", ["x", "y"], ConsensusLevel.ARBITER)
    assert rec.resolution == "x"
    assert rec.level == ConsensusLevel.ARBITER


def test_consensus_no_options_rejected():
    eng = ConsensusEngine()
    with pytest.raises(ValueError):
        eng.reach("topic", [])


def test_consensus_arbiter_without_fn_falls_back():
    eng = ConsensusEngine()
    rec = eng.reach("topic", ["x", "y"], ConsensusLevel.ARBITER)
    assert rec.resolution in ("x", "y")


def test_consensus_human_escalation_flag():
    eng = ConsensusEngine()
    rec = eng.reach("topic", ["x", "y"], ConsensusLevel.HUMAN)
    assert rec.resolution in ("x", "y")


# ── router ───────────────────────────────────────────────────────────

def test_router_assign_known_role():
    r = AgentRouter()
    st = SubTask(id="s1", description="research", role="researcher")
    assignment = r.assign(st)
    assert isinstance(assignment, RouteAssignment)
    assert assignment.role == "researcher"
    assert assignment.model_id != ""


def test_router_assign_unknown_role_falls_back_to_executor():
    r = AgentRouter()
    st = SubTask(id="s1", description="x", role="alien")
    assignment = r.assign(st)
    assert assignment.role == "executor"


def test_router_assign_fallback_role_used():
    r = AgentRouter()
    # architect 有 fallback_role="researcher"；不注入 profile 时用空 profile
    st = SubTask(id="s1", description="x", role="architect")
    assignment = r.assign(st)
    assert assignment.role in ("architect", "researcher")


# ── orchestrator ─────────────────────────────────────────────────────

def test_orchestrator_single_subtask():
    async def run():
        d = TaskDecomposer()
        r = AgentRouter()
        c = ConsensusEngine()
        o = SwarmOrchestrator(d, r, c)
        return await o.execute("simple task", industry="tech")

    result = asyncio.run(run())
    assert isinstance(result, SwarmResult)
    assert result.success is True
    assert result.final_text != ""


def test_orchestrator_dag_three_roles():
    async def run():
        d = TaskDecomposer()
        r = AgentRouter()
        c = ConsensusEngine()
        o = SwarmOrchestrator(d, r, c)
        return await o.execute("complex task", industry="tech")

    result = asyncio.run(run())
    assert result.success is True
    assert len(result.subtasks) == 3
    assert "researcher" in [s.role for s in result.subtasks]


def test_orchestrator_custom_executor():
    def executor(st, graph):
        return {"text": f"done-{st.role}", "role": st.role}

    async def run():
        d = TaskDecomposer()
        r = AgentRouter()
        c = ConsensusEngine()
        o = SwarmOrchestrator(d, r, c, executor_fn=executor)
        return await o.execute("complex", industry="")

    result = asyncio.run(run())
    assert result.success is True
    assert result.final_text.startswith("done-")


def test_orchestrator_executor_raises_marks_rejected():
    def executor(st, graph):
        raise RuntimeError("boom")

    async def run():
        d = TaskDecomposer()
        r = AgentRouter()
        c = ConsensusEngine()
        o = SwarmOrchestrator(d, r, c, executor_fn=executor)
        return await o.execute("complex", industry="")

    result = asyncio.run(run())
    assert result.success is False
    assert "boom" in result.error


def test_orchestrator_verify_fn_gates_success():
    def executor(st, graph):
        return {"text": "bad", "role": st.role}

    async def run():
        d = TaskDecomposer()
        r = AgentRouter()
        c = ConsensusEngine()
        o = SwarmOrchestrator(d, r, c, executor_fn=executor, verify_fn=lambda t: False)
        return await o.execute("simple", industry="")

    result = asyncio.run(run())
    assert result.success is False
    assert result.error == "verification failed"


def test_orchestrator_decompose_failure_returns_error():
    async def bad_decompose(task, family, difficulty):
        raise ValueError("decompose exploded")

    async def run():
        d = TaskDecomposer(decompose_fn=bad_decompose)
        r = AgentRouter()
        c = ConsensusEngine()
        o = SwarmOrchestrator(d, r, c)
        return await o.execute("complex", industry="")

    result = asyncio.run(run())
    assert result.success is False
    assert "decompose failed" in result.error


def test_orchestrator_parallel_execution_max_concurrency():
    running = []
    max_running = []

    def executor(st, graph):
        running.append(st.id)
        max_running.append(len(running))
        time.sleep(0.01)
        running.remove(st.id)
        return {"text": "ok", "role": st.role}

    async def run():
        d = TaskDecomposer()
        r = AgentRouter()
        c = ConsensusEngine()
        o = SwarmOrchestrator(d, r, c, executor_fn=executor, max_concurrency=2)
        return await o.execute("complex", industry="")

    result = asyncio.run(run())
    assert result.success is True
    assert max(max_running) <= 2


def test_orchestrator_dag_deadlock_detected():
    async def bad(task, family, difficulty):
        return [
            SubTask(id="a", description="a", role="writer", dependencies=["b"]),
            SubTask(id="b", description="b", role="writer", dependencies=["a"]),
        ]

    async def run():
        d = TaskDecomposer(decompose_fn=bad)
        r = AgentRouter()
        c = ConsensusEngine()
        o = SwarmOrchestrator(d, r, c)
        return await o.execute("complex", industry="")

    # 环在 decompose 阶段即被拒绝
    result = asyncio.run(run())
    assert result.success is False


# ── CLI ──────────────────────────────────────────────────────────────

def test_cli_swarm_roles(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["zilli", "swarm", "--roles"])
    from zilli.cli import main
    main()
    out = capsys.readouterr().out
    assert "researcher" in out
    assert "verifier" in out


def test_cli_swarm_execute(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["zilli", "swarm", "重构 auth 模块"])
    from zilli.cli import main
    main()
    out = capsys.readouterr().out
    assert "成功: ✅" in out
    assert "researcher" in out
