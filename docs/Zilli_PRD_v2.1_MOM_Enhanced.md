# Zilli — 产品需求文档（PRD v2.0）

> **版本**: v2.0  
> **状态**: 生产就绪（v1.0.0）  
> **核心理念**: MOM 元级人工智能系统 —— 面向 AI 自主开发的下一代工具工程平台，融合群体智能调度与企业级隐私治理。  
> **信条**: "AI 写 AI"、"评估即开发"、"从环境中来"、"从 Agent 到 RL"。

---

## 目录

1. [产品概述](#1-产品概述)
2. [系统架构与核心飞轮](#2-系统架构与核心飞轮)
3. [用户旅程与场景](#3-用户旅程与场景)
4. [功能需求](#4-功能需求)
   - 4.1 [执行层：智能路由与任务调度](#41-执行层智能路由与任务调度)
   - 4.2 [评估层：质量判定与元评估](#42-评估层质量判定与元评估)
   - 4.3 [进化层：自我改进与技能生长](#43-进化层自我改进与技能生长)
   - 4.4 [学习层：RL 训练与知识蒸馏](#44-学习层rl-训练与知识蒸馏)
   - 4.5 [治理层：成本、隐私与合规](#45-治理层成本隐私与合规)
   - 4.6 [基础设施层：API、分布式与存储](#46-基础设施层api分布式与存储)
   - 4.7 [环境反馈与持续学习](#47-环境反馈与持续学习)
5. [非功能需求：平台承诺（SLA）](#5-非功能需求平台承诺sla)
6. [路线图：能力成熟度阶梯](#6-路线图能力成熟度阶梯)
7. [依赖分析](#7-依赖分析)
8. [附录](#8-附录)

---

## 1. 产品概述

### 1.1 愿景

Zilli（原 Hermes-NG）相信：**最好的 Agent 不是被人类写出来的，而是从执行轨迹、失败反思和环境反馈中生长出来的。**

我们的目标不是替代开发者，而是创造一个能 7×24 小时自我改进的"数字同事"——它不仅能执行任务，还能从每一次执行中学习、进化自身技能、优化路由决策，并在持续反馈中收敛到最优行为。

### 1.2 MOM 元级系统（Meta-Object Model）

MOM 是 Zilli 的**元级人工智能系统**——它不是直接处理用户请求的"模型"，而是**管理模型的模型**（Model of Models）。MOM 的核心理念：

> **让合适的数据，在合适的安全级别，由合适的模型处理。**

#### 为什么需要 MOM？

企业部署 AI 面临两大核心矛盾：

| 矛盾 | 传统方案 | MOM 解法 |
|------|---------|---------|
| **数据安全 vs 模型能力** | 全部上云 → 数据泄露风险；全部本地 → 能力受限 | **数据分级 + 隐私路由**：敏感数据本地处理，脱敏后复杂任务上云 |
| **成本控制 vs 任务质量** | 全部用 SOTA → 成本爆炸；全部用本地 → 质量不足 | **PPM 预测 + 策略选择**：简单任务本地经济模型，复杂任务按需调用云端 SOTA |

#### MOM 三层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    MOM 元级系统（Meta-Object Model）              │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Layer 1: 数据治理层（Data Governance）                  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │   │
│  │  │ PII 检测    │→│ 数据分级    │→│ 脱敏/隔离策略   │   │   │
│  │  │ 3 级过滤    │  │ 5 级分类    │  │ LOCAL/CLOUD/    │   │   │
│  │  │             │  │             │  │ REJECTED       │   │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Layer 2: 智能路由层（Intelligent Routing）              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │   │
│  │  │ PPM 预测    │→│ 策略选择    │→│ 模型画像选择    │   │   │
│  │  │ 难度/家族   │  │ ECONOMY/    │  │ 本地模型 /      │   │   │
│  │  │             │  │ STANDARD/   │  │ 云端 SOTA /     │   │   │
│  │  │             │  │ ENHANCED    │  │ 混合组合        │   │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Layer 3: 执行与反馈层（Execution & Feedback）             │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │   │
│  │  │ 本地执行    │  │ 云端执行    │  │ 反馈闭环        │   │   │
│  │  │ 零数据出境  │  │ 脱敏后出境  │  │ 画像更新 /      │   │   │
│  │  │ 延迟 < 2s   │  │ 质量优先    │  │ PPM 训练        │   │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 数据分级与路由策略

MOM 的核心是**数据驱动的路由决策**——不是"一刀切"地上云或本地，而是根据数据敏感度 + 任务复杂度，动态选择最优执行路径：

| 数据级别 | 敏感度 | 本地模型 | 云端 SOTA | 脱敏要求 | 典型场景 |
|---------|--------|---------|----------|---------|---------|
| **PUBLIC** | 公开 | ✅ 优先 | ✅ 可用 | 无需 | 产品文档、公开 API 查询 |
| **INTERNAL** | 内部 | ✅ 强制 | ❌ 禁止 | 无需 | 内部邮件、会议纪要摘要 |
| **CONFIDENTIAL** | 机密 | ✅ 优先 | ⚠️ 脱敏后 | 实体替换 | 客户名单分析、财务数据 |
| **RESTRICTED** | 受限 | ✅ 强制 | ❌ 禁止 | 必须 | 员工档案、合同条款 |
| **REGULATED** | 监管 | ❌ 拒绝 | ❌ 拒绝 | — | PHI（医疗）、PCI（支付）、学生记录 |

#### 成本-安全-质量的帕累托最优

MOM 通过三层控制实现**帕累托最优**（在不牺牲安全的前提下最大化质量，在不牺牲质量的前提下最小化成本）：

```
        质量（Quality）
            ↑
   SOTA 云端  │  ● 复杂任务 + 公开数据
   （ENHANCED）│
            │     ● 复杂任务 + 脱敏数据
   混合策略  │
（STANDARD）  │        ● 简单任务 + 内部数据
            │
   本地模型  │  ● 简单任务 + 本地强制
  （ECONOMY）│
            └────────────────→ 成本（Cost）

   安全边界（Security Boundary）：
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   RESTRICTED/REGULATED 数据 → 强制本地或拒绝
   CONFIDENTIAL 数据 → 脱敏后可选云端
   INTERNAL 数据 → 强制本地
   PUBLIC 数据 → 无限制
```

#### MOM 的自我进化

MOM 不仅是静态路由规则，而是**从执行反馈中持续学习**的元级系统：

1. **PPM 在线训练**：每次路由决策后，对比预测难度 vs 实际难度，调整权重
2. **模型画像 EMA**：每次调用后更新模型成功率、能力向量，让"选择"越来越准
3. **反馈闭环**：100 条反馈触发画像更新，200 条触发 PPM 重新训练
4. **Champion-Challenger**：新模型/新策略必须通过统计检验才能替换旧策略

> **结果**：MOM 越用越聪明——它知道什么任务该用本地模型省钱，什么任务该脱敏后上云求质量，什么任务必须拒绝以保护数据。


### 1.3 核心飞轮

Zilli 的终极形态是一个**自我运转的进化飞轮**：

```
┌─────────────────────────────────────────────────────────────┐
│                     ZILLI 核心飞轮                            │
│                                                              │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│   │  执行    │───→│  评估    │───→│  进化    │              │
│   │ Execute  │    │ Evaluate │    │ Evolve   │              │
│   └──────────┘    └──────────┘    └──────────┘              │
│        ↑                              │                      │
│        └────────── 学习 ←─────────────┘                      │
│                                                              │
│   支撑层: 路由(PPM) | 隐私 | 成本 | 多租户 | 向量存储          │
└─────────────────────────────────────────────────────────────┘
```

- **执行（Execute）**：GPS-MOM 智能路由选择最优模型组合，完成任务交付
- **评估（Evaluate）**：LLM-as-Judge + 贝叶斯元评估 + Champion-Challenger 统计检验，判定输出质量
- **进化（Evolve）**：Skill 自进化引擎 + Self-Harness 元循环，从失败中提取改进方案
- **学习（Learn）**：RL 训练（CISPO/GRPO）+ 知识蒸馏，将经验转化为策略参数

### 1.4 核心能力矩阵

| 能力 | 状态 | 说明 | 进化关系 |
|------|------|------|---------|
| 多模型路由（Plan→Execute→Review） | ✅ 生产就绪 | 三阶段混合路由 + 行业合规路由 | 为 PPM 提供训练数据 |
| GPS-MOM 预测路由 | ✅ 生产就绪 | PPM + 三档策略 + 模型画像 + 反馈闭环 | 依赖 FeedbackCollector 闭环 |
| 模型化 PPM 分类器 | ✅ 生产就绪 | RegexClassifier 零依赖 + SklearnONNXClassifier（`ppm` extra） | 路由决策的前置大脑 |
| 贝叶斯元评估 | ✅ v0.5.0 新增 | 高斯共轭先验更新，替代 bias/variance 简单统计 | 为进化提供可信信号 |
| RL 训练（CISPO/GRPO） | ✅ 生产就绪 | 策略优化 + 优势估计 + 批量训练 + 断点续训 | 消耗进化产生的轨迹 |
| 技能自进化 | ✅ 生产就绪 | 4 策略 + 多样性控制 + MOM 反馈闭环 + 异步并发 | 输出到 Loop 验证 |
| Loop 循环引擎 | ✅ 生产就绪 | 重试 → 验证 → 修正 → 升级 | 进化方案的验证沙盒 |
| 自适应 Self-Harness | ✅ 生产就绪 | 弱点挖掘 → 有界提案 → 分体验证 | 元级进化触发器 |
| 未知项发现（Fable 方法） | ✅ v0.5.0 新增 | 盲点扫描 → 面试问题 → 实现笔记 → 测验 | 发现进化盲区 |
| 知识蒸馏 | ✅ 生产就绪 | BC + KL + RL + Embedding 正则化 | 教师→学生能力迁移 |
| Champion-Challenger Arena | ✅ 生产就绪 | 统计显著性检验的模型擂台 | 进化成果的准入门槛 |
| 端到端进化训练管线 | ✅ 生产就绪 | EvolveToTrainPipeline：Evolve → Train → Deploy → Monitor | 全自动进化闭环 |
| 预算/成本控制 | ✅ 生产就绪 | DynamicSOTA + 频率控制器 + 月度预算 + SOTA 硬约束 | 进化的经济约束 |
| 隐私合规 | ✅ 生产就绪 | PII 检测、脱敏、审计日志、数据隔离 | 企业部署的准入条件 |
| 合规报告导出 CLI | ✅ v0.5.0 新增 | `zilli audit export --framework gdpr\|hipaa\|soc2\|...` | 审计的可交付物 |
| Streamlit 管理台 | ✅ 生产就绪 | 登录鉴权（admin/viewer 角色）、审计浏览、成本监控、PPM Stats、自动刷新 | 运维可视化 |
| API 服务器 | ✅ 生产就绪 | FastAPI，OpenAI 兼容接口；fail-closed 鉴权 | 生产集成入口 |
| Celery 分布式工作流 | ✅ 生产就绪 | DAG 持久化执行、任务重试、结果回调 | 大规模任务编排 |
| ChromaDB 向量存储 | ✅ 生产就绪 | 语义检索、元数据过滤、集合管理 | 经验回放与检索 |
| 行业工作流 | ✅ 生产就绪 | 法律/医疗/金融/教育合规路由 | 垂直场景适配 |
| SWE-bench 修复 | ✅ 生产就绪 | Bug 复现 → 探索 → 诊断 → 修复 → 验证 | 工程能力基准 |
| DAG 可视化 | ✅ v0.5.0 新增 | `TaskDAG.to_mermaid()` 流程图导出 | 可观测性增强 |
| CI/CD | ✅ v0.5.0 新增 | GitHub Actions：lint + pyright typecheck + 多版本测试 | 质量门禁 |
| Rust 辅助库 | ✅ v1.0.0 生产就绪 | `zilli-rs` 热路径（PPM 预测 + 代码指纹），PyO3 绑定 `zilli_hotpath`（0.054ms） | 性能关键路径 |
| 多租户支持 | ✅ v1.0.0 生产就绪 | TenantManager YAML 持久化 + /v1/tenants 端点 + 数据命名空间隔离 | SaaS 化基础 |
| 端到端持续运行器 | ✅ v1.0.0 生产就绪 | `zilli soak` 健康监控 + 崩溃恢复 + 指标落盘 | 无人值守保障 |

---

## 2. 系统架构与核心飞轮

### 2.1 MOM 元级架构

MOM（Meta-Object Model）是 Zilli 区别于普通 Agent 框架的核心设计。它不是"一个更聪明的模型"，而是**管理所有模型的元级系统**——包括本地模型、云端模型、甚至模型之间的协作方式。

#### MOM 的元级特性

| 特性 | 普通 Agent 框架 | Zilli MOM |
|------|---------------|-----------|
| 模型选择 | 固定配置（如"用 GPT-4"） | 动态预测 + 数据分级驱动 |
| 数据安全 | 手动开关（全局上云/本地） | 自动分级 + 脱敏 + 路由 |
| 成本控制 | 预算告警（事后） | 实时预测 + 硬约束（事前） |
| 能力进化 | 人工升级 prompt/模型 | 自动从反馈中学习最优策略 |
| 多租户 | 共享实例（数据混用） | 命名空间隔离 + 独立画像 |

#### MOM 数据流：从请求到执行的完整链路

```
用户请求（含原始数据）
        │
        ▼
[Layer 1: 数据治理]
  ├── InputSanitizer（PII 检测 Level 1）
  │     → 命中关键词？→ 脱敏（姓名→[NAME]）
  ├── PrivacyEngine.evaluate()（Level 2 + Level 3）
  │     → 数据分类：PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED / REGULATED
  ├── PrivacyGatekeeper.decide()
  │     → REGULATED → REJECTED（直接拒绝，返回错误）
  │     → RESTRICTED → LOCAL（强制本地模型）
  │     → INTERNAL → LOCAL（强制本地模型）
  │     → CONFIDENTIAL → LOCAL_WITH_CLOUD_FALLBACK（本地优先，脱敏后可上云）
  │     → PUBLIC → CLOUD（无限制）
  └── 脱敏后的请求文本（若需上云）
        │
        ▼
[Layer 2: 智能路由]
  ├── PPMPredictor.predict()
  │     → 任务家族（chat/code/reasoning/analysis/creative/translation）
  │     → 难度评分（0.0 ~ 1.0）
  │     → 置信度（0.0 ~ 1.0）
  ├── StrategySelector.select()
  │     → 结合数据分类 + 难度 + 预算
  │     → ECONOMY（本地优先）/ STANDARD（平衡）/ ENHANCED（云端 SOTA）
  ├── ModelProfile.filter()
  │     → 按家族 + 成本 + 成功率筛选候选模型
  │     → 本地模型（Ollama/vLLM/llama.cpp）+ 云端模型（OpenAI/Anthropic）
  └── ModelProfile.select_best()
        → Softmax Thompson 采样（探索 vs 利用）
        → RouteDecision（model_id, strategy, route_type, estimated_cost, estimated_latency）
        │
        ▼
[Layer 3: 执行与反馈]
  ├── [本地执行路径]
  │     → LocalHybridRouter.run() → FAST_LANE / FULL_ROUTE
  │     → 本地模型生成（零数据出境）
  │     → OutputSanitizer（PII 回检）
  │     → 返回响应
  ├── [云端执行路径]
  │     → 数据已脱敏（PII 替换为占位符）
  │     → 云端 SOTA 模型生成
  │     → 响应中的占位符替换回原始值（本地处理）
  │     → 返回响应
  └── [反馈闭环]
        → FeedbackCollector.record()（异步，不阻塞）
        → ModelProfile.update_success_rate()（实时）
        → 每 100 条 → 画像 EMA 更新
        → 每 200 条 → PPM 在线训练
        → 权重偏移 > 5% → 自动清缓存
```

#### MOM 的本地-云端混合执行

```
┌─────────────────────────────────────────────────────────────┐
│                     企业内网（本地）                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ 用户请求 │→│ PII 检测 │→│ 数据分级 │→│ 本地模型 │  │
│  │          │  │ 3 级过滤 │  │ 5 级分类 │  │ Ollama   │  │
│  │          │  │          │  │          │  │ vLLM     │  │
│  │          │  │          │  │          │  │ llama.cpp│  │
│  └──────────┘  └──────────┘  └──────────┘  └────┬─────┘  │
│                                                  │         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐       │         │
│  │ 响应脱敏 │←│ 占位符   │←│ 本地处理 │←─────┘         │
│  │ 回检     │  │ 替换     │  │ 结果合并 │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
│                              ↑                              │
│                              │ 云端响应（脱敏数据）          │
│                    ┌─────────┴─────────┐                   │
│                    │   互联网（脱敏）   │                   │
│                    └─────────┬─────────┘                   │
│                              ↓                              │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                   云端 SOTA 模型                       │  │
│  │  （OpenAI GPT-4 / Anthropic Claude / Google Gemini）  │  │
│  │  输入：脱敏后的请求（无 PII）                        │  │
│  │  输出：脱敏后的响应（占位符）                        │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

#### MOM 的成本-安全权衡公式

MOM 的决策可以形式化为一个**约束优化问题**：

```
最大化:    Quality(model, task) × Safety(data, route)
约束:      Cost(total) ≤ Budget(monthly)
           SOTA_Ratio ≤ max_sota_ratio (硬约束 5%)
           Data_Class(data) ≤ Route_Max_Class(route)

其中:
  Quality(model, task) = ModelProfile.capability[model][task_family] × success_rate[model]
  Safety(data, route) = 1 - (data_sensitivity × route_risk)
  Cost(total) = Σ calls[model] × cost_per_call[model]
```

**求解方式**：PPM 预测 + 策略选择 + Thompson 采样 → 近似最优解（毫秒级）。


### 2.2 架构分层

```
┌─────────────────────────────────────────────────────────────┐
│                      应用层（Application）                     │
│  Streamlit Dashboard  │  CLI (`zilli *`)  │  OpenAI API     │
├─────────────────────────────────────────────────────────────┤
│                      编排层（Orchestration）                 │
│  MOMRouter  │  LoopRunner  │  Celery DAG  │  TaskDAG        │
├─────────────────────────────────────────────────────────────┤
│                      进化层（Evolution）                      │
│  SkillEvolutionEngine  │  Self-Harness  │  ContextCurator  │
│  UnknownsDiscovery     │  DiversityCtrl │  ChampionArena   │
├─────────────────────────────────────────────────────────────┤
│                      学习层（Learning）                       │
│  CISPO Trainer  │  GRPO Trainer  │  KnowledgeDistiller     │
│  PPM Online Training  │  TrajectoryStore  │  ExperienceReplay │
├─────────────────────────────────────────────────────────────┤
│                      评估层（Evaluation）                     │
│  LLM-as-Judge  │  BayesianMetaEvaluator  │  WeaknessMiner  │
├─────────────────────────────────────────────────────────────┤
│                      路由层（Routing）                        │
│  PPM (Regex + ONNX + Rust)  │  StrategySelector           │
│  ModelProfile (5D + EMA)  │  FeedbackCollector          │
├─────────────────────────────────────────────────────────────┤
│                      治理层（Governance）                      │
│  PrivacyEngine  │  CostController  │  AuditLogger         │
│  TenantManager  │  InputSanitizer  │  WorkflowRegistry    │
├─────────────────────────────────────────────────────────────┤
│                      存储层（Storage）                        │
│  ChromaDB (Vector)  │  JSONL (Trajectory)  │  YAML (Config) │
├─────────────────────────────────────────────────────────────┤
│                      运行时（Runtime）                        │
│  FastAPI  │  Celery + Redis  │  PyO3 (zilli-rs)          │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 数据流与反馈闭环

```
用户请求 → [PPM 分类] → [策略选择] → [模型画像] → [模型调用]
              ↓              ↓              ↓              ↓
         难度评分      预算/质量权衡    Thompson采样    执行轨迹
              └──────────────┴──────────────┴──────────────┘
                             ↓
                    [LLM-as-Judge / 贝叶斯评估]
                             ↓
                    [FeedbackCollector] ──→ 100条触发批量更新
                             ↓
              ┌──────────────┼──────────────┐
              ↓              ↓              ↓
         [PPM训练]    [模型画像EMA]    [轨迹存储]
              ↓              ↓              ↓
         权重偏移      能力向量更新    经验回放池
              └──────────────┴──────────────┘
                             ↓
              ┌──────────────┼──────────────┐
              ↓              ↓              ↓
         [RL训练]      [知识蒸馏]      [技能进化]
         CISPO/GRPO   教师→学生      4策略+多样性
              └──────────────┴──────────────┘
                             ↓
                    [Champion-Challenger Arena]
                             ↓
                    统计显著？→ 合并 / 回滚
                             ↓
                    [Loop 验证] → [Self-Harness]
                             ↓
                         新 Skill 上线
```

---

## 3. 用户旅程与场景

### 3.1 AI Agent 开发者

| 阶段 | 痛点 | ZILLI 解法 | 对应能力 |
|------|------|-----------|---------|
| **Day 0 原型** | 不知道选什么模型，每次都要手动调参 | PPM 自动分类任务家族 + StrategySelector 自动选择 ECONOMY/STANDARD/ENHANCED 档位 | F-2 GPS-MOM |
| **Day 3 调试** | Agent 反复在同类任务上失败，手动修 prompt 治标不治本 | WeaknessMiner 聚类失败模式 → Self-Harness 自动生成测试集 → Skill 进化引擎产出改进 PR | F-9 Self-Harness, F-7 技能进化 |
| **Day 7 迭代** | 新模型出来了，不知道是否比当前模型好 | Champion-Challenger Arena 自动对决，统计显著性检验（min_win_gap=0.05）判定是否升级 | F-6 Champion-Challenger |
| **Day 30 生产** | 成本爆炸，月度预算超支；合规审计不通过 | DynamicSOTA 硬约束（max_sota_ratio=0.05）+ 隐私引擎 PII 检测 + 一键导出合规报告 | F-12 成本控制, F-13 隐私合规, F-21 合规报告 |

### 3.2 RL 工程师

| 阶段 | 痛点 | ZILLI 解法 | 对应能力 |
|------|------|-----------|---------|
| **训练阶段** | 策略不收敛，Value Network 在简单场景反而拖后腿 | CISPO（Conservative Importance Sampling）+ GRPO（Group Relative Policy Optimization，无 Value Network）双算法支持 | F-4 RL 训练 |
| **数据阶段** | 高质量轨迹太少，冷启动困难 | 混合采样（golden_ratio=0.5）+ 经验回放 + 知识蒸馏从 Planner 向 Executor 迁移能力 | F-5 知识蒸馏 |
| **评估阶段** | 奖励函数设计主观，难以量化策略改进 | LLM-as-Judge 自动评分（0~1）+ 贝叶斯元评估提供小样本下的可信误差估计 | F-17 LLM-as-Judge, F-18 贝叶斯评估 |

### 3.3 研究科学家

| 阶段 | 痛点 | ZILLI 解法 | 对应能力 |
|------|------|-----------|---------|
| **探索阶段** | 想研究 Agent 自我改进机制，但缺乏标准化实验平台 | 端到端进化训练管线（EvolveToTrainPipeline）+ 未知项发现（Fable 方法）暴露系统盲区 | F-11 ACE, F-19 未知项发现 |
| **验证阶段** | 改进方案难以复现，缺乏控制变量 | Loop 循环引擎提供通用 Retry→Verify→Correct 框架，支持 5 种验证器 + 3 种触发器 | F-8 Loop 引擎 |
| **发表阶段** | 需要可解释的决策过程，而非黑盒 | DAG 可视化（Mermaid 导出）+ 审计日志完整记录路由决策、模型调用、评估结果 | F-22 DAG 可视化, F-13 审计日志 |

### 3.4 企业部署

#### 通用场景

| 阶段 | 痛点 | ZILLI 解法 | 对应能力 |
|------|------|-----------|---------|
| **接入阶段** | 需要行业合规（HIPAA/SOX/FERPA），担心数据泄露 | 行业工作流（法律/医疗/金融/教育）+ PII 3 级检测 + 数据脱敏 + 输入隔离 | F-13 隐私合规, F-15 行业工作流 |
| **运维阶段** | 多团队共用，需要数据隔离和成本分摊 | 多租户支持（TenantManager YAML 持久化 + 命名空间隔离）+ 租户级预算控制 | F-24 多租户, F-12 成本控制 |
| **审计阶段** | 监管要求提供完整数据处理记录 | 审计日志 JSONL 持久化 + `zilli audit export` 一键导出 GDPR/HIPAA/SOC2 报告 | F-21 合规报告 |

#### 医疗行业（HIPAA / HITRUST）

| 场景 | 数据类型 | 合规要求 | MOM 路由策略 | 典型任务 |
|------|---------|---------|------------|---------|
| **电子病历摘要** | PHI（患者姓名、病历号、诊断、处方） | HIPAA 最小必要原则、审计追踪、BAA 协议 | `REGULATED` → **拒绝**（除非本地部署 + 本地模型） | 医生口述转病历摘要 |
| **医学影像报告生成** | 影像元数据（患者 ID、检查日期）+ 影像本身 | HIPAA 安全规则（加密、访问控制）、HITECH 违规通知 | `RESTRICTED` → **本地模型**强制；影像元数据脱敏后可选云端增强 | CT/MRI 报告自动撰写 |
| **药物相互作用查询** | 药物名称（非患者关联） | FDA 21 CFR Part 11（电子记录完整性） | `PUBLIC` → **云端**可用（药物知识库属公开信息） | 查询阿司匹林与华法林相互作用 |
| **临床决策支持** | 去标识化患者数据（年龄区间、性别、症状） | HIPAA 去标识化安全港（Safe Harbor，18 项标识符移除） | `CONFIDENTIAL` → **脱敏后云端**（年龄区间化、症状泛化） | 基于症状推荐检查方案 |
| **医保理赔审核** | 理赔金额、诊断代码（ICD-10）、Provider NPI | CMS 合规、SOX 财务控制 | `INTERNAL` → **本地模型**（财务数据不出境） | 自动审核理赔合理性 |

**医疗行业 MOM 决策示例**:

```
医生输入: "患者张三，男，65岁，病历号20240818001，
          主诉胸痛3小时，既往高血压、糖尿病，
          查体BP 160/100，心电图ST段抬高，
          请生成入院记录和初步诊断"

→ InputSanitizer: 检测到 PHI（姓名、病历号、具体年龄、诊断）
→ PrivacyEngine.evaluate(): 
   - 姓名 → [NAME]（Level 1 关键词）
   - 病历号 → [MRN]（Level 2 正则）
   - 具体年龄 "65岁" → 年龄区间 "60-70岁"（Level 3 NER + 泛化）
   - 诊断 "高血压、糖尿病" → 保留（医学术语，非直接标识符）
→ DataClassifier: `CONFIDENTIAL`（含 PHI，但已脱敏）
→ PrivacyGatekeeper.decide(): `LOCAL_WITH_CLOUD_FALLBACK`
   - 本地模型优先生成基础记录
   - 复杂诊断推理部分 → 脱敏后云端 SOTA（ST 段抬高 → 急性心梗？）
→ 响应回替: 占位符替换回原始值（仅本地处理）
→ AuditLogger: 记录完整 PHI 检测日志、脱敏操作、路由决策（HIPAA 审计要求）
```

#### 金融行业（SOX / PCI-DSS / GDPR）

| 场景 | 数据类型 | 合规要求 | MOM 路由策略 | 典型任务 |
|------|---------|---------|------------|---------|
| **客户投资建议生成** | 客户资产组合、风险偏好、收入区间 | SEC 投资顾问法、SOX 财务控制、GDPR 数据处理 | `CONFIDENTIAL` → **脱敏后云端**（客户 ID 替换、资产区间化） | 基于客户画像生成个性化投资建议 |
| **交易异常检测** | 交易金额、对手方、时间戳、账户 ID | PCI-DSS（持卡人数据保护）、SOX（交易完整性）、AML 反洗钱 | `RESTRICTED` → **本地模型**强制（交易数据绝对不出境） | 实时检测可疑交易模式 |
| **财报摘要生成** | 公开财报数据（营收、利润、EPS） | SOX 信息披露、SEC 10-K/10-Q | `PUBLIC` → **云端**可用（公开信息） | 自动生成季度财报摘要 |
| **信用评分解释** | 信用评分、还款历史、负债比率 | FCRA（公平信用报告法）、GDPR 解释权（第 22 条） | `INTERNAL` → **本地模型**（信用数据不出境） | 解释信用评分变化原因 |
| **合规文档审查** | 合同条款、监管通知、内部政策 | SOX 内控、GDPR DPO 要求、行业特定法规 | `INTERNAL` → **本地模型**（内部政策不出境） | 自动审查合同是否符合监管要求 |
| **市场 sentiment 分析** | 公开新闻、社交媒体、分析师报告 | 无敏感数据限制 | `PUBLIC` → **云端**可用 | 分析市场情绪对股价影响 |

**金融行业 MOM 决策示例**:

```
理财经理输入: "客户李四，身份证号310101198001011234，
              资产组合：股票500万、债券300万、现金200万，
              风险偏好：稳健型，年龄45岁，
              请生成下季度再平衡建议"

→ InputSanitizer: 检测到金融 PII（身份证号、具体姓名、精确资产）
→ PrivacyEngine.evaluate():
   - 身份证号 → [ID]（Level 2 正则，PCI-DSS 要求）
   - 姓名 → [NAME]（Level 1 关键词）
   - 精确资产 "500万" → 区间 "400-600万"（Level 3 泛化，SOX 财务控制）
   - 年龄 "45岁" → 区间 "40-50岁"（Level 3 泛化）
   - 风险偏好 "稳健型" → 保留（分类标签，非标识符）
→ DataClassifier: `CONFIDENTIAL`（含金融 PII，已脱敏）
→ PrivacyGatekeeper.decide(): `LOCAL_WITH_CLOUD_FALLBACK`
   - 资产配置基础逻辑 → 本地模型（规则引擎）
   - 复杂市场预测/组合优化 → 脱敏后云端 SOTA
→ 响应回替: 占位符替换回原始值（仅本地处理）
→ AuditLogger: 记录完整数据处理链（SOX 审计要求：谁、何时、访问了什么数据）
→ ComplianceReporter: 自动生成 SOX 控制测试报告（数据访问控制有效性）
```
#### 法律行业（ABA 职业规则 / 特权保护 / GDPR）

| 场景 | 数据类型 | 合规要求 | MOM 路由策略 | 典型任务 |
|------|---------|---------|------------|---------|
| **合同条款审查** | 合同全文、当事人名称、金额、违约责任 | ABA 1.6 保密义务、ABA 1.1 称职、SOX（若涉及上市公司） | `CONFIDENTIAL` → **脱敏后云端**（当事人名称替换、金额区间化） | 审查合同条款是否符合监管要求 |
| **律师-客户特权通信分析** | 客户案情、策略讨论、法律意见草稿 | ABA 1.6 绝对保密、Attorney-Client Privilege、Work Product Doctrine | `RESTRICTED` → **本地模型**强制（特权信息禁止任何出境） | 分析历史案件通信，提取关键事实时间线 |
| **判例检索与法律研究** | 公开判例、法规条文、法院意见 | 无敏感数据限制（公开信息） | `PUBLIC` → **云端**可用 | 检索支持当前案情的先例 |
| **尽职调查报告生成** | 目标公司财务数据、法律风险、知识产权 | ABA 1.7 利益冲突、SOX 财务控制、GDPR 数据处理 | `CONFIDENTIAL` → **脱敏后云端**（目标公司名替换、财务区间化） | 生成并购尽职调查摘要 |
| **诉讼策略模拟** | 对方当事人信息、证据清单、预期判决 | ABA 3.3 诚实、Work Product Doctrine（策略文件受保护） | `RESTRICTED` → **本地模型**强制（策略文件绝对不出境） | 模拟不同诉讼策略的胜率 |
| **合规政策审查** | 内部合规手册、监管通知、员工行为准则 | ABA 1.13 组织客户、SOX 内控 | `INTERNAL` → **本地模型**（内部政策不出境） | 审查内部政策是否符合最新监管要求 |

**法律行业 MOM 决策示例**:

```
律师输入: "客户王五（身份证号110101199001011234）委托我们处理
          与赵六公司的合同纠纷，合同金额500万元，
          争议焦点：赵六公司未按约定交付软件源代码，
          我方策略：主张违约+索赔，同时准备反诉对方侵犯商业秘密，
          请分析类似判例和诉讼策略建议"

→ InputSanitizer: 检测到法律敏感信息（姓名、身份证号、具体金额、当事人公司名、策略讨论）
→ PrivacyEngine.evaluate():
   - 客户姓名 "王五" → [CLIENT_NAME]（Level 1 关键词，ABA 1.6 保密）
   - 身份证号 → [ID]（Level 2 正则，绝对标识符）
   - 对方公司 "赵六公司" → [COUNTERPARTY]（Level 1 关键词，利益冲突检查）
   - 合同金额 "500万元" → 区间 "400-600万元"（Level 3 泛化，SOX 财务控制）
   - 策略讨论 "主张违约+索赔，准备反诉" → 保留但标记为 Work Product（策略文件特权保护）
→ DataClassifier: `CONFIDENTIAL`（含客户信息，已脱敏；含策略讨论，需特权保护）
→ PrivacyGatekeeper.decide(): `LOCAL_WITH_CLOUD_FALLBACK`
   - 判例检索、法律条文分析 → 脱敏后云端 SOTA（公开法律信息）
   - 策略讨论、客户案情分析 → 本地模型（特权信息禁止出境）
→ 响应回替: 占位符替换回原始值（仅本地处理）
→ AuditLogger: 记录完整访问日志（ABA 1.6 保密要求：谁访问了客户信息）
→ 利益冲突检查: 自动检索律所历史客户，检测是否与 "赵六公司" 存在利益冲突（ABA 1.7）
```

#### 教育行业（FERPA / COPPA / GDPR）

| 场景 | 数据类型 | 合规要求 | MOM 路由策略 | 典型任务 |
|------|---------|---------|------------|---------|
| **学生成绩单分析** | 学生姓名、学号、各科成绩、GPA | FERPA 99.10 教育记录定义、99.30 披露同意、GDPR 数据处理 | `REGULATED` → **本地模型**或拒绝（学生成绩禁止出境） | 分析班级成绩分布，识别学习困难学生 |
| **个性化学习推荐** | 学生学习行为、答题记录、知识掌握度 | FERPA 99.3 学校官员例外（需教育利益）、COPPA 13 岁以下家长同意 | `CONFIDENTIAL` → **脱敏后云端**（学生 ID 替换、行为聚合） | 基于学习数据推荐个性化学习路径 |
| **课程资料生成** | 公开教材、教学大纲、练习题 | 无敏感数据限制（公开教育内容） | `PUBLIC` → **云端**可用 | 基于公开教材生成练习题和讲解 |
| **招生决策支持** | 申请者成绩单、推荐信、个人陈述 | FERPA 99.31 研究例外（去标识化）、GDPR 第 22 条自动化决策 | `CONFIDENTIAL` → **脱敏后云端**（申请者 ID 替换、成绩区间化） | 辅助招生委员会评估申请者匹配度 |
| **学生行为预警** | 出勤记录、图书馆访问、食堂消费 | FERPA 99.36 司法命令例外、GDPR 合法利益 | `INTERNAL` → **本地模型**（行为数据不出境） | 识别可能辍学或心理危机的学生 |
| **教育研究数据分析** | 去标识化学生数据、聚合统计、学习效果 | FERPA 99.31(b)(1) 研究例外（去标识化）、IRB 伦理审查 | `CONFIDENTIAL`（去标识化）→ **脱敏后云端** | 分析教学法对学生成绩的影响 |

**教育行业 MOM 决策示例**:

```
教师输入: "学生陈七，学号202408001，数学85分、语文78分、英语92分，
          最近3次作业提交延迟，课堂参与度下降，
          请分析该学生的学习状态并推荐干预措施"

→ InputSanitizer: 检测到 FERPA 保护的学生教育记录（姓名、学号、成绩、行为记录）
→ PrivacyEngine.evaluate():
   - 学生姓名 "陈七" → [STUDENT_NAME]（Level 1 关键词，FERPA 保护）
   - 学号 "202408001" → [STUDENT_ID]（Level 2 正则，教育记录标识符）
   - 具体成绩 "85分、78分、92分" → 区间 "中上、中等、优秀"（Level 3 泛化，FERPA 要求）
   - 行为记录 "作业延迟、参与度下降" → 保留但去标识化（行为描述本身非标识符，但与学生关联后成为教育记录）
→ DataClassifier: `REGULATED`（含学生教育记录，FERPA 核心保护对象）
→ PrivacyGatekeeper.decide(): `LOCAL`（强制本地模型）
   - 学生教育记录 → 本地模型强制处理（FERPA 要求机构控制数据）
   - 若本地模型能力不足 → 返回错误，提示"涉及学生教育记录，请使用本地部署"
→ 响应回替: 占位符替换回原始值（仅本地处理，教师查看）
→ AuditLogger: 记录完整访问日志（FERPA 要求：谁访问了学生教育记录）
→ 家长通知检查: 若涉及 13 岁以下学生（COPPA），自动触发家长同意验证
→ 目录信息排除: 验证学生未选择退出目录信息（FERPA 99.37）
```



#### 跨行业对比：MOM 数据分级与路由策略

| 数据类型 | 医疗行业 | 金融行业 | 通用企业 | MOM 默认策略 |
|---------|---------|---------|---------|------------|
| 患者姓名/病历号 | `REGULATED`（HIPAA PHI） | — | `INTERNAL` | `RESTRICTED` |
| 身份证号/SSN | `REGULATED`（HIPAA） | `RESTRICTED`（PCI-DSS） | `RESTRICTED` | `RESTRICTED` |
| 具体金额/资产 | — | `RESTRICTED`（SOX） | `CONFIDENTIAL` | `CONFIDENTIAL` |
| 诊断/处方 | `REGULATED`（HIPAA） | — | `INTERNAL` | `CONFIDENTIAL` |
| 交易记录 | — | `RESTRICTED`（PCI-DSS/AML） | `CONFIDENTIAL` | `RESTRICTED` |
| 公开财报/市场数据 | `PUBLIC`（医学文献） | `PUBLIC`（SEC 披露） | `PUBLIC` | `PUBLIC` |
| 内部政策/会议纪要 | `INTERNAL`（医院管理） | `INTERNAL`（合规政策） | `INTERNAL` | `INTERNAL` |

#### 行业工作流 CLI

```bash
# 医疗行业：配置 HIPAA 合规工作流
zilli industry run --framework hipaa   --tenant hospital-001   --policy "phi_strict"   --local-models "llama3-70b,mistral-large"   --cloud-models "gpt-4,claude-3-opus"   --sota-max-ratio 0.02

# 金融行业：配置 SOX + PCI-DSS 合规工作流
zilli industry run --framework sox,pci_dss   --tenant bank-001   --policy "financial_restricted"   --local-models "llama3-70b"   --cloud-models "gpt-4"   --sota-max-ratio 0.01   --audit-retention 7years

# 查看行业工作流状态
zilli industry list
zilli industry status --tenant hospital-001
```


### 3.5 OSS 贡献者

| 阶段 | 痛点 | ZILLI 解法 | 对应能力 |
|------|------|-----------|---------|
| **理解阶段** | 代码库庞大，模块关系复杂 | 架构分层清晰（执行/评估/进化/学习/治理/存储），循环导入零容忍 | 架构设计 |
| **贡献阶段** | 担心提交破坏现有功能 | CI/CD 门禁（ruff + pyright + 多版本 pytest），1048 测试覆盖 85% | F-23 CI/CD |
| **优化阶段** | Python 热路径性能瓶颈 | Rust 辅助库 `zilli-rs`（PyO3 绑定），PPM 预测 + 代码指纹 0.054ms | F-24 Rust 辅助库 |

---

## 4. 功能需求

### 4.0 MOM 元级功能（新增）

#### F-0.1 MOM 数据治理引擎

- **描述**: 请求进入系统的第一层处理——PII 检测、数据分级、脱敏策略、路由决策
- **输入**: 用户原始请求文本 + 可选租户上下文
- **输出**: `MOMDecision`（data_class + sanitized_text + route_policy + privacy_verdict）
- **流程**:
  1. `InputSanitizer` Level 1 关键词检测（< 1ms）
  2. `PrivacyEngine` Level 2 正则 + Level 3 NER 模型（< 50ms）
  3. `DataClassifier` 五级分类（PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED/REGULATED）
  4. `PrivacyGatekeeper.decide()` → LOCAL / CLOUD / LOCAL_WITH_CLOUD_FALLBACK / REJECTED
  5. 若需上云 → `EntityReplacer` 脱敏（姓名→[NAME]，电话→[PHONE]）
  6. 返回脱敏后的请求 + 路由策略 + 占位符映射表（用于响应回替）
- **验收标准**:
  - PII 检测召回率 > 95%，误报率 < 5%
  - 数据分级准确率 > 98%（人工标注测试集）
  - REGULATED 数据 100% 拒绝（零误放）
  - 脱敏后云端请求无原始 PII 残留（正则扫描验证）

#### F-0.2 MOM 智能路由决策

- **描述**: 基于数据分级 + 任务难度 + 预算状态，选择最优执行路径
- **输入**: `MOMDecision`（来自 F-0.1）+ 任务文本 + 租户配额
- **输出**: `RouteDecision`（model_id + strategy + route_type + estimated_cost + estimated_latency + data_residency）
- **决策矩阵**:

| 数据级别 | 难度 < 0.3 | 难度 0.3~0.7 | 难度 > 0.7 | 预算紧张 |
|---------|-----------|-------------|-----------|---------|
| PUBLIC | FAST_LANE + 本地 | FULL_ROUTE + 混合 | FULL_ROUTE + 云端 SOTA | 强制本地 |
| INTERNAL | FAST_LANE + 本地 | FULL_ROUTE + 本地 | FULL_ROUTE + 本地 | 强制本地 |
| CONFIDENTIAL | FAST_LANE + 本地 | FULL_ROUTE + 本地优先 | FULL_ROUTE + 脱敏后云端 | 强制本地 |
| RESTRICTED | 本地强制 | 本地强制 | 本地强制 | 本地强制 |
| REGULATED | 拒绝 | 拒绝 | 拒绝 | 拒绝 |

- **验收标准**:
  - 本地模型处理比例 > 60%（INTERNAL/RESTRICTED 强制本地）
  - 云端调用中脱敏率 = 100%（CONFIDENTIAL 上云必须脱敏）
  - 路由决策延迟 < 15ms（PPM 0.054ms + 数据分级 5ms + 策略选择 1ms）
  - 月度预算超支 = 0（硬封顶）

#### F-0.3 MOM 响应回替与审计

- **描述**: 云端返回的响应中可能包含脱敏占位符，需在本地替换回原始值；同时完整审计整个决策链
- **输入**: 云端响应文本 + 占位符映射表（来自 F-0.1）+ RouteDecision
- **输出**: 最终用户响应 + 审计记录
- **流程**:
  1. `EntityRestorer` 将 `[NAME]`、`[PHONE]` 等占位符替换回原始值（本地处理，零数据出境）
  2. `OutputSanitizer` 最终 PII 回检（防止云端模型泄露训练数据中的 PII）
  3. `AuditLogger` 记录完整决策链：
     - `mom_decision`: data_class, sanitization_applied, route_policy
     - `route_decision`: model_id, strategy, difficulty, family, confidence
     - `model_call`: tokens, duration, cost, success
     - `privacy_verdict`: pii_detected, entities_replaced, data_class_final
- **验收标准**:
  - 占位符替换准确率 = 100%
  - 响应回替后无残留占位符（正则扫描）
  - 审计日志完整率 = 100%（每条请求必有记录）
  - 审计日志不可篡改（追加模式 + 哈希链）

#### F-0.4 MOM 多租户数据隔离

- **描述**: 每个租户拥有独立的 MOM 决策空间——独立的数据分级策略、独立的模型画像、独立的预算
- **机制**:
  - `TenantPrivacyPolicy`: 每个租户可自定义数据分级规则（如医疗租户默认 REGULATED 范围更大）
  - `TenantModelProfile`: 租户独立的模型成功率、能力向量（租户 A 的本地模型表现不影响租户 B）
  - `TenantCostController`: 租户级预算硬封顶，超支时仅影响该租户
  - `TenantAuditLog`: 租户隔离的审计日志（`audit_logs/tenant_{id}/`）
- **验收标准**:
  - 租户 A 的 PII 检测规则不影响租户 B
  - 租户 A 的模型画像数据不可被租户 B 访问
  - 租户 A 预算超支时，租户 B 正常服务
  - 审计日志按租户物理隔离（不同目录/集合）


### 4.1 执行层：智能路由与任务调度

#### F-1 多模型平面路由

- **描述**: 根据请求特征选择 FULL_ROUTE（Plan→Execute→Review）或 FAST_LANE（直接执行）
- **输入**: 用户请求文本 + 可选的行业上下文
- **输出**: `RouteResult`（final_text + 各阶段结果 + 耗时）
- **验收标准**: 
  - 简单请求走 FAST_LANE，复杂请求走 FULL_ROUTE
  - RouteClassifier 模式匹配准确率 > 80%
  - 端到端延迟：FAST_LANE < 2s，FULL_ROUTE < 8s

#### F-2 GPS-MOM 智能路由

- **描述**: 基于 PPM 预测 → 策略选择 → 模型画像 → 模型选择的四步决策流水线
- **组件**:
  - **PPM（前置预测器）**: 分类任务家族（6 类：chat/code/reasoning/analysis/creative/translation）+ 难度评分（0~1）+ LRU 缓存（命中率 > 60%）
  - **StrategySelector**: 三档策略（ECONOMY/STANDARD/ENHANCED），基于难度 + 预算 + 租户配额
  - **ModelProfile**: 5 维能力画像（推理/代码/创意/分析/多语言）+ 贝叶斯 EMA 更新（α=0.3 能力, α=0.1 成功率）+ softmax Thompson 采样
  - **FeedbackCollector**: 异步队列 + JSONL 批量持久化（100 条触发）+ 评价器（LLM-as-Judge / 用户反馈）
- **验收标准**:
  - 简单聊天（难度 < 0.3）直通 fast-lane，延迟 < 10ms（PPM 预测）
  - 高难度（> 0.7）+ 低预算正确走 ENHANCED（SOTA 硬约束允许时）
  - 反馈闭环 100 条触发画像更新，200 条触发 PPM 在线训练

#### F-3 模型能力画像系统

- **描述**: 在线追踪模型成功率、5 维能力向量，支持加权 softmax 模型选择
- **存储**: JSON 原子持久化（tmp→replace），支持多租户隔离（tenant_prefix）
- **更新**: EMA 平滑，避免单条异常反馈剧烈波动
- **冷启动**: 新模型接入时继承同系列模型先验，3 次调用后切换为实测值

---

### 4.2 评估层：质量判定与元评估

#### F-16 PPM 在线训练

- **描述**: 基于实际反馈数据调整 PPM 的难度预测权重，实现路由系统的自我校准
- **机制**:
  - 每条反馈记录包含 `prediction` vs `actual`（实际难度由 LLM-as-Judge 或任务成功率推导）
  - EMA 更新各家族权重参数（α=0.1）
  - 权重偏移 > 5% 时自动清 PPM 缓存，强制重新预测
- **验收标准**:
  - 训练后权重发生有意义的偏移（相对变化 > 5%）
  - `zilli ppm reset` 恢复出厂权重
  - 训练过程不阻塞路由（异步后台线程）

#### F-17 LLM-as-Judge 评分

- **描述**: 使用 LLM 对响应质量进行评分（0~1），作为反馈闭环的主信号源
- **机制**:
  - 构建评分 Prompt（含评分维度：准确性/完整性/安全性/风格一致性）
  - 调用任意 async `llm_generate`（走 ECONOMY 档位降低成本）
  - 正则解析 `Rating: X.XX`，失败时回退到 heuristic（基于规则的长度/格式/关键词检查）
  - stats 追踪调用次数 / 回退次数 / 平均评分
- **验收标准**:
  - 正确解析 `Rating: 0.85`（容忍 ±0.01 格式偏差）
  - 异常情况下 100ms 内回退到 auto_score
  - 评分分布不过度集中（标准差 > 0.1）

#### F-18 贝叶斯元评估

- **描述**: 用高斯共轭先验更新替代简单 bias/variance 统计，小样本下稳健估计真实误差分布
- **机制**:
  - 先验: μ₀ ~ N(0.5, 0.1²)（保守初始化）
  - 似然: x̄ ~ N(样本均值, 样本方差/n)
  - 后验: posterior_mean = (μ₀/σ₀² + n·x̄/s²) / (1/σ₀² + n/s²)
  - 输出: `posterior_mean`（期望误差）+ `posterior_std`（不确定性）
- **决策规则**: 可靠性（posterior_mean < 0.2）与校准误差（posterior_std < 0.05）联合判定
- **验收标准**: 8 项单元测试通过，小样本（n=5）下比 MLE 估计稳定 3 倍

#### F-6 Champion-Challenger Arena

- **描述**: 双模型统计对决，胜者成为新的 Champion，败者回滚或降级
- **统计方法**: 
  - 最小样本量: 30 对同任务对决
  - 显著性检验: 配对 t 检验，p < 0.05
  - 最小胜率差: min_win_gap = 0.05
  - 能力雷达图: 5 维对比可视化
- **输出**: Leaderboard（ELO 评分 + 能力雷达图 + 置信区间）
- **验收标准**: 
  - 假阳性率（错误升级）< 5%
  - 升级过程可回滚（保留上一版本 Champion）

---

### 4.3 进化层：自我改进与技能生长

#### F-7 技能进化引擎

- **描述**: 从项目源码（.py/.md）中提取技能模块 → 轨迹反思 → 进化策略应用 → 多样性门控 → PR 输出
- **4 种进化策略**:
  1. **prompt_optimization**: 优化系统提示词，提升指令遵循率
  2. **error_handling**: 增加异常分支和重试逻辑
  3. **boundary_refinement**: 明确技能的能力边界，减少幻觉
  4. **tool_addiction**: 发现新工具需求，扩展工具调用能力
- **多样性控制**: 
  - 代码指纹提取（6 维加权 Jaccard：AST 结构/变量名/调用链/注释/导入/控制流）
  - n-gram 指纹 + fitness-sharing 剪枝
  - 温度加权亲本选择（高温度鼓励探索，低温度鼓励利用）
- **验收标准**:
  - 单策略和多策略模式均可正常工作（`--strategy` 参数支持组合）
  - 多样性控制器拒绝相似度 > 0.85 的突变
  - 阈值可调（0.0=全部接受, 1.0=全部拒绝）

#### F-8 Loop 循环引擎

- **描述**: 通用 Retry→Verify→Correct→Upgrade 循环，泛型设计支持任意任务类型
- **实现**:
  - `LoopRunner[T]`（泛型，T 为验证结果类型）
  - `MetaLoopRunner`（双层元循环，监控 LoopRunner 自身性能）
- **触发器**:
  - `FixedInterval`: 固定间隔（默认 24h）
  - `Event`: 特定事件（如连续 3 次失败）
  - `DynamicInterval`: 基于收敛速度动态调整（损失下降快则间隔缩短）
- **验证器**:
  - `TestSuite`: 单元测试通过
  - `Predicate`: 自定义断言函数
  - `ExternalModel`: 外部模型判定
  - `Skill`: 技能自身验证逻辑
  - `Composite`: 多验证器组合（AND/OR）
- **验收标准**:
  - 最大重试次数可配置（默认 5 次）
  - 验证失败时自动降级策略（ENHANCED → STANDARD → ECONOMY）
  - 元循环能在 LoopRunner 卡死时触发熔断

#### F-9 Self-Harness（自我改进的 Harness）

- **描述**: 三阶段元循环——弱点挖掘 → 有界提案 → 分体验证
- **阶段 1: 弱点挖掘（WeaknessMiner）**
  - 对历史失败轨迹进行聚类（k-means + 语义嵌入）
  - 识别高频失败模式（如"API 调用超时未处理"）
  - 输出: `WeaknessReport`（模式描述 + 影响范围 + 置信度）
- **阶段 2: 有界提案（Bounded Harness Edit）**
  - 基于弱点报告生成 Harness 修改提案
  - "有界"限制：只修改与弱点相关的代码区域，禁止大范围重构
  - 输出: `HarnessEdit`（文件路径 + 行范围 + 修改内容 + 回滚指令）
- **阶段 3: 分体验证**
  - held-in 验证：弱点相关测试集（通过率目标 ≥ 基线 + 5%）
  - held-out 验证：回归测试集（通过率目标 ≥ 基线 - 2%）
  - 双通过则接受，否则拒绝并记录偏差
- **验收标准**:
  - 产生可操作的 HarnessEdit（可自动应用 + 可回滚）
  - held-out 通过率无回归（下降 < 2%）
  - 全过程审计日志完整

#### F-10 多样性控制

- **描述**: 防止群体崩溃的 novel 性压力，确保进化池保持多样性
- **机制**:
  - **代码指纹**: 6 维加权 Jaccard 相似度（AST 结构 30%、变量名 15%、调用链 25%、注释 10%、导入 10%、控制流 10%）
  - **n-gram 指纹**: 3-gram 代码 token 序列，用于快速去重
  - **fitness-sharing**: 相似个体共享适应度，惩罚同质化群体
  - **温度加权亲本选择**: 温度 τ 控制探索/利用权衡（τ→∞ 均匀随机，τ→0 只选最优）
- **验收标准**:
  - 完全相同代码（相似度 = 1.0）100% 被拒绝
  - 进化池内平均相似度 < 0.6
  - 参数可调：diversity_threshold（0.0~1.0）

#### F-11 ACE 上下文策展（Agentic Context Engineering）

- **描述**: 增量式结构化上下文管理，让 Agent 在长时间运行中保持上下文清晰
- **机制**:
  - `ContextBullet`: 原子上下文条目（类型/内容/优先级/时间戳/来源）
  - `reflect()`: 从执行轨迹中提炼洞察，合并冗余条目，提升高价值条目优先级
  - `format_context()`: 输出 Markdown 格式上下文，支持截断策略（保留高优先级 + 最近 N 条）
- **验收标准**:
  - 上下文条目数增长可控（reflect 后压缩率 > 30%）
  - 关键信息不丢失（用户明确标记的条目永远保留）
  - 格式化输出可被任意 LLM 解析

#### F-19 未知项发现（Fable 方法）

- **描述**: Anthropic "Finding Your Unknowns" 方法论的工程化实现，系统性暴露系统盲区
- **机制**:
  - **盲点扫描**: LLM 驱动，分析历史轨迹中"本应该做但没做"的决策缺口
  - **面试问题生成**: 针对盲点生成探针问题，测试系统边界
  - **实现笔记**: 记录偏差（实际行为 vs 预期行为），追踪根因
  - **测验生成**: 自动生成回归测验，确保修复后不再复发
- **CLI 接口**:
  - `zilli unknowns blind-spot`: 扫描当前技能库的盲点
  - `zilli unknowns interview`: 运行探针面试
  - `zilli unknowns summary`: 生成四象限分类（known-knowns / known-unknowns / unknown-knowns / unknown-unknowns）
  - `zilli unknowns resolve`: 将未知项转化为进化任务
- **验收标准**:
  - 未知项 JSON 持久化（含分类/优先级/状态/创建时间）
  - 四象限分类可视化（Streamlit 管理台展示）
  - 与 Loop 引擎集成：`unknowns plan` 输出作为 `LoopRunner` 输入契约

#### F-23 未知项全生命周期工作流

- **描述**: 补全 Fable 方法论的实施前/后环节，覆盖 brainstorm → reference → plan → pitch 全流程
- **机制**:
  - **Brainstorm/Prototype**: `unknowns brainstorm <task>` — 生成 N 个差异化解法草案（廉价原型），供反应式筛选，暴露 unknown knowns
  - **References**: `unknowns reference <path>` — 读取参考实现（源码/文档），提炼语义注入 prompt 上下文
  - **Implementation Plan**: `unknowns plan` — 生成实施计划，前置最易被修改的决策（数据模型、类型接口、UX 流），机械性重构置底
  - **Pitch Packager**: `unknowns pitch` — 打包 prototype + spec + implementation notes 为单文档（评审/共识），测验及格方可合并
- **Loop 衔接**:
  - `plan` 输出作为 `LoopRunner` 输入契约（验证器 + 触发器配置）
  - `notes` 的 deviation 流回 `CycleMemory` 成为 RL 训练信号
- **验收标准**: 四方法与 Loop 引擎集成测试通过，端到端耗时 < 30 分钟（标准任务）

---

### 4.4 学习层：RL 训练与知识蒸馏

#### F-4 RL 训练管线

- **算法**:
  - **CISPO**（Conservative Importance Sampling Policy Optimization）: 重要性采样比率裁剪，避免策略更新过大
  - **GRPO**（Group Relative Policy Optimization）: 组内相对优势，无需 Value Network，适合简单场景
- **数据流**:
  ```
  Rollout → 轨迹存储（TrajectoryStore）→ 混合采样（golden_ratio=0.5，合成:经验=1:1）
  → 优势估计（MC + GAE，λ=0.95）→ 损失计算（policy + value + entropy）
  → 策略更新（梯度累积，max_grad_norm=1.0）→ 断点保存（每 100 步）
  ```
- **验收标准**:
  - 训练后策略损失收敛（最后 100 步标准差 < 0.01）
  - 无 Value Network 场景 GRPO 正确运行（仅 policy loss）
  - 断点续训：中断后从最新 checkpoint 恢复，损失曲线连续

#### F-5 知识蒸馏

- **描述**: 从 Planner（教师，大模型）蒸馏知识到 Executor（学生，小模型），实现质量与成本的帕累托最优
- **损失函数**:
  - `L_total = α·L_BC + β·L_KL + γ·L_RL + δ·L_embed`
  - `L_BC`: 行为克隆（教师动作的对数似然）
  - `L_KL`: KL 散度（学生分布逼近教师分布）
  - `L_RL`: RL 损失（学生自主探索的奖励）
  - `L_embed`: Embedding 距离正则化（隐藏状态对齐，δ=0.5）
- **触发条件**:
  - 自动间隔：默认 24h（`distillation_interval`）
  - LoRA 阈值：教师产生 1000 条新轨迹
  - 全 SFT 阈值：7 天未进行全量蒸馏
- **验收标准**:
  - 蒸馏后 Executor 在 held-out 测试集上保持率 ≥ 教师 90%
  - 推理成本下降 ≥ 30%（学生模型更小或档位更低）
  - 蒸馏过程可中断，支持断点续训

#### F-11 端到端进化训练管线（EvolveToTrainPipeline）

- **描述**: 全自动闭环——进化产生新 Skill → 训练优化策略 → 部署到生产 → 监控反馈 → 触发下一轮进化
- **流程**:
  ```
  Evolve（SkillEvolutionEngine 产出 PR）→ 
  Train（RL 训练 + 蒸馏）→ 
  Deploy（Champion-Challenger 检验后灰度发布）→ 
  Monitor（7 天观察期，成功率/延迟/成本）→ 
  达标？→ 正式合并 / 回滚 → 轨迹入库 → 触发 Evolve
  ```
- **验收标准**:
  - 单轮端到端耗时 < 4 小时（标准任务）
  - 回滚时间 < 5 分钟（自动切换 Champion）
  - 观察期指标异常自动告警（成功率下降 > 5% 触发回滚）

---

### 4.5 治理层：成本、隐私与合规

#### F-12 成本控制

- **描述**: 多维度预算控制，确保进化不失控、生产不破产
- **组件**:
  - `CostController`: 月度预算、小时配额、租户级隔离
  - `DynamicSOTAScheduler`: 动态调整 SOTA 模型调用频率，基于任务难度和预算余量
  - `PlannerBudget`: Plan 阶段的预算预分配，防止执行阶段超支
- **硬约束**:
  - `max_sota_ratio=0.05`: SOTA 模型调用比例上限 5%，超限直接拒绝（F-20）
  - 紧急模式：余额 < 10% 时，所有请求强制走 ECONOMY 档位，禁用进化
- **验收标准**:
  - 月度预算超支 0 次（硬封顶）
  - 成本优化 > 30%（相比无策略基线）
  - 紧急模式触发后，成本下降 > 50%

#### F-13 隐私合规

- **描述**: 企业级隐私治理，覆盖数据生命周期全阶段
- **组件**:
  - `PrivacyEngine`: PII 检测（3 级：Level 1 关键词 / Level 2 正则 / Level 3 NER 模型）
  - `InputSanitizer`: 数据脱敏（姓名→[NAME]，电话→[PHONE]，地址→[ADDR]）
  - `AuditLogger`: 完整审计日志（who/what/when/where/result），JSONL 持久化
  - `WorkflowRegistry`: 行业合规工作流注册（HIPAA/SOX/FERPA/CCPA/GDPR）
- **数据隔离**:
  - 输入数据与训练数据物理隔离（不同存储桶/集合）
  - 多租户场景下，租户 A 的数据不可用于训练租户 B 的模型
- **验收标准**:
  - PII 检测召回率 > 95%，误报率 < 5%
  - 审计日志不可篡改（追加模式 + 哈希链）
  - 合规检查 100% 通过（ruff + pyright 静态扫描）
#### F-15 行业合规工作流

- **描述**: 预配置的行业合规模板，一键启用医疗/金融/法律/教育行业的数据治理策略、模型路由规则和审计要求
- **支持框架**:

| 行业 | 主要法规 | 默认数据分级 | 默认 SOTA 比例 | 本地模型强制场景 | 审计保留期 |
|------|---------|------------|--------------|----------------|----------|
| **医疗** | HIPAA / HITECH / HITRUST | PHI → `REGULATED` | 2% | 所有含 PHI 请求 | 7 年 |
| **金融** | SOX / PCI-DSS / GDPR / AML | 交易数据 → `RESTRICTED` | 1% | 交易记录、信用数据 | 7 年 |
| **法律** | ABA 职业规则 / GDPR / CCPA | 客户案情 → `CONFIDENTIAL` | 3% | 律师-客户特权信息 | 7 年 |
| **教育** | FERPA / COPPA / GDPR | 学生记录 → `REGULATED` | 2% | 学生成绩、行为记录 | 7 年 |

- **机制**:
  - `IndustryWorkflowRegistry`: 注册行业模板（HIPAAWorkflow / SOXWorkflow / FERPAWorkflow / LegalWorkflow）
  - `IndustryPolicyLoader`: 加载行业特定的 PII 检测规则、数据分级字典、脱敏策略
  - `IndustryAuditTemplate`: 预配置的合规报告模板（HIPAA Security Rule / SOX 404 / FERPA 审计）
  - `IndustryModelWhitelist`: 行业允许使用的模型清单（医疗：仅通过 HIPAA BAA 的模型）

- **医疗行业工作流（HIPAAWorkflow）**:
  ```
  1. PHI 检测增强：
     - 18 项 HIPAA Safe Harbor 标识符（姓名、地址、日期、电话、传真、邮箱、
       SSN、MRN、健康计划号、账号、证书号、车辆号、设备号、URL、IP、生物特征、
       照片、任何其他唯一标识符）
     - 检测模式：关键词 + 正则 + NER（医疗实体专用模型）

  2. 数据分级规则：
     - 含 18 项标识符中任意一项 → `REGULATED`（本地模型或拒绝）
     - 去标识化后（Safe Harbor 18 项全部移除）→ `CONFIDENTIAL`（脱敏后可选云端）
     - 医学知识查询（无患者关联）→ `PUBLIC`（云端可用）

  3. 路由策略：
     - `REGULATED` → 本地模型强制（若本地模型能力不足 → 返回错误，提示"涉及 PHI，请使用本地部署"）
     - `CONFIDENTIAL`（去标识化）→ 本地优先 + 脱敏后云端 fallback
     - `PUBLIC` → 正常 MOM 路由

  4. 审计要求：
     - 所有 PHI 访问记录（who/what/when/where/result）
     - 脱敏操作日志（原始标识符 → 替换值映射，加密存储）
     - 年度 HIPAA Security Rule 合规报告自动生成
     - 违规通知（Breach Notification）自动检测（>500 人触发）
  ```

- **金融行业工作流（SOXWorkflow）**:
  ```
  1. 金融 PII 检测增强：
     - PCI-DSS 持卡人数据（PAN、CVV、有效期、磁条数据）
     - SOX 财务数据（精确金额、账户余额、交易流水）
     - AML 敏感数据（可疑交易报告、客户风险评级）
     - 检测模式：PCI-DSS 正则（PAN：Luhn 算法验证）+ SOX 金额模式 + NER

  2. 数据分级规则：
     - 含 PAN/CVV/精确金额 → `RESTRICTED`（本地模型强制，零出境）
     - 含客户资产区间、风险偏好 → `CONFIDENTIAL`（脱敏后可选云端）
     - 公开财报数据、市场数据 → `PUBLIC`（云端可用）
     - 内部合规政策 → `INTERNAL`（本地模型）

  3. 路由策略：
     - `RESTRICTED`（交易数据）→ 本地模型强制，SOTA 比例硬限制 1%
     - `CONFIDENTIAL`（客户画像）→ 脱敏后云端，SOTA 比例限制 3%
     - `PUBLIC`（市场数据）→ 正常 MOM 路由

  4. 审计要求：
     - SOX 404 内控测试：数据访问控制有效性（每季度自动测试）
     - PCI-DSS 要求 10：网络资源访问监控（所有模型调用记录）
     - 交易完整性审计：所有含交易数据的请求 100% 本地处理证明
     - 年度 SOX 合规报告自动生成（管理层声明 + 审计师测试）
  ```

#### F-15 行业合规工作流

- **描述**: 预配置的行业合规模板，一键启用医疗/金融/法律/教育行业的数据治理策略、模型路由规则和审计要求
- **支持框架**:

| 行业 | 主要法规 | 默认数据分级 | 默认 SOTA 比例 | 本地模型强制场景 | 审计保留期 |
|------|---------|------------|--------------|----------------|----------|
| **医疗** | HIPAA / HITECH / HITRUST | PHI → `REGULATED` | 2% | 所有含 PHI 请求 | 7 年 |
| **金融** | SOX / PCI-DSS / GDPR / AML | 交易数据 → `RESTRICTED` | 1% | 交易记录、信用数据 | 7 年 |
| **法律** | ABA 职业规则 / GDPR / CCPA | 客户案情 → `CONFIDENTIAL` | 3% | 律师-客户特权信息 | 7 年 |
| **教育** | FERPA / COPPA / GDPR | 学生记录 → `REGULATED` | 2% | 学生成绩、行为记录 | 7 年 |

- **机制**:
  - `IndustryWorkflowRegistry`: 注册行业模板（HIPAAWorkflow / SOXWorkflow / FERPAWorkflow / LegalWorkflow）
  - `IndustryPolicyLoader`: 加载行业特定的 PII 检测规则、数据分级字典、脱敏策略
  - `IndustryAuditTemplate`: 预配置的合规报告模板（HIPAA Security Rule / SOX 404 / FERPA 审计）
  - `IndustryModelWhitelist`: 行业允许使用的模型清单（医疗：仅通过 HIPAA BAA 的模型）

- **医疗行业工作流（HIPAAWorkflow）**:
  ```
  1. PHI 检测增强：
     - 18 项 HIPAA Safe Harbor 标识符（姓名、地址、日期、电话、传真、邮箱、
       SSN、MRN、健康计划号、账号、证书号、车辆号、设备号、URL、IP、生物特征、
       照片、任何其他唯一标识符）
     - 检测模式：关键词 + 正则 + NER（医疗实体专用模型）

  2. 数据分级规则：
     - 含 18 项标识符中任意一项 → `REGULATED`（本地模型或拒绝）
     - 去标识化后（Safe Harbor 18 项全部移除）→ `CONFIDENTIAL`（脱敏后可选云端）
     - 医学知识查询（无患者关联）→ `PUBLIC`（云端可用）

  3. 路由策略：
     - `REGULATED` → 本地模型强制（若本地模型能力不足 → 返回错误，提示"涉及 PHI，请使用本地部署"）
     - `CONFIDENTIAL`（去标识化）→ 本地优先 + 脱敏后云端 fallback
     - `PUBLIC` → 正常 MOM 路由

  4. 审计要求：
     - 所有 PHI 访问记录（who/what/when/where/result）
     - 脱敏操作日志（原始标识符 → 替换值映射，加密存储）
     - 年度 HIPAA Security Rule 合规报告自动生成
     - 违规通知（Breach Notification）自动检测（>500 人触发）
  ```

- **金融行业工作流（SOXWorkflow）**:
  ```
  1. 金融 PII 检测增强：
     - PCI-DSS 持卡人数据（PAN、CVV、有效期、磁条数据）
     - SOX 财务数据（精确金额、账户余额、交易流水）
     - AML 敏感数据（可疑交易报告、客户风险评级）
     - 检测模式：PCI-DSS 正则（PAN：Luhn 算法验证）+ SOX 金额模式 + NER

  2. 数据分级规则：
     - 含 PAN/CVV/精确金额 → `RESTRICTED`（本地模型强制，零出境）
     - 含客户资产区间、风险偏好 → `CONFIDENTIAL`（脱敏后可选云端）
     - 公开财报数据、市场数据 → `PUBLIC`（云端可用）
     - 内部合规政策 → `INTERNAL`（本地模型）

  3. 路由策略：
     - `RESTRICTED`（交易数据）→ 本地模型强制，SOTA 比例硬限制 1%
     - `CONFIDENTIAL`（客户画像）→ 脱敏后云端，SOTA 比例限制 3%
     - `PUBLIC`（市场数据）→ 正常 MOM 路由

  4. 审计要求：
     - SOX 404 内控测试：数据访问控制有效性（每季度自动测试）
     - PCI-DSS 要求 10：网络资源访问监控（所有模型调用记录）
     - 交易完整性审计：所有含交易数据的请求 100% 本地处理证明
     - 年度 SOX 合规报告自动生成（管理层声明 + 审计师测试）
  ```

- **法律行业工作流（LegalWorkflow）**:
  ```
  1. 法律特权检测增强：
     - 律师-客户特权（Attorney-Client Privilege）标记：
       * 关键词："attorney"、"client"、"privileged"、"confidential"、"legal advice"
       * 上下文模式："我与律师讨论..."、"法律意见认为..."、"策略建议是..."
       * 通信标记：邮件头、备忘录标记、文件属性
     - 工作成果保护（Work Product Doctrine）：
       * 关键词："litigation strategy"、"trial preparation"、"anticipated litigation"
       * 文件类型：策略备忘录、专家报告草稿、证人访谈笔记
       * 检测模式：关键词 + 文件类型 + 上下文分析（ABA Model Rule 1.6 注释）
     - 利益冲突检测（ABA 1.7）：
       * 当事人名称库（律所历史客户、对方当事人、关联实体）
       * 检测模式：NER 实体识别 + 利益冲突数据库匹配
     - 检测模式：特权关键词 + 上下文语义分析 + 文件类型识别 + 利益冲突数据库

  2. 数据分级规则：
     - 含律师-客户特权信息（通信内容、法律意见、策略讨论） → `RESTRICTED`（本地模型强制，禁止任何云端处理）
     - 含 Work Product（诉讼策略、专家草稿、证人笔记） → `RESTRICTED`（本地模型强制）
     - 含一般客户案情（事实描述、合同条款、当事人信息） → `CONFIDENTIAL`（脱敏后可选云端）
     - 含利益冲突风险（对方当事人与历史客户关联） → `RESTRICTED`（本地处理 + 利益冲突告警）
     - 公开判例、法规条文、法院意见 → `PUBLIC`（云端可用）
     - 内部合规政策、律所管理文件 → `INTERNAL`（本地模型）

  3. 路由策略：
     - `RESTRICTED`（特权信息 / Work Product / 利益冲突） → 本地模型强制，禁止任何云端处理
       * 若本地模型能力不足 → 返回错误，提示"涉及律师-客户特权，请使用本地部署"
       * 利益冲突检测触发 → 返回告警，提示"检测到潜在利益冲突，请人工审查"
     - `CONFIDENTIAL`（一般客户案情） → 客户 ID 脱敏后可选云端（判例检索、法规分析）
       * 案情事实描述 → 脱敏后云端 SOTA（法律推理）
       * 合同条款审查 → 脱敏后云端（条款比对）
     - `PUBLIC`（公开法律信息） → 正常 MOM 路由
     - `INTERNAL`（内部政策） → 本地模型

  4. 审计要求：
     - 所有特权信息访问记录（ABA 1.6 保密义务：谁访问了客户信息）
     - 利益冲突检查日志（每次涉及当事人名称时自动检索冲突数据库）
     - 脱敏操作日志（原始标识符 → 替换值映射，加密存储，仅限合伙人访问）
     - Work Product 访问控制日志（策略文件访问需案件负责人授权）
     - 年度 ABA 职业责任合规报告（保密、利益冲突、称职义务审查）
  ```

- **教育行业工作流（FERPAWorkflow）**:
  ```
  1. 学生记录检测增强：
     - FERPA 保护的学生教育记录（99.10 定义）：
       * 成绩、成绩单、GPA（直接教育记录）
       * 行为记录、出勤记录、纪律记录（间接教育记录）
       * 财务资助记录、入学信息、课程注册（关联教育记录）
       * 检测模式：学生 ID 正则（学号格式）+ 教育机构关键词 + 成绩模式（数字+"分"/"grade"）
     - COPPA 保护的 13 岁以下儿童信息：
       * 年龄推断（出生日期、年级、"小学"关键词）
       * 家长联系信息（家长姓名、电话、邮箱）
       * 检测模式：年龄推断算法 + 家长信息关键词 + 学校类型标记
     - 目录信息（Directory Information，FERPA 99.37）：
       * 学生姓名、地址、电话、出生日期、年级、参与活动
       * 检测模式：目录信息字典 + 学生退出标记（若学生选择退出目录信息）
     - 检测模式：学生 ID 正则 + 教育机构关键词 + 成绩模式 + 年龄推断 + 家长信息 + 目录信息排除

  2. 数据分级规则：
     - 含学生教育记录（成绩、行为、出勤、资助） → `REGULATED`（本地模型或拒绝）
       * 直接标识符（姓名、学号、SSN）→ `REGULATED`（绝对禁止出境）
       * 间接标识符（出生日期、地址、照片）→ `RESTRICTED`（本地强制）
     - 含 COPPA 13 岁以下儿童信息 → `REGULATED`（本地模型或拒绝，需家长同意验证）
     - 去标识化教育数据（聚合统计、匿名化行为数据） → `CONFIDENTIAL`（脱敏后可选云端）
       * 要求：k-匿名（k≥5）、l-多样性、差分隐私（ε≤1.0）
     - 公开课程资料、教学大纲、公开教材 → `PUBLIC`（云端可用）
     - 内部教育政策、教师评估、行政管理文件 → `INTERNAL`（本地模型）
     - 目录信息（学生未退出） → `PUBLIC`（云端可用，但需验证退出状态）

  3. 路由策略：
     - `REGULATED`（学生教育记录 / COPPA 儿童信息） → 本地模型强制（FERPA 要求机构控制数据）
       * 若本地模型能力不足 → 返回错误，提示"涉及学生教育记录，请使用本地部署"
       * COPPA 场景 → 触发家长同意验证（未获得同意则拒绝处理）
     - `CONFIDENTIAL`（去标识化教育数据） → 本地优先 + 脱敏后云端 fallback
       * 要求：满足 k-匿名 + 差分隐私后方可上云
       * 研究场景 → 需 IRB 伦理审查标记
     - `PUBLIC`（公开课程资料） → 正常 MOM 路由
     - `INTERNAL`（内部政策） → 本地模型
     - 目录信息 → 验证学生退出状态（退出 → `INTERNAL`；未退出 → `PUBLIC`）

  4. 审计要求：
     - 所有学生教育记录访问日志（FERPA 99.32 记录要求：谁、何时、访问了什么记录）
     - 家长同意记录（COPPA：家长姓名、同意时间、同意范围、撤回记录）
     - 脱敏操作日志（去标识化方法、匿名化参数、差分隐私 ε 值）
     - 目录信息退出状态验证日志（学生选择退出目录信息的记录）
     - 年度 FERPA 合规报告（教育记录访问统计、披露记录、第三方接收者清单）
     - 违规通知（Breach Notification）：学生教育记录泄露 > 5000 人触发通知（FERPA 99.31 研究例外违规）
  ```


- **验收标准**:
  - 行业模板加载时间 < 5 秒
  - 行业 PII 检测召回率 > 98%（行业特定标识符）
  - 行业合规报告 100% 通过监管格式校验（HIPAA Security Rule / SOX 404 / PCI-DSS ROC）
  - 跨行业租户共存时，行业策略互不干扰（租户 A 医疗策略不影响租户 B 金融策略）


#### F-21 合规报告导出 CLI

- **描述**: 一键导出合规审计报告，满足监管要求
- **命令**:
  ```bash
  zilli audit export \
    --framework <gdpr|hipaa|soc2|pci_dss|ferpa|ccpa> \
    --tenant <id> \
    --start <YYYY-MM-DD> \
    --end <YYYY-MM-DD> \
    --output <path>
  ```
- **报告内容**:
  - 执行摘要（总请求数、PII 检测次数、异常事件数）
  - Findings（未通过项，含严重级别/根因/修复建议）
  - Passed 判定（通过的检查项列表）
  - 原始日志索引（可供深度审计）
- **验收标准**:
  - 报告格式为 JSON，可被第三方审计工具解析
  - 导出耗时 < 1 分钟（10 万条日志规模）
  - 支持增量导出（仅导出上次导出后新增日志）

#### F-24 多租户支持

- **描述**: SaaS 化基础，支持多团队/多客户共享 Zilli 实例，数据与资源完全隔离
- **机制**:
  - `TenantManager`: YAML 持久化租户配置（配额/策略/白名单）
  - 数据命名空间隔离：ChromaDB 集合前缀（`tenant_{id}_`），JSONL 文件目录隔离
  - API 端点: `/v1/tenants`（CRUD 租户，admin 权限）
  - 租户级预算：每个租户独立的 `CostController` 实例，超租户的预算不影响其他租户
- **安全模型**:
  - 租户管理员：只能查看本租户日志和仪表盘
  - 平台管理员：查看聚合视图，管理租户生命周期
  - 系统租户（id=system）：运行平台级进化任务，不占用租户配额
- **验收标准**:
  - 租户 A 的 API Key 无法访问租户 B 的数据（401 拒绝）
  - 租户删除后，所有相关数据 30 天内物理清除

---

### 4.6 基础设施层：API、分布式与存储

#### F-14 API 服务器

- **描述**: FastAPI 服务器，OpenAI 兼容接口，支持流式响应与生产级运维
- **端点**:
  - `POST /v1/chat/completions`: 主接口，支持 streaming=true
  - `GET /health`: 健康检查（返回路由状态、PPM 缓存命中率、成本余额）
  - `GET /dashboard/*`: Streamlit 管理台反向代理
- **认证**:
  - fail-closed 鉴权：无 `ZILLI_API_KEYS` 环境变量时，非本地请求返回 401
  - API Key 分级：admin（全权限）/ viewer（只读）/ service（仅 /v1/chat）
- **速率限制**:
  - 租户级：基于 `TenantManager` 配额
  - 全局级：基于 `CostController` 预算余量
- **验收标准**:
  - 并发 1000 请求，P99 延迟 < 5s
  - 流式响应首 token 延迟 < 500ms
  - 无 API Key 场景 100% 返回 401

#### F-15 Celery 分布式工作流

- **描述**: Celery + Redis 的 DAG 工作流执行引擎，支持复杂任务编排
- **功能**:
  - DAG 持久化：工作流定义序列化到 Redis，崩溃后恢复
  - 任务重试：指数退避（2^attempt × 1s），最大重试 5 次
  - 结果回调：任务完成后 webhook 通知或写入消息队列
  - 工作流状态追踪：running / completed / failed / skipped / retrying
- **验收标准**:
  - 1000 节点 DAG 执行时间 < 10 分钟
  - 工作节点崩溃后，任务自动迁移（< 30 秒检测）
  - DAG 可视化：F-22 Mermaid 导出

#### F-22 DAG 可视化

- **描述**: 任务 DAG 导出为 Mermaid 流程图，增强可观测性
- **机制**:
  - `TaskDAG.to_mermaid()`: 遍历 DAG 节点，生成 Mermaid 语法字符串
  - 节点状态着色：completed（绿色）/ failed（红色）/ running（蓝色）/ skipped（灰色）
  - 支持子图折叠（复杂 DAG 可分层展示）
- **验收标准**:
  - 输出合法 Mermaid 语法（可在 GitHub / Notion / Streamlit 中直接渲染）
  - 100 节点 DAG 渲染时间 < 100ms
  - 状态颜色与 Streamlit 管理台一致

#### F-24 Rust 辅助库

- **描述**: Python 热路径性能优化，关键计算下沉到 Rust
- **范围**:
  - PPM 预测：RegexClassifier 匹配 + SklearnONNXClassifier 推理
  - 代码指纹：6 维 Jaccard 相似度计算 + n-gram 提取
- **绑定**: PyO3 绑定 `zilli_hotpath`，安装方式 `pip install zilli[rust]`
- **性能**:
  - PPM 预测: 0.054ms（Python 基线 2.3ms，加速 42×）
  - 代码指纹: 0.12ms（Python 基线 8.5ms，加速 70×）
- **验收标准**:
  - 功能一致性：Rust 与 Python 实现 100% 输出一致（单元测试交叉验证）
  - 降级策略：Rust 库加载失败时自动回退到 Python 实现
  - 内存安全：通过 `cargo clippy` 和 `miri` 检查

#### F-25 端到端持续运行器（`zilli soak`）

- **描述**: 7×24 小时无人值守运行，保障系统健康与自愈
- **机制**:
  - 健康监控：每分钟检查 /health，异常时记录并告警
  - 崩溃恢复：进程崩溃后自动重启，恢复上下文（从最新 checkpoint）
  - 指标落盘：延迟/成功率/成本/缓存命中率，每分钟写入时序数据库（JSONL 格式）
  - 资源水位：CPU > 80% 或内存 > 90% 时触发优雅降级（关闭非核心进化任务）
- **CLI**:
  ```bash
  zilli soak --config soak.yaml --duration 7d --checkpoint-interval 1h
  ```
- **验收标准**:
  - 7 天连续运行，可用性 > 99.9%
  - 崩溃恢复时间 < 30 秒
  - 指标无丢失（落盘失败时缓存到内存，恢复后补写）

---

### 4.7 环境反馈与持续学习

#### 数据飞轮设计

Zilli 的进化不是凭空发生的，而是依赖**环境反馈数据飞轮**：

```
┌─────────────────────────────────────────────────────────────┐
│                    环境反馈数据飞轮                           │
│                                                              │
│  执行轨迹 ──→ 隐私脱敏 ──→ 向量存储 ──→ 经验回放 ──→ RL 训练  │
│      ↑           │            │            │            │   │
│      │           ↓            ↓            ↓            ↓   │
│      │      PII 检测      语义检索     混合采样      策略更新 │
│      │      3 级过滤      元数据索引    golden_ratio   断点保存│
│      │                                                      │
│      └────────── 用户反馈（显式 👍/👎 + 隐式信号）───────────┘
│                                                              │
│  隐式信号类型：                                               │
│  - 重试次数（> 1 次 = 质量不佳）                              │
│  - 延迟异常（> P95 = 可能卡顿）                               │
│  - Fallback 触发（走兜底策略 = 路由失效）                      │
│  - 用户中断（流式响应中途关闭 = 不满意）                       │
└─────────────────────────────────────────────────────────────┘
```

#### 数据保鲜策略

| 数据类型 | 热数据（7 天） | 温数据（30 天） | 冷归档（90 天） |
|---------|--------------|---------------|--------------|
| 执行轨迹 | 全量保留，用于实时进化 | 抽样保留（10%），用于 PPM 训练 | 蒸馏为知识摘要，删除原始轨迹 |
| 反馈记录 | 全量保留，用于画像更新 | 聚合统计（日均/周均），删除明细 | 仅保留趋势报告 |
| 审计日志 | 本地快速查询 | 压缩存储，支持导出 | 归档到对象存储，保留 7 年（合规） |
| 向量嵌入 | 高频检索，内存缓存 | 磁盘索引，低频检索 | 删除或迁移到廉价存储 |

---

## 5. 非功能需求：平台承诺（SLA）

Zilli 对外提供以下**平台承诺**，作为企业部署的置信基础：

| 承诺维度 | 指标 | 用户价值 | 实现机制 |
|---------|------|---------|---------|
| **响应速度** | PPM 预测 < 10ms；FAST_LANE 端到端 < 2s；FULL_ROUTE < 8s | 对话不卡顿，体验流畅 | Rust 热路径 + LRU 缓存 + 异步流水线 |
| **成本透明** | 每次请求成本实时可见（响应头 `X-Zilli-Cost`）；月度预算硬封顶 | 无账单惊吓，预算可控 | CostController 实时计费 + DynamicSOTA 硬约束 |
| **进化可信** | 新 Skill 必须经过 held-out 验证 + Champion-Challenger 统计检验（p < 0.05） | 不越改越差，升级可回滚 | Self-Harness + Arena + 自动回滚机制 |
| **隐私可证** | 一键导出 GDPR/HIPAA/SOC2 合规报告；PII 召回率 > 95% | 审计无忧，合规达标 | PrivacyEngine 3 级检测 + AuditLogger 哈希链 |
| **服务韧性** | `zilli soak` 保障 99.9% 可用性；崩溃恢复 < 30s | 生产级可靠，无人值守 | 健康监控 + 自动重启 + 优雅降级 |
| **数据隔离** | 租户间数据 100% 隔离；删除后 30 天内物理清除 | 多团队安全共用 | 命名空间隔离 + 独立存储桶 + 清除任务 |
| **可观测性** | 全链路审计日志；DAG Mermaid 可视化；PPM 统计面板 | 问题可定位，决策可解释 | AuditLogger + TaskDAG + Streamlit Dashboard |

### 质量门禁

| 检查项 | 目标 | 当前状态 | 衡量方式 |
|--------|------|---------|---------|
| 测试覆盖 | > 85% | ✅ 85.0%（1048 tests / 0 warnings） | pytest 覆盖率报告 |
| 静态检查 | 0 errors | ✅ ruff 0 / pyright 0 | CI 强制门禁 |
| 路由延迟 | PPM 预测 < 10ms | ✅ | latency_ms 统计 |
| 缓存命中率 | > 60% | ✅ OrderedDict LRU | PPM cache hit_rate |
| 进化收敛 | 连续 3 轮无新 PR | ✅ | 进化引擎 self-verification |
| 内存安全 | 无安全隐患 | ✅ | ruff + pyright 静态检查 + Rust miri |
| 模型选择 | 成本优化 > 30% | ✅ | StrategySelector 预算利用率 |
| 反馈闭环 | 100 条触发批量持久化 | ✅ record() 早触发 | FeedbackCollector batch_size |
| 架构健康 | 0 循环导入 | ✅ ppm_types 拆分 | import graph 扫描 |

---

## 6. 路线图：能力成熟度阶梯

Zilli 的发展不是功能堆砌，而是**能力成熟度的阶梯式进化**：

| 阶段 | 主题 | 成熟度标志 | 状态 | 版本 |
|------|------|-----------|------|------|
| **L0 可运行** | 核心骨架 | 能执行单次任务，完成基础路由 | ✅ | v0.1.0 |
| **L1 可路由** | 智能调度 | PPM 准确率 > 80%，成本优化 > 30%，缓存命中率 > 60% | ✅ | v0.2.0 |
| **L2 可进化** | 自我改进 | Skill 进化引擎运行，连续 3 轮无新 PR 即收敛，多样性控制生效 | ✅ | v0.3.0 |
| **L3 可训练** | RL 驱动 | CISPO/GRPO 策略损失收敛，蒸馏保持率 ≥ 90%，经验回放池 > 1000 条 | ✅ | v0.4.0 |
| **L4 可治理** | 企业就绪 | 合规报告导出 + 隐私 3 级检测 + 审计日志 + 行业工作流 | ✅ | v0.5.0 |
| **L5 自运转** | 无人值守 | `zilli soak` 7×24 健康监控，崩溃恢复 < 30s，99.9% 可用性 | ✅ | v1.0.0 |
| **L6 群智能** | 多 Agent 协作 | *待规划：Agent 间路由、任务分解、共识机制* | 🔮 | v2.0.0 |

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
- 隐私引擎 + PII 检测 + 数据隔离
- 审计日志 + 合规报告
- 行业工作流（法律/医疗/金融/教育）
- Streamlit Dashboard
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
- 模型化 PPM 默认分类器（sklearn ONNX，acc 1.0 / RMSE 0.044），regex+rust 回退
- `zilli soak` 端到端持续运行器（健康监控 + 崩溃恢复 + 指标落盘）
- API server 审计追踪（route_decision / model_call 落盘）
- 参考文档 × 4 + 安全审计报告
- 1048 tests / ruff 0 / pyright 0 / 覆盖率 85.0%

---

## 7. 依赖分析

| 依赖 | 用途 | 替代方案 | 可选性 |
|------|------|---------|--------|
| pydantic | Schema 定义与数据验证 | msgspec | 必选 |
| pyyaml | 配置管理（租户、工作流） | tomli | 必选 |
| numpy | 数值计算（向量运算、统计） | — | 必选 |
| httpx | HTTP 客户端（模型调用） | aiohttp | 必选 |
| dspy-ai | 语言模型调用与提示工程 | litellm | 必选 |
| torch | GPU 加速训练（RL + 蒸馏） | — | 可选（`[train]` extra） |
| fastapi | API 服务器 | starlette | 可选（`[api]` extra） |
| celery | 分布式工作流 | arq | 可选（`[worker]` extra） |
| chromadb | 向量存储（经验回放） | lancedb | 可选（`[vector]` extra） |
| scikit-learn | PPM ONNX 分类器 | — | 可选（`[ppm]` extra） |
| pyo3 | Rust 绑定（zilli-rs） | — | 可选（`[rust]` extra） |
| streamlit | 管理台 | gradio | 可选（`[dashboard]` extra） |

### 安装矩阵

```bash
# 最小安装：仅核心路由与执行
pip install zilli

# 开发安装：全部能力
pip install zilli[all]

# 特定场景：
pip install zilli[train]      # RL 训练 + 知识蒸馏
pip install zilli[api,dashboard]  # 生产部署（API + 管理台）
pip install zilli[worker]     # 分布式工作流节点
pip install zilli[rust]       # 性能优化（Rust 热路径）
```

---

## 8. 附录

### 附录 A：术语表

| 术语 | 全称 | 定义 |
|------|------|------|
| MOM | Meta-Object Model | 元级对象模型，Zilli 的核心架构范式，支持 Agent 自我引用和进化 |
| PPM | Preemptive Prediction Model | 前置预测模型，用于任务家族分类和难度评分 |
| CISPO | Conservative Importance Sampling Policy Optimization | 保守重要性采样策略优化，RL 算法 |
| GRPO | Group Relative Policy Optimization | 组相对策略优化，无 Value Network 的 RL 算法 |
| ACE | Agentic Context Engineering | 智能体上下文工程，增量式结构化上下文管理 |
| EMA | Exponential Moving Average | 指数移动平均，用于模型画像平滑更新 |
| SOTA | State Of The Art | 当前最优模型，通常指最大/最贵的模型 |
| FAST_LANE | — | 快速通道，直接执行，跳过 Plan/Review |
| FULL_ROUTE | — | 完整路由，Plan → Execute → Review 三阶段 |
| ECONOMY | — | 经济档位，使用 cheapest 可用模型 |
| STANDARD | — | 标准档位，平衡成本与质量 |
| ENHANCED | — | 增强档位，使用 SOTA 或模型组合 |
| held-in | — | 同分布验证集（与训练数据分布一致） |
| held-out | — | 异分布验证集（测试泛化能力） |
| fitness-sharing | — | 适应度共享，惩罚同质化个体的进化机制 |
| golden_ratio | — | 混合采样中合成数据与经验数据的比例（默认 1:1） |

### 附录 B：故障排查决策树

```
问题：进化不收敛（连续 > 5 轮产生新 PR）
├── 检查多样性控制器
│   ├── 相似度阈值是否过低？（建议 0.7~0.85）
│   └── 温度 τ 是否过高？（建议 1.0~2.0）
├── 检查 Self-Harness
│   ├── WeaknessMiner 聚类数是否 < 3？（增加历史轨迹量）
│   └── held-out 验证是否过严？（允许 2% 回归）
├── 检查反馈信号
│   ├── LLM-as-Judge 是否回退过多？（检查 Prompt 模板）
│   └── PPM 训练权重是否漂移？（执行 zilli ppm reset）
└── 检查资源约束
    ├── 成本是否触发紧急模式？（禁用进化，需手动解除）
    └── 向量存储是否满载？（清理冷归档数据）

问题：成本超支（月度预算耗尽）
├── 检查 DynamicSOTA
│   ├── max_sota_ratio 是否设置过高？（建议 ≤ 0.05）
│   └── 策略选择是否偏向 ENHANCED？（检查 PPM 难度校准）
├── 检查路由分布
│   ├── FAST_LANE 比例是否过低？（简单请求应 > 60%）
│   └── 缓存命中率是否 < 60%？（扩容 LRU 容量）
└── 检查异常调用
    ├── 是否有循环重试？（LoopRunner 最大重试次数）
    └── 是否有恶意请求？（检查 API 调用日志）

问题：PPM 预测漂移（路由决策明显变差）
├── 检查反馈数据质量
│   ├── 近期是否有批量异常反馈？（过滤 outlier）
│   └── 反馈来源是否单一？（需多评价器交叉验证）
├── 检查在线训练
│   ├── 训练频率是否过高？（建议 200 条触发）
│   └── 学习率是否过大？（EMA α 建议 0.1）
└── 回滚方案
    └── 执行 zilli ppm reset → 恢复出厂权重 → 观察 24h
```

### 附录 C：API 兼容性矩阵

Zilli API 兼容 OpenAI Chat Completions API（`/v1/chat/completions`），具体支持如下：

| OpenAI 参数 | Zilli 支持 | 说明 |
|------------|-----------|------|
| `model` | ✅ 完整支持 | 映射到 Zilli 模型画像系统，支持别名（`gpt-4` → `enhanced`） |
| `messages` | ✅ 完整支持 | 标准 message 格式，支持 system/user/assistant/tool |
| `stream` | ✅ 完整支持 | SSE 流式响应，首 token < 500ms |
| `temperature` | ⚠️ 部分支持 | 映射到 StrategySelector 温度（0→ECONOMY, 1→STANDARD, >1→ENHANCED） |
| `max_tokens` | ✅ 完整支持 | 硬限制，超限返回截断标记 |
| `top_p` | ❌ 忽略 | 由 PPM 策略控制，请求参数不生效 |
| `presence_penalty` | ❌ 忽略 | 暂不支持 |
| `frequency_penalty` | ❌ 忽略 | 暂不支持 |
| `logprobs` | ❌ 忽略 | 暂不支持 |
| `tools` | ✅ 完整支持 | 映射到 Zilli Skill 系统，支持 tool_choice=auto/none/forced |
| `tool_choice` | ✅ 完整支持 | 支持 `auto` / `none` / `{"type": "function", "function": {"name": "..."}}` |
| `response_format` | ⚠️ 部分支持 | 支持 `json_object`，映射到输出解析器 |
| `seed` | ❌ 忽略 | 暂不支持确定性输出 |
| `user` | ✅ 完整支持 | 映射到租户 ID（多租户场景） |

**扩展响应头**:
- `X-Zilli-Route`: 实际路由（`fast_lane` / `full_route`）
- `X-Zilli-Cost`: 本次请求成本（USD）
- `X-Zilli-Model`: 实际调用的模型名称
- `X-Zilli-PPM-Difficulty`: PPM 难度评分（0~1）
- `X-Zilli-Request-ID`: 审计追踪 ID

### 附录 D：评估即开发工作流（Eval-Driven Development）

Zilli 提倡"评估即开发"——评估不是开发的终点，而是驱动的起点：

```
开发者提交 Skill 草案
        ↓
Self-Harness 自动生成测试集（held-in + held-out）
        ↓
LoopRunner 执行验证（最大 5 轮重试）
        ↓
Champion-Challenger Arena：新 Skill vs 基线 Skill
        ↓
统计显著？（p < 0.05 且 win_gap > 0.05）
    ├── 是 → 合并到主分支，触发知识蒸馏
    └── 否 → 触发 Skill 进化引擎，生成改进 PR
                ↓
            回到 LoopRunner 验证
                ↓
            达标？→ 合并 / 继续进化（最多 10 轮）
        ↓
轨迹入库（TrajectoryStore）→ 经验回放 → RL 训练
        ↓
策略更新 → 影响未来路由决策 → 闭环
```

**配套指标**:
- **评估→代码转化率**: 每次评估迭代产生的有效代码行数（目标 > 50 LOC）
- **回归率**: 新版本 Skill 导致旧任务失败的比例（目标 < 2%）
- **进化收敛轮数**: 从草案到合并的平均进化轮数（目标 < 3 轮）
- **评估成本占比**: 评估阶段成本占总成本比例（目标 < 15%）

---

> **文档维护**: 本 PRD 随版本迭代更新，变更记录见 `CHANGELOG.md`。  
> **反馈渠道**: GitHub Issues / Discussions / `zilli feedback` CLI。  
> **许可证**: Apache-2.0

### 附录 E：行业合规决策矩阵

#### 医疗行业（HIPAA）MOM 决策速查表

| 输入数据示例 | 检测到的标识符 | 数据分级 | 脱敏操作 | 路由策略 | 允许云端？ | 审计要求 |
|------------|--------------|---------|---------|---------|-----------|---------|
| "患者张三，男，65岁，胸痛" | 姓名、具体年龄 | `CONFIDENTIAL` | 姓名→[NAME]，年龄→区间 | LOCAL_WITH_CLOUD_FALLBACK | 脱敏后 ✅ | PHI 访问日志 |
| "病历号20240818001，诊断心梗" | 病历号 | `REGULATED` | 病历号→[MRN] | LOCAL（强制）或 REJECTED | ❌ | PHI 访问日志 + 违规检测 |
| "阿司匹林与华法林相互作用" | 无 | `PUBLIC` | 无需 | 正常 MOM 路由 | ✅ | 标准访问日志 |
| "CT影像（DICOM含患者ID）" | DICOM 元数据 | `RESTRICTED` | 元数据剥离 | LOCAL（强制） | ❌ | PHI 访问日志 + 影像访问记录 |
| "医保理赔：金额5000元，诊断I21.9" | 金额、ICD-10 | `INTERNAL` | 金额→区间 | LOCAL（强制） | ❌ | 财务访问日志 |

#### 金融行业（SOX/PCI-DSS）MOM 决策速查表

| 输入数据示例 | 检测到的标识符 | 数据分级 | 脱敏操作 | 路由策略 | 允许云端？ | 审计要求 |
|------------|--------------|---------|---------|---------|-----------|---------|
| "客户李四，资产500万，股票60%" | 姓名、精确金额 | `CONFIDENTIAL` | 姓名→[NAME]，金额→区间 | LOCAL_WITH_CLOUD_FALLBACK | 脱敏后 ✅ | SOX 访问日志 |
| "交易：PAN 4111111111111111，金额1000" | PAN（Luhn验证）、金额 | `RESTRICTED` | PAN→[PAN]，金额→[AMT] | LOCAL（强制） | ❌ | PCI-DSS 访问日志 + 交易完整性 |
| "Q3营收增长15%，EPS 2.5" | 无（公开数据） | `PUBLIC` | 无需 | 正常 MOM 路由 | ✅ | 标准访问日志 |
| "信用评分720，逾期2次" | 信用评分、还款历史 | `INTERNAL` | 评分→区间 | LOCAL（强制） | ❌ | FCRA 访问日志 |
| "合同条款：违约金为投资额的10%" | 无（内部政策） | `INTERNAL` | 无需 | LOCAL（强制） | ❌ | 内控访问日志 |

#### 跨行业数据分级映射

| 数据元素 | 医疗（HIPAA） | 金融（SOX/PCI） | 法律（ABA） | 教育（FERPA） | MOM 默认 |
|---------|-------------|----------------|-----------|-------------|---------|
| 姓名 | `REGULATED`（PHI） | `CONFIDENTIAL` | `CONFIDENTIAL` | `REGULATED` | `INTERNAL` |
| 身份证号/SSN | `REGULATED`（PHI） | `RESTRICTED`（PCI） | `RESTRICTED` | `REGULATED` | `RESTRICTED` |
| 电话号码 | `REGULATED`（PHI） | `CONFIDENTIAL` | `CONFIDENTIAL` | `REGULATED` | `INTERNAL` |
| 邮箱地址 | `REGULATED`（PHI） | `CONFIDENTIAL` | `CONFIDENTIAL` | `REGULATED` | `INTERNAL` |
| 精确金额 | `INTERNAL`（理赔） | `RESTRICTED`（SOX） | `CONFIDENTIAL` | `INTERNAL` | `CONFIDENTIAL` |
| 日期（生日/交易日期） | `REGULATED`（PHI） | `RESTRICTED`（PCI） | `CONFIDENTIAL` | `REGULATED` | `CONFIDENTIAL` |
| 账户号码 | `REGULATED`（PHI） | `RESTRICTED`（PCI） | `RESTRICTED` | `REGULATED` | `RESTRICTED` |
| 诊断/成绩/评级 | `REGULATED`（PHI） | `CONFIDENTIAL`（信用） | `CONFIDENTIAL` | `REGULATED` | `CONFIDENTIAL` |
| 公开文献/财报 | `PUBLIC` | `PUBLIC` | `PUBLIC` | `PUBLIC` | `PUBLIC` |
| 内部政策/会议纪要 | `INTERNAL` | `INTERNAL` | `INTERNAL` | `INTERNAL` | `INTERNAL` |

#### 行业合规审计检查清单

**医疗（HIPAA Security Rule）**:
- [ ] 所有 PHI 访问记录完整（164.312(b) 审计控制）
- [ ] 去标识化流程验证（Safe Harbor 18 项检查）
- [ ] 本地模型处理 PHI 的证明（无出境日志）
- [ ] 年度风险评估报告（164.308(a)(1)）
- [ ] 违规通知检测（>500 人触发 HITECH）

**金融（SOX 404 + PCI-DSS）**:
- [ ] 交易数据 100% 本地处理证明（SOX 404 内控）
- [ ] PAN 数据零出境证明（PCI-DSS 要求 3.4）
- [ ] 数据访问控制季度测试（SOX ITGC）
- [ ] 管理员访问日志审查（PCI-DSS 要求 10.2）
- [ ] 年度合规报告（管理层声明 + 审计师测试）


#### 法律行业（ABA / 特权保护）MOM 决策速查表

| 输入数据示例 | 检测到的标识符 | 数据分级 | 脱敏操作 | 路由策略 | 允许云端？ | 审计要求 |
|------------|--------------|---------|---------|---------|-----------|---------|
| "客户王五委托处理与赵六公司的合同纠纷，金额500万" | 客户姓名、对方公司名、精确金额 | `CONFIDENTIAL` | 姓名→[CLIENT_NAME]，公司→[COUNTERPARTY]，金额→区间 | LOCAL_WITH_CLOUD_FALLBACK | 脱敏后 ✅ | ABA 1.6 访问日志 |
| "律师-客户特权：我方策略是主张违约+索赔，准备反诉商业秘密" | 特权标记、策略讨论 | `RESTRICTED` | 策略内容标记为 Work Product | LOCAL（强制） | ❌ | 特权访问日志 + Work Product 控制 |
| "检索支持合同纠纷的先例判例" | 无（公开法律信息） | `PUBLIC` | 无需 | 正常 MOM 路由 | ✅ | 标准访问日志 |
| "尽职调查：目标公司营收5000万，知识产权3项专利" | 目标公司名、精确金额 | `CONFIDENTIAL` | 公司→[TARGET]，金额→区间 | LOCAL_WITH_CLOUD_FALLBACK | 脱敏后 ✅ | 利益冲突检查日志 |
| "内部合规手册：员工不得接受超过1000元礼品" | 无（内部政策） | `INTERNAL` | 无需 | LOCAL（强制） | ❌ | 内控访问日志 |
| "诉讼策略模拟：对方当事人赵六，证据清单..." | 对方当事人名、策略文件 | `RESTRICTED` | 当事人→[COUNTERPARTY]，策略标记 | LOCAL（强制） | ❌ | 特权访问日志 + 利益冲突告警 |

#### 教育行业（FERPA / COPPA）MOM 决策速查表

| 输入数据示例 | 检测到的标识符 | 数据分级 | 脱敏操作 | 路由策略 | 允许云端？ | 审计要求 |
|------------|--------------|---------|---------|---------|-----------|---------|
| "学生陈七，学号202408001，数学85分、语文78分" | 学生姓名、学号、具体成绩 | `REGULATED` | 姓名→[STUDENT_NAME]，学号→[STUDENT_ID]，成绩→区间 | LOCAL（强制） | ❌ | FERPA 访问日志 |
| "班级成绩分布：平均分82分，标准差8分" | 无（聚合统计） | `CONFIDENTIAL` | 无需（已聚合） | LOCAL_WITH_CLOUD_FALLBACK | 匿名化后 ✅ | 研究例外日志 |
| "生成高中物理力学章节练习题" | 无（公开教材） | `PUBLIC` | 无需 | 正常 MOM 路由 | ✅ | 标准访问日志 |
| "申请者GPA 3.8，托福110，推荐人评价优秀" | 申请者成绩、推荐人评价 | `CONFIDENTIAL` | 申请者 ID 替换，成绩区间化 | LOCAL_WITH_CLOUD_FALLBACK | 脱敏后 ✅ | 招生访问日志 |
| "学生出勤率下降，图书馆访问减少，食堂消费降低" | 学生行为记录 | `INTERNAL` | 学生 ID 替换 | LOCAL（强制） | ❌ | 行为数据访问日志 |
| "8岁学生小明，家长电话13800138000，需家长同意使用AI辅导" | 儿童姓名、年龄、家长信息 | `REGULATED` | 姓名→[STUDENT_NAME]，电话→[PHONE] | LOCAL（强制）或 REJECTED | ❌ | COPPA 家长同意日志 |
| "分析教学法A与教学法B对学生成绩的影响（去标识化数据，k=5, ε=0.5）" | 无（差分隐私数据） | `CONFIDENTIAL` | 差分隐私已应用 | LOCAL_WITH_CLOUD_FALLBACK | 匿名化后 ✅ | IRB 审查 + 研究例外日志 |

#### 跨行业数据分级映射（完整版）

| 数据元素 | 医疗（HIPAA） | 金融（SOX/PCI） | 法律（ABA） | 教育（FERPA） | MOM 默认 |
|---------|-------------|----------------|-----------|-------------|---------|
| 姓名 | `REGULATED`（PHI） | `CONFIDENTIAL` | `CONFIDENTIAL`（客户） | `REGULATED`（学生） | `INTERNAL` |
| 身份证号/SSN | `REGULATED`（PHI） | `RESTRICTED`（PCI） | `RESTRICTED`（客户身份） | `REGULATED`（学生） | `RESTRICTED` |
| 电话号码 | `REGULATED`（PHI） | `CONFIDENTIAL` | `CONFIDENTIAL` | `REGULATED`（学生/家长） | `INTERNAL` |
| 邮箱地址 | `REGULATED`（PHI） | `CONFIDENTIAL` | `CONFIDENTIAL` | `REGULATED`（学生） | `INTERNAL` |
| 精确金额 | `INTERNAL`（理赔） | `RESTRICTED`（SOX） | `CONFIDENTIAL`（合同） | `INTERNAL`（学费） | `CONFIDENTIAL` |
| 日期（生日/交易日期） | `REGULATED`（PHI） | `RESTRICTED`（PCI） | `CONFIDENTIAL` | `REGULATED`（学生） | `CONFIDENTIAL` |
| 账户号码 | `REGULATED`（PHI） | `RESTRICTED`（PCI） | `RESTRICTED`（客户账户） | `REGULATED`（学号） | `RESTRICTED` |
| 诊断/成绩/评级 | `REGULATED`（PHI） | `CONFIDENTIAL`（信用） | `CONFIDENTIAL`（案情） | `REGULATED`（成绩） | `CONFIDENTIAL` |
| 策略/意见/法律建议 | — | — | `RESTRICTED`（特权） | — | `INTERNAL` |
| 学生行为记录 | — | — | — | `REGULATED`（FERPA） | `INTERNAL` |
| 家长信息（COPPA） | — | — | — | `REGULATED`（COPPA） | `INTERNAL` |
| 公开文献/财报/判例/教材 | `PUBLIC` | `PUBLIC` | `PUBLIC` | `PUBLIC` | `PUBLIC` |
| 内部政策/会议纪要 | `INTERNAL` | `INTERNAL` | `INTERNAL` | `INTERNAL` | `INTERNAL` |
| 儿童信息（<13岁） | `REGULATED`（PHI） | `CONFIDENTIAL` | `CONFIDENTIAL` | `REGULATED`（COPPA） | `REGULATED` |

#### 行业合规审计检查清单（完整版）

**医疗（HIPAA Security Rule）**:
- [ ] 所有 PHI 访问记录完整（164.312(b) 审计控制）
- [ ] 去标识化流程验证（Safe Harbor 18 项检查）
- [ ] 本地模型处理 PHI 的证明（无出境日志）
- [ ] 年度风险评估报告（164.308(a)(1)）
- [ ] 违规通知检测（>500 人触发 HITECH）
- [ ] BAA 协议验证（与云端提供商的业务伙伴协议）

**金融（SOX 404 + PCI-DSS）**:
- [ ] 交易数据 100% 本地处理证明（SOX 404 内控）
- [ ] PAN 数据零出境证明（PCI-DSS 要求 3.4）
- [ ] 数据访问控制季度测试（SOX ITGC）
- [ ] 管理员访问日志审查（PCI-DSS 要求 10.2）
- [ ] 年度合规报告（管理层声明 + 审计师测试）
- [ ] 可疑交易报告（SAR）访问审计（AML 要求）

**法律（ABA + 特权保护）**:
- [ ] 特权信息 100% 本地处理证明（Attorney-Client Privilege）
- [ ] Work Product 访问控制日志（策略文件仅限案件团队）
- [ ] 客户信息脱敏记录（ABA 1.6 保密义务）
- [ ] 利益冲突检查日志（每次涉及当事人名称时自动检索）
- [ ] 年度职业责任合规报告（保密、利益冲突、称职义务审查）
- [ ] Malpractice 保险风险评估（AI 辅助决策的责任归属）

**教育（FERPA + COPPA）**:
- [ ] 学生教育记录 100% 本地处理证明（FERPA 99.10）
- [ ] 家长同意记录（COPPA：家长姓名、同意时间、同意范围、撤回记录）
- [ ] 目录信息退出状态验证（FERPA 99.37：学生选择退出目录信息的记录）
- [ ] 去标识化教育数据匿名化验证（k-匿名 ≥ 5，差分隐私 ε ≤ 1.0）
- [ ] 年度 FERPA 合规报告（教育记录访问统计、披露记录、第三方接收者清单）
- [ ] 违规通知（Breach Notification）：学生教育记录泄露 > 5000 人触发通知
- [ ] IRB 伦理审查标记（研究场景使用去标识化教育数据）
