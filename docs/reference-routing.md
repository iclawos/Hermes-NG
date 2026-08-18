# Reference: Routing API

> **文档类型**: API 参考  
> **对应 PRD**: [MOM 元级系统](../prd.md#12-mom-元级系统meta-object-model)、[F-1 多模型平面路由](../prd.md#f-1-多模型平面路由)、[F-2 GPS-MOM 智能路由](../prd.md#f-2-gps-mom-智能路由)、[F-3 模型能力画像系统](../prd.md#f-3-模型能力画像系统)、[F-16 PPM 在线训练](../prd.md#f-16-ppm-在线训练)  
> **版本对齐**: PRD v2.1 / Zilli v1.0.0

---

## 目录

- [MOM 数据治理与路由](#mom-数据治理与路由)
- [RouteClassifier](#routeclassifier)
- [LocalHybridRouter](#localhybridrouter)
- [MOMRouter (GPS-MOM)](#momrouter-gps-mom)
- [PPMPredictor](#ppmpredictor)
- [ModelProfile](#modelprofile)
- [FeedbackCollector](#feedbackcollector)
- [StrategySelector](#strategyselector)
- [DynamicSOTAScheduler](#dynamicsotascheduler)
- [PrivacyGatekeeper](#privacygatekeeper)

---

## MOM 数据治理与路由

MOM（Meta-Object Model）路由不是简单的"选模型"，而是**数据敏感度 + 任务复杂度 + 预算状态**的三维决策。

### 数据分级驱动路由

```python
from zilli.privacy import PrivacyEngine, PrivacyGatekeeper
from zilli.routing import MOMRouter

# 第一步：数据治理（Layer 1）
engine = PrivacyEngine()
verdict = engine.evaluate("张三的电话是 13800138000，请分析消费习惯")

# 第二步：MOM 路由决策（Layer 2 + 3）
router = MOMRouter(ppm, profile, strategy, feedback)
decision = router.route(verdict.sanitized_text, context="analysis")
```

### 数据级别与路由策略映射

| 数据级别 | 本地模型 | 云端 SOTA | 脱敏 | 路由策略 |
|---------|---------|----------|------|---------|
| PUBLIC | ✅ 优先 | ✅ 可用 | 无需 | `CLOUD` |
| INTERNAL | ✅ 强制 | ❌ 禁止 | 无需 | `LOCAL` |
| CONFIDENTIAL | ✅ 优先 | ⚠️ 脱敏后 | 实体替换 | `LOCAL_WITH_CLOUD_FALLBACK` |
| RESTRICTED | ✅ 强制 | ❌ 禁止 | 必须 | `LOCAL` |
| REGULATED | ❌ 拒绝 | ❌ 拒绝 | — | `REJECTED` |

---

## RouteClassifier

```python
zilli.routing.RouteClassifier
```

将请求分类为 `FAST_LANE`（直接执行）或 `FULL_ROUTE`（Plan→Execute→Review）。

### 方法

| 方法 | 返回 | 说明 |
|------|------|------|
| `classify(request)` | `RouteDecision` | Regex + 可选 LLM 分类 |

### 分类逻辑

```
请求文本
  → Regex 模式匹配（关键词/长度/结构）
  → 置信度 < 0.8 ?
      → 调用 LLM 二次分类（ECONOMY 档位，降低成本）
      → 合并分数
  → RouteDecision(type=FAST_LANE | FULL_ROUTE, confidence, reason)
```

### 验收标准

- 简单请求（问候、闲聊）→ `FAST_LANE`，延迟 < 2s
- 复杂请求（代码、推理、多步）→ `FULL_ROUTE`
- 模式匹配准确率 > 80%
- LLM 回退调用率 < 20%（说明 Regex 覆盖足够）

---

## LocalHybridRouter

```python
zilli.routing.LocalHybridRouter(
    registry,      # ModelRegistry
    classifier,    # RouteClassifier
    config,        # ZilliConfig
    cache,         # CacheEngine
    planner_budget, # PlannerBudget
    mom_router,    # MOMRouter (optional)
)
```

三阶段混合路由器，集成脱敏、缓存、预算控制。

### 方法

| 方法 | 返回 | 说明 |
|------|------|------|
| `run(request, industry, force_full_route)` | `RouteResult` | 完整路由流水线 |
| `plan(request, industry)` | `str` | Planner 阶段：生成执行计划 |
| `execute(plan, request, industry)` | `str` | Executor 阶段：执行计划 |
| `review(plan, draft, request, industry)` | `str` | Reviewer 阶段：审查输出 |

### RouteResult 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `final_text` | `str` | 最终输出文本 |
| `route_type` | `str` | `fast_lane` / `full_route` |
| `decision` | `RouteDecision` | 分类决策详情 |
| `planner_result` | `str | None` | Plan 阶段输出（FULL_ROUTE 时） |
| `executor_result` | `str` | Execute 阶段输出 |
| `reviewer_result` | `str | None` | Review 阶段输出（FULL_ROUTE 时） |
| `total_duration_ms` | `float` | 端到端耗时（毫秒） |
| `error` | `str | None` | 错误信息（如有） |
| `data_residency` | `str` | `local` / `cloud` / `hybrid` |
| `sanitization_applied` | `bool` | 是否应用了 PII 脱敏 |

### 流水线细节（MOM 集成）

```
用户请求
  → InputSanitizer（PII 检测 + 脱敏）
  → PrivacyEngine.evaluate()（数据分级：PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED/REGULATED）
  → PrivacyGatekeeper.decide()
      → REGULATED → REJECTED（直接返回错误）
      → RESTRICTED/INTERNAL → LOCAL（强制本地模型）
      → CONFIDENTIAL → LOCAL_WITH_CLOUD_FALLBACK（本地优先，脱敏后可上云）
      → PUBLIC → CLOUD（无限制）
  → CacheEngine（LRU 缓存，命中则直接返回）
  → RouteClassifier（FAST_LANE / FULL_ROUTE）
  → [FAST_LANE] → Executor 直接生成
  → [FULL_ROUTE]
      → PlannerBudget.check()（是否超出 Planner 调用配额？）
      → plan() → 生成结构化计划（JSON/Markdown）
      → execute() → Executor 执行计划
      → review() → Reviewer 检查质量（可选）
  → OutputSanitizer（PII 回检）
  → EntityRestorer（占位符替换回原始值，如 [NAME] → 张三）
  → 返回 RouteResult
  → FeedbackCollector.record()（异步，不阻塞响应）
```

---

## MOMRouter (GPS-MOM)

```python
zilli.routing.mom_router.MOMRouter(
    ppm,              # PPMPredictor
    profile,          # ModelProfile
    strategy,         # StrategySelector
    feedback,         # FeedbackCollector
    budget_provider,  # CostController / PlannerBudget
    privacy_engine,   # PrivacyEngine（MOM Layer 1）
    train_every=200,  # 每 N 条反馈触发 PPM 训练
)
```

四步预测路由 + 数据治理：Privacy → PPM → Strategy → Profile → Selection。

### 方法

| 方法 | 返回 | 说明 |
|------|------|------|
| `route(text, context, privacy_verdict)` | `RouteDecision` | 预测模型选择（含数据驻留决策） |
| `record_feedback(...)` | `None` | 记录结果（自动触发 PPM 训练，每 `train_every` 条） |
| `train_ppm_from_feedback(records)` | `dict` | 手动触发 PPM 训练 |
| `update_profile_from_feedback(model_id, success, score)` | `None` | ELO + 能力向量更新 |
| `stats()` | `dict` | PPM + Profile + 训练计数器统计 |

### 路由决策流程（MOM 完整版）

```
用户文本 + 上下文 + PrivacyVerdict
  → [数据治理已处理]
      → REGULATED ? 直接拒绝
      → RESTRICTED/INTERNAL ? 强制本地模型池
      → CONFIDENTIAL ? 本地模型池 + 脱敏后云端候选
      → PUBLIC ? 全部模型池
  → PPMPredictor.predict()
      → 任务家族（6 类：chat/code/reasoning/analysis/creative/translation）
      → 难度评分（0.0 ~ 1.0）
      → 置信度（0.0 ~ 1.0）
  → StrategySelector.select(difficulty, budget_status, data_class)
      → ECONOMY（难度 < 0.3，预算紧张，或 INTERNAL/RESTRICTED）
      → STANDARD（难度 0.3~0.7，预算正常，或 CONFIDENTIAL）
      → ENHANCED（难度 > 0.7，预算充足，且 PUBLIC）
  → ModelProfile.filter(task_family, max_cost, min_success_rate, data_residency)
      → 本地模型（Ollama/vLLM/llama.cpp）：data_residency=local
      → 云端模型（OpenAI/Anthropic）：data_residency=cloud（仅 PUBLIC/CONFIDENTIAL 脱敏后）
  → ModelProfile.select_best(task_family, candidates)
      → Softmax Thompson 采样（探索 vs 利用）
  → RouteDecision(model_id, strategy, difficulty, confidence, data_residency, estimated_cost, estimated_latency)
```

### 反馈闭环（MOM 增强）

```python
# 每次路由后自动记录（异步，不阻塞）
mom_router.record_feedback(
    request_id="req-123",
    model_id="gpt-4-executor",
    predicted_difficulty=0.65,
    actual_difficulty=0.72,      # 由 LLM-as-Judge 或任务成功率推导
    predicted_family="code",
    actual_family="code",
    success=True,
    latency_ms=1200,
    cost_usd=0.015,
    data_class="CONFIDENTIAL",   # MOM 新增：数据级别
    sanitization_applied=True,   # MOM 新增：是否脱敏
    data_residency="cloud",      # MOM 新增：数据驻留
)

# 达到 train_every（默认 200）条时，自动触发 PPM 在线训练
# 权重偏移 > 5% 时自动清缓存
```

---

## PPMPredictor

```python
zilli.routing.PPMPredictor(
    cache_size=1000,      # LRU 缓存大小
    timeout_ms=10,        # 预测超时（Rust 热路径 0.054ms，留足余量）
    learning_rate=0.1,    # 在线训练学习率（EMA α）
    classifier=None,      # 外部分类器（SklearnONNXClassifier）
)
```

分类器链：训练模型（`ZILLI_PPM_MODEL` / `./models/ppm_model*.{joblib,onnx}`）→ RegexClassifier（零依赖）→ Rust 热路径（`zilli_hotpath` 安装时自动启用）。

### 方法

| 方法 | 返回 | 说明 |
|------|------|------|
| `predict(text, context)` | `PPMPrediction` | 难度 + 家族 + 置信度（LRU 缓存） |
| `train(records)` | `dict` | 从反馈记录在线更新权重 |
| `reset_training()` | `None` | 恢复出厂权重 |
| `stats()` | `dict` | 缓存命中率 + 权重分布 + 分类器名称 |

### PPMPrediction 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `difficulty` | `float` | 0.0 ~ 1.0，任务难度 |
| `family` | `str` | 任务家族（6 类之一） |
| `confidence` | `float` | 0.0 ~ 1.0，预测置信度 |
| `cache_hit` | `bool` | 是否命中 LRU 缓存 |
| `latency_ms` | `float` | 预测耗时 |

### 分类器优先级

```
1. SklearnONNXClassifier（`ppm` extra，acc 1.0 / RMSE 0.044）
2. RegexClassifier（零依赖，Python 实现）
3. Rust HotPath（`zilli-rs` + PyO3，0.054ms，功能一致性 100%）
```

> 安装模型化 PPM：`pip install zilli[ppm]`  
> 安装 Rust 加速：`pip install zilli[rust]`

---

## ModelProfile

```python
zilli.routing.ModelProfile(
    exploration_factor=0.1,  # Thompson 采样温度（越高越探索）
)
```

在线追踪模型成功率、5 维能力向量，支持加权 softmax 模型选择。

### 方法

| 方法 | 说明 |
|------|------|
| `register(entry)` | 注册新模型（冷启动：继承同系列先验，3 次调用后切实测值） |
| `unregister(model_id)` | 注销模型 |
| `update_success_rate(model_id, success)` | 更新成功率（EMA α=0.1） |
| `update_capability(model_id, scores)` | 更新 5 维能力向量（EMA α=0.3） |
| `filter(task_family, max_cost, min_success_rate, data_residency)` | 按家族 + 成本 + 成功率 + 数据驻留筛选候选 |
| `select_best(task_family, candidates)` | Softmax Thompson 采样选择最优 |

### 5 维能力向量

| 维度 | 说明 | 典型高能力模型 |
|------|------|--------------|
| `reasoning` | 逻辑推理、数学、分析 | GPT-4, Claude-3-Opus |
| `code` | 代码生成、调试、重构 | GPT-4, CodeLlama-70B |
| `creative` | 创意写作、头脑风暴 | Claude-3, GPT-4 |
| `analysis` | 数据分析、摘要、提取 | GPT-4, Gemini-1.5 |
| `multilingual` | 多语言理解、翻译 | GPT-4, DeepL API |

### 存储与持久化

- 存储格式：JSON 原子写入（tmp → replace）
- 多租户支持：自动添加 `tenant_{id}_` 前缀隔离
- 更新频率：每次反馈实时更新（内存），每 100 次批量持久化（磁盘）

---

## FeedbackCollector

```python
zilli.routing.FeedbackCollector(
    persist_path="./feedback.jsonl",  # JSONL 持久化路径
    batch_size=100,                   # 批量触发画像更新
    flush_interval_seconds=300,      # 最大刷新间隔（5 分钟）
)
```

异步队列 + JSONL 批量持久化。`record()` 达到 `batch_size` 时早触发 flush，避免数据丢失。

### 方法

| 方法 | 说明 |
|------|------|
| `record(feedback)` | 记录单条反馈（异步入队） |
| `flush()` | 强制刷盘（队列 → JSONL） |
| `get_stats()` | 队列长度、已持久化条数、平均延迟 |

### Feedback 数据结构（MOM 增强版）

```python
@dataclass
class FeedbackRecord:
    request_id: str
    model_id: str
    predicted_difficulty: float
    actual_difficulty: float
    predicted_family: str
    actual_family: str
    success: bool
    latency_ms: float
    cost_usd: float
    timestamp: float
    tenant_id: str | None = None
    # MOM 新增字段
    data_class: str | None = None          # PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED/REGULATED
    sanitization_applied: bool = False     # 是否脱敏
    data_residency: str | None = None      # local / cloud / hybrid
    route_policy: str | None = None        # LOCAL / CLOUD / LOCAL_WITH_CLOUD_FALLBACK / REJECTED
```

---

## StrategySelector

```python
zilli.routing.StrategySelector
```

三档策略选择器：基于难度 + 预算 + 租户配额 + **数据级别**。

### 策略档位

| 档位 | 条件 | 模型选择 | 成本特征 | 数据级别限制 |
|------|------|---------|---------|------------|
| **ECONOMY** | 难度 < 0.3 或预算紧张或 INTERNAL/RESTRICTED | cheapest 可用本地模型 | 最低成本 | 强制本地 |
| **STANDARD** | 难度 0.3~0.7 且预算正常，或 CONFIDENTIAL | 中等能力本地模型，脱敏后可选云端 | 平衡 | 本地优先 |
| **ENHANCED** | 难度 > 0.7 或预算充足，且 PUBLIC | SOTA 云端模型或混合 | 最高质量 | 云端可用 |

### 选择逻辑（MOM 增强）

```python
def select(difficulty: float, budget_status: BudgetStatus, data_class: DataClass) -> Strategy:
    # 数据级别硬约束
    if data_class in (DataClass.RESTRICTED, DataClass.INTERNAL):
        return Strategy.ECONOMY  # 强制本地，无论难度
    if data_class == DataClass.REGULATED:
        return Strategy.REJECTED  # 直接拒绝

    # 预算紧急模式
    if budget_status.remaining < budget_status.monthly * 0.1:
        return Strategy.ECONOMY  # 强制省钱

    # 难度 + 预算 + 数据级别综合决策
    if data_class == DataClass.CONFIDENTIAL:
        # 机密数据：本地优先，高难度时脱敏后上云
        if difficulty > 0.7 and budget_status.sota_ratio < 0.05:
            return Strategy.ENHANCED  # 脱敏后云端
        return Strategy.STANDARD  # 本地优先

    # PUBLIC 数据：正常难度-预算决策
    if difficulty > 0.7 and budget_status.sota_ratio < 0.05:
        return Strategy.ENHANCED
    if difficulty < 0.3:
        return Strategy.ECONOMY
    return Strategy.STANDARD
```

---

## DynamicSOTAScheduler

```python
zilli.adaptive.DynamicSOTAScheduler(
    monthly_budget_usd=1000.0,   # 月度预算
    cost_per_call=0.05,          # SOTA 单次调用成本
    max_sota_ratio=0.05,         # SOTA 硬约束：调用比例上限 5%
)
```

Thompson Sampling 阈值 bandit + 预算分层 + **硬封顶**。

### 方法

| 方法 | 返回 | 说明 |
|------|------|------|
| `should_call_sota(task_type, state, data_class)` | `bool` | 是否允许调用 SOTA（MOM 增强：数据级别检查） |
| `record_call(success, cost)` | `None` | 记录调用结果，更新 Thompson 采样参数 |
| `get_budget_status()` | `BudgetStatus` | 当前预算状态（剩余/已用/SOTA 比例） |

### 硬约束机制（MOM 增强）

```python
# 数据级别硬约束：RESTRICTED/INTERNAL/REGULATED 直接拒绝 SOTA
if data_class in (DataClass.RESTRICTED, DataClass.INTERNAL, DataClass.REGULATED):
    return False  # 无论任务难度多高，敏感数据不上云

# SOTA 调用比例硬约束
if sota_calls / total_calls >= max_sota_ratio:
    return False  # 比例超限，无论任务难度多高

# 软约束（预算/配额）继续生效
if remaining_budget < cost_per_call:
    return False  # 余额不足
```

### 预算状态

```python
@dataclass
class BudgetStatus:
    monthly_budget: float        # 月度总预算
    spent_this_month: float      # 本月已用
    remaining: float             # 剩余预算
    sota_calls: int              # SOTA 调用次数
    total_calls: int             # 总调用次数
    sota_ratio: float            # SOTA 比例（实时）
    emergency_mode: bool         # 是否触发紧急模式（余额 < 10%）
    local_calls: int             # MOM 新增：本地模型调用次数
    cloud_calls: int             # MOM 新增：云端模型调用次数
    data_residency_breakdown: dict  # MOM 新增：各数据级别调用次数
```

---

## PrivacyGatekeeper

```python
zilli.privacy.PrivacyGatekeeper
```

MOM Layer 1 的最终决策点：根据数据级别决定路由策略。

### 方法

| 方法 | 返回 | 说明 |
|------|------|------|
| `decide(verdict)` | `str` | `LOCAL` / `CLOUD` / `LOCAL_WITH_CLOUD_FALLBACK` / `REJECTED` |
| `decide_with_rationale(verdict)` | `dict` | 决策 + 理由 + 风险评分 |

### 决策矩阵

| 数据级别 | 决策 | 理由 | 风险评分 |
|---------|------|------|---------|
| PUBLIC | `CLOUD` | 公开数据，无隐私风险 | 0.0 |
| INTERNAL | `LOCAL` | 内部数据，禁止出境 | 0.1 |
| CONFIDENTIAL | `LOCAL_WITH_CLOUD_FALLBACK` | 机密数据，脱敏后可出境 | 0.3 |
| RESTRICTED | `LOCAL` | 受限数据，强制本地 | 0.5 |
| REGULATED | `REJECTED` | 监管数据，禁止处理 | 1.0 |

---

## 快速参考：MOM 路由决策时序

```
用户请求 (text + context + tenant_id)
        │
        ▼
[1] InputSanitizer ──→ PII 检测 + 脱敏
        │
        ▼
[2] PrivacyEngine.evaluate() ──→ 数据分级（PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED/REGULATED）
        │
        ▼
[3] PrivacyGatekeeper.decide() ──→ LOCAL / CLOUD / LOCAL_WITH_CLOUD_FALLBACK / REJECTED
        │ (REGULATED → 直接拒绝，返回错误)
        ▼
[4] CacheEngine ──→ 命中？→ 直接返回（延迟 < 1ms）
        │ 未命中
        ▼
[5] PPMPredictor.predict() ──→ difficulty + family + confidence
        │ (0.054ms ~ 2ms)
        ▼
[6] StrategySelector.select() ──→ ECONOMY / STANDARD / ENHANCED
        │ (结合 data_class + difficulty + budget)
        ▼
[7] DynamicSOTAScheduler.should_call_sota() ──→ 数据级别 + 硬约束检查
        │
        ▼
[8] ModelProfile.filter() ──→ 按 family + cost + success_rate + data_residency 筛选候选
        │ (RESTRICTED/INTERNAL → 仅本地模型；PUBLIC → 全部模型)
        ▼
[9] ModelProfile.select_best() ──→ Softmax Thompson 采样
        │
        ▼
[10] RouteClassifier ──→ FAST_LANE / FULL_ROUTE
        │
        ├── FAST_LANE ──→ Executor 直接生成（延迟 < 2s）
        └── FULL_ROUTE ──→ Plan → Execute → Review（延迟 < 8s）
                    │
                    ▼
[11] OutputSanitizer ──→ PII 回检
        │
        ▼
[12] EntityRestorer ──→ 占位符替换回原始值（[NAME] → 张三）
        │              （zilli.privacy.entities，支持 dict/list/JSON 嵌套结构，2026-08-18）
        │
        ▼
[13] FeedbackCollector.record() ──→ 异步反馈（不阻塞响应）
        │
        ▼
[14] 每 100 条 → ModelProfile 更新
[15] 每 200 条 → PPM 在线训练
```

---

> **相关文档**: [MOM 架构解释](explanation-architecture.md) | [入门教程](tutorial-getting-started.md) | [服务器与租户参考](reference-server-tenancy.md)
