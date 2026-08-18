# Changelog

## Unreleased (2026-08-18)

### e2e 集成测试批次（route → execute → feedback → evolve）

1105 tests / ruff 0 / pyright 0 / 覆盖率 86.0%。

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

