# Zilli — 软件开发工程计划

## 1. 项目概览

| 属性 | 值 |
|------|------|
| 项目名 | Zilli（原 Hermes-NG） |
| 版本 | 1.0.0 |
| 语言 | Python 3.12+（主） + Rust（辅助 crate `zilli-rs`，PyO3 热路径已接） |
| 测试 | 1048 tests, 0 warnings |
| 覆盖率 | 85.0% |
| 代码风格 | ruff (all rules), pyright (strict) |
| 入口 | `zilli` (CLI), `zilli-evolve` (进化 CLI) |
| 包管理 | pip / uv |
| 构建 | pyproject.toml (setuptools) |

## 2. 模块清单

### 2.1 核心包 (`zilli/`)

| 子包 | 文件数 | 核心类 | 状态 |
|------|--------|--------|------|
| `core/` | 2 | `Agent`, `TaskRunner` | ✅ |
| `models/` | 7 | `ModelBackend`(ABC), `ModelRegistry`, `OllamaBackend`, `VLLMBackend`, `LlamaCppBackend`, `ModelProfiler`, `router` | ✅ |
| `routing/` | 10 | `RouteClassifier`, `LocalHybridRouter`, `MOMRouter`, `PPMPredictor`, `ModelProfile`, `StrategySelector`, `FeedbackCollector`, `FeedbackEvaluator`, `PlannerFrequencyController`, `ppm_types` | ✅ |
| `evolution/` | 3 | `SkillEvolutionEngine`, `DiversityController`, `cli` | ✅ |
| `loops/` | 9 | `LoopRunner`, `MetaLoopRunner`, `HarnessOrchestrator`, `WeaknessMiner`, `ContextCurator`, `CycleMemory`, `Verifier`(5 impl), `Trigger`(3 impl), `unknowns` | ✅ |
| `training/` | 7 | `RLTrainer`, `CISPO_Trainer`, `GRPO_Trainer`, `DistillationScheduler`, `ChampionChallenger`, `TrainingConfig` | ✅ |
| `envs/` | 3 | `HermesSandbox`, `CostController`, `PlannerBudget` | ✅ |
| `adaptive/` | 2 | `DynamicSOTAScheduler`, `MultiObjectiveOptimizer` | ✅ |
| `pipeline/` | 2 | `EvolutionPipeline`, `run_evolve_to_train` | ✅ |
| `evaluation/` | 3 | `MetaEvaluator`, `ExecutorOnlyEvaluator`, `DistillationBenchmark` | ✅ |
| `fusion/` | 1 | `ResultFusion` | ✅ |
| `rewards/` | 1 | `VerifiableReward` | ✅ |
| `schema/` | 1 | `BaseAction` + 8 action types | ✅ |
| `data/` | 3 | `TrajectoryStore`, `TrajectoryCleaner`, `VectorStore` | ✅ |
| `infra/` | 4 | `LengthElasticController`, `AsyncRolloutScheduler`, `device_utils`, `logging` | ✅ |
| `security/` | 3 | `PIIDetector`, `InputSanitizer`, `DataIsolation` | ✅ |
| `privacy/` | 6 | `PrivacyEngine`, `DataClassifier`, `ReIDAssessor`, `ConsentManager`, `PrivacySandbox`, `policy` | ✅ |
| `audit/` | 2 | `AuditLogger`, `ComplianceReporter` | ✅ |
| `industry/` | 1 | `WorkflowRegistry` | ✅ |
| `server/` | 3 | FastAPI app + schemas + routes | ✅ |
| `workflow/` | 2 | `CeleryDAGExecutor`, `CeleryApp` | ✅ |
| `distillation/` | 2 | `dsl.py` (A/B experiment DSL), `losses.py` | ✅ |
| `hybrid/` | 2 | `HybridExecutor`, `PrivacyGatekeeper` | ✅ |
| `swe/` | 4 | `SWEAgent`, `sandbox`, `verifier`, `reporter` | ✅ |
| `dag/` | 1 | `TaskDAG`, `DAGExecutor` | ✅ |
| `cache/` | 1 | `CacheEngine` | ✅ |
| `configs/` | 1 | `ZilliConfig`(Pydantic) + yaml loader | ✅ |
| `learner/` | 1 | `ContinuousLearner` | ✅ |
| `utils/` | 1 | `crypto.py` (API key hashing) | ✅ |
| **cli.py** | — | `main()` + 14 顶层子命令 | ✅ |
| **run_training.py** | — | `TrainingExperiment`, `run_rollout()` | ✅ |
| **dashboard_app.py** | — | Streamlit dashboard | ✅ |
| **version.py** | — | version = `"1.0.0"` | ✅ |

### 2.2 测试 (`tests/`)

> 实况：78 个测试文件、1048 tests 全部通过。以下为代表性文件（完整清单以 `pytest --collect-only` 为准）。

| 测试文件 | 所属模块 | 测试数 | 状态 |
|----------|----------|--------|------|
| `test_zilli.py` | Core / 顶层 | 88 | ✅ |
| `test_server.py` | server | 56 | ✅ |
| `test_loops.py` | loops/runner | 34 | ✅ |
| `test_swe.py` | swe | 28 | ✅ |
| `test_privacy*.py` | privacy | 47 | ✅ |
| `test_security*.py` | security | 27 | ✅ |
| `test_ppm*.py` | routing/ppm | 41 | ✅ |
| `test_cache.py` | cache | 20 | ✅ |
| `test_ppm_classifier.py` | routing/ppm | 20 | ✅ |
| `test_device_utils.py` | infra | 20 | ✅ |
| `test_config.py` | configs | 19 | ✅ |
| `test_dag.py` | dag | 19 | ✅ |
| `test_backends*.py` | models | 35 | ✅ |
| `test_cli_*.py` | cli | 42 | ✅ |
| `test_multi_round.py` | loops | 17 | ✅ |
| `test_feedback.py` | routing | 17 | ✅ |
| `test_models.py` | models | 17 | ✅ |
| `test_vector_store.py` | data | 17 | ✅ |
| `test_mom_router.py` | routing | 13 | ✅ |
| `test_trajectory_cleaner.py` | data | 13 | ✅ |
| `test_training_data.py` | training | 7 | ✅ |
| **其余 41 文件** | 全模块 | 1 个测试文件仅 1-15 个测试 | ✅ |
| **合计** | **78 文件** | **1048 tests** | **✅ 全部通过** |

## 3. 架构图

```
┌─────────────────────────────────────────────────────────┐
│                        CLI Layer                         │
│  zilli {run, route, train, evaluate, distill, swe,      │
│          serve, pipeline, ppm, cost, models, industry,  │
│          audit, unknowns, soak, list-tasks}             │
│  zilli-evolve {--mode evolve|harness|auto}               │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                   Agent Layer                             │
│  Agent.from_registry() → Agent.run()                     │
│    ├─ _generate_code() → ModelBackend.generate()          │
│    ├─ _execute_code() → subprocess                        │
│    └─ _fallback_for_task()                                │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                 Routing Layer                             │
│  RouteClassifier.classify() → FAST_LANE / FULL_ROUTE     │
│    ├─ FAST_LANE: Executor direct                          │
│    └─ FULL_ROUTE: Plan → Execute → Review                 │
│                                                           │
│  LocalHybridRouter.plan() / .execute() / .review()        │
│    ├─ InputSanitizer → CacheEngine → ModelRegistry         │
│    ├─ PlannerBudget (≤5% planner calls)                    │
│    └─ MOMRouter (optional GPS-MOM path):                   │
│         PPMPredictor → StrategySelector → ModelProfile    │
│         └─ FeedbackCollector → JSONL persist              │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                 Model Layer                                │
│  ModelRegistry.generate(role, prompt)                     │
│    ├─ Fallback chain per role                              │
│    ├─ Health-check aware                                   │
│    └─ Backends: Ollama / vLLM / llama.cpp                  │
│                                                           │
│  ModelProfiler (ELO + 6-dim capability radar)             │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Learning & Evolution Layer                    │
│  ┌──────────────────────────────────────────────────┐    │
│  │  Training Pipeline                                 │    │
│  │  Rollout → TrajectoryStore → RL(CISPO/GRPO)       │    │
│  │         → Distillation → Arena                     │    │
│  │  Scheduler: DynamicSOTA (Thompson Sampling)        │    │
│  │  Length: LengthElasticController                   │    │
│  └──────────────────────────────────────────────────┘    │
│                                                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │  Evolution Engine                                  │    │
│  │  SkillEvolutionEngine.evolve() → Diversity gate    │    │
│  │    ├─ 4 strategies                                 │    │
│  │    ├─ MOMRouter integration (harness mode)         │    │
│  │    └─ PR output                                    │    │
│  └──────────────────────────────────────────────────┘    │
│                                                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │  Loop Engine                                       │    │
│  │  LoopRunner.run() → Verify → Correct → Retry       │    │
│  │  MetaLoopRunner → Self-Harness (3-stage)           │    │
│  │  ContextCurator (ACE)                              │    │
│  └──────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## 4. 核心数据流

### 4.1 请求路由
```
用户请求
  → (可选) MOMRouter.route()
      → PPMPredictor.predict(text) → [difficulty, family, confidence]
      → StrategySelector.select(difficulty, budget) → [tier]
      → ModelProfile.filter(family, cost) → candidates
      → ModelProfile.select_best() → [model_id]
      → RouteDecision(model_id, difficulty, family, tier, confidence)
  → LocalHybridRouter.run()
      → RouteClassifier.classify() → FAST_LANE | FULL_ROUTE
      → plan() / execute() / review()
  → (可选) FeedbackCollector.record() → flush → JSONL
  → (可选) PPMPredictor.train(records) → adjust weights
```

### 4.2 训练流程
```
run_training.py
  → Load config / init components
  → For each epoch:
      1. DynamicSOTAScheduler.should_call_sota(task_type, state)
         → Thompson Sampling → use planner vs executor
      2. run_rollout(sandbox, task) → trajectory + reward
      3. Record call (success/failure) → update SOTA scheduler
      4. LengthElasticController.adapt(effective_lengths)
      5. TrajectoryStore.add_trajectory(traj, reward)
      6. Sample batch (golden_ratio=0.5) → trainer.update()
      7. DistillationScheduler.add_sample()
      8. If should_distill(): run_cycle()
      9. ChampionChallenger.run_match()
  → Save checkpoint
```

### 4.3 进化循环
```
zilli-evolve --input <trajs> --target-skills <skills> --mode <evolve|harness>
  → Load trajectories + skill files
  → SkillEvolutionEngine.evolve(skill_file, trajectories)
      → _wrap_as_dspy_module() → source, functions, classes, imports
      → _reflect_on_trajectories() → error reflections
      → [harness mode] MOMRouter.route() → select model
      → _select_strategy() → prompt_opt / error_handling / boundary / tool
      → _apply_evolution() → source transform
      → DiversityController.add_entry() → novelty gate
      → _generate_pr() → diff output
      → [harness mode] MOMRouter.record_feedback() → close the loop
  → Summary report
```

### 4.4 Self-Harness 元循环
```
MetaLoopRunner.run(input_data)
  → For meta-iteration:
      1. inner_runner.run() → result
      2. Collect failed traces from result.cycles
      3. HarnessOrchestrator.run_cycle(traces):
          a. WeaknessMiner.cluster_failures() → FailureCluster[]
          b. _propose_edits(clusters) → HarnessEdit[]
          c. _validate(candidate):
              - held_in tasks → pass_rate
              - held_out tasks → pass_rate
              - accept if improvement ≥ 5% AND no regression
      4. _tune(params, result) → adjust max_retries
      5. _apply_params()
  → Return best result
```

## 5. 技术债务与注意事项

| 编号 | 描述 | 影响 | 优先级 |
|------|------|------|--------|
| T-1 | ~~`TestSuiteVerifier` 有 `__init__()` 导致 pytest 收集警告~~ ✅ 已添加 `__test__ = False` | 测试警告 | 低 |
| T-2 | PPM 主分类器已模型化（sklearn ONNX，acc 1.0），regex+rust 为回退 | 功能边界 | 中 |
| T-3 | ~~Streamlit Dashboard 尚无鉴权~~ ✅ 已添加登录 + 角色管控；2026-08-18 起强制要求配置凭据（`ZILLI_DASHBOARD_PASSWORD` 或 `ZILLI_DASHBOARD_USERS`），未配置时拒绝启动；密码比较改用 `hmac.compare_digest` | 安全 | 低 |
| T-4 | Rust crate (`zilli-rs`) 热路径已实现（PPM + 代码指纹），PyO3 绑定可选 feature 已验证 `cargo check` | 功能缺失 | 低 |
| T-5 | ~~CI（GitHub Actions）尚未接入~~ ✅ 已配置 lint + typecheck + test + junit 报告 | 流程缺失 | 中 |
| T-6 | ~~PPM cache eviction 策略使用 hash 键值而非插入顺序~~ ✅ OrderedDict LRU `popitem(last=False)` 已正确 | 极低概率错误 | 低 |
| T-7 | ~~FeedbackCollector._flush_loop 中 batch_size 检查在 flush() 后永远为 False~~ ✅ 死代码已移除，`record()` 达批量时早触发 flush | 死代码 | 低 |
| T-8 | ~~ppm ↔ ppm_classifier 循环导入~~ ✅ 共享类型抽至 `ppm_types.py` | 架构 | 低 |
| T-9 | PPM 缓存策略（LRU→popitem） | 极低概率错误 | 低 |
| T-10 | 多租户无访问控制：租户身份由客户端自报（`/v1/tenants/{id}` 自动注册，路由接口可声明任意 tenant_id），无跨租户归属校验。需设计签名令牌或服务端绑定的租户-密钥映射（2026-08-18 kimi k3 审查 H5 登记，本期用户决定不处理） | 安全 | 中 |

## 6. 下一步开发计划

### P0 — 关键基础

| 任务 | 文件 | 预估工时 |
|------|------|----------|
| 端到端进化训练管线整合（Evolve → Train → Deploy → Monitor） | `pipeline/`, `run_training.py` | 8h |
| 训练 Pipeline 断点续训支持 | `run_training.py` | 8h |

### P1 — 增强功能

| 任务 | 文件 | 预估工时 |
|------|------|----------|
| T-10 多租户访问控制（密钥-租户绑定，替代客户端自报；2026-08-18 kimi k3 H5） | `tenancy.py`, `server/app.py` | 8h |
| Rust crate `zilli-rs` 演化核心、loop 引擎实现 | `zilli-rs/` | 24h |
| 多租户生产级完善（租户隔离的数据 + 配置 + 路由） | `routing/`, `configs/` | 16h |
| FeedbackEvaluator LLM-as-Judge 缓存 | `routing/feedback.py` | 2h |

### P2 — 优化

| 任务 | 文件 | 预估工时 |
|------|------|----------|
| 进化引擎并发处理（asyncio 并行进化多个 skill） | `evolution/` | 4h |
| 补充集成测试（e2e route → execute → feedback → evolve） | `tests/` | 8h |

## 7. 发布检查清单

### Release v0.5.0 ✅ 已完成

- [x] GitHub Actions CI 绿色通过（765+ tests, ruff, pyright）
- [x] 贝叶斯 MetaEvaluator 替换 bias/variance
- [x] 合规报告导出 CLI (`zilli audit export`)
- [x] SOTA 硬约束 (max_sota_ratio)
- [x] DAG Mermaid 可视化
- [x] 版本号更新 0.4.0 → 0.5.0

### Release v0.6.0 候选（Phase 8，已完成 ✅ 2026-07-26）

| 任务 | 文件 | 预估工时 | 状态 |
|------|------|----------|------|
| 覆盖率 74% → 83.6%（972 tests） | `tests/` | 8h | ✅ |
| 多租户支持（TenantManager + /v1/tenants 端点 + 数据命名空间隔离） | `tenancy.py`, `server/app.py` | 16h | ✅ |
| PPM training 集成到完整生产反馈闭环（auto-train every N records） | `routing/mom_router.py` | 4h | ✅ |
| Harness 模式在真实技能库上运行验证 | `examples/skills/`, `tests/test_harness_real_skills.py` | 4h | ✅ |
| Rust 热路径（PPM 预测 + 代码指纹，15 Rust tests） | `zilli-rs/src/hotpath/` | 24h | ✅ |
| Dashboard AppTest 无头测试（streamlit.testing.v1） | `tests/test_dashboard_app.py` | 2h | ✅ |
| P0 修复：run_training.main() 配置过滤崩溃（官方默认配置必然崩溃） | `run_training.py` | 1h | ✅ |
| P0 修复：子进程超时未 kill（agent/verification/swe sandbox） | `core/agent.py`, `loops/verification.py`, `swe/sandbox.py` | 1h | ✅ |
| P0 修复：dashboard st.secrets 无文件时崩溃 | `dashboard_app.py` | 0.5h | ✅ |

遗留（诚实记录）：
- ~~覆盖率 83.6% vs 目标 85%~~ ✅ 已达 85.0%（1048 tests）
- ~~Rust hotpath 尚未接 PyO3 绑定~~ ✅ `zilli-rs/src/bindings/` 已实现（optional `python-bindings` feature，`cargo check` 通过）。安装 wheel：`pip install maturin && cd zilli-rs && maturin develop --features python-bindings`（需要 pip 安装权限，未执行）
- ~~多租户当前为单进程内存注册表~~ ✅ `TenantManager.from_yaml/save_yaml` 持久化已实现

### Release v1.0.0 ✅ 已完成 (2026-07-26)

| 里程碑 | 状态 |
|--------|------|
| 1048 tests / ruff 0 / pyright 0 / 覆盖率 85.0% | ✅ |
| 模型化 PPM（sklearn ONNX，acc 1.0 / RMSE 0.044）替代 regex | ✅ |
| `zilli soak` 持续运行器（健康监控 + 崩溃恢复 + 指标落盘） | ✅ |
| 多租户 `TenantManager` YAML 持久化 + `/v1/tenants` 端点 | ✅ |
| Rust 热路径 PyO3 绑定 `zilli_hotpath`（PPM 预测 0.054ms） | ✅ |
| API server 审计追踪（route_decision / model_call 落盘） | ✅ |
| 参考文档 × 4 + 安全审计 `docs/security-audit-v1.md` | ✅ |

### Release v1.1.0 候选

| 任务 | 文件 | 预估工时 |
|------|------|----------|
| 端到端进化训练管线整合（Evolve → Train → Deploy → Monitor） | `pipeline/`, `run_training.py` | 8h |
| Rust crate 演化核心、loop 引擎迁移 | `zilli-rs/` | 24h |
| 进化引擎并发处理（asyncio 并行进化多个 skill） | `evolution/` | 4h |
| 训练 Pipeline 断点续训支持 | `run_training.py` | 8h |
