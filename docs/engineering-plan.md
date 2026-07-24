# Zilli — 软件开发工程计划

## 1. 项目概览

| 属性 | 值 |
|------|------|
| 项目名 | Zilli（原 Hermes-NG） |
| 版本 | 0.5.0 |
| 语言 | Python 3.12+（主） + Rust（辅助 crate, 规划中） |
| 测试 | 770 tests, 0 warnings |
| 代码风格 | ruff (all rules), pyright (strict) |
| 入口 | `zilli` (CLI), `zilli-evolve` (进化 CLI) |
| 包管理 | pip / uv |
| 构建 | pyproject.toml (setuptools) |

## 2. 模块清单

### 2.1 核心包 (`zilli/`)

| 子包 | 文件数 | 核心类 | 状态 |
|------|--------|--------|------|
| `core/` | 2 | `Agent`, `TaskRunner` | ✅ |
| `models/` | 6 | `ModelBackend`(ABC), `ModelRegistry`, `OllamaBackend`, `VLLMBackend`, `LlamaCppBackend`, `ModelProfiler` | ✅ |
| `routing/` | 9 | `RouteClassifier`, `LocalHybridRouter`, `MOMRouter`, `PPMPredictor`, `ModelProfile`, `StrategySelector`, `FeedbackCollector`, `FeedbackEvaluator`, `PlannerFrequencyController` | ✅ |
| `evolution/` | 4 | `SkillEvolutionEngine`, `DiversityController` | ✅ |
| `loops/` | 8 | `LoopRunner`, `MetaLoopRunner`, `HarnessOrchestrator`, `WeaknessMiner`, `ContextCurator`, `CycleMemory`, `Verifier`(5 impl), `Trigger`(3 impl) | ✅ |
| `training/` | 7 | `RLTrainer`, `CISPO_Trainer`, `GRPO_Trainer`, `DistillationScheduler`, `ChampionChallenger`, `TrainingConfig` | ✅ |
| `envs/` | 5 | `HermesSandbox`, `CostController`, `PlannerBudget`, `VectorStore`(ChromaDB) | ✅ |
| `adaptive/` | 2 | `DynamicSOTAScheduler`, `MultiObjectiveOptimizer` | ✅ |
| `pipeline/` | 1 | `EvolutionPipeline` | ✅ |
| `evaluation/` | 3 | `MetaEvaluator`, `ExecutorOnlyEvaluator`, `DistillationBenchmark` | ✅ |
| `fusion/` | 1 | `ResultFusion` | ✅ |
| `rewards/` | 1 | `VerifiableReward` | ✅ |
| `schema/` | 1 | `BaseAction` + 8 action types | ✅ |
| `data/` | 3 | `TrajectoryStore`, `TrajectoryCleaner`, `VectorStore` | ✅ |
| `infra/` | 4 | `LengthElasticController`, `AsyncRolloutScheduler`, `device_utils`, `logging` | ✅ |
| `security/` | 3 | `PIIDetector`, `InputSanitizer`, `DataIsolation` | ✅ |
| `privacy/` | 5 | `PrivacyEngine`, `DataClassifier`, `ReIDAssessor`, `ConsentManager`, `PrivacySandbox` | ✅ |
| `audit/` | 2 | `AuditLogger`, `ComplianceReporter` | ✅ |
| `industry/` | 2 | `WorkflowRegistry`, `IndustryType` | ✅ |
| `server/` | 3 | FastAPI app + schemas + routes | ✅ |
| `workflow/` | 4 | `CeleryDAGExecutor`, `CeleryApp`, tasks, workflow DAG | ✅ |
| `distillation/` | 2 | `dsl.py` (A/B experiment DSL), `losses.py` | ✅ |
| `hybrid/` | 2 | `HybridExecutor`, `PrivacyGatekeeper` | ✅ |
| `swe/` | 1 | `SWEAgent` | ✅ |
| `dag/` | 2 | `TaskDAG`, `DAGExecutor` | ✅ |
| `cache/` | 1 | `CacheEngine` | ✅ |
| `configs/` | 5 | `ZilliConfig`(Pydantic), `model_config.yaml`, `training_config.yaml`, `loader.py` | ✅ |
| `learner/` | 1 | `ContinuousLearner` | ✅ |
| `utils/` | 1 | `crypto.py` (API key hashing) | ✅ |
| **cli.py** | — | `main()` + 12 subcommands | ✅ |
| **run_training.py** | — | `TrainingExperiment`, `run_rollout()` | ✅ |
| **dashboard_app.py** | — | Streamlit dashboard | ✅ |
| **version.py** | — | version = `"0.4.0"` | ✅ |

### 2.2 测试 (`tests/`)

| 测试文件 | 所属模块 | 测试数 | 状态 |
|----------|----------|--------|------|
| `test_zilli.py` | Core | ~8 | ✅ |
| `test_core_agent.py` | core/agent | ~8 | ✅ |
| `test_core_runner.py` | core/runner | ~5 | ✅ |
| `test_models.py` | models | ~12 | ✅ |
| `test_backends.py` | models/backends | ~5 | ✅ |
| `test_profiler.py` | models/profiler | ~6 | ✅ |
| `test_routing.py` | routing/classifier | ~8 | ✅ |
| `test_mom_router.py` | routing/mom_router | 6 | ✅ |
| `test_ppm.py` | routing/ppm | 17 | ✅ |
| `test_profile.py` | routing/profile | 13 | ✅ |
| `test_strategy.py` | routing/strategy | 9 | ✅ |
| `test_feedback.py` | routing/feedback | 15 | ✅ |
| `test_frequency_controller.py` | routing/frequency_controller | ~4 | ✅ |
| `test_evolution_cli.py` | evolution/cli | ~5 | ✅ |
| `test_evolution_cli_integration.py` | evolution CLI | 7 | ✅ |
| `test_diversity.py` | evolution/diversity | ~10 | ✅ |
| `test_loops.py` | loops/runner | ~8 | ✅ |
| `test_harness_orchestrator.py` | loops/harness_orchestrator | ~5 | ✅ |
| `test_failure_analyzer.py` | loops/failure_analyzer | ~5 | ✅ |
| `test_context_curator.py` | loops/context_curator | ~5 | ✅ |
| `test_verification.py` | loops/verification | ~6 | ✅ |
| `test_sota_scheduler.py` | adaptive/sota_scheduler | ~6 | ✅ |
| `test_moo.py` | adaptive/moo | ~6 | ✅ |
| `test_pipeline.py` | pipeline | ~5 | ✅ |
| `test_meta_evaluator.py` | evaluation | ~4 | ✅ |
| `test_cache.py` | cache | ~4 | ✅ |
| `test_dag.py` | dag | ~4 | ✅ |
| `test_fusion.py` | fusion | ~4 | ✅ |
| `test_industry.py` | industry | ~4 | ✅ |
| `test_security*.py` | security | ~8 | ✅ |
| `test_privacy*.py` | privacy | ~8 | ✅ |
| `test_server.py` | server | ~6 | ✅ |
| `test_swe.py` | swe | ~4 | ✅ |
| `test_audit.py` | audit | ~3 | ✅ |
| `test_*.py` (training) | training | ~15 | ✅ |
| **合计** | **58 文件** | **770 tests** | **✅ 全部通过** |

## 3. 架构图

```
┌─────────────────────────────────────────────────────────┐
│                        CLI Layer                         │
│  zilli {run, route, train, evaluate, distill, swe,      │
│          serve, cost, models, industry, list-tasks}      │
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
| T-2 | PPM 使用 regex 而非模型进行分类，复杂任务分类精度有限 | 功能边界 | 中 |
| T-3 | ~~Streamlit Dashboard 尚无鉴权~~ ✅ 已添加登录 + 角色管控 | 安全 | 低 |
| T-4 | Rust crate (`zilli-rs`) 已决策但尚未实现 | 功能缺失 | 低 |
| T-5 | ~~CI（GitHub Actions）尚未接入~~ ✅ 已配置 lint + typecheck + test | 流程缺失 | 中 |
| T-6 | ~~PPM cache eviction 策略使用 hash 键值而非插入顺序~~ ✅ OrderedDict LRU `popitem(last=False)` 已正确 | 极低概率错误 | 低 |
| T-7 | ~~FeedbackCollector._flush_loop 中 batch_size 检查在 flush() 后永远为 False~~ ✅ 死代码已移除，`record()` 达批量时早触发 flush | 死代码 | 低 |
| T-8 | ~~ppm ↔ ppm_classifier 循环导入~~ ✅ 共享类型抽至 `ppm_types.py` | 架构 | 低 |

## 6. 下一步开发计划

### P0 — 关键基础

| 任务 | 文件 | 预估工时 |
|------|------|----------|
| 接入 GitHub Actions CI | `.github/workflows/` | 2h |
| 端到端进化训练管线整合（Evolve → Train → Deploy → Monitor） | `pipeline/`, `run_training.py` | 8h |
| 模型化 PPM（ONNX/Triton 替代 regex 分类） | `routing/ppm.py` | 16h |

### P1 — 增强功能

| 任务 | 文件 | 预估工时 |
|------|------|----------|
| Rust crate `zilli-rs` 实现（演化核心、loop 引擎） | `zilli-rs/` | 24h |
| 多租户支持（租户隔离的数据 + 配置 + 路由） | `routing/`, `configs/` | 16h |
| Dashboard 鉴权 + 实时监控 | `dashboard_app.py` | 4h |
| FeedbackEvaluator LLM-as-Judge 缓存 | `routing/feedback.py` | 2h |

### P2 — 优化

| 任务 | 文件 | 预估工时 |
|------|------|----------|
| PPM 缓存策略修复（LRU→popitem） | `routing/ppm.py` | 0.5h |
| 进化引擎并发处理（asyncio 并行进化多个 skill） | `evolution/` | 4h |
| 训练 Pipeline 断点续训支持 | `run_training.py` | 8h |
| 全量测试类型注解（pyright strict） | 全项目 | 8h |
| 补充集成测试（e2e route → execute → feedback → evolve） | `tests/` | 8h |

## 7. 发布检查清单

### Release v0.5.0 ✅ 已完成

- [x] GitHub Actions CI 绿色通过（765+ tests, ruff, pyright）
- [x] 贝叶斯 MetaEvaluator 替换 bias/variance
- [x] 合规报告导出 CLI (`zilli audit export`)
- [x] SOTA 硬约束 (max_sota_ratio)
- [x] DAG Mermaid 可视化
- [x] 版本号更新 0.4.0 → 0.5.0

### Release v0.6.0 候选

- [ ] PPM training 集成到完整反馈闭环
- [ ] LLM-as-Judge 评分在生产场景验证
- [ ] Harness 模式在真实技能库上运行验证
- [ ] 多租户支持
- [ ] Rust crate zilli-rs 实现

### Release v1.0.0 标准

- [ ] 端到端自进化闭环在生产环境运行 ≥ 7 天
- [ ] 模型化 PPM 替代 regex 分类器
- [ ] Rust 辅助库实现关键热路径
- [ ] 文档（教程 + 参考 + 如何做 + 架构解释）全部补齐
- [ ] 多租户支持
- [ ] 安全审计（隐私 + 鉴权 + 合规）通过
