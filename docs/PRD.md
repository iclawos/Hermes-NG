# Zilli — 产品需求文档

## 1. 产品概述

Zilli（原 Hermes-NG）是一个面向 AI 自主开发的下一代 Agent 工具工程方案。核心理念："AI 写 AI"、"评估即开发"、"从环境中来"、"从 Agent 到 RL"。

### 愿景

构建一个能够**自我进化**的 AI 开发 Agent 框架——Agent 不仅执行任务，还能从执行轨迹中学习、进化自身技能、优化路由决策、并在持续反馈中收敛到最优行为。

### 核心能力矩阵

| 能力 | 状态 | 说明 |
|------|------|------|
| 多模型路由（Plan→Execute→Review） | ✅ 生产就绪 | 三阶段混合路由 + 行业合规路由 |
| GPS-MOM 预测路由 | ✅ 生产就绪 | PPM + 三档策略 + 模型画像 + 反馈闭环 |
| RL 训练（CISPO/GRPO） | ✅ 生产就绪 | 策略优化 + 优势估计 + 批量训练 |
| 技能自进化 | ✅ 生产就绪 | 4 策略 + 多样性控制 + MOM 反馈闭环 |
| Loop 循环引擎 | ✅ 生产就绪 | 重试 → 验证 → 修正 → 升级 |
| 自适应 Self-Harness | ✅ 生产就绪 | 弱点挖掘 → 有界提案 → 分体验证 |
| 知识蒸馏 | ✅ 生产就绪 | BC + KL + RL + Embedding 正则化 |
| Champion-Challenger Arena | ✅ 生产就绪 | 统计显著性检验的模型擂台 |
| 预算/成本控制 | ✅ 生产就绪 | DynamicSOTA + 频率控制器 + 月度预算 |
| 隐私合规 | ✅ 生产就绪 | PII 检测、脱敏、审计日志、数据隔离 |
| Streamlit 管理台 | ✅ 基础版 | 审计浏览、成本监控、系统状态 |
| API 服务器 | ✅ 生产就绪 | FastAPI，OpenAI 兼容接口 |
| Celery 分布式工作流 | ✅ 生产就绪 | DAG 持久化执行、任务重试、结果回调 |
| ChromaDB 向量存储 | ✅ 生产就绪 | 语义检索、元数据过滤、集合管理 |
| 行业工作流 | ✅ 生产就绪 | 法律/医疗/金融/教育合规路由 |
| SWE-bench 修复 | ✅ 生产就绪 | Bug 复现 → 探索 → 诊断 → 修复 → 验证 |
| Rust 辅助库 | 📋 已决策 | 项目内 Rust helper crate（尚未实现） |
| CI/CD | 📋 待接入 | GitHub Actions 自动执行 706 测试 |

## 2. 目标用户

| 用户画像 | 需求 | 使用场景 |
|----------|------|----------|
| AI Agent 开发者 | 快速构建能自我进化的 Agent | 使用 Zilli 框架开发 Agent 应用 |
| RL 工程师 | 训练和优化 Agent 策略 | 运行 RL 训练循环 + 知识蒸馏 |
| 研究科学家 | 探索 Agent 自我改进机制 | 研究 Self-Harness、技能进化 |
| 企业部署 | 安全的合规 Agent 部署 | 行业工作流 + 审计 + 隐私 |
| OSS 贡献者 | 参与 AI Agent 工具开发 | 阅读源码、提交 PR |

## 3. 功能需求

### 3.1 核心路由系统

#### F-1 多模型平面路由
- **描述**: 根据请求特征选择 FULL_ROUTE（Plan→Execute→Review）或 FAST_LANE（直接执行）
- **输入**: 用户请求文本 + 可选的行业上下文
- **输出**: `RouteResult`（final_text + 各阶段结果 + 耗时）
- **验收标准**: 简单请求走 FAST_LANE，复杂请求走 FULL_ROUTE；RouteClassifier 模式匹配准确率 > 80%

#### F-2 GPS-MOM 智能路由
- **描述**: 基于 PPM 预测 → 策略选择 → 模型画像 → 模型选择的四步决策流水线
- **组件**:
  - PPM（前置预测器）: 分类任务家族（6 类）+ 难度评分（0~1）+ LRU 缓存
  - StrategySelector: 三档策略（ECONOMY/STANDARD/ENHANCED），基于难度+预算
  - ModelProfile: 5 维能力画像 + 贝叶斯 EMA 更新 + softmax Thompson 采样
  - FeedbackCollector: 异步队列 + JSONL 批量持久化 + 评价器
- **验收标准**: 简单聊天直通 fast-lane；高难度 + 低预算正确走 ENHANCED；反馈闭环 100 条触发更新

#### F-3 模型能力画像系统
- **描述**: 在线追踪模型成功率、5 维能力向量，支持加权 softmax 模型选择
- **存储**: JSON 原子持久化（tmp→replace）
- **更新**: EMA（α=0.3 for 能力, α=0.1 for 成功率）

### 3.2 训练系统

#### F-4 RL 训练管线
- **算法**: CISPO（Conservative Importance Sampling Policy Optimization）/ GRPO（Group Relative Policy Optimization）
- **数据流**: Rollout → 轨迹存储 → 混合采样（golden_ratio=0.5）→ 优势估计（MC+GAE）→ 损失计算 → 策略更新
- **验收标准**: 训练后策略损失收敛；无 Value Network 场景 GRPO 正确运行

#### F-5 知识蒸馏
- **描述**: 从 Planner（教师）蒸馏知识到 Executor（学生）
- **损失函数**: BC loss + KL 散度 + RL loss + Embedding 距离正则化（δ=0.5）
- **触发**: 自动间隔（默认 24h），或在 LoRA 阈值（1000 样本）或全 SFT 阈值（7 天）触发
- **验收标准**: 蒸馏后 Executor 保持率 ≥ 教师 90%

#### F-6 Champion-Challenger Arena
- **描述**: 双模型统计对决，胜者成为新的 Champion
- **统计**: 显著性检验（min_win_gap=0.05）
- **输出**: Leaderboard（ELO + 能力雷达图）

### 3.3 自我进化系统

#### F-7 技能进化引擎
- **描述**: 从一个项目的 .py/.md 文件中提取技能模块 → 轨迹反思 → 进化策略应用 → 多样性门控 → PR 输出
- **4 种策略**: prompt_optimization, error_handling, boundary_refinement, tool_addiction
- **验收标准**: 单策略和多策略模式均可正常工作；多样性控制器拒绝相似度 > 阈值 的突变

#### F-8 Loop 循环引擎
- **描述**: 通用 Retry→Verify→Correct 循环
- **实现**: `LoopRunner[T]`（泛型）+ `MetaLoopRunner`（双层元循环）
- **触发器**: FixedInterval / Event / DynamicInterval
- **验证器**: TestSuite / Predicate / ExternalModel / Skill / Composite

#### F-9 Self-Harness（自我改进的 Harness）
- **描述**: 三阶段元循环——弱点挖掘（WeaknessMiner 聚类）→ 有界提案（Bounded Harness Edit）→ 分体验证（held-in/held-out）
- **验收标准**: 产生可操作的 HarnessEdit；分体通过率改善 ≥ 5% 且无回归时接受

#### F-10 多样性控制
- **描述**: 防止群体崩溃的 novel 性压力
- **机制**: 代码指纹提取（6 维加权 Jaccard）+ n-gram 指纹 + fitness-sharing 剪枝 + 温度加权亲本选择
- **验收标准**: 完全相同代码被拒绝；阈值可调（0.0=全部接受, 1.0=全部拒绝）

#### F-11 ACE 上下文策展
- **描述**: Agentic Context Engineering——增量式结构化上下文管理
- **机制**: `ContextBullet` 条目管理 → `reflect()` 从轨迹提炼洞察 → `format_context()` 输出 markdown

### 3.4 运维与合规

#### F-12 成本控制
- **描述**: 月度预算、小时配额、Thompson Sampling 阈值、紧急模式（余额 < 10% 时触发）
- **组件**: `CostController` + `DynamicSOTAScheduler` + `PlannerBudget`

#### F-13 隐私合规
- **描述**: PII 检测（3 级）、数据脱敏、行业合规（HIPAA/SOX/FERPA）、审计日志
- **组件**: `PrivacyEngine` + `InputSanitizer` + `AuditLogger` + `WorkflowRegistry`

#### F-14 API 服务器
- **描述**: FastAPI 服务器，OpenAI 兼容接口，流式响应，速率限制，API Key 认证
- **端点**: `/v1/chat/completions`, `/health`, `/dashboard/*`

#### F-15 Celery 分布式工作流
- **描述**: Celery + Redis 的 DAG 工作流执行引擎
- **功能**: DAG 持久化、任务重试、结果回调、工作流状态追踪

### 3.5 预测与反馈（新增）

#### F-16 PPM 在线训练
- **描述**: 基于实际反馈数据调整 PPM 的难度预测权重
- **机制**: 每条反馈记录包含 prediction vs actual → EMA 更新各家族权重参数 → 自动清缓存
- **验收标准**: 训练后权重发生有意义的偏移；reset 恢复出厂值

#### F-17 LLM-as-Judge 评分
- **描述**: 使用 LLM 对响应质量进行评分（0~1）
- **机制**: 构建评分 Prompt → 调用任意 async llm_generate → 正则解析 `Rating: X.XX` → 失败时回退到 heuristic
- **验收标准**: 正确解析 `Rating: 0.85`；异常情况下回退到 auto_score；stats 追踪调用/回退计数

## 4. 非功能需求

| 需求 | 目标 | 衡量方式 |
|------|------|----------|
| 测试覆盖 | > 85% | pytest 覆盖率报告 |
| 路由延迟 | PPM 预测 < 10ms | latency_ms 统计 |
| 缓存命中率 | > 60% | PPM cache hit_rate |
| 进化收敛 | 连续 3 轮无新 PR | 进化引擎 self-verification |
| 内存安全 | 无安全隐患 | ruff + pyright 静态检查 |
| 模型选择 | 成本优化 > 30% | StrategySelector 预算利用率 |
| 反馈闭环 | 100 条触发批量持久化 | FeedbackCollector batch_size |

## 5. 依赖分析

| 依赖 | 用途 | 替代方案 |
|------|------|----------|
| pydantic | Schema 定义 | msgspec |
| pyyaml | 配置管理 | tomli |
| numpy | 数值计算 | — |
| httpx | HTTP 客户端 | aiohttp |
| dspy-ai | 语言模型调用 | litellm |
| torch（可选） | GPU 加速训练 | — |
| fastapi（可选） | API 服务器 | starlette |
| celery（可选） | 分布式工作流 | arq |
| chromadb（可选） | 向量存储 | lancedb |

## 6. 功能路线图

### Phase 1（已完成 ✅）
- 项目骨架：Schema、TaskRunner、Sandbox
- 轨迹存储：TrajectoryStore、经验回放
- RL 基础设施：训练配置、长度控制、异步调度
- RL 算法：CISPO + GRPO + VerifiableReward
- 进化引擎：SkillEvolutionEngine + ContinuousLearner + CLI

### Phase 2（已完成 ✅）
- 品牌更名 Hermes-NG → Zilli
- 8 个代码结构问题修复
- 生产数据读取替代桩代码
- CLI evaluate 重写

### Phase 3 路由系统（已完成 ✅）
- RouteClassifier 正则 + LLM 路由
- LocalHybridRouter 三阶段路由（Plan→Execute→Review）
- 安全脱敏 + 缓存 + 预算控制
- GPS-MOM：PPM + Strategy + Profile + Feedback + MOMRouter
- 14 个自我进化 Bug 修复 + 收敛验证

### Phase 4 循环工程（已完成 ✅）
- LoopRunner / MetaLoopRunner
- 5 种验证器 + 3 种触发器
- 升级处理 + 循环记忆
- WeaknessMiner 失败聚类
- Self-Harness 三阶段元循环
- ContextCurator（ACE）

### Phase 5 生产增强（已完成 ✅）
- 隐私引擎 + PII 检测 + 数据隔离
- 审计日志 + 合规报告
- 行业工作流（法律/医疗/金融/教育）
- Streamlit Dashboard
- Celery 分布式工作流
- ChromaDB 向量存储
- Trainer 频率控制器
- 模型画像系统（ELO + 雷达图）

### Phase 6 自我进化收敛（已完成 ✅）
- PPM 在线训练
- LLM-as-Judge 评分
- MOMRouter 接入 Harness 模式
- 706 测试通过，lint 干净

### Phase 7（规划中 📋）
- 接入 CI（GitHub Actions）
- Model-based PPM（ONNX/Triton 替代 regex）
- 端到端进化训练管线整合
- Rust 辅助库实现
- 多租户支持
