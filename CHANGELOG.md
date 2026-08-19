# Changelog

## Unreleased (2026-08-19)

### Swarm 审计修复（k3 代码审计）

对 L6 swarm 包 + routing/profile 的专项审计，修复 6 项发现，补 6 个测试（1247→1253 tests）。

#### Fixed
- **consensus**：`ConsensusRecord.human_escalated` 字段从未被填充（`_decide` 写的是引擎级残留状态且跨调用不清除）——改为在 `reach()` 内按 level 直接置位，删除引擎级 `_human_escalated` 属性
- **orchestrator**：并行分支下 `final_text` 取"最后完成"的子任务产物——完成顺序由时序决定导致结果不可复现；改为确定性取 sink 节点（无下游依赖者）中声明顺序最后的 done 节点
- **decomposer**：`MAX_DEPTH = 6` 已声明但从未执行——补上最长依赖链深度校验（新增 `max_depth` 构造参数）
- **artifacts**：产物被 `consume()` 后状态变 `consumed`，导致下游依赖判定为未满足而死锁——`pending_dependencies` 现在把 `consumed` 视为已满足
- **router**：`_pick_model` 访问 `ModelProfile._models` 私有成员，且子串匹配优先于精确匹配——改用新增公开访问器 `ModelProfile.models()`，精确匹配优先、子串匹配兜底
- **orchestrator**：`_FreeSchema` 改用 `ConfigDict(extra="allow")`，移除 `# type: ignore`；清理 `_run_dag` 中不再使用的 `completed` 列表

#### Tests
- consensus：`human_escalated` 置位 / 非 HUMAN 不误标（2 tests）
- decomposer：深度上限拒绝 7 层链 / 6 层链通过（2 tests）
- artifacts：consumed 依赖仍可运行（1 test）
- orchestrator：并行分支 sink 确定性（含 3 次重复一致性）（1 test）

#### Docs
- `docs/engineering-plan.md`：能力成熟度阶梯 L6 行由"🔮 待规划"更正为"✅ RFC-006"

### Rust 演化核心热路径（PPM 预测迁移至 Rust）

`zilli_hotpath` PyO3 绑定 v0.3.0，与纯 Python `RegexClassifier` **功能一致性 100%**（parity 14/14 含中文样本），性能 ~20×。

1244→1247 tests / ruff 0 / pyright 0 / 覆盖率 90%。

#### Added
- **`zilli-rs/hotpath/`**：PyO3 扩展 crate（workspace 成员），暴露 `ppm_predict(text)`：
  - 家族预测：与 Python `_predict_family` 相同的正则 + 优先级（code→reasoning→analysis→creative→simple→unknown）
  - 难度预测：与 Python `_predict_difficulty` 相同的权重表 + 长度/关键词/复杂/架构/数学奖励
  - 置信度：与 Python `_estimate_confidence` 相同的长度阈值（<10→0.95，>500→0.6，否则 0.8）
- **maturin 构建**：`pip install zilli[rust]` 兼容，wheel 已安装（`zilli_hotpath-0.3.0`）
- **`tests/test_ppm_classifier.py::TestRustHotpathParity`**：3 tests（importable / parity / 性能 ≥5×）
- **性能**：7.7µs/call vs 纯 Python 155µs/call ≈ **20.2×**（目标 10× 达成）

#### Fixed
- 已安装的 `zilli-hotpath` 0.1.0（无源码、未入库）与 Python 实现**不一致**（置信度阈值错误、难度数学错误），已用 v0.3.0 替换

#### Tests
- 1244 → **1247** tests；Rust `cargo test` 38+12 = 50 passed，clippy 0 warnings

### L6 群智能（Swarm Intelligence）里程碑

多 Agent 协作骨架落地。RFC-006 + `zilli/swarm/` 包 + `zilli swarm` CLI。

1244 tests / ruff 0 / pyright 0 / 覆盖率 90%。

#### Added
- **`docs/rfc-006-l6-swarm-intelligence.md`**：L6 群智能设计 RFC——Agent 间路由、任务分解、共识机制；与 MOM 三层复用关系、产物图（Artifact Graph）、四级共识链、里程碑/验收指标
- **`zilli/swarm/` 包**（6 模块）：
  - `roles.py`：AgentRoleSpec 角色注册表（researcher/architect/writer/verifier/reviewer/executor，工具白名单+上下文预算+回退角色）
  - `artifacts.py`：Artifact + ArtifactGraph（产物 DAG，schema 校验、状态机、GC）+ SubTask
  - `decomposer.py`：TaskDecomposer（PPM 难度阈值、扇出上限、无环校验、依赖解析）
  - `consensus.py`：ConsensusEngine（四级共识链：多数→权重投票→仲裁→人工升级）
  - `router.py`：AgentRouter（子任务→角色+模型槽位，未知角色回退 executor，角色回退）
  - `orchestrator.py`：SwarmOrchestrator（分解→路由→并行执行→产物图→验证→反馈，并发上限、死锁检测）
- **`zilli swarm` CLI**：`zilli swarm "任务" --industry X --difficulty 0.8`；`zilli swarm --roles` 列出角色
- **`tests/test_swarm.py`**：40 tests（roles/artifacts/decomposer/consensus/router/orchestrator/CLI）

#### Tests
- 1204 → **1244** tests

### 覆盖率 90% 里程碑（CLI + 小模块补测）

1204 tests / ruff 0 / pyright 0 / 覆盖率 90.0%。

#### Added
- `tests/test_cli_coverage.py`：CLI 处理器与关键小模块覆盖补测：
  - CLI：`route`（含 `--verbose` 全输出/截断路径）、`industry run/list`、`models list/health/generate`、`cost status/reset`、`evaluate --cost-aware`、`train --cost-aware`、`pipeline`、`soak`（stop-file 退出）、`swe`、`unknowns summary/resolve/interview/blind-spot/brainstorm/reference/plan`
  - `ModelProfile`（routing）：filter/select_best/softmax/exploration/capability/success 更新与持久化加载
  - `ContinuousLearner`：run() 单周期与异常路径、stop、collect/archive、SFT 触发日志
  - `TrajectoryStore`：priority 采样/purify/噪声/容量上限/误差摘要
  - `HermesSandbox`：未知工具/error_probability/scenario 初始化/技能与文件操作/bash/web/code
- `tests/test_models.py`：registry fallback 链（unhealthy→error→exception→下一模型）、generate_local/cloud
- `tests/test_server.py`：metrics、cache stats/clear、OpenAI models、cost-configured app、RateLimiter

#### Fixed
- **`UnknownsDiscovery._load()` 不把 JSON 中的 `category` 反序列化为 `UnknownCategory` 枚举**：持久化重载后 `u.category.value` 崩溃（`AttributeError: 'str' object has no attribute 'value'`）。现在加载时显式转换

#### Tests
- 覆盖率 86.0% → **90.0%**（`cli.py` 57%→94%，`loops/unknowns` 68%→96%，`learner/continuous_learner` 75%→96%，`routing/profile` 79%→94%，`data/experience_replay` 84%→94%，`envs/mock_env` 83%→94%）
- 1105 → **1204** tests

### e2e 集成测试批次（route → execute → feedback → evolve）

#### Added
- `tests/test_e2e_route_execute_feedback_evolve.py`：补齐 e2e 链条缺失的 **execute 环节**（此前 route→feedback→evolve 不执行真实任务）：
  - route → `Agent` 真实子进程执行 → feedback → evolve 全链路
  - 执行失败轨迹驱动 error_handling 进化
  - route → `HybridExecutor`（mock registry）→ feedback
  - PPM 分类器 Python 回退路径难度分支全覆盖（coding complex/arch、reasoning math/analysis、analysis bonus、chat 负向、自定义权重、unknown）——强制禁用 rust 热路径以覆盖纯 Python 分支
  - ModelRegistry fallback 链（注册/未知后端跳过/无健康模型/部署路径/主模型失败回退下一模型）

#### Fixed
- **`ModelRegistry.generate()` / `_generate_by_deployment()` 不检查 `GenerationResult.error`**：此前主模型返回 error-bearing 结果会直接返回而非回退链上下一模型，fallback 机制失效。现在 error 结果视为失败并继续尝试下一模型（`lower_tier` 语义对齐）

#### Tests
- 覆盖率 85.0% → **86.0%**（`ppm_classifier` 56%→73%，`models/registry` 60%→81%）
- 1087 → **1105** tests

### v1.1.0 候选批次（T-10 + 并发 + 热更新 + 嵌套回替）

1087 tests / ruff 0 / pyright 0 / 覆盖率 85.0%。

#### Added
- **多租户密钥绑定（T-10 关闭）**：`ZILLI_API_KEYS` 支持 `key@tenant` 绑定格式，请求 `X-Tenant-ID` 与密钥绑定租户强制校验——跨租户 / 伪造租户 / 缺租户头一律 401；`ZilliAppState.bind_tenant_key()` 运行时注册；未绑定全局 key 不受限（平台管理员）
- **行业模板动态加载（运行时热更新）**：`WorkflowRegistry` 支持从 `ZILLI_INDUSTRY_CONFIG` 目录加载 YAML 模板（framework→industry 映射，含 `hipaa/sox/aba/ferpa` 别名），`reload_templates()` 无重启热更新 + 删除检测 + 审计保留期换算；新增 `GET /v1/industry/list` 与 `POST /v1/industry/reload`
- **EntityReplacer / EntityRestorer（嵌套结构）**：新增 `zilli/privacy/entities.py`，PII 占位符替换（`[EMAIL]`/`[EMAIL_1]`）与回替，支持 dict/list/tuple/JSON 字符串递归处理；`EntityMap` 可序列化持久化

#### Changed
- `EvolveToTrainPipeline._stage_evolve` 串行进化 → asyncio 并发（`evolution_concurrency` 配置，默认 4），单文件失败仅记 rejected 不中断批次，兼容同步/异步 evolve

#### Tests
- 新增 39 项：T-10 密钥绑定（跨租户/伪造/缺头/全局放行/运行时绑定）、并发进化（峰值并发/异步引擎/失败计数/diversity）、行业模板加载（YAML 热更新/增删/别名/审计保留期/环境变量）、Entity 嵌套 roundtrip
- 1048 → **1087** tests，覆盖率保持 **85.0%**

### kimi k3 二次审查批次（H1–H20 高危 + M1–M13 中危）

#### Security
- **API 鉴权改为 fail-closed**：未配置 `ZILLI_API_KEYS` 时，非本地客户端请求一律 401（此前 fail-open 全部放行）；`127.0.0.1`/`::1` 仍放行便于本地开发
- **Dashboard 强制凭据**：未设置 `ZILLI_DASHBOARD_PASSWORD` / `ZILLI_DASHBOARD_USERS` 时拒绝启动并提示配置方法（此前默认 admin/admin）；密码比较改用 `hmac.compare_digest`
- **测试不再触碰真实预算文件**：新增 `ZILLI_BUDGET_FILE` 环境变量覆盖，CLI/成本测试全部隔离到临时目录（此前测试会删除/重置 `~/.zilli_budget.json`）

#### Fixed
- `FeedbackCollector` 后台 flush task 持有强引用，`stop()` 正确取消（此前 task 引用被丢弃，可能被 GC 回收）
- `TaskRunner` 死锁/依赖失败时未运行的 step 返回 failed `StepResult`（此前必然 `KeyError`）
- `review()` 不再把修正文本截断为 200 字符残片；空修正回退 draft
- `evolve()` 单策略 diversity 拒绝的 PR 现在带 `# Diversity rejected` 标记，CLI 统计不再误记为 accepted
- `docs/reference-distillation.md` 全文重写对齐真实 API（`reward_gamma`、`DistillationCycle`、classmethod `load_checkpoint`、`device_utils`、`BenchmarkTracker.record_before/after/ab_result`）
- `AGENTS.md` 项目结构同步至 v1.0.0 实际布局

#### Tests
- 新增 20 项回归测试：fail-closed 鉴权、localhost 放行、dashboard 无凭据拒绝、死锁 StepResult、协程 step、review 全量/空修正/错误回退、execute_batch 成功与逐任务错误、plan/execute 错误抛出、反馈持久化失败容错、单事件循环 start/record/stop、`run_forever` 连续失败停止/触发器停止/weakness mining
- 覆盖率 85.1% → 84.5%（安全新分支）→ 补测回升至 **85.0%**

#### Known Issues
- **T-12**：EntityRestorer 此前不存在（文档先于实现），本轮已补建并支持嵌套结构

## v1.0.0 (2026-07-26)

### 里程碑
全部 v1.0.0 发布标准达成。1028 tests / ruff 0 / pyright 0 / 覆盖率 85.1%。

### Added
- **模型化 PPM 默认分类器**：sklearn Pipeline（char_wb 2-5 gram，CJK 安全），2583 样本训练，acc 1.0 / RMSE 0.044；分类器链 model → regex(+rust)
- **`zilli soak`**：端到端自进化闭环持续运行器——健康监控、崩溃恢复（指数退避）、指标 JSONL 落盘、停止信号文件
- **多租户持久化**：`TenantManager.from_yaml()` / `save_yaml()`
- **PyO3 绑定**：`zilli_hotpath` wheel（maturin 构建），PPM 预测 0.054ms
- **API server 审计追踪**：`/v1/route` → `route_decision`、`/v1/chat/completions` → `model_call` 落盘
- **参考文档 × 4**：routing / evolution-loops / server-tenancy / distillation
- **安全审计报告**：`docs/security-audit-v1.md`

### Fixed
- **P1**：API server 审计日志断链（合规报告无数据源）
- **P1**：`run_training.main()` 用官方默认配置必然崩溃（extra="forbid" 配置过滤缺失）
- **P2**：`/docs` 无鉴权暴露 → `ZILLI_API_DOCS` 环境门控
- **P2**：`SklearnONNXClassifier` 推理实现全错（单文档 fit 向量化器 + ONNX 输入类型错误）→ 重写 joblib/ONNX 双格式加载
- **P2**：dashboard `st.secrets` 无文件时崩溃
- **P3**：子进程超时未 kill（agent/verification/swe sandbox）
- **P3**：soak backoff 不检查 deadline
- **P3**：ONNX 对 CJK 不可转换（skl2onnx 不支持 char_wb）→ 优雅回退 joblib

### Changed
- 版本 0.5.0 → 1.0.0
- PPM 训练默认 char_wb 分析器（中文支持）
- SoakHealth.healthy 阈值与 runner max_consecutive_failures 统一

## v0.5.0 (2026-07-23)

- 贝叶斯 MetaEvaluator（高斯共轭先验）
- SOTA 硬约束 max_sota_ratio
- 合规导出 CLI（6 框架）
- DAG Mermaid 可视化
- Fable 未知项全生命周期（F-19/F-23）
- 多租户基础、PPM 生产反馈闭环、Harness 真实技能库验证
- Rust hotpath（PPM + 指纹）
- 循环导入清零、异步死锁修复、反馈批量早触发
- CI：lint + pyright + 多版本测试

