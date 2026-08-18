from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Zilli Dashboard", layout="wide")

BASE_DIR = Path(__file__).resolve().parent.parent
AUDIT_DIR = BASE_DIR / "audit_logs"
COST_FILE = Path(os.environ.get("ZILLI_BUDGET_FILE", str(Path.home() / ".zilli_budget.json")))
STATE_FILE = BASE_DIR / "state" / "STATE.md"


def _check_password() -> bool:
    if "authenticated" in st.session_state and st.session_state.authenticated:
        return True

    users = _load_users()
    if not users:
        st.error(
            "Dashboard 未配置登录凭据，已拒绝启动。\n\n"
            "请设置环境变量 `ZILLI_DASHBOARD_PASSWORD`（单用户 admin）或 "
            "`ZILLI_DASHBOARD_USERS`（多用户 JSON）后重启。"
        )
        return False

    st.markdown("## Zilli Dashboard Login")

    with st.form("login_form"):
        username = st.text_input("Username", placeholder="admin")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Login", use_container_width=True)

    if submitted:
        if username in users:
            stored = users[username]
            pw_hash = hashlib.sha256(password.encode()).hexdigest()
            if hmac.compare_digest(pw_hash, stored.get("password_hash", "")):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.session_state.role = stored.get("role", "viewer")
                st.rerun()
        st.error("Invalid username or password")
    return st.session_state.get("authenticated", False)


def _load_users() -> dict:
    try:
        secrets_users = st.secrets.get("dashboard", {}).get("users", {})
    except Exception:
        secrets_users = {}
    if secrets_users:
        return secrets_users

    env_users_raw = os.environ.get("ZILLI_DASHBOARD_USERS", "")
    if env_users_raw:
        try:
            users = json.loads(env_users_raw)
            if users:
                return users
        except json.JSONDecodeError:
            pass

    password = os.environ.get("ZILLI_DASHBOARD_PASSWORD", "")
    if not password:
        return {}
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    return {
        "admin": {"password_hash": pw_hash, "role": "admin"},
    }


def _check_admin() -> bool:
    return st.session_state.get("role") == "admin"


def load_audit_logs(limit: int = 100) -> list[dict]:
    logs: list[dict] = []
    if not AUDIT_DIR.exists():
        return logs
    for f in sorted(AUDIT_DIR.glob("*.jsonl"), reverse=True)[:5]:
        with open(f) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    logs.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
                if len(logs) >= limit:
                    return logs
    return logs


def load_cost_stats() -> dict:
    if not COST_FILE.exists():
        return {"remaining_budget": 500.0, "total_calls": 0}
    try:
        return json.loads(COST_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def load_state() -> str:
    if STATE_FILE.exists():
        return STATE_FILE.read_text()
    return "No state file found"


def load_ppm_stats() -> dict:
    try:
        from zilli.routing.ppm import PPMPredictor
        p = PPMPredictor()
        return p.stats()
    except Exception:
        return {}


if not _check_password():
    st.stop()

st.sidebar.title("Zilli Dashboard")
st.sidebar.markdown(f"**User**: `{st.session_state.get('username', '?')}`")
st.sidebar.markdown(f"**Role**: `{st.session_state.get('role', '?')}`")

auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=False)
if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.rerun()

if auto_refresh:
    placeholder = st.empty()
    time.sleep(30)
    st.rerun()

st.title("Zilli Management Dashboard")

col1, col2, col3, col4, col5 = st.columns(5)
cost = load_cost_stats()
col1.metric("Budget Remaining", f"${cost.get('remaining_budget', 0):.2f}")
col2.metric("Total API Calls", cost.get("total_calls", 0))
col3.metric("Audit Logs", len(load_audit_logs()))
col4.metric("State File", "OK" if STATE_FILE.exists() else "Missing")

ppm_s = load_ppm_stats()
col5.metric(
    "PPM Cache Hit Rate",
    f"{ppm_s.get('hit_rate', 0) * 100:.0f}%"
    if ppm_s.get("hit_rate")
    else "N/A",
)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Audit Logs", "Cost Control", "System State", "DAG Runs", "PPM Stats"
])

with tab1:
    st.subheader("Recent Audit Events")
    logs = load_audit_logs()
    if logs:
        st.dataframe(
            [{k: str(v)[:80] for k, v in entry.items()} for entry in logs],
            use_container_width=True,
        )
        log_text = "\n".join(json.dumps(e, ensure_ascii=False) for e in logs)
        st.download_button(
            "Export as JSONL",
            data=log_text,
            file_name=f"audit_export_{int(time.time())}.jsonl",
            mime="application/x-ndjson",
        )
    else:
        st.info("No audit logs found")

with tab2:
    st.subheader("Cost & Budget")
    c = load_cost_stats()
    remaining = c.get("remaining_budget", 500.0)
    total = c.get("total_calls", 0)
    st.progress(
        max(0.0, min(1.0, remaining / 500.0)),
        text=f"${remaining:.2f} remaining",
    )
    st.write(f"**Total calls**: {total}")
    st.write(f"**Last updated**: {c.get('updated_at', 'N/A')}")

with tab3:
    st.subheader("Current State")
    st.text(load_state())

with tab4:
    st.subheader("DAG Execution Records")
    st.info("Connect to Redis to view live DAG run history")
    if st.button("Clear All Records", disabled=not _check_admin()):
        st.warning("Not implemented — Redis connection required")

with tab5:
    st.subheader("PPM Classifier Stats")
    if ppm_s:
        st.json(ppm_s)
        if ppm_s.get("difficulty_weights"):
            st.subheader("Per-Family Difficulty Weights")
            st.dataframe(
                [
                    {"family": k, **v}
                    for k, v in ppm_s["difficulty_weights"].items()
                ],
                use_container_width=True,
            )
    else:
        st.info("PPM stats unavailable")

st.caption("Zilli v0.3.0 — Management Dashboard")
