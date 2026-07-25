import asyncio
import json

from zilli.dag.engine import DAGNode, TaskDAG, TaskType
from zilli.workflow.celery_executor import CeleryDAGExecutor, DAGRunRecord


def _make_dag() -> TaskDAG:
    dag = TaskDAG()
    dag.add_node(DAGNode(task_id="a", description="task A", task_type=TaskType.CODEGEN))
    dag.add_node(DAGNode(task_id="b", description="task B", task_type=TaskType.TEST))
    return dag


class TestCeleryDAGExecutorFallback:
    def test_fallback_when_celery_unavailable(self):
        ex = CeleryDAGExecutor()
        ex._celery_available = False
        dag = _make_dag()

        async def task_fn(node):
            return f"done:{node.task_id}"

        results = asyncio.run(ex.execute(dag, task_fn))
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_celery_path_records_run(self):
        ex = CeleryDAGExecutor()
        ex._celery_available = True
        dag = _make_dag()

        async def fake_submit(node, task_fn):
            return {"node": node.task_id, "ok": True}

        ex._submit_celery_task = fake_submit

        async def task_fn(node):
            return None

        results = asyncio.run(ex.execute(dag, task_fn, run_id="run_1"))
        record = ex.get_run("run_1")
        assert record is not None
        assert record.status == "completed"
        assert json.loads(record.dag_json)["nodes"]
        assert len(results) == 2

    def test_run_id_auto_generated(self):
        ex = CeleryDAGExecutor()
        ex._celery_available = True
        dag = _make_dag()

        async def fake_submit(node, task_fn):
            return node.task_id

        ex._submit_celery_task = fake_submit

        asyncio.run(ex.execute(dag, None))
        runs = ex.list_runs()
        assert len(runs) == 1
        assert runs[0].run_id.startswith("dag_")

    def test_list_runs_limit(self):
        ex = CeleryDAGExecutor()
        for i in range(15):
            ex._records[f"r{i}"] = DAGRunRecord(
                run_id=f"r{i}", dag_json="{}", created_at=float(i))
        runs = ex.list_runs(limit=5)
        assert len(runs) == 5
        assert runs[0].run_id == "r14"

    def test_get_run_missing(self):
        ex = CeleryDAGExecutor()
        assert ex.get_run("nope") is None


class TestIterateReady:
    def test_yields_only_when_parents_completed(self):
        from zilli.dag.engine import DAGEdge, NodeStatus
        dag = TaskDAG()
        dag.add_node(DAGNode(task_id="a", description="A"))
        dag.add_node(DAGNode(task_id="b", description="B"))
        dag.add_edge(DAGEdge(source="a", target="b"))

        ex = CeleryDAGExecutor()
        ex._celery_available = True

        yielded = [n.task_id for n in ex._iterate_ready(dag)]
        assert yielded == ["a"]

        dag.nodes["a"].status = NodeStatus.COMPLETED
        yielded = [n.task_id for n in ex._iterate_ready(dag)]
        assert yielded == ["b"]

    def test_empty_dag(self):
        ex = CeleryDAGExecutor()
        ex._celery_available = True
        assert list(ex._iterate_ready(TaskDAG())) == []


class TestDAGRunRecord:
    def test_defaults(self):
        r = DAGRunRecord(run_id="x", dag_json="{}")
        assert r.status == "pending"
        assert r.results == []
        assert r.created_at == 0.0
