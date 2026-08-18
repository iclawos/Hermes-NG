# Reference: Server, Tenancy & Compliance API

## FastAPI Server

```
zilli serve [--host 127.0.0.1] [--port 8900]
```

### Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/healthz`, `/v1/health` | GET | public | Health + model liveness |
| `/v1/route` | POST | key | Hybrid routing (X-Tenant-ID header) |
| `/v1/chat/completions` | POST | key | OpenAI-compatible chat |
| `/v1/tenants` | GET | key | List registered tenants |
| `/v1/tenants/{id}` | GET | key | Tenant summary |
| `/v1/models` | GET | key | Model registry listing |
| `/v1/cost/status` | GET | key | Budget snapshot |
| `/v1/cost/reset` | POST | key | Monthly budget reset |
| `/v1/cache/stats` | GET | key | Cache metrics |
| `/v1/cache/clear` | POST | key | Cache flush |
| `/docs` `/redoc` `/openapi.json` | GET | public* | *Only when `ZILLI_API_DOCS=true` |

### Environment variables

| Var | Default | Description |
|-----|---------|-------------|
| `ZILLI_API_KEYS` | — | Comma-separated API keys (hashed at rest) |
| `ZILLI_CORS_ORIGINS` | localhost | CORS whitelist |
| `ZILLI_API_DOCS` | true | Set `false` to hide OpenAPI docs |
| `ZILLI_PPM_MODEL` | — | Path to trained PPM model (joblib/onnx) |
| `ZILLI_BUDGET_FILE` | `~/.zilli_budget.json` | Budget state file path |

**Fail-closed auth (since 2026-08-18)**: without `ZILLI_API_KEYS` configured, protected endpoints are **rejected with 401** for non-local clients; only requests from `127.0.0.1`/`::1` are allowed through (local dev convenience). Previously auth was fail-open when no keys were set.

### Security middleware chain

Body size (10MB) → API key verify → rate limit (60/min/IP) → request-id injection.

### Audit trail

Every route/chat request writes to `audit_logs/audit_YYYY-MM-DD.jsonl`:
- `route_decision`: tenant, route_type, reason
- `model_call`: tenant, tokens, duration, success

## Tenancy

```
zilli.tenancy.TenantManager(base_dir)
```

| Method | Description |
|--------|-------------|
| `register(TenantConfig)` | Add tenant (validates id) |
| `get(tenant_id)` | Get or auto-register context |
| `from_yaml(path)` | Load tenant definitions |
| `save_yaml(path)` | Persist registry |
| `remove(tenant_id)` | Drop tenant |

`TenantContext`: isolated `data_dir`, `storage_path()` (traversal-safe), per-tenant `planner_budget`, `check_role()`.

`TenantConfig.from_dict(id, data)`: budget, planner_ratio_limit, max_sota_ratio, industry, full IsolationPolicy.

## Compliance

```
zilli audit export --framework <fw> --tenant <id> --start <date> --end <date> --output <path> [--audit-dir ./audit_logs]
```

Frameworks: `gdpr`, `hipaa`, `soc2`, `pci_dss`, `ferpa`, `ccpa`.

`ComplianceReporter.generate()` reads `audit_*.jsonl`, filters by tenant + date range, produces findings (critical → `passed=False`).

### Privacy

- `PrivacyEngine.evaluate(text, tenant_id, mode)` → `PrivacyVerdict` (passed, sanitized_text, data_class)
- `PrivacyGatekeeper.decide(...)` → `LOCAL` / `CLOUD` / `LOCAL_WITH_CLOUD_FALLBACK` / `REJECTED`
- `DataGovernancePolicy.allows_cloud_for(data_class)` — 5-level ordering: PUBLIC < INTERNAL < CONFIDENTIAL < RESTRICTED < REGULATED
- `PolicyStore(path)` — per-tenant policy persistence

## CLI 全命令

| Command | Description |
|---------|-------------|
| `zilli run <prompt>` | Agent execution loop |
| `zilli route <request>` | Hybrid routing |
| `zilli train [--resume ckpt]` | RL training (checkpoint resume) |
| `zilli evaluate [task_id]` | Sandbox evaluation |
| `zilli distill [--ab-test cfg]` | Distillation cycles |
| `zilli swe --issue <bug>` | SWE-bench fix loop |
| `zilli serve` | API server |
| `zilli pipeline` | Evolve→Train pipeline |
| `zilli ppm stats / train-model` | PPM management |
| `zilli audit export` | Compliance reports |
| `zilli unknowns <sub>` | Fable unknowns lifecycle |
| `zilli models list/health/generate` | Model registry |
| `zilli cost status / reset-month` | Budget control |
| `zilli industry list / run` | Industry workflows |
| `zilli-evolve --input ... --target-skills ...` | Skill evolution |
