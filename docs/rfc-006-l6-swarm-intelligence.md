# RFC-006: L6 群智能（Swarm Intelligence）设计

> **状态**: 草案（Draft）  
> **作者**: Zilli 工程团队  
> **日期**: 2026-08-19  
> **目标版本**: v2.0.0  
> **关联**: PRD v2.1（MOM 元级系统）、engineering-plan §6、`multi_agent.tasks.yaml`

---

## 1. 背景与动机

Zilli 已交付 L0–L5：

| 阶段 | 能力 | 现状 |
|------|------|------|
| L0–L4 | 单 Agent 执行、路由、进化、训练、治理 | ✅ v0.1–v0.5 |
| L5 | `zilli soak` 7×24 无人值守 | ✅ v1.0.0 |

**现状瓶颈**：所有能力都是**单 Agent 上下文**内完成的。一个任务无论多复杂，都由一个 Agent 在单个上下文窗口内 Plan→Execute→Review 完成。这导致：

1. **上下文墙**：复杂任务（跨 10+ 文件重构、企业级审计、多服务编排）超过单上下文容量，被迫截断或降级。
2. **单点能力上限**：执行质量取决于单一模型的单次生成，没有"多个专家"协作带来的交叉验证。
3. **无并行收益**：可并行分解的任务被串行执行，浪费时间与成本。
4. **无共识保障**：单 Agent 的幻觉无法被其他 Agent 校验，错误直接进入产出。

**L6 的目标**：把 Zilli 从"单个聪明的 Agent"升级为"一群协作的 Agent"——在 MOM 元级系统的调度下，多个专业化 Agent 通过**任务分解、Agent 间路由、共识机制**协作完成单 Agent 无法完成的任务。

---

## 2. 设计原则

| # | 原则 | 说明 |
|---|------|------|
| P1 | **MOM 为唯一调度者** | 群智能不引入独立调度器；复用 MOM 三层（治理→路由→执行反馈）做编排，保证安全/成本/质量边界不被绕过 |
| P2 | **角色专业化** | Agent 按角色分工（researcher / writer / architect / reviewer / verifier），每个角色工具受限、上下文聚焦 |
| P3 | **分工可验证** | 每次 Agent 间交接（handoff）必须携带结构化产物（schema 校验），交接失败可回滚重做 |
| P4 | **共识可仲裁** | 意见分歧走仲裁链：多数共识 → 权重投票 → 指定仲裁 Agent → 升级人工 |
| P5 | **成本可审计** | 每个子任务独立计费与审计，汇总进既有 `AuditLogger` / `CostController` |
| P6 | **向下兼容** | 单 Agent 路径完全保留；群智能仅在有"分解收益"时启用 |

---

## 3. 总体架构

```
┌────────────────────────────────────────────────────────────────────┐
│                        L6 群智能协调层（Swarm Orchestrator）          │
│                                                                    │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────────────┐    │
│  │ Task Decomposer│ → │ Agent Router │ → │ Consensus Engine    │    │
│  │ 任务分解       │    │ Agent 间路由  │    │ 共识与仲裁          │    │
│  └──────────────┘    └──────────────┘    └────────────────────┘    │
│         ↑ 复用了 MOM 的 PPM / ModelProfile / Strategy               │
└────────────────────────────────────────────────────────────────────┘
        │ 产物（Artifact Graph）
        ▼
┌────────────────────────────────────────────────────────────────────┐
│                     Agent 池（Swarm Pool）                          │
│                                                                    │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐     │
│  │Researcher│ │Architect│ │ Writer  │ │Verifier │ │Reviewer │ ... │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘     │
│     每个 Agent = 既有 Agent 类 + 角色约束（tools/context/prompt）     │
└────────────────────────────────────────────────────────────────────┘
```

### 3.1 与 MOM 的复用关系

| L6 组件 | 复用的 MOM 组件 | 说明 |
|---------|---------------|------|
| Agent Router | `PPMClassifier` + `ModelProfile` + `StrategySelector` | 子任务难度/家族 → 选择执行 Agent（及其底层模型） |
| 数据边界 | `PrivacyEngine` + `WorkflowRegistry` | 子任务同样经过数据分级与行业合规 |
| 反馈闭环 | `FeedbackCollector` + Champion-Challenger | 每个子任务结果计入画像，驱动后续调度 |
| 成本控制 | `CostController` | 子任务级计费汇总 |

---

## 4. 核心组件设计

### 4.1 Agent 间路由（Agent Router）

**问题**：任务分解后，如何决定"这个子任务交给哪个 Agent"？

**方案**：三阶段决策，复用 MOM 路由管线。

```
子任务 ──→ PPM 难度/家族分类 ──→ 角色匹配（Role Registry） ──→ Agent 选择
                                    │
                                    ├─ 需要外部信息？     → Researcher
                                    ├─ 需要设计决策？     → Architect
                                    ├─ 需要生成产物？     → Writer
                                    ├─ 需要代码/行为校验？→ Verifier
                                    └─ 需要人工复核？     → Reviewer
```

**角色注册表（Role Registry）**：

```python
@dataclass
class AgentRoleSpec:
    role: str                      # researcher / architect / writer / verifier / reviewer
    tools: list[str]               # 允许的工具白名单
    max_context: int               # 上下文预算
    model_profile: str             # 使用的模型画像槽位
    eval_criteria: list[str]       # 本角色产出如何被验证
    fallback_role: str = ""        # 可回退角色
```

**路由决策规则**：

1. **难度阈值**：PPM 判定 `difficulty > 0.7` 且 `family ∈ {coding, analysis, reasoning}` → 触发分解。
2. **工具需求**：任务工具需求超出单 Agent 工具集 → 必须分工。
3. **角色回退**：若某角色模型不可用，回退到其 `fallback_role`（如 writer → executor）。
4. **安全拦截**：RESTRICTED/REGULATED 数据绝不进入外部 Agent 上下文（复用 `PrivacyEngine`）。

### 4.2 任务分解（Task Decomposition）

**问题**：一个复杂任务如何拆成可并行、可验证、可合并的子任务？

**方案**：分层 DAG 分解 + 产物图（Artifact Graph）。

```
任务 ──→ Decomposer ──→ 子任务 DAG
                         │
         ┌───────────────┼────────────────┐
         ▼               ▼                ▼
    子任务 A          子任务 B          子任务 C
    （可并行）        （依赖 A）         （可并行）
         └───────┬───────┘
                 ▼
             子任务 D（合并）
```

**分解约束**：

| 约束 | 规则 |
|------|------|
| 扇出上限 | 单层最多 8 个子任务（控制上下文总量） |
| 依赖显式 | 子任务间依赖通过产物 ID 声明，无隐式共享状态 |
| 产物 schema | 每个子任务输出必须通过 `BaseModel` 校验（复用 `schema/actions.py` 严格模式） |
| 可并行性 | 无依赖的子任务标记 `parallel: true` |
| 可验证性 | 每个子任务至少 1 条 `eval_criteria` |

**分解策略**：Decomposer 由 PPM 分类驱动，给出分解建议；`SwarmOrchestrator` 校验分解合法性（依赖无环、产物 schema 完备）。

### 4.3 共识机制（Consensus Engine）

**问题**：多个 Agent 对同一决策或产物意见不一致时，如何收敛？

**方案**：四级共识链，从廉价到昂贵。

```
Level 1: 多数共识（Majority）
    N≥3 个 Agent 独立产出 → 投票 → 多数票胜出
    适用：事实性、可客观验证的决策

Level 2: 权重投票（Weighted Voting）
    每个 Agent 按其历史成功率（ModelProfile.success_rate）加权投票
    适用：意见分歧、无绝对正确解

Level 3: 指定仲裁（Arbiter）
    指定一个高可信 Agent（或更高 tier 模型）审查分歧并裁定
    适用：技术架构决策、安全敏感判断

Level 4: 升级人工（Human Escalation）
    仲裁仍分歧 / 涉及安全边界 → 生成结构化争议报告，暂停等待人工
    适用：RESTRICTED 数据处理、破坏性操作
```

**共识结果记录**：每次共识输出 `ConsensusRecord`（含各方意见、投票、理由、仲裁链路径），写入审计日志——满足 L4 可治理的回溯要求。

```python
@dataclass
class ConsensusRecord:
    topic: str
    options: list[str]
    votes: dict[str, float]        # option -> weighted score
    level: ConsensusLevel
    arbiter: str = ""
    human_escalated: bool = False
    resolution: str = ""
    reason: str = ""
    created_at: float = 0.0
```

### 4.4 产物图（Artifact Graph）

子任务交接的唯一通道是**产物**（非共享内存）。产物图是 DAG：

```python
@dataclass
class Artifact:
    id: str
    producer_role: str
    consumer_roles: list[str]
    schema: type[BaseModel]        # 严格校验
    payload: dict
    status: Literal["pending", "done", "rejected", "consumed"]
    created_at: float = 0.0
```

- 交接时消费者校验 `schema`，失败 → 产物标 `rejected` → 生产者重做（限 2 次）。
- 无消费者时产物可 GC（与 `cache/engine.py` 生命周期管理一致）。

---

## 5. 执行流程（端到端）

```
用户请求
   │
   ▼
[1] MOM 数据治理层（分级 + 脱敏）──── 安全拦截则拒绝
   │
   ▼
[2] PPM 难度评估 ── 单 Agent 可胜任？──→ 走既有 L0–L5 单 Agent 路径
   │                 （difficulty ≤ 0.7）
   ▼ 需要群智能
[3] Task Decomposer：子任务 DAG + 产物 schema
   │
   ▼
[4] Agent Router：为每个子任务分配角色与模型
   │
   ▼
[5] 并行/串行执行子任务（复用 Agent + HybridExecutor）
   │   每个子任务 → 产物校验 → 写 Artifact Graph
   ▼
[6] 子任务产出汇总 → 合并为最终产物
   │
   ▼
[7] Consensus Engine：对关键决策 / 冲突产物仲裁
   │
   ▼
[8] Verifier 全量校验最终产物 → 通过则交付
   │
   ▼
[9] 反馈闭环：每个子任务结果 → FeedbackCollector → 画像/PPM 更新
```

---

## 6. 数据模型（新增）

全部纳入 `zilli/swarm/` 包：

```
zilli/swarm/
├── __init__.py
├── orchestrator.py      # SwarmOrchestrator（主协调器）
├── decomposer.py        # TaskDecomposer + 子任务 DAG
├── router.py            # AgentRouter + AgentRoleSpec
├── consensus.py         # ConsensusEngine + ConsensusLevel + ConsensusRecord
├── artifacts.py         # ArtifactGraph + Artifact
└── roles.py             # 内置角色注册表（researcher/architect/writer/verifier/reviewer）
```

**核心接口**：

```python
class SwarmOrchestrator:
    async def execute(self, request: str, industry: str = "") -> SwarmResult:
        """分解 → 路由 → 执行 → 共识 → 验证 → 反馈。"""

class TaskDecomposer:
    async def decompose(self, task: str, ppm_family: str, difficulty: float) -> list[SubTask]:
        """返回子任务 DAG（含依赖、产物 schema、并行标记）。"""

class AgentRouter:
    async def assign(self, subtask: SubTask) -> tuple[AgentRoleSpec, ModelEntry]:
        """角色 + 模型选择。"""

class ConsensusEngine:
    async def reach(self, topic: str, options: list[str],
                    agents: list[Agent], level: ConsensusLevel) -> ConsensusRecord:
        """四级共识链。"""

class ArtifactGraph:
    def put(self, artifact: Artifact) -> None
    def get(self, artifact_id: str) -> Artifact | None
    def consumers_of(self, artifact_id: str) -> list[str]
```

---

## 7. 里程碑与验收

| 里程碑 | 内容 | 验收标准 |
|--------|------|---------|
| M1 角色与分解 | `SwarmOrchestrator` 骨架 + `TaskDecomposer` | 分解 DAG 无环、schema 校验通过、扇出 ≤8 |
| M2 路由与执行 | `AgentRouter` + 并行子任务执行 | `multi_agent_collaboration` 任务通过（researcher→writer 交接） |
| M3 共识机制 | `ConsensusEngine` 四级链 | 分歧场景 100% 收敛，Level4 记录审计 |
| M4 反馈闭环 | 子任务级画像更新 | 复用既有 FeedbackCollector，画像无回归 |
| M5 端到端 | `zilli swarm` CLI + 基准 | 群智能路径在 `multi_agent.tasks.yaml` 全量通过，成本 ≤ 单 Agent 1.5× |

**成功指标**：

| 指标 | 目标 |
|------|------|
| 复杂任务完成率 | 较单 Agent 提升 ≥ 20% |
| 交接成功率 | ≥ 95%（schema 校验通过率） |
| 共识收敛率 | ≥ 95%（无需人工升级） |
| 上下文利用率 | 单 Agent 平均上下文使用下降 ≥ 30% |
| 成本 | 不超过单 Agent 路径的 1.5× |

---

## 8. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 分解过度（碎片化） | 成本上升、协调开销大 | 难度阈值 + 扇出上限；单 Agent 路径完全保留 |
| 交接数据丢失/错误 | 产物质量下降 | schema 严格校验 + 失败重做（≤2 次）+ 回滚 |
| 共识永远达不成 | 任务卡死 | 超时（默认 60s/级）+ Level4 人工升级 |
| 外部 Agent 上下文越权 | 数据泄露 | 每个子任务独立走 `PrivacyEngine`；RESTRICTED/REGULATED 强制本地 |
| 审计爆炸 | 日志膨胀 | 共识只记录最终记录 + 分歧摘要，不记录中间 token 流 |

---

## 9. 决策记录（ADR）

| 决策 | 选项 | 选择 | 理由 |
|------|------|------|------|
| 协调者 | 独立 Swarm 引擎 vs 复用 MOM | 复用 MOM | 安全/成本/审计边界不被绕过；工程量减半 |
| 通信方式 | 共享内存 vs 产物图 | 产物图（DAG） | 可校验、可回滚、可并行、可审计 |
| 共识链 | 固定规则 vs 可配置 | 四级链可配置 | 事实性任务走快速多数，安全任务走仲裁 |
| 角色模型 | 每角色独立模型 vs 共享模型池 | 共享模型池 | 复用 ModelProfile，Champion-Challenger 统一管理 |

---

## 10. 附录

- 关联任务：`zilli/tasks/benchmark/multi_agent.tasks.yaml`（首个群智能基准）
- 关联 PRD 章节：§1.2 MOM 元级系统、L6 路线图
- 复用模块：`routing/mom_router.py`、`routing/ppm_classifier.py`、`routing/profile.py`、`hybrid/executor.py`、`swe/agent.py`、`data/experience_replay.py`