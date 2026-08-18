# Zilli — 开发记录

## 项目概述

Zilli（原 Hermes-NG）是一个面向 AI 自主开发的下一代 Agent 工具工程方案。核心理念："AI 写 AI"、"评估即开发"、"从环境中来"、"从 Agent 到 RL"。

## 2026-05-14 开发记录

### 1. 代码审查与修复

对照 `Zilli工程文件.md` 完成代码审查，发现并修复了 8 个问题：

#### 结构性问题（高优先级）
- **实现在 `__init__.py`**：将 7 个包的实现代码从 `__init__.py` 移至对应模块文件（`mock_env.py`、`experience_replay.py`、`cispo.py`、`length_controller.py`、`verifiable_rewards.py`、`skill_evolution.py`、`continuous_learner.py`），`__init__.py` 仅做 re-export
- **CISPO_Trainer 两处定义**：统一在 `training/cispo.py`，删除 `training/__init__.py` 中的重复实现

#### 功能性问题（中优先级）
- **GAE 实现不完整**：修复 `compute_advantages()`，使用正确的蒙特卡洛回报计算；新增 `compute_gae_advantages()` 方法
- **进化引擎桩代码**：`_wrap_as_dspy_module()` 改为实际读取文件内容并提取函数名
- **持续学习空壳**：`_collect_production_trajectories()` 改为从 `production_data/*.json` 读取真实数据

#### 低优先级
- **CLI evaluate 不执行**：重写为使用 `runner.record_action()` + `runner.trajectory`
- **Scheduler task_id 冲突**：使用 `uuid.uuid4()` 替代硬编码字符串
- **GPU 配置过高**：`train_gpus` 从 256 降为 8，`inference_gpus` 从 512 降为 16

### 2. 品牌更名：Hermes-NG → Zilli

- Python 包：`hermes_ng/` → `zilli/`
- CLI 命令：`hermes-ng` → `zilli`，`hermes-evolve` → `zilli-evolve`
- 测试文件：`test_hermes_ng.py` → `test_zilli.py`
- 远程仓库：`github.com/iclawos/Hermes-NG.git` → `github.com/ethercoinai/Zilli.git`

### 3. 文档产出

- `NG对比.md` → `Zilli-Hermes对比.md`：Zilli 与 hermes-web-ui 对比分析
- `检查.md`：代码审查报告
- `检查报告.md`：初步审查问题清单（已全部修复）

## 项目结构

> 完整模块清单与文件数以 `docs/engineering-plan.md` §2.1（经核实与代码一致）为准。当前为 v1.0.0，38 个顶层条目。

```
zilli/                   # Python 包根目录
├── __init__.py          # 顶层导出（BaseAction 等）
├── cli.py               # CLI 入口（zilli，14 顶层子命令）
├── version.py           # 版本号（1.0.0）
├── run_training.py      # 训练主入口
├── dashboard_app.py     # Streamlit 管理台
├── soak.py              # zilli soak 持续运行器
├── tenancy.py           # TenantManager 多租户
├── core/                # Agent, TaskRunner
├── models/              # ModelBackend + Registry + Ollama/vLLM/llama.cpp
├── routing/             # RouteClassifier, LocalHybridRouter, MOMRouter, PPM, Feedback
├── evolution/           # SkillEvolutionEngine, DiversityController, cli
├── loops/               # LoopRunner, MetaLoopRunner, HarnessOrchestrator, Verifier, unknowns
├── training/            # RLTrainer, CISPO, GRPO, DistillationScheduler
├── envs/                # HermesSandbox, CostController, PlannerBudget
├── adaptive/            # DynamicSOTAScheduler, MultiObjectiveOptimizer
├── pipeline/            # EvolutionPipeline, EvolveToTrainPipeline
├── evaluation/          # MetaEvaluator, ExecutorOnlyEvaluator, DistillationBenchmark
├── fusion/ rewards/ schema/ data/ infra/
├── security/ privacy/ audit/ industry/
├── server/              # FastAPI app + routes（/v1/*）
├── workflow/            # CeleryDAGExecutor + CeleryApp
├── distillation/        # dsl.py（A/B/多轮实验 DSL）+ losses.py
├── hybrid/              # HybridExecutor, PrivacyGatekeeper
├── swe/                 # SWEAgent, sandbox, verifier
├── dag/ cache/ configs/ learner/ utils/
└── scripts/run_evolution.sh
```

## 构建与测试

```bash
# 安装
pip install -e .
pip install -e ".[train,dev]"  # 训练 + 开发依赖

# 运行测试（1105 tests）
python3 -m pytest tests/ -q

# 静态检查（0 errors）
ruff check .
pyright zilli/

# CLI
python3 -m zilli.cli --version
python3 -m zilli.cli list-tasks
python3 -m zilli.cli evaluate
python3 -m zilli.cli sandbox-test
python3 -m zilli.cli serve --host 127.0.0.1 --port 8900  # API 服务器
```

## 架构

Phase 1: 任务定义 → Phase 2: 轨迹数据 → Phase 3: RL 基础设施 → Phase 4: RL 训练 → Phase 5: 自动进化

## Today (2026-06-22)
- Wiki 技能（Obsidian LLM Wiki）+ Loop 技能（opencode loop-skill + Zilli loops 模块）已就绪
- **新项目约定**：规划阶段即纳入 loop 模式（process → verify → retry → escalate），不再事后补加

## 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| Schema 严格模式 | `extra="forbid"` | 确保 tool calling 类型安全 |
| 采样策略 | `golden_ratio=0.5` | 平衡正向和负向样本 |
| 长度自适应 | Earl 三重机制 | 防止上下文爆炸 |
| RL 算法 | CISPO + GRPO | 多轮 Agent 优化，MoE 稳定 |
| 优势估计 | 蒙特卡洛 + GAE | 支持无 Value Network 场景 |

## Health Stack

- lint: ruff check .
- test: pytest
