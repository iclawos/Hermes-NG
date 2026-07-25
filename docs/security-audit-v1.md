# Zilli 安全审计报告 (v1.0.0-rc)

**审计日期**: 2026-07-26
**范围**: API server 鉴权、限速、输入安全、隐私治理、审计追踪、合规导出

---

## 审计结论：通过 ✅

| 维度 | 状态 | 说明 |
|------|------|------|
| API 鉴权 | ✅ | Bearer + X-API-Key 双通道，`hmac.compare_digest` 常量时间比较，密钥仅存 SHA-256 哈希 |
| 速率限制 | ✅ | 滑动窗口限速器（60 req/min/IP），周期清理过期键 |
| 请求体限制 | ✅ | 10MB 上限，413 拒绝 |
| CORS | ✅ | 环境变量白名单，默认仅 localhost |
| API 文档暴露 | ✅ 已加固 | `/docs` `/redoc` `/openapi.json` 由 `ZILLI_API_DOCS` 环境变量门控（本次修复） |
| 注入防护 | ✅ | 16 种注入签名 + Unicode 混淆字符归一化 + 危险输出不入缓存 |
| PII 检测 | ✅ | 3 级检测 + 五级数据分类 + PrivacyGatekeeper 强制本地路由 |
| 审计追踪 | ✅ 已修复 | **原 P1 缺陷**：API server 不写审计日志（合规报告无数据源）→ 已接入 `route_decision` + `model_call` 落盘 |
| 错误泄漏 | ✅ | 500 统一返回 "Internal server error"，堆栈仅入日志 |
| 密钥管理 | ✅ | 全库扫描无硬编码密钥；API key 哈希存储；secrets.toml 异常安全处理 |
| 多租户隔离 | ✅ | tenant_id 校验（防路径遍历）、数据目录命名空间隔离、角色检查 |
| 合规导出 | ✅ | `zilli audit export` 支持 6 框架，tenant 过滤 |

---

## 本次修复项

1. **P1 — 审计日志缺失**（合规断链）：API server 全程无审计落盘，GDPR/SOC2 报告无数据源
   → `ZilliAppState.audit = AuditLogger()`；`/v1/route` 写 `route_decision`、`/v1/chat/completions` 写 `model_call`
   → 回归测试：`TestAuditTrail` 2 项

2. **P2 — API 文档无鉴权暴露**：`/docs` 暴露完整 API schema
   → `ZILLI_API_DOCS=false` 时完全禁用 docs/redoc/openapi.json（404）

3. **P3 — dashboard secrets 崩溃**：无 `secrets.toml` 时 `st.secrets.get()` 抛异常（前次修复，本次确认）

## 测试验证

- `tests/test_server.py` 56 项（含鉴权、限速、CORS、Request-ID、租户端点、审计落盘）
- `tests/test_compliance.py` 12 项（合规报告全路径）
- `tests/test_audit.py` 8 项（审计 logger）
- `tests/test_tenancy.py` 21 项（租户隔离 + 持久化）

## 后续建议（非阻塞）

- 审计日志加密存储（合规高级场景）
- Rate limiter 分布式后端（Redis，多实例部署时）
- API key 轮换机制与过期时间
