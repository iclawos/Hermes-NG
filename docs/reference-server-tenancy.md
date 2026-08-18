# Reference: Server, Tenancy & Compliance API

> **文档类型**: API 参考  
> **对应 PRD**: [MOM 元级系统](../prd.md#12-mom-元级系统meta-object-model)、[F-14 API 服务器](../prd.md#f-14-api-服务器)、[F-24 多租户支持](../prd.md#f-24-多租户支持)、[F-21 合规报告导出 CLI](../prd.md#f-21-合规报告导出-cli)、[F-13 隐私合规](../prd.md#f-13-隐私合规)  
> **版本对齐**: PRD v2.1 / Zilli v1.0.0

---

## 目录

- [FastAPI Server](#fastapi-server)
- [Environment Variables](#environment-variables)
- [Security Middleware Chain](#security-middleware-chain)
- [Audit Trail](#audit-trail)
- [Streamlit Dashboard](#streamlit-dashboard)
- [Tenancy](#tenancy)
- [Compliance](#compliance)
- [Privacy](#privacy)
- [Industry Workflows](#industry-workflows)
- [CLI 全命令](#cli-全命令)

---

## FastAPI Server

```bash
zilli serve [--host 127.0.0.1] [--port 8900]
```

### 端点列表

| 端点 | 方法 | 鉴权 | 说明 | 对应 PRD |
|------|------|------|------|---------|
| `/healthz`, `/v1/health` | GET | public | 健康检查 + 模型存活状态 | F-14 |
| `/v1/route` | POST | key | 混合路由（`X-Tenant-ID` header） | F-1, F-2, F-0.2 |
| `/v1/chat/completions` | POST | key | OpenAI 兼容聊天接口 | F-14 |
| `/v1/tenants` | GET | key | 列出已注册租户 | F-24 |
| `/v1/tenants/{id}` | GET | key | 租户摘要（预算、用量、状态） | F-24 |
| `/v1/models` | GET | key | 模型注册表列表 | F-3 |
| `/v1/cost/status` | GET | key | 预算快照（剩余、已用、SOTA 比例） | F-12 |
| `/v1/cost/reset` | POST | key | 月度预算重置（admin 权限） | F-12 |
| `/v1/cache/stats` | GET | key | 缓存指标（命中率、延迟） | F-2 |
| `/v1/cache/clear` | POST | key | 缓存刷新 | F-2 |
| `/v1/privacy/check` | POST | key | 隐私分级检查（输入文本 → 数据级别 + 路由策略） | F-0.1 |
| `/v1/mom/decision/{request_id}` | GET | key | MOM 决策追踪（完整决策链） | F-0.2 |
| `/v1/data/residency` | GET | key | 数据驻留统计（本地 vs 云端比例） | F-0.3 |
| `/docs`, `/redoc`, `/openapi.json` | GET | public* | *仅当 `ZILLI_API_DOCS=true` 时暴露 | F-14 |

### 请求/响应示例

#### `/v1/chat/completions`

```bash
curl -X POST http://localhost:8900/v1/chat/completions   -H "Content-Type: application/json"   -H "X-API-Key: sk-zilli-xxx"   -H "X-Tenant-ID: tenant-acme"   -d '{
    "model": "zilli-auto",
    "messages": [{"role": "user", "content": "Write a Python function to sort a list"}],
    "stream": false,
    "temperature": 0.7
  }'
```

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1724000000,
  "model": "gpt-4-executor",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "def sort_list(lst): return sorted(lst)"},
    "finish_reason": "stop"
  }],
  "usage": {"prompt_tokens": 15, "completion_tokens": 25, "total_tokens": 40},
  "X-Zilli-Route": "full_route",
  "X-Zilli-Cost": "0.015",
  "X-Zilli-Model": "gpt-4-executor",
  "X-Zilli-PPM-Difficulty": "0.45",
  "X-Zilli-Request-ID": "req-abc123",
  "X-Zilli-Data-Class": "PUBLIC",
  "X-Zilli-Data-Residency": "cloud"
}
```

#### `/v1/route`

```bash
curl -X POST http://localhost:8900/v1/route   -H "Content-Type: application/json"   -H "X-API-Key: sk-zilli-xxx"   -H "X-Tenant-ID: tenant-acme"   -d '{"text": "Write a Python function", "context": "coding"}'
```

```json
{
  "model_id": "gpt-4-executor",
  "strategy": "STANDARD",
  "difficulty": 0.45,
  "family": "code",
  "confidence": 0.92,
  "route_type": "full_route",
  "estimated_cost_usd": 0.015,
  "estimated_latency_ms": 2500,
  "data_class": "PUBLIC",
  "data_residency": "cloud",
  "sanitization_applied": false
}
```

#### `/v1/privacy/check`

```bash
curl -X POST http://localhost:8900/v1/privacy/check   -H "Content-Type: application/json"   -H "X-API-Key: sk-zilli-xxx"   -H "X-Tenant-ID: tenant-acme"   -d '{"text": "患者张三，病历号20240818001，诊断心梗"}'
```

```json
{
  "data_class": "REGULATED",
  "route_policy": "REJECTED",
  "pii_detected": ["姓名", "病历号"],
  "sanitized_text": "患者[NAME]，病历号[MRN]，诊断心梗",
  "risk_score": 1.0,
  "recommendation": "涉及 PHI，请使用本地部署"
}
```

#### `/v1/mom/decision/{request_id}`

```bash
curl -X GET http://localhost:8900/v1/mom/decision/req-abc123   -H "X-API-Key: sk-zilli-xxx"
```

```json
{
  "request_id": "req-abc123",
  "timestamp": "2026-08-18T10:30:00Z",
  "tenant_id": "tenant-acme",
  "decision_chain": [
    {"stage": "input_sanitizer", "pii_detected": ["姓名"], "sanitization_applied": true},
    {"stage": "privacy_engine", "data_class": "CONFIDENTIAL", "confidence": 0.95},
    {"stage": "privacy_gatekeeper", "route_policy": "LOCAL_WITH_CLOUD_FALLBACK"},
    {"stage": "ppm_predictor", "difficulty": 0.45, "family": "code", "confidence": 0.92},
    {"stage": "strategy_selector", "strategy": "STANDARD", "data_class_constraint": "CONFIDENTIAL"},
    {"stage": "model_profile", "candidates": ["gpt-4-executor", "llama3-70b"], "selected": "gpt-4-executor"},
    {"stage": "route_classifier", "route_type": "full_route"},
    {"stage": "execution", "model_id": "gpt-4-executor", "latency_ms": 1200, "success": true},
    {"stage": "output_sanitizer", "pii_recheck": "clean"},
    {"stage": "entity_restorer", "placeholder_replaced": ["[NAME]"], "residency": "local"}
  ],
  "audit_log_index": "audit_logs/audit_2026-08-18.jsonl"
}
```

---

## Environment Variables

| 变量 | 默认值 | 说明 | 安全等级 |
|------|--------|------|---------|
| `ZILLI_API_KEYS` | — | 逗号分隔 API 密钥（SHA-256 哈希存储），支持 `key@tenant` 绑定格式（T-10） | 🔴 必须配置 |
| `ZILLI_CORS_ORIGINS` | `localhost` | CORS 白名单（逗号分隔） | 🟡 生产需限制 |
| `ZILLI_API_DOCS` | `true` | `false` 时隐藏 OpenAPI 文档 | 🟡 生产必设 `false` |
| `ZILLI_PPM_MODEL` | — | 训练好的 PPM 模型路径（`.joblib` / `.onnx`） | 🟢 可选 |
| `ZILLI_BUDGET_FILE` | `~/.zilli_budget.json` | 预算状态文件路径 | 🟡 测试需隔离 |
| `ZILLI_DASHBOARD_PASSWORD` | — | 单用户模式密码（SHA-256） | 🔴 必须配置 |
| `ZILLI_DASHBOARD_USERS` | — | 多用户 JSON（`{"user": {"password_hash": "...", "role": "admin|viewer"}}`） | 🔴 必须配置 |
| `ZILLI_AUDIT_DIR` | `./audit_logs` | 审计日志目录 | 🟢 可选 |
| `ZILLI_TENANT_YAML` | `./tenants.yaml` | 租户配置持久化路径 | 🟢 可选 |
| `ZILLI_INDUSTRY_CONFIG` | `./industries` | 行业合规模板目录 | 🟢 可选 |

### Fail-closed 鉴权（2026-08-18 更新）

**旧行为（v0.5.0 及之前）**: 未配置 `ZILLI_API_KEYS` 时，`verify_api_key` 返回 `None`，全部接口公开（fail-open）。

**新行为（v1.0.0）**: 未配置 `ZILLI_API_KEYS` 时：
- 非本地客户端（非 `127.0.0.1` / `::1`）→ **401 Unauthorized**
- 本地客户端（`127.0.0.1` / `::1`）→ **放行**（开发便利）

**生产部署检查清单**:
```bash
# 1. 配置 API 密钥（支持 key@tenant 绑定，T-10）
export ZILLI_API_KEYS="sk-global,sk-acme@acme,sk-law@law_firm"
#    - sk-global          → 未绑定全局 key（平台管理员，任意租户）
#    - sk-acme@acme       → 绑定租户 acme，仅 X-Tenant-ID: acme 可用
#    - 跨租户 / 伪造租户 / 缺 X-Tenant-ID 头 → 401

# 2. 禁用 API 文档
export ZILLI_API_DOCS=false

# 3. 限制 CORS
export ZILLI_CORS_ORIGINS="https://app.yourcompany.com"

# 4. 配置 Dashboard 凭据
export ZILLI_DASHBOARD_PASSWORD="$(echo -n 'your-password' | sha256sum | cut -d' ' -f1)"
# 或
export ZILLI_DASHBOARD_USERS='{"admin": {"password_hash": "...", "role": "admin"}}'

# 5. 隔离预算文件（测试/生产分离）
export ZILLI_BUDGET_FILE="/var/lib/zilli/budget.json"

# 6. 配置行业模板目录
export ZILLI_INDUSTRY_CONFIG="/etc/zilli/industries"
```

---

## Security Middleware Chain

```
请求进入
  [1] Body Size Limit (10MB)
      → 超限 → 413 Payload Too Large
  [2] API Key Verify
      → 无密钥 / 无效 → 401 Unauthorized
      → 本地请求（127.0.0.1/::1）且未配置密钥 → 放行（开发模式）
  [3] Rate Limit (60 req/min/IP)
      → 滑动窗口计数
      → 超限 → 429 Too Many Requests
      → 周期清理过期键（防止内存泄漏）
  [4] Request-ID Injection
      → 无 X-Request-ID → 自动生成 UUID
      → 透传至下游所有调用（追踪链）
  [5] CORS Check
      → Origin 不在白名单 → 403 Forbidden
  [6] Tenant-ID Validation
      → 含路径遍历字符（..、/、\）→ 400 Bad Request
      → 未注册租户 → 自动注册（默认配额）
  [7] PII Detection (Level 1)
      → 命中关键词 → 脱敏或拒绝
  [8] PrivacyEngine.evaluate()（Level 2 + Level 3）
      → 数据分类：PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED / REGULATED
      → 行业差异化字典（HIPAA/SOX/ABA/FERPA）
  [9] PrivacyGatekeeper.decide()
      → REGULATED → 直接拒绝
      → RESTRICTED/INTERNAL → 强制本地模型
      → CONFIDENTIAL → 本地优先 + 脱敏后云端 fallback
      → PUBLIC → 正常路由
  [10] Route Decision
      → PPM 预测 → 策略选择 → 模型选择
  [11] PII Detection (Level 3, 异步)
      → NER 模型深度检测
  [12] Audit Log Write
      → route_decision / model_call → JSONL 追加
      → 含 data_class, sanitization_applied, data_residency, route_policy
```

---

## Audit Trail

每次路由/聊天请求写入 `audit_logs/audit_YYYY-MM-DD.jsonl`：

### `route_decision` 记录（MOM 增强）

```json
{
  "timestamp": "2026-08-18T10:30:00Z",
  "request_id": "req-abc123",
  "tenant_id": "tenant-acme",
  "event_type": "route_decision",
  "route_type": "full_route",
  "model_id": "gpt-4-executor",
  "strategy": "STANDARD",
  "difficulty": 0.45,
  "family": "code",
  "confidence": 0.92,
  "latency_ms": 2500,
  "cost_usd": 0.015,
  "success": true,
  "data_class": "CONFIDENTIAL",
  "sanitization_applied": true,
  "data_residency": "cloud",
  "route_policy": "LOCAL_WITH_CLOUD_FALLBACK",
  "industry_framework": "general"
}
```

### `model_call` 记录（MOM 增强）

```json
{
  "timestamp": "2026-08-18T10:30:01Z",
  "request_id": "req-abc123",
  "tenant_id": "tenant-acme",
  "event_type": "model_call",
  "model_id": "gpt-4-executor",
  "tokens_in": 15,
  "tokens_out": 25,
  "duration_ms": 1200,
  "cost_usd": 0.015,
  "success": true,
  "error": null,
  "data_class": "CONFIDENTIAL",
  "sanitization_applied": true,
  "data_residency": "cloud",
  "route_policy": "LOCAL_WITH_CLOUD_FALLBACK"
}
```

### 审计日志特性

- **追加模式**: 只写不删，支持外部审计工具 tail -f
- **哈希链**: 每条记录含上一条 SHA-256，防篡改
- **按日轮转**: `audit_YYYY-MM-DD.jsonl`，便于归档和清理
- **租户过滤**: 合规导出时按 `tenant_id` 筛选
- **MOM 字段**: 含 data_class, sanitization_applied, data_residency, route_policy, industry_framework

---

## Streamlit Dashboard

```bash
streamlit run zilli/dashboard_app.py
```

### 强制凭据（2026-08-18 更新）

**旧行为**: 默认 admin/admin，无盐 SHA-256 + `==` 比较。

**新行为**: 未配置 `ZILLI_DASHBOARD_PASSWORD` 或 `ZILLI_DASHBOARD_USERS` 时，**Streamlit 拒绝启动**，打印配置说明。

### 配置方式

**方式 1: 环境变量（单用户）**
```bash
export ZILLI_DASHBOARD_PASSWORD="$(echo -n 'your-password' | sha256sum | cut -d' ' -f1)"
```

**方式 2: 环境变量（多用户）**
```bash
export ZILLI_DASHBOARD_USERS='{
  "admin": {"password_hash": "a1b2c3...", "role": "admin"},
  "viewer1": {"password_hash": "d4e5f6...", "role": "viewer"}
}'
```

**方式 3: secrets.toml（优先）**
```toml
# .streamlit/secrets.toml
[dashboard.users]
admin = {password_hash = "a1b2c3...", role = "admin"}
viewer1 = {password_hash = "d4e5f6...", role = "viewer"}
```

### 角色权限

| 角色 | 权限 | 适用场景 |
|------|------|---------|
| `admin` | 全部功能：审计浏览、成本监控、PPM Stats、缓存管理、租户管理、预算重置、行业工作流配置 | 平台管理员 |
| `viewer` | 只读：审计浏览、成本监控、PPM Stats（无修改权限） | 审计员、运营 |

### 页面功能

| 页面 | 功能 | 数据刷新 |
|------|------|---------|
| **Overview** | 系统概览：请求量、成功率、平均延迟、成本趋势 | 自动 30s |
| **Audit** | 审计日志浏览：按日期/租户/事件类型/数据级别过滤 | 手动 |
| **Cost** | 成本监控：月度预算、SOTA 比例、各租户用量、数据驻留分布 | 自动 60s |
| **PPM Stats** | PPM 性能：缓存命中率、预测分布、权重偏移 | 自动 30s |
| **Tenants** | 租户管理：注册/查看/删除租户（admin 专属） | 手动 |
| **Models** | 模型画像：ELO 评分、能力雷达图、健康状态 | 自动 60s |
| **Compliance** | 合规报告：一键导出 GDPR/HIPAA/SOC2/SOX/PCI/ABA/FERPA | 手动 |
| **MOM Decision** | MOM 决策追踪：查看请求完整决策链（数据分级 → 脱敏 → 路由 → 执行） | 手动 |
| **Data Residency** | 数据驻留：本地 vs 云端处理比例、各数据级别分布 | 自动 60s |
| **Industry** | 行业工作流：配置 HIPAA/SOX/ABA/FERPA 模板、查看行业审计状态 | 手动 |

---

## Tenancy

```python
zilli.tenancy.TenantManager(base_dir="./tenants")
```

### 方法

| 方法 | 说明 |
|------|------|
| `register(TenantConfig)` | 注册租户（校验 id 合法性） |
| `get(tenant_id)` | 获取或自动注册上下文（默认配额） |
| `from_yaml(path)` | 从 YAML 加载租户定义 |
| `save_yaml(path)` | 持久化注册表到 YAML |
| `remove(tenant_id)` | 删除租户（标记删除，30 天后物理清除） |

### TenantConfig

```python
@dataclass
class TenantConfig:
    id: str                          # 租户 ID（字母、数字、-、_）
    budget: float = 1000.0          # 月度预算（USD）
    planner_ratio_limit: float = 0.05  # Planner 调用比例上限
    max_sota_ratio: float = 0.05     # SOTA 调用比例上限
    industry: str = "general"          # 行业（general/healthcare/finance/legal/education）
    isolation_policy: str = "standard"  # 隔离策略（standard/strict）
    privacy_policy: str = "default"    # 隐私策略（default/hipaa/sox/aba/ferpa）
```

### TenantContext

```python
@dataclass
class TenantContext:
    tenant_id: str
    data_dir: str                   # 隔离数据目录
    storage_path() -> str           # 防路径遍历的存储路径
    planner_budget: PlannerBudget   # 租户级预算控制器
    check_role(required: str) -> bool  # 角色检查
    industry_framework: str         # 行业框架（HIPAA/SOX/ABA/FERPA）
    privacy_policy: PrivacyPolicy   # 租户级隐私策略
```

### 安全模型

| 角色 | 可见范围 | 操作权限 |
|------|---------|---------|
| 租户管理员 | 本租户日志、仪表盘、预算 | 查看、导出报告 |
| 平台管理员 | 全部租户聚合视图 | 租户生命周期管理、全局配置、行业模板配置 |
| 系统租户（id=system） | 平台级进化任务 | 不占用租户配额，运行全局优化 |

### 数据隔离

```python
# 命名空间隔离
ChromaDB: collection_prefix = f"tenant_{tenant_id}_"
JSONL: file_path = f"./data/tenant_{tenant_id}/trajectories.jsonl"
YAML: config_path = f"./tenants/{tenant_id}.yaml"
Audit: audit_dir = f"./audit_logs/tenant_{tenant_id}/"

# 路径遍历防护
def storage_path(filename: str) -> str:
    safe_name = os.path.basename(filename)  # 去除 ../ 等
    return os.path.join(self.data_dir, safe_name)
```

---

## Compliance

```bash
zilli audit export   --framework <gdpr|hipaa|soc2|pci_dss|ferpa|ccpa|sox|aba>   --tenant <id>   --start <YYYY-MM-DD>   --end <YYYY-MM-DD>   --output <path>   [--audit-dir ./audit_logs]   [--include-phi-log]   [--industry-config ./industries]
```

### 支持框架

| 框架 | 适用行业 | 关键检查项 | 审计保留期 |
|------|---------|-----------|----------|
| `gdpr` | 欧盟通用 | 数据最小化、删除权、审计追踪 | 7 年 |
| `hipaa` | 美国医疗 | PHI 保护、Safe Harbor 18 项、BAA 协议 | 6 年 |
| `soc2` | 企业服务 | 安全性、可用性、处理完整性 | 7 年 |
| `pci_dss` | 支付行业 | 持卡人数据保护、加密、访问控制 | 7 年 |
| `ferpa` | 美国教育 | 学生教育记录隐私、目录信息退出 | 永久 |
| `ccpa` | 加州消费者 | 知情权、删除权、选择退出 | 7 年 |
| `sox` | 美国金融 | 财务控制、信息披露、内控测试 | 7 年 |
| `aba` | 美国法律 | 律师-客户特权、利益冲突、保密义务 | 案件结束后 7 年 |

### 报告结构

```json
{
  "framework": "hipaa",
  "tenant_id": "tenant-acme",
  "period": {"start": "2026-01-01", "end": "2026-08-18"},
  "generated_at": "2026-08-18T10:30:00Z",
  "summary": {
    "total_requests": 150000,
    "pii_detections": 3200,
    "anomaly_events": 12,
    "compliance_score": 0.98,
    "data_residency": {"local": 85, "cloud": 15},
    "industry_framework": "HIPAA"
  },
  "findings": [
    {
      "id": "F-001",
      "severity": "medium",
      "category": "data_retention",
      "description": "3 records exceeded retention period",
      "root_cause": "TrajectoryCleaner missed cold data",
      "remediation": "Run zilli data cleanup --older-than 90d",
      "passed": false
    }
  ],
  "passed_checks": [
    {"id": "P-001", "category": "encryption", "description": "All data encrypted at rest", "passed": true},
    {"id": "P-002", "category": "access_control", "description": "API key rotation enforced", "passed": true}
  ],
  "log_index": "audit_logs/audit_2026-01-01_to_2026-08-18.jsonl"
}
```

---

## Privacy

### PrivacyEngine

```python
zilli.privacy.PrivacyEngine.evaluate(text, tenant_id, mode="standard")
→ PrivacyVerdict(passed, sanitized_text, data_class, confidence, route_policy, pii_list)
```

### 3 级 PII 检测

| 级别 | 方法 | 延迟 | 召回率 | 误报率 |
|------|------|------|--------|--------|
| Level 1 | 关键词匹配（姓名、电话、邮箱等） | < 1ms | 85% | 8% |
| Level 2 | 正则表达式（身份证号、信用卡、SSN、病历号、学号） | < 5ms | 95% | 3% |
| Level 3 | NER 模型（上下文感知实体识别，医疗/金融/法律/教育专用） | < 50ms | 98% | 1% |

### 五级数据分类

| 级别 | 说明 | 路由策略 | 示例 |
|------|------|---------|------|
| `PUBLIC` | 公开数据 | CLOUD（允许外部模型） | 产品文档、公开 API、医学文献、判例、教材 |
| `INTERNAL` | 内部数据 | LOCAL（本地模型） | 内部邮件、会议纪要、内部政策、教师评估 |
| `CONFIDENTIAL` | 机密数据 | LOCAL_WITH_CLOUD_FALLBACK | 客户名单、财务数据、合同条款、去标识化学生数据 |
| `RESTRICTED` | 受限数据 | LOCAL（强制本地） | 员工档案、交易记录、律师-客户特权、策略文件 |
| `REGULATED` | 监管数据 | REJECTED（拒绝处理） | PHI（医疗）、PCI（支付）、学生成绩、COPPA 儿童信息 |

### PrivacyGatekeeper

```python
decision = PrivacyGatekeeper.decide(verdict)
→ "LOCAL" | "CLOUD" | "LOCAL_WITH_CLOUD_FALLBACK" | "REJECTED"
```

---

## Industry Workflows

### 行业模板配置

```bash
# 配置行业工作流目录
export ZILLI_INDUSTRY_CONFIG="/etc/zilli/industries"

# 目录结构
/etc/zilli/industries/
├── hipaa.yaml          # 医疗行业 HIPAA 模板
├── sox.yaml            # 金融行业 SOX 模板
├── pci_dss.yaml        # 支付行业 PCI-DSS 模板
├── aba.yaml            # 法律行业 ABA 模板
├── ferpa.yaml          # 教育行业 FERPA 模板
└── general.yaml        # 通用模板（默认）
```

### 行业模板示例（HIPAA）

```yaml
# industries/hipaa.yaml
name: "HIPAA Healthcare"
framework: hipaa

# PII 检测增强规则
pii_rules:
  - name: "patient_name"
    pattern: "关键词"
    level: 1
    data_class: "REGULATED"
    reason: "PHI - 18th identifier (164.514)"
  - name: "medical_record_number"
    pattern: "正则: [A-Z]{2,4}-\d{5,10}"
    level: 2
    data_class: "REGULATED"
    reason: "PHI - 3rd identifier"
  - name: "diagnosis_code"
    pattern: "NER: 医疗诊断实体"
    level: 3
    data_class: "REGULATED"
    reason: "PHI - 间接标识符"

# 数据分级规则
data_classification:
  - identifiers: ["patient_name", "mrn", "ssn", "phone", "email", "address", "date_of_birth"]
    class: "REGULATED"
    route_policy: "REJECTED"
  - identifiers: ["diagnosis", "prescription", "treatment_plan"]
    class: "REGULATED"
    route_policy: "LOCAL"
  - identifiers: ["medical_knowledge", "drug_interaction"]
    class: "PUBLIC"
    route_policy: "CLOUD"

# 路由策略
routing_policy:
  REGULATED:
    action: "LOCAL_OR_REJECT"
    cloud_fallback: false
    deidentification_required: "safe_harbor_18"
  CONFIDENTIAL:
    action: "LOCAL_WITH_CLOUD_FALLBACK"
    cloud_fallback: true
    deidentification_required: "safe_harbor_18"

# 审计要求
audit:
  retention_years: 6
  breach_threshold: 500
  required_logs: ["phi_access", "deidentification", "local_processing_proof"]
  third_party_agreement: "BAA"
  annual_report: "HIPAA Security Rule"
```

### CLI 行业工作流管理

```bash
# 列出可用行业模板
zilli industry list

# 查看行业模板详情
zilli industry show --framework hipaa

# 为租户配置行业工作流
zilli industry run --framework hipaa   --tenant hospital-001   --policy "phi_strict"   --local-models "llama3-70b,mistral-large"   --cloud-models "gpt-4,claude-3-opus"   --sota-max-ratio 0.02

# 金融行业：配置 SOX + PCI-DSS 联合工作流
zilli industry run --framework sox,pci_dss   --tenant bank-001   --policy "financial_restricted"   --local-models "llama3-70b"   --cloud-models "gpt-4"   --sota-max-ratio 0.01   --audit-retention 7years

# 查看行业工作流状态
zilli industry status --tenant hospital-001

# 验证行业合规性
zilli industry validate --tenant hospital-001 --framework hipaa
```

### 行业模板运行时热更新（2026-08-18）

`ZILLI_INDUSTRY_CONFIG` 目录下的 YAML 模板支持**无重启热更新**：

```bash
# 更新模板后触发重载
curl -X POST "$ZILLI_API_BASE/v1/industry/reload" \
  -H "Authorization: Bearer $API_KEY"
# → {"loaded": [{"file": "hipaa.yaml", "industry": "medical", ...}],
#    "skipped": [], "removed": ["education"]}

# 列出当前生效模板
curl "$ZILLI_API_BASE/v1/industry/list" \
  -H "Authorization: Bearer $API_KEY"
```

- 模板文件名为 `framework`（`hipaa.yaml` / `sox.yaml` / `aba.yaml` / `ferpa.yaml`），或文件内 `framework:` / `industry:` 键
- 重载报告含 `loaded` / `skipped`（无法识别行业或 YAML 解析失败）/ `removed`（目录中已删除的行业）
- 支持字段：`name`、`compliance_rules`、`access_level`、`require_audit`、`require_sanitization`、`retention_days`（或 `audit.retention_years`，自动换算 365×年）
- 未配置 `ZILLI_INDUSTRY_CONFIG` 时使用内置模板（legal / medical / financial / education）

---

## CLI 全命令

| 命令 | 说明 | 对应 PRD |
|------|------|---------|
| `zilli run <prompt>` | Agent 执行循环 | F-1, F-2 |
| `zilli route <request>` | 混合路由（查看决策详情） | F-1, F-2, F-0.2 |
| `zilli train [--resume ckpt]` | RL 训练（CISPO/GRPO） | F-4 |
| `zilli evaluate [task_id]` | 沙盒评估 | F-8 |
| `zilli distill [--ab-test cfg]` | 蒸馏周期 | F-5 |
| `zilli swe --issue <bug>` | SWE-bench 修复循环 | SWE-bench |
| `zilli serve` | 启动 API 服务器 | F-14 |
| `zilli pipeline` | Evolve→Train 管线 | F-11 |
| `zilli ppm stats / train-model` | PPM 管理 | F-2, F-16 |
| `zilli audit export` | 合规报告导出 | F-21 |
| `zilli unknowns <sub>` | Fable 未知项生命周期 | F-19, F-23 |
| `zilli models list/health/generate` | 模型注册表 | F-3 |
| `zilli cost status / reset-month` | 预算控制 | F-12 |
| `zilli industry list / run / status / validate` | 行业工作流 | F-15 |
| `zilli privacy check --text <text>` | 隐私分级检查 | F-0.1 |
| `zilli mom decision --request-id <id>` | MOM 决策追踪 | F-0.2 |
| `zilli data residency --tenant <id>` | 数据驻留统计 | F-0.3 |
| `zilli soak` | 持续监控器 | F-25 |
| `zilli-evolve --input ... --target-skills ...` | 技能进化 | F-7 |

---

> **相关文档**: [MOM 架构解释](explanation-architecture.md) | [路由 API 参考](reference-routing.md) | [安全审计报告](security-audit-v1.md) | [常见任务指南](howto-common-tasks.md)
