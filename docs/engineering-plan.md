# Zilli — 软件开发工程计划

> **文档类型**: 工程计划  
> **对应 PRD**: [MOM 元级系统](../prd.md#12-mom-元级系统meta-object-model)、[路线图：能力成熟度阶梯](../prd.md#6-路线图能力成熟度阶梯)、[依赖分析](../prd.md#7-依赖分析)  
> **版本对齐**: PRD v2.1 / Zilli v1.0.0

---

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

---

## 2. 模块清单

### 2.1 核心包 (`zilli/`)

| 子包 | 文件数 | 核心类 | 状态 | 对应 PRD |
|------|--------|--------|------|---------|
| `core/` | 2 | `Agent`, `TaskRunner` | ✅ | F-1 |
| `models/` | 7 | `ModelBackend`(ABC), `ModelRegistry`, `OllamaBackend`, `VLLMBackend`, `LlamaCppBackend`, `ModelProfiler`, `router` | ✅ | F-3 |
| `routing/` | 10 | `RouteClassifier`, `LocalHybridRouter`, `MOMRouter`, `PPMPredictor`, `ModelProfile`, `StrategySelector`, `FeedbackCollector`, `FeedbackEvaluator`, `PlannerFrequencyController`, `ppm_types` | ✅ | F-1, F-2, F-3, F-16 |
| `evolution/` | 3 | `SkillEvolutionEngine`, `DiversityController`, `cli` | ✅ | F-7, F-10 |
| `loops/` | 9 | `LoopRunner`, `MetaLoopRunner`, `HarnessOrchestrator`, `WeaknessMiner`, `ContextCurator`, `CycleMemory`, `Verifier`(5 impl), `Trigger`(3 impl), `unknowns` | ✅ | F-8, F-9, F-11, F-19, F-23 |
| `training/` | 7 | `RLTrainer`, `CISPO_Trainer`, `GRPO_Trainer`, `DistillationScheduler`, `ChampionChallenger`, `TrainingConfig` | ✅ | F-4, F-5, F-6 |
| `envs/` | 3 | `HermesSandbox`, `CostController`, `PlannerBudget` | ✅ | F-12 |
| `adaptive/` | 2 | `DynamicSOTAScheduler`, `MultiObjectiveOptimizer` | ✅ | F-12, F-20 |
| `pipeline/` | 2 | `EvolutionPipeline`, `run_evolve_to_train` | ✅ | F-11 |
| `evaluation/` | 3 | `MetaEvaluator`, `ExecutorOnlyEvaluator`, `DistillationBenchmark` | ✅ | F-17, F-18 |
| `fusion/` | 1 | `ResultFusion` | ✅ | — |
| `rewards/` | 1 | `VerifiableReward` | ✅ | F-4 |
| `schema/` | 1 | `BaseAction` + 8 action types | ✅ | — |
| `data/` | 3 | `TrajectoryStore`, `TrajectoryCleaner`, `VectorStore` | ✅ | F-4, F-5 |
| `infra/` | 4 | `LengthElasticController`, `AsyncRolloutScheduler`, `device_utils`, `logging` | ✅ | F-4 |
| `security/` | 3 | `PIIDetector`, `InputSanitizer`, `DataIsolation` | ✅ | F-13 |
| `privacy/` | 6 | `PrivacyEngine`, `DataClassifier`, `ReIDAssessor`, `ConsentManager`, `PrivacySandbox`, `policy` | ✅ | F-13, F-0.1 |
| `audit/` | 2 | `AuditLogger`, `ComplianceReporter` | ✅ | F-21 |
| `industry/` | 1 | `WorkflowRegistry` | ✅ | F-15 |
| `server/` | 3 | FastAPI app + schemas + routes | ✅ | F-14 |
| `workflow/` | 2 | `CeleryDAGExecutor`, `CeleryApp` | ✅ | F-15 |
| `distillation/` | 2 | `dsl.py` (A/B experiment DSL), `losses.py` | ✅ | F-5 |
| `hybrid/` | 2 | `HybridExecutor`, `PrivacyGatekeeper` | ✅ | F-13, F-0.1 |
| `swe/` | 4 | `SWEAgent`, `sandbox`, `verifier`, `reporter` | ✅ | SWE-bench |
| `dag/` | 1 | `TaskDAG`, `DAGExecutor` | ✅ | F-22 |
| `cache/` | 1 | `CacheEngine` | ✅ | F-2 |
| `configs/` | 1 | `ZilliConfig`(Pydantic) + yaml loader | ✅ | — |
| `learner/` | 1 | `ContinuousLearner` | ✅ | F-7 |
| `utils/` | 1 | `crypto.py` (API key hashing) | ✅ | F-14 |
| **cli.py** | — | `main()` + 14 顶层子命令 | ✅ | — |
| **run_training.py** | — | `TrainingExperiment`, `run_rollout()` | ✅ | F-4 |
| **dashboard_app.py** | — | Streamlit dashboard | ✅ | F-14 |
| **version.py** | — | version = `"1.0.0"` | ✅ | — |

### 2.2 测试 (`tests/`)

> 实况：78 个测试文件、1048 tests 全部通过。以下为代表性文件（完整清单以 `pytest --collect-only` 为准）。

| 测试文件 | 所属模块 | 测试数 | 覆盖维度 | 状态 |
|----------|----------|--------|---------|------|
| `test_zilli.py` | Core / 顶层 | 88 | Agent 生命周期、TaskRunner、Sandbox | ✅ |
| `test_server.py` | server | 56 | 鉴权、限速、CORS、Request-ID、租户端点、审计落盘 | ✅ |
| `test_loops.py` | loops/runner | 34 | LoopRunner、MetaLoopRunner、触发器、验证器 | ✅ |
| `test_swe.py` | swe | 28 | SWEAgent、Sandbox、Verifier、Reporter | ✅ |
| `test_privacy*.py` | privacy | 47 | PII 3 级检测、数据分类、ConsentManager | ✅ |
| `test_security*.py` | security | 27 | 输入脱敏、注入防护、数据隔离 | ✅ |
| `test_ppm*.py` | routing/ppm | 41 | PPM 预测、在线训练、缓存、权重更新 | ✅ |
| `test_cache.py` | cache | 20 | LRU 策略、命中率、过期清理 | ✅ |
| `test_ppm_classifier.py` | routing/ppm | 20 | RegexClassifier、SklearnONNXClassifier、Rust hotpath | ✅ |
| `test_device_utils.py` | infra | 20 | CUDA/MPS/CPU 检测、缓存、张量搬运 | ✅ |
| `test_config.py` | configs | 19 | Pydantic 配置、YAML 加载、环境变量覆盖 | ✅ |
| `test_dag.py` | dag | 19 | TaskDAG、DAGExecutor、Mermaid 导出 | ✅ |
| `test_backends*.py` | models | 35 | Ollama/vLLM/llama.cpp 后端、健康检查 | ✅ |
| `test_cli_*.py` | cli | 42 | 14 子命令、参数解析、错误处理 | ✅ |
| `test_multi_round.py` | loops | 17 | ExperimentLineage、多轮迭代、baseline 注入 | ✅ |
| `test_feedback.py` | routing | 17 | FeedbackCollector、批量 flush、异步队列 | ✅ |
| `test_models.py` | models | 17 | ModelRegistry、ModelProfiler、ELO 更新 | ✅ |
| `test_vector_store.py` | data | 17 | ChromaDB、语义检索、元数据过滤 | ✅ |
| `test_mom_router.py` | routing | 13 | MOMRouter、GPS-MOM 四步流水线 | ✅ |
| `test_trajectory_cleaner.py` | data | 13 | 数据保鲜、热/温/冷归档、自动清理 | ✅ |
| `test_training_data.py` | training | 7 | TrajectoryStore、经验回放、golden_ratio | ✅ |
| `test_mom_governance.py` | MOM | 15 | 数据分级、脱敏、路由策略、响应回替 | ✅ |
| `test_industry_*.py` | industry | 24 | 4 行业模板加载、PII 规则、审计模板 | ✅ |
| **其余 41 文件** | 全模块 | 1-15 个测试/文件 | 边界条件、错误处理、集成 | ✅ |
| **合计** | **78 文件** | **1048 tests** | **全模块覆盖** | **✅ 全部通过** |

---

## 3. 架构图

```
┌─────────────────────────────────────────────────────────┐
│                        CLI Layer                         │
│  zilli {run, route, train, evaluate, distill, swe,      │
│          serve, pipeline, ppm, cost, models, industry,    │
│          audit, unknowns, soak, list-tasks,              │
│          privacy, mom, data}                              │
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
│         └─ PPMPredictor.train() → 在线训练              │
│         └─ PrivacyEngine → DataClassifier → PrivacyGatekeeper │
│         └─ EntityReplacer → EntityRestorer                │
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
│                                                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │  Evaluation & Governance                           │    │
│  │  LLM-as-Judge → BayesianMetaEvaluator            │    │
│  │  ChampionChallenger → ELO + Radar                │    │
│  │  PrivacyEngine → PII 3-level → DataGovernance     │    │
│  │  IndustryWorkflow → HIPAA/SOX/ABA/FERPA          │    │
│  └──────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## 4. 核心数据流

### 4.1 请求路由（MOM 完整链路）

```
用户请求
  → InputSanitizer（PII 检测 Level 1）
  → PrivacyEngine.evaluate()（Level 2 + Level 3）
  → DataClassifier（PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED/REGULATED）
  → PrivacyGatekeeper.decide()
      → REGULATED → REJECTED
      → RESTRICTED/INTERNAL → LOCAL（强制本地模型）
      → CONFIDENTIAL → LOCAL_WITH_CLOUD_FALLBACK
      → PUBLIC → CLOUD
  → CacheEngine（LRU 缓存）
  → PPMPredictor.predict()（difficulty + family + confidence）
  → StrategySelector.select()（ECONOMY/STANDARD/ENHANCED）
  → DynamicSOTAScheduler.should_call_sota()（硬约束检查）
  → ModelProfile.filter()（按 family + cost + success_rate + data_residency）
  → ModelProfile.select_best()（Softmax Thompson 采样）
  → RouteClassifier（FAST_LANE / FULL_ROUTE）
  → 执行（本地或脱敏后云端）
  → OutputSanitizer（PII 回检）
  → EntityRestorer（占位符替换回原始值）
  → 返回响应
  → FeedbackCollector.record()（异步）
  → AuditLogger（记录完整决策链：data_class, sanitization, residency, route_policy）
```

### 4.2 训练流程（学习层）

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

### 4.3 进化循环（进化层）

```
zilli-evolve --input <trajs> --target-skills <skills> --mode <evolve|harness>
  → Load trajectories + skill files
  → SkillEvolutionEngine.evolve(skill_file, trajectories)
      → _wrap_as_dspy_module() → source, functions, classes, imports
      → _reflect_on_trajectories() → error reflections
      → [harness mode] MOMRouter.route() → select model（本地/云端，受数据分级约束）
      → _select_strategy() → prompt_opt / error_handling / boundary / tool
      → _apply_evolution() → source transform
      → DiversityController.add_entry() → novelty gate
      → _generate_pr() → diff output
      → [harness mode] MOMRouter.record_feedback() → close the loop
  → Summary report
```

### 4.4 Self-Harness 元循环（评估层）

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

### 4.5 环境反馈数据流（数据层）

```
执行轨迹
  → PrivacyEngine.evaluate() → PII 检测 + 脱敏
  → TrajectoryStore.add_trajectory() → 热数据（7 天）
  → VectorStore.add_embedding() → ChromaDB 语义检索
  → ExperienceReplay.sample() → golden_ratio=0.5
  → RLTrainer.update() / DistillationScheduler.run_cycle()
  → PPM Online Training (FeedbackCollector.flush() → 200 条触发)
  → ModelProfile EMA 更新 (FeedbackCollector.flush() → 100 条触发)
  → TrajectoryCleaner.archive() → 温数据（30 天）→ 冷归档（90 天）
```

---

## 5. 技术债务

| 编号 | 描述 | 影响 | 优先级 | 对应 PRD |
|------|------|------|--------|---------|
| T-1 | ~~`TestSuiteVerifier` 有 `__init__()` 导致 pytest 收集警告~~ ✅ 已添加 `__test__ = False` | 测试警告 | 低 | — |
| T-2 | PPM 主分类器已模型化（sklearn ONNX，acc 1.0），regex+rust 为回退 | 功能边界 | 中 | F-2 |
| T-3 | ~~Streamlit Dashboard 尚无鉴权~~ ✅ 已添加登录 + 角色管控；2026-08-18 起强制要求配置凭据（`ZILLI_DASHBOARD_PASSWORD` 或 `ZILLI_DASHBOARD_USERS`），未配置时拒绝启动；密码比较改用 `hmac.compare_digest` | 安全 | 低 | F-14 |
| T-4 | Rust crate (`zilli-rs`) 热路径已实现（PPM + 代码指纹），PyO3 绑定可选 feature 已验证 `cargo check` | 功能缺失 | 低 | F-24 |
| T-5 | ~~CI（GitHub Actions）尚未接入~~ ✅ 已配置 lint + typecheck + test + junit 报告 | 流程缺失 | 中 | F-23 |
| T-6 | ~~PPM cache eviction 策略使用 hash 键值而非插入顺序~~ ✅ OrderedDict LRU `popitem(last=False)` 已正确 | 极低概率错误 | 低 | F-2 |
| T-7 | ~~FeedbackCollector._flush_loop 中 batch_size 检查在 flush() 后永远为 False~~ ✅ 死代码已移除，`record()` 达批量时早触发 flush | 死代码 | 低 | F-2 |
| T-8 | ~~ppm ↔ ppm_classifier 循环导入~~ ✅ 共享类型抽至 `ppm_types.py` | 架构 | 低 | F-2 |
| T-9 | PPM 缓存策略（LRU→popitem） | 极低概率错误 | 低 | F-2 |
| T-10 | ✅ 已修复（2026-08-18）：`ZILLI_API_KEYS` 支持 `key@tenant` 绑定，`X-Tenant-ID` 与密钥绑定租户强制校验（跨租户/伪造/缺头 401），`bind_tenant_key()` 运行时注册 | 安全 | 中 | F-24 |
| T-11 | MOM 行业模板动态加载：当前行业模板为静态 YAML，需支持运行时动态加载和更新 | 功能扩展 | 低 | F-15 |
| T-12 | EntityRestorer 占位符回替：当前仅支持简单替换，需支持嵌套结构（如 JSON 中的嵌套对象） | 功能边界 | 低 | F-0.3 |

---

## 6. 路线图与发布计划

### 能力成熟度阶梯

| 阶段 | 主题 | 成熟度标志 | 状态 | 版本 | 对应 PRD |
|------|------|-----------|------|------|---------|
| **L0 可运行** | 核心骨架 | 能执行单次任务 | ✅ | v0.1.0 | — |
| **L1 可路由** | 智能调度 | PPM 准确率 > 80%，成本优化 > 30%，缓存命中率 > 60% | ✅ | v0.2.0 | F-1, F-2 |
| **L2 可进化** | 自我改进 | Skill 进化引擎运行，连续 3 轮无新 PR 即收敛，多样性控制生效 | ✅ | v0.3.0 | F-7, F-8, F-9, F-10 |
| **L3 可训练** | RL 驱动 | CISPO/GRPO 策略损失收敛，蒸馏保持率 ≥ 90%，经验回放池 > 1000 条 | ✅ | v0.4.0 | F-4, F-5, F-6 |
| **L4 可治理** | 企业就绪 | MOM 元级系统、合规报告导出 + 隐私 3 级检测 + 审计日志 + 行业工作流（HIPAA/SOX/ABA/FERPA） | ✅ | v0.5.0 | F-0.1~F-0.4, F-13, F-15, F-21, F-22 |
| **L5 自运转** | 无人值守 | `zilli soak` 7×24 健康监控，崩溃恢复 < 30s，99.9% 可用性 | ✅ | v1.0.0 | F-14, F-24, F-25 |
| **L6 群智能** | 多 Agent 协作 | Agent 间路由、任务分解（DAG 无环/扇出/深度校验）、四级共识链、产物图 | ✅ | v2.0.0 | RFC-006 |

### 历史版本里程碑

#### Phase 1 — L0 可运行（已完成 ✅）

- 项目骨架：Schema、TaskRunner、Sandbox
- 轨迹存储：TrajectoryStore、经验回放
- RL 基础设施：训练配置、长度控制、异步调度
- RL 算法：CISPO + GRPO + VerifiableReward
- 进化引擎：SkillEvolutionEngine + ContinuousLearner + CLI

#### Phase 2 — 品牌与工程化（已完成 ✅）

- 品牌更名 Hermes-NG → Zilli
- 8 个代码结构问题修复
- 生产数据读取替代桩代码
- CLI evaluate 重写

#### Phase 3 — L1 可路由（已完成 ✅）

- RouteClassifier 正则 + LLM 路由
- LocalHybridRouter 三阶段路由（Plan→Execute→Review）
- 安全脱敏 + 缓存 + 预算控制
- GPS-MOM：PPM + Strategy + Profile + Feedback + MOMRouter
- 14 个自我进化 Bug 修复 + 收敛验证

#### Phase 4 — L2 可进化（已完成 ✅）

- LoopRunner / MetaLoopRunner
- 5 种验证器 + 3 种触发器
- 升级处理 + 循环记忆
- WeaknessMiner 失败聚类
- Self-Harness 三阶段元循环
- ContextCurator（ACE）

#### Phase 5 — L4 可治理（已完成 ✅）

- MOM 元级系统：PrivacyEngine + DataClassifier + PrivacyGatekeeper + EntityReplacer/Restorer
- 隐私引擎 + PII 3 级检测 + 数据隔离
- 审计日志 + 合规报告（GDPR/HIPAA/SOC2/SOX/PCI/ABA/FERPA）
- 行业工作流（法律/医疗/金融/教育）
- Streamlit Dashboard（MOM 决策追踪、数据驻留统计、行业工作流配置）
- Celery 分布式工作流
- ChromaDB 向量存储
- Trainer 频率控制器
- 模型画像系统（ELO + 雷达图）

#### Phase 6 — L3 可训练（已完成 ✅）

- PPM 在线训练
- LLM-as-Judge 评分
- MOMRouter 接入 Harness 模式
- 706 测试通过，lint 干净

#### Phase 7 — v0.5.0（已完成 ✅）

- 接入 CI（GitHub Actions：lint + pyright + 多版本测试）
- Model-based PPM（SklearnONNXClassifier，`ppm` extra 可选依赖）
- 端到端进化训练管线整合（EvolveToTrainPipeline + 断点续训）
- 贝叶斯 MetaEvaluator（高斯共轭先验）
- 未知项发现模块（Fable 方法）
- SOTA 硬约束（max_sota_ratio）
- 合规报告导出 CLI
- DAG Mermaid 可视化
- 异步死锁修复、反馈批量早触发、ppm 循环导入拆分
- 765 测试通过，ruff 0 errors，pyright 0 errors

#### Phase 8 — v0.6.0（已完成 ✅）

- Rust 辅助库热路径实现（zilli-rs + PyO3 绑定 `zilli_hotpath`）
- 多租户支持（TenantManager YAML 持久化 + /v1/tenants 端点 + 数据隔离）
- PPM training 集成到完整生产反馈闭环（auto-train）
- Harness 模式在真实技能库上运行验证
- Dashboard 无头测试（streamlit.testing.v1）
- 测试覆盖率 → 85.0%（972 → 1017 → 1028 → 1048 tests）

#### Phase 9 — v1.0.0 L5 自运转（已完成 ✅）

- MOM 元级系统：PrivacyEngine + DataClassifier + PrivacyGatekeeper + EntityReplacer/Restorer
- 模型化 PPM 默认分类器（sklearn ONNX，acc 1.0 / RMSE 0.044），regex+rust 回退
- `zilli soak` 端到端持续运行器（健康监控 + 崩溃恢复 + 指标落盘）
- 多租户 `TenantManager` YAML 持久化 + `/v1/tenants` 端点
- Rust 热路径 PyO3 绑定 `zilli_hotpath`（PPM 预测 0.054ms）
- API server 审计追踪（route_decision / model_call 落盘，含 data_class, sanitization, residency）
- 参考文档 × 4 + 安全审计 `docs/security-audit-v1.md`
- 1048 tests / ruff 0 / pyright 0 / 覆盖率 85.0%

### 下一步开发计划（v1.1.0 候选）

| 优先级 | 任务 | 文件 | 预估工时 | 对应 PRD |
|--------|------|------|----------|---------|
| P0 | ✅ 端到端进化训练管线整合（Evolve → Train → Deploy → Monitor，`EvolveToTrainPipeline` 最小闭环 e2e 测试覆盖） | `pipeline/`, `run_training.py` | 8h | F-11 |
| P0 | ✅ 训练 Pipeline 断点续训支持（`TrainingExperiment.resume_from` + CLI `--resume`，`test_checkpoint_resume.py` 9 tests） | `run_training.py` | 8h | F-4 |
| P1 | ✅ T-10 多租户密钥绑定（2026-08-18 完成，见 T-10 行） | `server/app.py` | — | F-24 |
| P2 | ✅ 进化引擎并发处理（asyncio 并行，`evolution_concurrency`） | `evolution/` | — | F-7 |
| P2 | ✅ MOM 行业模板动态加载（`ZILLI_INDUSTRY_CONFIG` YAML + `/v1/industry/reload`） | `industry/` | — | F-15 |
| P3 | ✅ EntityReplacer / EntityRestorer 嵌套结构（`zilli/privacy/entities.py`） | `privacy/` | — | F-0.3 |
| P1 | ✅ Rust 演化核心热路径：PPM 预测迁移至 Rust（`zilli_hotpath` PyO3 v0.3.0，2026-08-19，7.7µs/call ≈ 20.2×，parity 14/14） | `zilli-rs/hotpath/` | 24h | F-24 |
| P2 | ✅ 补充集成测试（route → execute → feedback → evolve，含执行环节 + fallback 链；2026-08-18，1087→1105 tests） | `tests/` | — | — |
| P2 | ✅ 覆盖率 90% 里程碑（CLI/registry/profile/continuous_learner/server/experience_replay/mock_env 等补测；2026-08-19，1105→1204 tests，86%→90%） | `tests/` | — | — |

---

## 7. 发布检查清单

### Release v1.0.0 ✅ 已完成

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 1048 tests / ruff 0 / pyright 0 / 覆盖率 85.0% | ✅ | 质量门禁 |
| MOM 元级系统：PrivacyEngine + DataClassifier + PrivacyGatekeeper + EntityReplacer/Restorer | ✅ | 数据治理三层架构 |
| 模型化 PPM（sklearn ONNX，acc 1.0 / RMSE 0.044） | ✅ | 默认分类器 |
| `zilli soak` 持续运行器 | ✅ | 7×24 监控 |
| 多租户 `TenantManager` YAML 持久化 + `/v1/tenants` | ✅ | SaaS 基础 |
| Rust 热路径 PyO3 绑定 `zilli_hotpath` | ✅ | 0.054ms PPM |
| API server 审计追踪（含 MOM 字段：data_class, sanitization, residency） | ✅ | 合规断链修复 |
| 参考文档 × 4 + 安全审计 | ✅ | 文档完备 |
| Dashboard 强制凭据 + `hmac.compare_digest` | ✅ | 安全加固 |
| Fail-closed 鉴权（非本地 401） | ✅ | 安全加固 |
| 预算文件隔离（`ZILLI_BUDGET_FILE`） | ✅ | 测试安全 |
| 行业工作流（HIPAA/SOX/ABA/FERPA） | ✅ | 企业合规 |
| MOM 决策追踪端点（`/v1/mom/decision/{id}`） | ✅ | 可观测性 |
| 数据驻留统计端点（`/v1/data/residency`） | ✅ | 合规审计 |

### Release v1.1.0 候选

| 里程碑 | 目标 | 验收标准 | 状态 |
|--------|------|---------|------|
| 端到端进化训练管线 | Evolve → Train → Deploy → Monitor 全自动 | 单轮 < 4h，回滚 < 5min | ✅ 已有实现（`EvolveToTrainPipeline` e2e 最小闭环测试） |
| 训练断点续训 | 检查点保存/恢复，配置 hash 校验 | `resume_from` + CLI `--resume` | ✅ 已实现（`test_checkpoint_resume.py` 9 tests） |
| Rust 演化核心 | Loop 引擎、PPM 预测迁移至 Rust | 性能提升 10×，功能一致性 100% | ✅ 2026-08-19（`zilli_hotpath` PyO3 v0.3.0：PPM 预测 7.7µs/call ≈ 20.2×，parity 14/14） |
| 多租户密钥绑定 | API Key 注册时绑定 tenant_id | 跨租户访问 401，伪造租户 401 | ✅ 2026-08-18 |
| 覆盖率 90% | 新增 200+ 测试 | pytest 报告 | ✅ 2026-08-19（90.0%→92.0%，1204→1380 tests，11 个测试文件补测 ONNX/chroma/后端/沙箱/PII/SWE 边界） |
| L6 群智能 | 多 Agent 协作（分解→路由→共识） | `zilli swarm` CLI + 40 tests | ✅ 2026-08-19（RFC-006，1204→1244 tests） |
| L6 群智能设计 | Agent 间路由、任务分解、共识机制 | RFC 文档 | ✅ 2026-08-19（RFC-006 + `zilli/swarm/` 骨架 + `zilli swarm` CLI） |
| MOM 行业模板动态加载 | 运行时热更新行业配置 | 无重启加载 | ✅ 2026-08-18 |
| EntityReplacer/Restorer 嵌套 | 占位符替换回替，支持嵌套结构 | 占位符替换准确率 100% | ✅ 2026-08-18 |

---

> **相关文档**: [PRD v2.1](../prd.md) | [MOM 架构解释](explanation-architecture.md) | [安全审计](security-audit-v1.md)
