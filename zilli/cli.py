from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import yaml

from zilli.data import TrajectoryStore
from zilli.envs import HermesSandbox
from zilli.rewards import VerifiableReward
from zilli.tasks import TaskRunner, load_tasks
from zilli.training.rl_trainer import RLTrainer
from zilli.version import version

if TYPE_CHECKING:
    from zilli.configs import ZilliConfig


def main():
    parser = argparse.ArgumentParser(description="Zilli: 面向AI自主开发的Agent工具")
    parser.add_argument("--version", action="version", version=f"zilli v{version}")
    parser.add_argument("--zilli-config", type=str, default=None,
                        help="Zilli 主配置文件路径 (默认: zilli.yaml, ~/.zilli.yaml, configs/model_config.yaml)")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list-tasks", help="列出所有可用任务")
    sub.add_parser("list-basic", help="列出基础验证任务")
    sub.add_parser("list-benchmark", help="列出基准评估任务")
    sub.add_parser("sandbox-test", help="测试沙箱环境")

    run_parser = sub.add_parser("run", help="运行一个自然语言任务")
    run_parser.add_argument("prompt", type=str, help="任务描述")
    run_parser.add_argument("--iterations", type=int, default=3, help="最大重试次数")

    models_parser = sub.add_parser("models", help="本地模型管理")
    models_sub = models_parser.add_subparsers(dest="models_command")
    models_sub.add_parser("list", help="列出已注册模型")
    models_sub.add_parser("health", help="检查各模型健康状态")
    models_gen = models_sub.add_parser("generate", help="使用指定角色生成")
    models_gen.add_argument("role", type=str, choices=["planner", "executor", "reviewer"])
    models_gen.add_argument("prompt", type=str)

    route_parser = sub.add_parser("route", help="混合路由：规划→执行→审查")
    route_parser.add_argument("request", type=str, help="用户请求")
    route_parser.add_argument("--industry", type=str, default="",
                              choices=["", "legal", "medical", "financial", "education"],
                              help="行业上下文")
    route_parser.add_argument("--full-route", action="store_true", help="强制完整三阶段路由")
    route_parser.add_argument("--verbose", action="store_true", help="显示中间结果")

    industry_parser = sub.add_parser("industry", help="行业工作流")
    industry_sub = industry_parser.add_subparsers(dest="industry_command")
    industry_sub.add_parser("list", help="列出支持的行业")
    industry_run = industry_sub.add_parser("run", help="运行行业工作流")
    industry_run.add_argument("industry", type=str,
                              choices=["legal", "medical", "financial", "education"])
    industry_run.add_argument("request", type=str, help="用户请求")
    industry_run.add_argument("--tenant", type=str, default="default", help="租户ID")
    industry_run.add_argument("--full-route", action="store_true", help="强制完整三阶段路由")
    industry_run.add_argument("--no-sanitize", action="store_true", help="禁用PII脱敏")

    eval_parser = sub.add_parser("evaluate", help="在沙箱中评估任务")
    eval_parser.add_argument("task_id", type=str, nargs="?", help="任务ID")
    eval_parser.add_argument("--cost-aware", action="store_true", help="启用成本控制调度")
    eval_parser.add_argument("--budget", type=float, default=None, help="月度预算上限（美元）")

    train_parser = sub.add_parser("train", help="运行训练循环")
    train_parser.add_argument("--config", type=str, default=None, help="训练配置路径")
    train_parser.add_argument("--cost-aware", action="store_true", help="启用成本控制调度")
    train_parser.add_argument("--budget", type=float, default=None, help="月度预算上限（美元）")
    train_parser.add_argument("--dry-run", action="store_true", help="模拟运行，不执行实际训练")
    train_parser.add_argument("--resume", type=str, default="", help="从检查点恢复训练（检查点路径）")

    distill_parser = sub.add_parser("distill", help="运行蒸馏循环")
    distill_parser.add_argument("--config", type=str, default=None, help="蒸馏配置YAML路径")
    distill_parser.add_argument("--samples", type=int, default=100, help="蒸馏样本数")
    distill_parser.add_argument("--checkpoint", type=str, default=None, help="检查点路径（存/加载）")
    distill_parser.add_argument("--ab-test", type=str, default=None, help="AB实验配置YAML路径")
    distill_parser.add_argument("--log-dir", type=str, default="", help="日志目录")
    distill_parser.add_argument("--device", type=str, default="auto", help="推理设备 (cpu/cuda/auto)")

    cost_parser = sub.add_parser("cost", help="预算控制")
    cost_sub = cost_parser.add_subparsers(dest="cost_command")
    cost_sub.add_parser("status", help="显示预算状态")
    cost_sub.add_parser("reset-month", help="重置月度预算")

    swe_parser = sub.add_parser("swe", help="SWE-bench 风格 Bug 修复循环")
    swe_parser.add_argument("--repo", type=str, default=".", help="目标仓库路径")
    swe_parser.add_argument("--issue", type=str, required=True, help="Bug 描述或 issue 文件路径")
    swe_parser.add_argument("--model", type=str, default="", help="诊断用模型名称")
    swe_parser.add_argument("--test-cmd", type=str, default="python -m pytest tests/ -x -q",
                            help="测试命令")
    swe_parser.add_argument("--iterations", type=int, default=3, help="最大迭代次数")
    swe_parser.add_argument("--sandbox", action="store_true", help="使用 Docker 沙箱隔离")
    swe_parser.add_argument("--verbose", action="store_true", help="显示详细信息")

    serve_parser = sub.add_parser("serve", help="启动 API 服务器")
    serve_parser.add_argument("--host", type=str, default="127.0.0.1", help="监听地址")
    serve_parser.add_argument("--port", type=int, default=8900, help="监听端口")

    pipeline_parser = sub.add_parser("pipeline", help="端到端进化训练管线")
    pipeline_parser.add_argument("--skills-dir", type=str, default="",
                                 help="待进化技能目录")
    pipeline_parser.add_argument("--trajectories-dir", type=str, default="",
                                 help="轨迹数据目录")
    pipeline_parser.add_argument("--epochs", type=int, default=5,
                                 help="训练轮数")
    pipeline_parser.add_argument("--cycles", type=int, default=3,
                                 help="管线循环次数")
    pipeline_parser.add_argument("--log-dir", type=str, default="./experiments",
                                 help="日志目录")

    ppm_parser = sub.add_parser("ppm", help="PPM 预测路由管理")
    ppm_sub = ppm_parser.add_subparsers(dest="ppm_command")
    ppm_sub.add_parser("stats", help="显示 PPM 统计信息")
    ppm_train = ppm_sub.add_parser("train-model", help="训练 sklearn/ONNX 分类模型")
    ppm_train.add_argument("--records", type=str, required=True,
                           help="训练记录 JSON 文件路径")
    ppm_train.add_argument("--output", type=str, default="ppm_model.onnx",
                           help="模型输出路径")
    ppm_train.add_argument("--classifier", type=str, default="sklearn",
                           choices=["sklearn"], help="分类器类型")

    audit_parser = sub.add_parser("audit", help="审计与合规")
    audit_sub = audit_parser.add_subparsers(dest="audit_command")
    audit_export = audit_sub.add_parser("export", help="导出合规报告")
    audit_export.add_argument("--framework", type=str, required=True,
                              choices=["gdpr", "hipaa", "soc2", "pci_dss", "ferpa", "ccpa"],
                              help="合规框架")
    audit_export.add_argument("--tenant", type=str, default="default", help="租户ID")
    audit_export.add_argument("--start", type=str, required=True, help="开始日期 (YYYY-MM-DD)")
    audit_export.add_argument("--end", type=str, required=True, help="结束日期 (YYYY-MM-DD)")
    audit_export.add_argument("--output", type=str, required=True, help="输出文件路径")
    audit_export.add_argument("--audit-dir", type=str, default="./audit_logs",
                              help="审计日志目录")

    unknowns_parser = sub.add_parser("unknowns", help="发现未知项 (Fable 5)")
    unknowns_sub = unknowns_parser.add_subparsers(dest="unknowns_command")
    unknowns_sub.add_parser("blind-spot", help="执行盲点扫描")
    unknowns_sub.add_parser("interview", help="生成面试问题")
    unknowns_sub.add_parser("summary", help="显示未知项摘要")
    unknowns_resolve = unknowns_sub.add_parser("resolve", help="标记未知项为已解决")
    unknowns_resolve.add_argument("id", type=str, help="未知项ID")
    unknowns_resolve.add_argument("resolution", type=str, help="解决方案描述")
    unknowns_brainstorm = unknowns_sub.add_parser("brainstorm", help="生成差异化解法草案")
    unknowns_brainstorm.add_argument("task", type=str, help="任务描述")
    unknowns_brainstorm.add_argument("--variants", type=int, default=4, help="草案数量")
    unknowns_reference = unknowns_sub.add_parser("reference", help="提炼参考实现语义")
    unknowns_reference.add_argument("path", type=str, help="参考文件/目录路径")
    unknowns_reference.add_argument("--goal", type=str, default="", help="提炼目标")
    unknowns_plan = unknowns_sub.add_parser("plan", help="生成实施计划")
    unknowns_plan.add_argument("task", type=str, help="任务描述")
    unknowns_plan.add_argument("--context", type=str, default="", help="上下文/代码摘要")
    unknowns_pitch = unknowns_sub.add_parser("pitch", help="打包评审文档")
    unknowns_pitch.add_argument("title", type=str, help="文档标题")

    args = parser.parse_args()

    from zilli.configs import load_config
    zilli_config = load_config(Path(args.zilli_config)) if args.zilli_config else None

    if args.command == "models":
        _run_models(args.models_command, args, zilli_config)
    elif args.command == "route":
        _run_route(args, zilli_config)
    elif args.command == "industry":
        _run_industry(args, zilli_config)
    elif args.command == "cost":
        _run_cost(args.cost_command, zilli_config)
    elif args.command == "list-tasks":
        tasks = load_tasks()
        for t in tasks:
            print(f"  [{t.get('category','?')}] {t['id']}: {t['name']}")

    elif args.command == "list-basic":
        _list_category("basic")

    elif args.command == "list-benchmark":
        _list_category("benchmark")

    elif args.command == "sandbox-test":
        _run_sandbox_test()

    elif args.command == "run":
        import asyncio

        from zilli.core.agent import Agent
        from zilli.models.registry import ModelRegistry

        async def _run():
            registry = ModelRegistry(config=zilli_config) if zilli_config else None
            agent = await Agent.from_registry(registry)
            result = await agent.run(args.prompt)
            sep = "=" * 50
            print(sep)
            print(f"  Task: {args.prompt}")
            print(f"  Result: {'✅ PASS' if result.success else '❌ FAIL'}")
            print(f"  Iterations: {result.iterations}")
            print(f"  Duration: {result.duration_ms:.0f}ms")
            print(sep)
            if result.output:
                print(result.output)
            if result.error:
                print(f"Error: {result.error}")
            print()
            print(f"--- {result.duration_ms:.0f}ms ---")

        asyncio.run(_run())

    elif args.command == "evaluate":
        _run_evaluation(task_id=args.task_id, cost_aware=args.cost_aware, budget=args.budget, zilli_config=zilli_config)

    elif args.command == "train":
        _run_train(args.config, cost_aware=args.cost_aware, budget=args.budget,
                    zilli_config=zilli_config, resume=args.resume)

    elif args.command == "distill":
        _run_distill(
            config_path=args.config,
            num_samples=args.samples,
            checkpoint_path=args.checkpoint,
            ab_test_path=args.ab_test,
            log_dir=args.log_dir or "",
        )

    elif args.command == "swe":
        _run_swe(args)

    elif args.command == "serve":
        from zilli.server.app import run_server
        run_server(
            host=args.host,
            port=args.port,
            config=zilli_config,
            config_path=Path(args.zilli_config) if args.zilli_config else None,
        )

    elif args.command == "pipeline":
        _run_pipeline(args)
    elif args.command == "ppm":
        _run_ppm(args)
    elif args.command == "audit":
        _run_audit(args)
    elif args.command == "unknowns":
        _run_unknowns(args)

    else:
        parser.print_help()


def _run_models(cmd: str | None = None, args: argparse.Namespace | None = None,
                zilli_config: Optional["ZilliConfig"] = None):
    from zilli.models import ModelRegistry, ModelRole

    registry = ModelRegistry(config=zilli_config) if zilli_config else ModelRegistry()

    if cmd == "list":
        models = registry.list_models()
        if not models:
            print("No models registered.")
            return
        sep = "=" * 60
        print(sep)
        print(f"  {'Name':12s} {'Role':12s} {'Backend':10s} {'Model ID':20s} {'Alive':6s}")
        print(sep)
        for m in models:
            alive = "[OK]" if m["alive"] else "[FAIL]"
            print(f"  {m['name']:12s} {m['role']:12s} {m['backend']:10s} {m['model_id']:20s} {alive:6s}")
        print(sep)

    elif cmd == "health":
        import asyncio

        async def _health():
            print("Checking model health...")
            for cfg in registry.profile.models:
                backend = registry.get_model(cfg.name)
                if backend is None:
                    print(f"  {cfg.name:12s} ✘ backend not loaded")
                    continue
                ok = await backend.health_check()
                status = "[healthy]" if ok else "[unreachable]"
                print(f"  {cfg.name:12s} {status}  ({cfg.model_id} @ {cfg.base_url})")

        asyncio.run(_health())

    elif cmd == "generate":
        role_str = args.role if args else "planner"
        prompt = args.prompt if args else ""
        role = ModelRole(role_str)

        import asyncio

        async def _gen():
            result = await registry.generate(role, prompt)
            if result.error:
                print(f"Error: {result.error}")
            else:
                print(f"[{role_str.upper()}] {result.text}")
                print(f"\n--- stats: {result.tokens_in} in, {result.tokens_out} out, "
                      f"{result.duration_ms:.0f}ms ---")

        asyncio.run(_gen())
    else:
        print("Usage: zilli models {list|health|generate <role> <prompt>}")


def _run_route(args: argparse.Namespace,
               zilli_config: Optional["ZilliConfig"] = None):
    import asyncio

    from zilli.models import ModelRegistry
    from zilli.routing import LocalHybridRouter, RouteClassifier

    async def route():
        registry = ModelRegistry(config=zilli_config)
        classifier = RouteClassifier(model_registry=registry, config=zilli_config)
        router = LocalHybridRouter(registry, classifier, config=zilli_config)

        result = await router.run(
            request=args.request,
            industry=args.industry,
            force_full_route=args.full_route,
        )

        sep = "=" * 60
        print(sep)
        print(f"  Route: {result.route_type.value}")
        print(f"  Decision: {result.decision.reason}")
        if result.error:
            print(f"  Error: {result.error}")
        print(sep)
        print()

        if args.verbose and result.planner_result:
            print("[PLANNER OUTPUT]")
            print(result.planner_result[:500])
            print()

        if args.verbose and result.executor_result:
            print("[EXECUTOR OUTPUT]")
            print(result.executor_result[:500])
            print()

        print("[FINAL OUTPUT]")
        text = result.final_text or ""
        if len(text) > 2000:
            print(text[:2000])
            print("... [truncated to 2000 chars]")
        else:
            print(text)

        print()
        print(f"--- {result.total_duration_ms:.0f}ms ---")

    asyncio.run(route())


def _run_industry(args: argparse.Namespace,
                  zilli_config: Optional["ZilliConfig"] = None):
    import asyncio

    from zilli.audit import AuditLogger
    from zilli.industry import IndustryType, WorkflowRegistry
    from zilli.models import ModelRegistry

    if args.industry_command == "list":
        registry = WorkflowRegistry(config=zilli_config)
        industries = registry.list_industries()
        if not industries:
            print("No industries registered.")
            return
        sep = "=" * 60
        print(sep)
        print(f"  {'Industry':12s} {'Access':14s} {'Audit':6s} {'Retention':10s}")
        print(sep)
        for ind in industries:
            audit = "[OK]" if ind["require_audit"] else "[NO]"
            print(f"  {ind['id']:12s} {ind['access_level']:14s} {audit:6s} {ind.get('retention_days', 90):10d}")
        print(sep)
        for ind in industries:
            print(f"\n  {ind['id'].upper()} compliance rules:")
            for rule in ind["compliance_rules"]:
                print(f"    • {rule}")
        return

    if args.industry_command == "run":
        async def _run():
            industry = IndustryType(args.industry)
            model_registry = ModelRegistry(config=zilli_config)
            audit_logger = AuditLogger(config=zilli_config)
            registry = WorkflowRegistry(
                model_registry=model_registry,
                audit_logger=audit_logger,
                config=zilli_config,
            )

            result = await registry.run(
                request=args.request,
                industry=industry,
                tenant_id=args.tenant,
                force_full_route=args.full_route,
                sanitize=not args.no_sanitize,
            )

            sep = "=" * 60
            print(sep)
            print(f"  Industry: {args.industry}")
            print(f"  Tenant:   {args.tenant}")
            print(f"  Route:    {result.route_type.value}")
            print(f"  Decision: {result.decision.reason}")
            if result.error:
                print(f"  Error:    {result.error}")
            print(sep)
            print()
            print("[OUTPUT]")
            text = result.final_text or ""
            if len(text) > 2000:
                print(text[:2000])
                print("... [truncated to 2000 chars]")
            else:
                print(text)
            print()
            print(f"--- {result.total_duration_ms:.0f}ms ---")

        asyncio.run(_run())


def _run_cost(cmd: str | None = None,
              zilli_config: Optional["ZilliConfig"] = None):
    from zilli.envs.cost_controller import CostController

    cc = CostController(config=zilli_config) if zilli_config else CostController()
    if cmd == "status":
        snap = cc.snapshot()
        sep = "=" * 40
        print(sep)
        print("  Budget Status")
        print(sep)
        print(f"  Remaining:    ${snap.remaining_budget:.2f}")
        print(f"  Total calls:  {snap.total_calls}")
        print(f"  Hourly calls: {snap.calls_this_hour} / {snap.hourly_quota:.0f}")
        emergency = "YES" if snap.emergency_mode else "no"
        print(f"  Emergency:    {emergency}")
        print(f"  Updated:      {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(snap.timestamp))}")
        print(sep)
        stats = cc.scheduler.stats()
        if stats["task_types"]:
            print("\n  Per-task stats:")
            for ttype, tstats in stats["task_types"].items():
                print(f"    {ttype:20s}  fail_rate={tstats['failure_rate']:.2f}  "
                      f"gap={tstats['success_with_sota'] - tstats['success_without_sota']:.2f}")
    elif cmd == "reset-month":
        cc.reset_monthly()
        print("Monthly budget reset.")
    else:
        print("Usage: zilli cost {status|reset-month}")


def _list_category(cat: str):
    tasks = load_tasks(category=cat)
    for t in tasks:
        steps = t.get("max_steps", "?")
        print(f"  {t['id']}")
        print(f"    Steps: {steps}")
        print(f"    {t.get('description', '')[:100]}")
        print()


def _run_sandbox_test():
    import asyncio

    from zilli.schema.actions import FinishAction, MemoryReadAction, MemoryWriteAction

    async def test():
        sandbox = HermesSandbox()
        print("Sandbox created.")

        r1 = await sandbox.step(MemoryWriteAction(
            action_id="1", reasoning="Store name",
            key="name", value="Hermes"
        ))
        print(f"Write result: {r1}")

        r2 = await sandbox.step(MemoryReadAction(
            action_id="2", reasoning="Recall name",
            key="name"
        ))
        print(f"Read result: {r2}")

        r3 = await sandbox.step(FinishAction(
            action_id="3", reasoning="Done",
            summary="Test complete"
        ))
        print(f"Finish result: {r3}")

        print(f"\nTrajectory: {len(sandbox.get_trajectory())} steps")
        print("Sandbox test PASSED")

    asyncio.run(test())


def _run_evaluation(task_id: str | None = None, cost_aware: bool = False, budget: float | None = None,
                    zilli_config: Optional["ZilliConfig"] = None):
    import asyncio

    from zilli.envs import CostController, HermesSandbox
    from zilli.schema.actions import MemoryWriteAction

    tasks = load_tasks()
    if task_id:
        tasks = [t for t in tasks if t["id"] == task_id]
        if not tasks:
            print(f"Task not found: {task_id}")
            return

    cc = (CostController(monthly_budget=budget or 500.0, config=zilli_config)
          if cost_aware else None)
    if cc:
        print(f"Cost-aware mode: ${cc.scheduler.monthly_budget:.0f} monthly budget")

    async def evaluate():
        planner_calls = 0
        executor_calls = 0

        for task in tasks:
            sandbox = HermesSandbox(scenario=task.get("initial_context"))
            runner = TaskRunner(task)
            reward_fn = VerifiableReward()

            task_type = task.get("category", "general")
            print(f"Evaluating: {task['id']} ({task['name']}) type={task_type}")

            for step_num in range(task.get("max_steps", 10)):
                if runner.should_truncate():
                    print(f"  Truncated at step {step_num}")
                    break

                if cc:
                    state = {"max_prob": max(0.3, 1.0 - step_num * 0.05)}
                    use_planner = cc.should_use_planner(task_type, state)
                else:
                    use_planner = False

                if use_planner:
                    planner_calls += 1
                    action = MemoryWriteAction(
                        action_id=f"eval_{step_num}",
                        reasoning=f"Planner step {step_num}",
                        key=f"k_{step_num}", value=f"v_{step_num}",
                    )
                else:
                    executor_calls += 1
                    action = MemoryWriteAction(
                        action_id=f"eval_{step_num}",
                        reasoning=f"Step {step_num}",
                        key=f"k_{step_num}", value=f"v_{step_num}",
                    )

                result = await sandbox.step(action)
                success = result.get("observation", {}).get("success", False) and result.get("reward", -1) > 0
                runner.record_action(action.model_dump(), result.get("observation", {}))

                if cc:
                    if use_planner:
                        cc.record_planner_call(task_type, success)
                    else:
                        cc.record_executor_call(task_type, success)

            final_state = {
                "task_completed": sandbox.context.get("finished", False),
                "steps": runner.step_count,
                "truncated": runner.should_truncate(),
            }

            score = runner.evaluate(final_state)
            reward = reward_fn.compute_trajectory(runner.trajectory, final_state)
            print(f"  score={score:.2f} reward={reward:.2f} steps={runner.step_count}")

        if cc:
            snap = cc.snapshot()
            print("\n  Cost summary:")
            print(f"    Planner calls: {planner_calls}")
            print(f"    Executor calls: {executor_calls}")
            print(f"    Remaining budget: ${snap.remaining_budget:.2f}")
            print(f"    Emergency mode: {'YES' if snap.emergency_mode else 'no'}")

    asyncio.run(evaluate())


def _run_train(config_path: str | None = None, cost_aware: bool = False, budget: float | None = None,
               zilli_config: Optional["ZilliConfig"] = None, dry_run: bool = False,
               resume: str = ""):
    from zilli.training.config import TrainingConfig
    from zilli.training.data import make_dummy_failure, make_dummy_golden

    cfg_dict = {}
    if config_path:
        p = Path(config_path)
        if ".." in str(p):
            print("Path traversal detected in config path")
            return
        p = p.resolve()
        if p.exists():
            with open(p) as f:
                cfg_dict = yaml.safe_load(f).get("training", {})

    training_config = TrainingConfig.from_dict(cfg_dict)
    trainer = RLTrainer(training_config.to_training_kwargs())
    store = TrajectoryStore()

    cc = None
    if cost_aware:
        from zilli.envs import CostController
        cc = CostController(monthly_budget=budget or 500.0, config=zilli_config)
        print(f"Cost-aware training: ${cc.scheduler.monthly_budget:.0f} monthly budget")

    golden = make_dummy_golden()
    failure = make_dummy_failure()
    for g in golden:
        store.add_trajectory(g["trajectory"], g["reward"])
    for f in failure:
        store.add_trajectory(f["trajectory"], f["reward"])

    planner_calls = 0
    executor_calls = 0
    for epoch in range(3):
        if cc:
            state = {"max_prob": max(0.3, 0.9 - epoch * 0.2)}
            if cc.should_use_planner("training", state):
                planner_calls += 1
                print(f"  Epoch {epoch}: using Planner")
                cc.record_planner_call("training", True)
            else:
                executor_calls += 1
                print(f"  Epoch {epoch}: using Executor")
                cc.record_executor_call("training", True)

        batch = store.sample_batch(batch_size=4, golden_ratio=0.5)
        if batch:
            metrics = trainer.update(batch)
            print(f"Epoch {epoch}: loss={metrics['loss']:.4f} policy_loss={metrics['policy_loss']:.4f}")
        else:
            print(f"Epoch {epoch}: no data yet")

    if cc:
        snap = cc.snapshot()
        print("\n  Cost summary:")
        print(f"    Planner calls: {planner_calls}")
        print(f"    Executor calls: {executor_calls}")
        print(f"    Remaining budget: ${snap.remaining_budget:.2f}")

    print("Training simulation complete. Use --dry-run to acknowledge this is a dry run.")
    print("Training test complete.")


def _run_swe(args: argparse.Namespace):
    import asyncio

    from zilli.models import ModelRegistry
    from zilli.swe import SWEAgent, SWEConfig

    async def run():
        issue = args.issue
        issue_path = Path(issue)
        if issue_path.exists():
            issue = await asyncio.to_thread(lambda: issue_path.read_text(encoding="utf-8").strip())

        model_backend = None
        if args.model:
            registry = ModelRegistry()
            registry.profile.models = []  # skip config, use CLI-provided model
            model_backend = registry.get_model(args.model)

        cfg = SWEConfig(
            model_name=args.model,
            max_iterations=args.iterations,
            test_command=args.test_cmd,
            sandbox_enabled=args.sandbox,
            verbose=args.verbose,
        )

        agent = SWEAgent(cfg, model_backend=model_backend)
        result = await agent.run(issue, args.repo)

        print()
        sep = "=" * 60
        print(sep)
        print(f"  SWE Fix Result: {'✅ PASS' if result.success else '❌ FAIL'}")
        print(f"  Iterations: {result.iterations}")
        print(f"  Duration: {result.total_duration_ms:.0f}ms")
        if result.error:
            print(f"  Error: {result.error}")
        print(sep)
        print()

        if result.patch.files:
            print("[PATCH]")
            print(result.patch.to_diff()[:2000])
            print()

        if args.verbose and result.context:
            print("[CONTEXT]")
            print(result.context.summarize()[:1000])

    asyncio.run(run())


def _run_unknowns(args: argparse.Namespace):
    import asyncio

    from zilli.loops.unknowns import UnknownsDiscovery

    discovery = UnknownsDiscovery()

    if args.unknowns_command == "summary":
        s = discovery.summary()
        print("Unknowns Discovery Summary")
        print("=" * 40)
        print(f"  Total unknowns: {s['total_unknowns']}")
        print(f"  Resolved: {s['resolved']}")
        print(f"  Unresolved: {s['unresolved']}")
        print(f"  Implementation notes: {s['implementation_notes']}")
        print(f"  Deviations: {s['deviations']}")
        print()
        for cat, counts in s['by_category'].items():
            print(f"  {cat}: {counts['resolved']}/{counts['total']} resolved")

    elif args.unknowns_command == "resolve":
        success = discovery.resolve_unknown(args.id, args.resolution)
        if success:
            print(f"Unknown {args.id} marked as resolved.")
        else:
            print(f"Unknown {args.id} not found.")

    elif args.unknowns_command in ("blind-spot", "interview", "brainstorm", "reference", "plan"):
        async def run():
            from zilli.models import ModelRegistry

            registry = ModelRegistry()
            model = registry.get_model("planner")
            if model is None:
                print("Error: model 'planner' is not registered. Check your model configuration.")
                return

            async def llm_fn(prompt: str) -> str:
                result = await model.generate(prompt)
                return result.text

            if args.unknowns_command == "blind-spot":
                task = input("Describe your task: ")
                context = input("Paste relevant codebase context (or file paths): ")
                report = await discovery.blind_spot_pass(task, context, llm_fn)
                print("\nBlind Spot Report")
                print("=" * 50)
                print(f"Found {len(report.unknowns)} unknowns")
                for u in report.unknowns:
                    print(f"  [{u.impact}] {u.description}")
                print(f"\nCodebase gaps: {len(report.codebase_gaps)}")
                for g in report.codebase_gaps:
                    print(f"  - {g}")
                print(f"\nRisk areas: {len(report.risk_areas)}")
                for r in report.risk_areas:
                    print(f"  - {r}")
                print("\nSuggested prompts:")
                for p in report.suggested_prompts:
                    print(f"  - {p}")

            elif args.unknowns_command == "interview":
                unresolved = discovery.get_unresolved()
                if not unresolved:
                    print("No unresolved unknowns. Run 'blind-spot' first.")
                    return
                task = input("Describe your task: ")
                questions = await discovery.generate_interview_questions(task, unresolved, llm_fn)
                print("\nInterview Questions")
                print("=" * 50)
                for i, q in enumerate(questions, 1):
                    print(f"{i}. {q}")

            elif args.unknowns_command == "brainstorm":
                variants = await discovery.brainstorm(args.task, llm_fn, num_variants=args.variants)
                print("\nBrainstorm Variants")
                print("=" * 50)
                for i, v in enumerate(variants, 1):
                    print(f"\n{i}. {v.get('name', 'Variant')} [{v.get('cost', '?')} cost]")
                    print(f"   {v.get('pitch', '')}")
                    print(f"   Tradeoff: {v.get('tradeoff', '')}")
                    print(f"   Prototype: {v.get('prototype_step', '')}")

            elif args.unknowns_command == "reference":
                brief = await discovery.distill_reference(args.path, llm_fn, goal=args.goal)
                print("\nReference Brief")
                print("=" * 50)
                print(brief)

            elif args.unknowns_command == "plan":
                plan = await discovery.generate_plan(args.task, args.context, llm_fn)
                print(plan)
                print(f"\nSaved to: {discovery.work_dir}/implementation-plan.md")

        asyncio.run(run())

    elif args.unknowns_command == "pitch":
        pitch = asyncio.run(discovery.package_pitch(args.title))
        print(pitch)
        print(f"\nSaved to: {discovery.work_dir}/pitch.md")


def _run_audit(args: argparse.Namespace):
    if args.audit_command == "export":
        from zilli.audit.compliance import ComplianceReporter

        reporter = ComplianceReporter(audit_dir=args.audit_dir)
        report = reporter.generate(
            framework=args.framework,
            tenant_id=args.tenant,
            period_start=args.start,
            period_end=args.end,
        )
        reporter.export_json(report, args.output)
        status = "PASS" if report.passed else "FAIL"
        print(f"Compliance report [{args.framework}] {status}")
        print(f"  Total requests: {report.total_requests}")
        print(f"  Cloud: {report.cloud_requests} | Local: {report.local_requests}")
        print(f"  Sanitized: {report.sanitized_requests} | Rejected: {report.rejected_requests}")
        print(f"  PII detected: {report.pii_detected_count}")
        print(f"  Consent violations: {report.consent_violations}")
        print(f"  Findings: {len(report.findings)}")
        print(f"  Exported to: {args.output}")


def _run_ppm(args: argparse.Namespace):
    if args.ppm_command == "stats":
        from zilli.routing.ppm import PPMPredictor
        p = PPMPredictor()
        print(json.dumps(p.stats(), indent=2, default=str))

    elif args.ppm_command == "train-model":
        records_path = Path(args.records)
        if not records_path.exists():
            print(f"Records file not found: {args.records}")
            return
        with open(records_path) as f:
            records = json.load(f)
        from zilli.routing.ppm_classifier import train_classifier
        result = train_classifier(records, output_path=args.output, classifier_type=args.classifier)
        print(json.dumps(result, indent=2))
        print(f"Model saved to: {args.output}")


def _run_pipeline(args: argparse.Namespace):
    import asyncio

    from zilli.evolution.diversity import DiversityController
    from zilli.evolution.skill_evolution import SkillEvolutionEngine
    from zilli.pipeline.evolve_to_train import EvolveToTrainPipeline, EvolveTrainConfig
    from zilli.training.rl_trainer import RLTrainer

    async def run():
        config = EvolveTrainConfig(
            skills_dir=args.skills_dir,
            trajectories_dir=args.trajectories_dir,
            num_train_epochs=args.epochs,
            log_dir=args.log_dir,
            max_cycles=args.cycles,
        )

        diversity = DiversityController()
        engine = SkillEvolutionEngine(diversity_controller=diversity)
        trainer = RLTrainer({})
        pipeline = EvolveToTrainPipeline(
            config=config,
            evolution_engine=engine,
            trainer=trainer,
        )

        for cycle in range(args.cycles):
            print(f"\n=== Cycle {cycle + 1}/{args.cycles} ===")
            records = await pipeline.run_cycle()
            for r in records:
                status = "✅" if r.success else "❌"
                print(f"  {status} {r.stage.value:8s} | {r.message}")
            print(f"  Summary: champion={pipeline.summary()['champion_model']}")

        print("\n=== Pipeline Complete ===")
        print(json.dumps(pipeline.summary(), indent=2))

    asyncio.run(run())


def _run_distill(config_path: str | None = None, num_samples: int = 100,
                  checkpoint_path: str | None = None, ab_test_path: str | None = None,
                  log_dir: str = ""):
    from zilli.infra.device_utils import set_device
    from zilli.training.distillation import DistillationSample, DistillationScheduler

    if config_path:
        p = Path(config_path)
        if ".." in str(p):
            print("Path traversal detected in config path")
            return
        p = p.resolve()
        if p.exists():
            with open(p) as f:
                config = yaml.safe_load(f).get("distillation", {})
        else:
            print(f"Config not found: {config_path}")
            return
    else:
        config = {}

    kw = {
        "lambda_bc": config.get("lambda_bc", 1.0),
        "lambda_rl": config.get("lambda_rl", 0.5),
        "lambda_reg": config.get("lambda_reg", 0.1),
        "kl_beta": config.get("kl_beta", 0.1),
        "reward_gamma": config.get("reward_gamma", 0.2),
        "embedding_delta": config.get("embedding_delta", 0.5),
        "lora_threshold": config.get("lora_threshold", 1000),
        "distill_interval_hours": config.get("distill_interval_hours", 24),
        "full_sft_interval_days": config.get("full_sft_interval_days", 7),
        "log_dir": log_dir,
    }

    device = config.get("device", "auto")
    set_device(device)
    print(f"Device: {device}")

    if checkpoint_path and Path(checkpoint_path).exists():
        scheduler = DistillationScheduler.load_checkpoint(checkpoint_path)
        print(f"Resumed from checkpoint: {checkpoint_path}")
    else:
        scheduler = DistillationScheduler(**kw)

    import numpy as np
    samples = []
    for idx in range(num_samples):
        samples.append(DistillationSample(
            executor_action={"tool": "write", "key": "x", "value": str(idx)},
            planner_action={"tool": "write", "key": "y", "value": str(idx)},
            executor_log_prob=float(np.random.normal(-1.0, 0.5)),
            planner_log_prob=float(np.random.normal(-0.5, 0.3)),
            executor_reward=float(np.random.uniform(0.3, 1.0)),
            planner_reward=float(np.random.uniform(0.6, 1.0)),
            executor_embedding=list(np.random.randn(4)),
            planner_embedding=list(np.random.randn(4)),
        ))
    scheduler.add_batch(samples)
    print(f"Added {num_samples} distillation samples")

    if ab_test_path:
        _run_ab_test_cli(scheduler, samples, ab_test_path, log_dir)
        return

    cycle = scheduler.run_cycle()
    if cycle:
        print(f"Cycle {cycle.cycle_id}: loss={cycle.total_loss:.4f} "
              f"bc={cycle.bc_loss:.4f} rl={cycle.rl_loss:.4f} "
              f"kl={cycle.kl_divergence:.4f}")

    if checkpoint_path:
        scheduler.save_checkpoint(checkpoint_path)
        print(f"Checkpoint saved: {checkpoint_path}")

    print("Distillation complete.")


def _run_ab_test_cli(scheduler, samples, ab_test_path: str, log_dir: str):
    from zilli.distillation.dsl import (
        ExperimentLineage,
        ExperimentParams,
        lineage_report,
        run_multi_round,
    )

    p = Path(ab_test_path)
    if ".." in str(p):
        print("Path traversal detected in AB test config path")
        return
    p = p.resolve()
    if not p.exists():
        print(f"AB test config not found: {ab_test_path}")
        return

    with open(p) as f:
        config = yaml.safe_load(f)

    lineage_config = config.get("lineage", {})
    lineage = ExperimentLineage(
        name=lineage_config.get("name", "cli_ab_test"),
        auto_baseline=lineage_config.get("auto_baseline", True),
    )

    for rd in lineage_config.get("rounds", []):
        variants = []
        for v in rd.get("variants", []):
            variant_params = {k: v for k, v in v.items() if k != "name"}
            variants.append(ExperimentParams(name=v.get("name", "variant"), **variant_params))
        lineage.add_round(rd.get("name", "round"), variants)

    if not lineage.rounds:
        print("No rounds defined in AB test config")
        return

    lineage.best_params = ExperimentParams(name="baseline")
    result = run_multi_round(lineage, samples, log_dir=log_dir)
    print(lineage_report(result))


if __name__ == "__main__":
    main()
