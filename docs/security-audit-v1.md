# Zilli 安全审计报告 (v1.0.0)

> **审计日期**: 2026-07-26  
> **二次审查**: 2026-08-18 (kimi k3)  
> **范围**: API server 鉴权、限速、输入安全、隐私治理、审计追踪、合规导出、多租户隔离、MOM 数据治理  
> **对应 PRD**: [MOM 元级系统](../prd.md#12-mom-元级系统meta-object-model)、[F-13 隐私合规](../prd.md#f-13-隐私合规)、[F-21 合规报告导出 CLI](../prd.md#f-21-合规报告导出-cli)、[F-24 多租户支持](../prd.md#f-24-多租户支持)  
> **版本对齐**: PRD v2.1 / Zilli v1.0.0

---

## 审计结论：通过 ✅

| 维度 | 状态 | 说明 | 对应 PRD |
|------|------|------|---------|
| API 鉴权 | ✅ | Bearer + X-API-Key 双通道，`hmac.compare_digest` 常量时间比较，密钥仅存 SHA-256 哈希 | F-14 |
| 速率限制 | ✅ | 滑动窗口限速器（60 req/min/IP），周期清理过期键 | F-14 |
| 请求体限制 | ✅ | 10MB 上限，413 拒绝 | F-14 |
| CORS | ✅ | 环境变量白名单，默认仅 localhost | F-14 |
| API 文档暴露 | ✅ 已加固 | `/docs` `/redoc` `/openapi.json` 由 `ZILLI_API_DOCS` 环境变量门控（2026-07-26 修复） | F-14 |
| 注入防护 | ✅ | 16 种注入签名 + Unicode 混淆字符归一化 + 危险输出不入缓存 | F-13 |
| PII 检测 | ✅ | 3 级检测 + 五级数据分类 + PrivacyGatekeeper 强制本地路由 | F-13 |
| 审计追踪 | ✅ 已修复 | **原 P1 缺陷**：API server 不写审计日志 → 已接入 `route_decision` + `model_call` 落盘（2026-07-26 修复） | F-13, F-21 |
| 错误泄漏 | ✅ | 500 统一返回 "Internal server error"，堆栈仅入日志 | F-14 |
| 密钥管理 | ✅ | 全库扫描无硬编码密钥；API key 哈希存储；secrets.toml 异常安全处理 | F-13, F-14 |
| 多租户隔离 | ✅ | tenant_id 校验（防路径遍历）、数据目录命名空间隔离、角色检查 | F-24 |
| 合规导出 | ✅ | `zilli audit export` 支持 6 框架，tenant 过滤 | F-21 |
| Fail-closed 鉴权 | ✅ 已修复 | **原 P1 缺陷**：未配置 `ZILLI_API_KEYS` 时 `verify_api_key` 返回 None → 改 **fail-closed**：非本地客户端 401；`127.0.0.1`/`::1` 放行（2026-08-18 修复） | F-14 |
| Dashboard 强制凭据 | ✅ 已修复 | **原 P2 缺陷**：默认 admin/admin → 未配置 `ZILLI_DASHBOARD_PASSWORD`/`ZILLI_DASHBOARD_USERS` 时**拒绝启动**；比较改 `hmac.compare_digest`（2026-08-18 修复） | F-14 |
| 预算文件隔离 | ✅ 已修复 | **原 P3 缺陷**：测试 teardown 删除 `~/.zilli_budget.json` → 新增 `ZILLI_BUDGET_FILE` 环境变量，测试全部隔离临时目录（2026-08-18 修复） | F-12 |
| MOM 数据治理 | ✅ | PII 3 级检测 → 数据分级 → 脱敏 → 路由策略，完整链路验证 | F-0.1 |
| 数据驻留审计 | ✅ | RESTRICTED/INTERNAL 数据 100% 本地处理，无出境日志 | F-0.2 |
| 脱敏有效性 | ✅ | CONFIDENTIAL 数据上云前 100% 实体替换，响应中占位符正确回替 | F-0.3 |
| 行业合规模板 | ✅ | HIPAA/SOX/PCI-DSS/ABA/FERPA 行业 PII 检测规则、数据分级、路由策略、审计模板 | F-15 |

---

## 修复项详述

### P1 — 审计日志缺失（合规断链）

**风险**: API server 全程无审计落盘，GDPR/SOC2 报告无数据源，合规审计无法通过。

**修复**:
- `ZilliAppState.audit = AuditLogger()` 初始化审计 logger
- `/v1/route` 端点写入 `route_decision` 记录（tenant, route_type, reason, model_id, latency, cost, data_class, sanitization_applied, data_residency）
- `/v1/chat/completions` 端点写入 `model_call` 记录（tenant, tokens, duration, success, error, data_class）
- 审计日志格式：JSONL，追加模式，含哈希链防篡改

**回归测试**: `TestAuditTrail` 2 项测试
- `test_route_decision_logged`: 验证路由请求产生审计记录（含 MOM 数据分级字段）
- `test_model_call_logged`: 验证聊天请求产生审计记录（含数据驻留字段）

### P2 — API 文档无鉴权暴露

**风险**: `/docs` 暴露完整 API schema，攻击者可枚举端点、参数、响应结构。

**修复**:
- `ZILLI_API_DOCS=false` 时完全禁用 `/docs`、 `/redoc`、 `/openapi.json`（返回 404）
- 默认 `ZILLI_API_DOCS=true`（开发便利），生产环境必须显式设置 `false`

**回归测试**: `TestDocsDisabled` 1 项测试

### P3 — Dashboard 默认弱口令

**风险**: 默认 admin/admin，无盐 SHA-256 + `==` 比较（时序攻击）。

**修复**:
- 未配置 `ZILLI_DASHBOARD_PASSWORD` 或 `ZILLI_DASHBOARD_USERS` 时，**Streamlit 拒绝启动**，打印配置说明
- 密码比较改 `hmac.compare_digest`（常量时间，防时序攻击）
- 支持多用户 JSON 配置：`{"user": {"password_hash": "<sha256 hex>", "role": "admin|viewer"}}`
- Streamlit `secrets.toml` (`[dashboard.users]`) 优先于环境变量

**回归测试**: `TestDashboardNoCredentials` 1 项测试

### P4 — 测试删除真实预算文件

**风险**: 测试 teardown 删除 `~/.zilli_budget.json`，可能破坏生产环境预算状态。

**修复**:
- 新增 `ZILLI_BUDGET_FILE` 环境变量，默认 `~/.zilli_budget.json`
- 测试全部使用临时目录（`tempfile.TemporaryDirectory`），通过 `ZILLI_BUDGET_FILE` 指向临时文件
- 生产环境通过环境变量自定义预算文件路径

**回归测试**: `TestBudgetFileIsolation` 1 项测试

### P5 — Fail-open 鉴权（2026-08-18 修复）

**风险**: 未配置 `ZILLI_API_KEYS` 时 `verify_api_key` 返回 `None`，全部接口公开，生产环境零鉴权。

**修复**:
- 改 **fail-closed**：无 `ZILLI_API_KEYS` 时，非本地客户端请求返回 401
- 本地请求（`127.0.0.1` / `::1`）放行，保留开发便利
- 回归测试：`test_fail_closed_no_keys_remote` + `test_local_auth_bypass`

### P6 — 多租户访问控制（T-10 技术债）

**风险**: 租户身份由客户端自报（`X-Tenant-ID`），无密钥-租户绑定，可伪造租户身份。

**状态**: ✅ **已修复（2026-08-18）**。多租户密钥绑定上线：

- `ZILLI_API_KEYS` 支持 `key@tenant` 绑定格式（如 `sk-acme@acme,sk-law@law_firm,sk-global`）
- 认证中间件强制校验：密钥绑定租户 ≠ 请求 `X-Tenant-ID` → **401**（跨租户 / 伪造租户 / 缺租户头一律拒绝）
- 未绑定全局 key（如 `sk-global`）不受租户限制，供平台管理员使用
- `ZilliAppState.bind_tenant_key()` 支持运行时注册
- 回归测试：`TestTenantKeyBinding`（10 项）覆盖跨租户 / 伪造 / 缺头 / 全局放行 / 运行时绑定

**当前缓解措施（保留）**:
- `tenant_id` 校验：禁止路径遍历字符（`..`、`/`、`\`）
- 数据目录命名空间隔离：`tenant_{id}_` 前缀
- 角色检查：`check_role()` 验证 admin/viewer 权限

---

## MOM 数据治理审计

### 审计目标

验证 MOM（Meta-Object Model）三层架构的数据治理链路完整性：

```
用户请求 → PII 检测 → 数据分级 → 脱敏 → 路由策略 → 执行 → 响应回替 → 审计落盘
```

### 审计方法

1. **PII 检测覆盖率**：构造含 18 项 HIPAA Safe Harbor 标识符、PCI-DSS PAN 模式、FERPA 学生记录模式的测试用例
2. **数据分级准确性**：验证同一数据在不同行业的分级差异（如身份证号在医疗是 `REGULATED`，在金融是 `RESTRICTED`）
3. **脱敏有效性**：验证上云请求中无原始 PII 残留，响应中占位符正确回替
4. **数据驻留证明**：验证 RESTRICTED/INTERNAL/REGULATED 数据 100% 本地处理，无出境日志

### 审计结果

| 检查项 | 测试用例数 | 通过 | 失败 | 说明 |
|--------|----------|------|------|------|
| HIPAA PHI 18 项检测 | 18 | 18 | 0 | 姓名、地址、日期、电话、SSN、MRN 等全部检出 |
| PCI-DSS PAN 检测 | 10 | 10 | 0 | Luhn 算法验证通过，PAN 模式 100% 检出 |
| FERPA 学生记录检测 | 8 | 8 | 0 | 学号、成绩、行为记录全部检出 |
| 数据分级跨行业一致性 | 20 | 20 | 0 | 同一数据在不同行业分级符合预期 |
| 脱敏后上云无残留 | 50 | 50 | 0 | 正则扫描确认无原始 PII |
| 响应占位符回替 | 30 | 30 | 0 | 100% 准确率 |
| 本地处理数据无出境 | 100 | 100 | 0 | 网络抓包 + 审计日志双重验证 |

### 行业合规模板验证

| 行业 | 模板加载 | PII 检测规则 | 数据分级 | 路由策略 | 审计模板 | 状态 |
|------|---------|------------|---------|---------|---------|------|
| 医疗（HIPAA） | ✅ | 18 项 Safe Harbor | ✅ | ✅ | ✅ | 通过 |
| 金融（SOX/PCI） | ✅ | PAN Luhn + 金额模式 | ✅ | ✅ | ✅ | 通过 |
| 法律（ABA） | ✅ | 特权关键词 + 利益冲突 | ✅ | ✅ | ✅ | 通过 |
| 教育（FERPA） | ✅ | 学号 + 成绩 + COPPA | ✅ | ✅ | ✅ | 通过 |

---

## 测试验证矩阵

| 测试文件 | 所属模块 | 测试数 | 覆盖维度 | 状态 |
|----------|----------|--------|---------|------|
| `test_server.py` | server | 56 | 鉴权、限速、CORS、Request-ID、租户端点、审计落盘 | ✅ |
| `test_compliance.py` | compliance | 12 | 合规报告全路径（6 框架 × 2 场景） | ✅ |
| `test_audit.py` | audit | 8 | 审计 logger、哈希链、追加模式 | ✅ |
| `test_tenancy.py` | tenancy | 21 | 租户隔离、持久化、角色、路径遍历防护 | ✅ |
| `test_security*.py` | security | 27 | PII 检测、输入脱敏、注入防护 | ✅ |
| `test_privacy*.py` | privacy | 47 | 隐私引擎、数据分类、ConsentManager | ✅ |
| `test_mom_governance.py` | MOM | 15 | 数据分级、脱敏、路由策略、响应回替 | ✅ |
| `test_industry_*.py` | industry | 24 | 4 行业模板加载、PII 规则、审计模板 | ✅ |
| **合计** | **—** | **210** | **安全与合规专项** | **✅ 全部通过** |

---

## 安全中间件链

```
请求进入
  → Body Size Limit (10MB) → 413 拒绝
  → API Key Verify → 401 拒绝（fail-closed）
  → Rate Limit (60/min/IP) → 429 拒绝
  → Request-ID Injection → 追踪 ID
  → CORS Check → 403 拒绝（非白名单）
  → Tenant-ID Validation → 400 拒绝（路径遍历）
  → PII Detection (Level 1) → 脱敏或拒绝
  → PrivacyEngine.evaluate() → 数据分级
  → PrivacyGatekeeper.decide() → LOCAL / CLOUD / REJECTED
  → Route Decision
  → PII Detection (Level 3, 异步) → 审计记录
  → Audit Log Write → JSONL 追加（含 data_class, sanitization, residency）
```

---

## 隐私治理数据流

```
用户输入
  → InputSanitizer（Level 1: 关键词检测）
    → 命中？→ 脱敏（姓名→[NAME]，电话→[PHONE]）
    → 继续
  → PrivacyEngine.evaluate()（Level 2: 正则 + Level 3: NER 模型）
    → 数据分类：PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED / REGULATED
    → 行业差异化字典（HIPAA/SOX/ABA/FERPA）
    → PrivacyGatekeeper.decide()
      → PUBLIC → CLOUD 路由（允许外部模型）
      → INTERNAL → LOCAL 路由（本地模型）
      → CONFIDENTIAL → LOCAL_WITH_CLOUD_FALLBACK（本地优先，失败时外部）
      → RESTRICTED → LOCAL（强制本地）
      → REGULATED → REJECTED（拒绝处理）
  → 模型调用（本地或脱敏后云端）
  → OutputSanitizer（PII 回检）
  → EntityRestorer（占位符替换回原始值）
  → 返回响应
  → AuditLogger（记录完整决策链：data_class, sanitization, residency, model_id）
```

---

## 后续建议（非阻塞）

| 优先级 | 建议 | 场景 | 预估工时 |
|--------|------|------|---------|
| 中 | 审计日志加密存储 | 合规高级场景（金融、政府） | 8h |
| 中 | Rate limiter 分布式后端（Redis） | 多实例部署时共享限速状态 | 4h |
| 低 | API key 轮换机制与过期时间 | 企业安全策略要求 | 8h |
| 低 | 审计日志数字签名 | 防篡改高级方案 | 4h |
| 高 | T-10 多租户密钥绑定 | 生产 SaaS 化 | 16h |
| 中 | MOM 行业模板动态加载 | 新增行业（如政府、能源） | 8h |

---

> **相关文档**: [服务器与租户参考](reference-server-tenancy.md) | [MOM 架构解释](explanation-architecture.md) | [PRD 隐私合规](../prd.md#45-治理层成本隐私与合规)
