# Changelog

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

