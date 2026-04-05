"""
DevOps MCP Toolkit — Streamlit Control Panel v2.0.0
Visual interface for all 15 MCP servers.
Run: streamlit run streamlit_app/app.py
"""

import streamlit as st
import json
import subprocess
import sys
import time
import socket
import shutil
from pathlib import Path

# ── Path setup ─────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from utils import (
    docker, kube, tf, http_get, http_post, jenkins_crumb, shell, shell_lines,
    service_health, JENKINS_URL, SONAR_URL, JENKINS_AUTH, SONAR_AUTH, TF_WORKDIR,
)

# ── Service config ──────────────────────────────────────────────────────────────
PROM_URL          = "http://localhost:30090"
GRAFANA_URL       = "http://localhost:30030"
GRAFANA_AUTH      = ("admin", "Admin@123456789@")
ARGOCD_URL        = "https://localhost:30085"
ARGOCD_AUTH       = ("admin", "Admin@123456789@")
VAULT_URL         = "http://localhost:30200"
VAULT_TOKEN       = "root"
LOKI_URL          = "http://localhost:30310"
REGISTRY_URL      = "http://127.0.0.1:30880"
REGISTRY_UI_URL   = "http://127.0.0.1:30881"
MINIO_URL         = "http://localhost:30920"
MINIO_CONSOLE_URL = "http://localhost:30921"
NEXUS_URL         = "http://localhost:30081"
NEXUS_AUTH        = ("admin", "Admin@123456789@")

# ── Page config ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DevOps MCP Toolkit",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Hide streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1b2a 0%, #1a2a3a 100%);
}
[data-testid="stSidebar"] * { color: #e0e0e0 !important; }

/* Radio nav labels */
[data-testid="stSidebar"] .stRadio label {
    color: #b0c4de !important;
    font-size: 0.88rem !important;
    padding: 2px 0 !important;
}

/* Page header card */
.page-header {
    background: linear-gradient(135deg, #1e3a5f 0%, #0e2440 100%);
    padding: 1.5rem 2rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
    border-left: 4px solid #4fc3f7;
}
.page-header h1 { color: white; margin: 0; font-size: 1.8rem; }
.page-header p { color: #90caf9; margin: 0.3rem 0 0 0; }

/* Service cards */
.service-card {
    background: #1e2a3a;
    border: 1px solid #2d3f55;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.5rem;
    height: 100%;
}
.service-card-up   { border-left: 4px solid #4caf50; }
.service-card-down { border-left: 4px solid #f44336; }
.card-title   { font-size: 0.85rem; color: #90caf9; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.3rem; }
.card-value   { font-size: 1.4rem; font-weight: bold; color: #ffffff; margin-bottom: 0.2rem; }
.card-subtitle{ font-size: 0.78rem; color: #78909c; }
.status-up    { color: #4caf50; font-weight: bold; }
.status-down  { color: #f44336; font-weight: bold; }

/* Status badges */
.badge-up {
    background: #1b5e20; color: #a5d6a7;
    padding: 2px 10px; border-radius: 20px;
    font-size: 0.75rem; font-weight: bold; display: inline-block;
}
.badge-down {
    background: #b71c1c; color: #ffcdd2;
    padding: 2px 10px; border-radius: 20px;
    font-size: 0.75rem; font-weight: bold; display: inline-block;
}
.badge-warn {
    background: #e65100; color: #ffe0b2;
    padding: 2px 10px; border-radius: 20px;
    font-size: 0.75rem; font-weight: bold; display: inline-block;
}
.badge-info {
    background: #0d47a1; color: #bbdefb;
    padding: 2px 10px; border-radius: 20px;
    font-size: 0.75rem; font-weight: bold; display: inline-block;
}

/* Metric gradient card */
.metric-card {
    background: linear-gradient(135deg, #1a237e 0%, #283593 100%);
    border-radius: 10px; padding: 1rem 1.2rem;
    text-align: center; height: 100%;
}
.metric-card .value { font-size: 2rem; font-weight: bold; color: #fff; }
.metric-card .label { font-size: 0.8rem; color: #9fa8da; text-transform: uppercase; letter-spacing: 0.05em; }

/* Status dot */
.dot-up   { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #4caf50; margin-right: 6px; }
.dot-down { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #f44336; margin-right: 6px; }

/* Pulse animation for live services */
@keyframes pulse-green {
  0%   { box-shadow: 0 0 0 0 rgba(76,175,80,0.6); }
  70%  { box-shadow: 0 0 0 7px rgba(76,175,80,0); }
  100% { box-shadow: 0 0 0 0 rgba(76,175,80,0); }
}
@keyframes pulse-red {
  0%   { box-shadow: 0 0 0 0 rgba(244,67,54,0.6); }
  70%  { box-shadow: 0 0 0 7px rgba(244,67,54,0); }
  100% { box-shadow: 0 0 0 0 rgba(244,67,54,0); }
}
.pulse-up   { animation: pulse-green 2s infinite; }
.pulse-down { animation: pulse-red  2s infinite; }

/* KPI summary cards */
.kpi-card {
  background: linear-gradient(135deg, #1a2535 0%, #243447 100%);
  border: 1px solid #2d4a6a;
  border-radius: 14px;
  padding: 1.1rem 1.4rem;
  text-align: center;
  height: 100%;
}
.kpi-number { font-size: 2.6rem; font-weight: 900; line-height: 1; margin-bottom: 0.2rem; }
.kpi-label  { font-size: 0.72rem; color: #78909c; text-transform: uppercase; letter-spacing: 0.08em; }
.kpi-sub    { font-size: 0.82rem; margin-top: 0.35rem; font-weight: 600; }

/* Rich service tiles */
.svc-tile {
  background: #151f2e;
  border: 1px solid #243040;
  border-radius: 14px;
  padding: 1rem 1.1rem;
  height: 100%;
  position: relative;
  overflow: hidden;
}
.svc-tile::before {
  content: "";
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
}
.svc-tile-up::before   { background: linear-gradient(90deg, #4caf50, #81c784); }
.svc-tile-down::before { background: linear-gradient(90deg, #f44336, #e57373); }
.svc-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.6rem; }
.svc-icon-name { display: flex; align-items: center; gap: 8px; }
.svc-icon   { font-size: 1.4rem; }
.svc-name   { font-size: 0.82rem; font-weight: 700; color: #90caf9; text-transform: uppercase; letter-spacing: 0.05em; }
.svc-status-dot {
  width: 10px; height: 10px; border-radius: 50%;
  flex-shrink: 0;
}
.svc-metric { font-size: 1.6rem; font-weight: 900; color: #ffffff; margin: 0.2rem 0 0.1rem 0; line-height: 1; }
.svc-detail { font-size: 0.72rem; color: #546e7a; }
.svc-link   { font-size: 0.7rem; color: #4fc3f7; text-decoration: none; font-weight: 600; }

/* Quick action tiles */
.qa-tile {
  background: linear-gradient(135deg, #1e2d40 0%, #162030 100%);
  border: 1px solid #2a3d55;
  border-radius: 12px;
  padding: 0.9rem 1rem;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s;
}
.qa-tile:hover { border-color: #4fc3f7; }
.qa-icon  { font-size: 1.6rem; margin-bottom: 0.3rem; }
.qa-label { font-size: 0.78rem; color: #b0bec5; font-weight: 600; }

/* Activity feed row */
.feed-row {
  display: flex; align-items: center; gap: 10px;
  padding: 6px 10px; border-radius: 8px;
  margin: 3px 0;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.05);
}
.feed-icon  { font-size: 1rem; flex-shrink: 0; }
.feed-title { font-size: 0.82rem; color: #cfd8dc; flex: 1; }
.feed-badge { font-size: 0.68rem; font-weight: bold; padding: 2px 8px; border-radius: 20px; }
.fb-success { background:#1b5e20; color:#a5d6a7; }
.fb-failure { background:#b71c1c; color:#ffcdd2; }
.fb-running { background:#e65100; color:#ffe0b2; }
.fb-info    { background:#0d47a1; color:#bbdefb; }
</style>
""", unsafe_allow_html=True)

# ── Helper functions ────────────────────────────────────────────────────────────
def port_up(port, host="localhost"):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.5)
    ok = s.connect_ex((host, port)) == 0
    s.close()
    return ok

def http_json(url, auth=None, params=None, timeout=6):
    import httpx
    try:
        r = httpx.get(url, auth=auth, params=params, timeout=timeout,
                      follow_redirects=True, verify=False)
        if r.status_code < 400:
            return r.json()
    except Exception:
        pass
    return None

def badge(text, style="up"):
    return f'<span class="badge-{style}">{text}</span>'

def status_badge(up, up_text="UP", down_text="DOWN"):
    return badge(up_text, "up") if up else badge(down_text, "down")

def show(result, success_msg=None):
    msg = success_msg or result.get("out") or "Done"
    if result["ok"]:
        st.success(msg)
    else:
        st.error(result.get("err") or result.get("out") or "Unknown error")

def page_header(icon, title, subtitle):
    st.markdown(f"""<div class="page-header">
      <h1>{icon} {title}</h1>
      <p>{subtitle}</p>
    </div>""", unsafe_allow_html=True)

def service_card(title, value, subtitle, up=True):
    card_class = "service-card-up" if up else "service-card-down"
    return f"""<div class="service-card {card_class}">
      <div class="card-title">{title}</div>
      <div class="card-value">{value}</div>
      <div class="card-subtitle">{subtitle}</div>
    </div>"""

# ── Sidebar ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:1rem 0 0.5rem 0;">
      <div style="font-size:2rem;">🛠️</div>
      <div style="font-size:1.1rem;font-weight:bold;color:#e0e0e0;">DevOps MCP Toolkit</div>
      <div style="font-size:0.7rem;color:#78909c;margin-top:0.2rem;">v2.0.0 | 15 MCP Servers</div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    # Support ?page=<slug> URL param (used by screenshot automation)
    _PAGE_MAP = {
        "dashboard":   "🏠 Dashboard",
        "docker":      "🐳 Docker",
        "kubernetes":  "☸️ Kubernetes",
        "terraform":   "🌍 Terraform",
        "jenkins":     "⚙️ Jenkins",
        "sonarqube":   "🔍 SonarQube",
        "argocd":      "🔀 ArgoCD",
        "trivy":       "🛡️ Trivy Scanner",
        "vault":       "🔐 Vault Secrets",
        "prometheus":  "📊 Prometheus & Grafana",
        "loki":        "📜 Loki Logs",
        "helm":        "⛵ Helm Manager",
        "registry":    "📦 Container Registry",
        "minio":       "🗄️ MinIO Storage",
        "nexus":       "🏛️ Nexus Repository",
    }
    _qp = st.query_params.get("page", "")
    if _qp and _qp in _PAGE_MAP:
        st.session_state["active_page"] = _PAGE_MAP[_qp]

    # ── All nav group keys ────────────────────────────────────────────────────
    _NAV_KEYS = ["nav_overview", "nav_infra", "nav_cicd",
                 "nav_sec", "nav_obs", "nav_dep", "nav_stor"]

    # First load: select Dashboard, clear all others
    if "active_page" not in st.session_state:
        st.session_state["active_page"] = "🏠 Dashboard"
        st.session_state["nav_overview"] = "🏠 Dashboard"
        for _k in _NAV_KEYS[1:]:
            st.session_state[_k] = None

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _strip_dot(label):
        if not label:
            return label
        for dot in ("🟢 ", "🔴 ", "🔵 "):
            if label.startswith(dot):
                return label[len(dot):]
        return label

    def _nav(key):
        """Select page; deselect every other radio group."""
        val = st.session_state.get(key)
        if not val:
            return
        st.session_state["active_page"] = _strip_dot(val)
        # Keep current key's value, clear all others
        current_val = val
        for _k in _NAV_KEYS:
            if _k != key:
                st.session_state[_k] = None
        st.session_state[key] = current_val  # ensure it stays selected

    # ── Live status dots ──────────────────────────────────────────────────────
    def _dot(port, host="localhost"):
        return "🔵" if port == 0 else ("🟢" if port_up(port, host=host) else "🔴")

    _dj   = _dot(30080);  _ds  = _dot(30900);  _da  = _dot(30085)
    _dp   = _dot(30090);  _dv  = _dot(30200);  _dl  = _dot(30310)
    _dreg = _dot(30880, host="127.0.0.1")
    _dm   = _dot(30921);  _dn  = _dot(30081)

    def _grp_header(label):
        st.markdown(
            f'<p style="font-size:0.68rem;color:#546e7a;text-transform:uppercase;'
            f'letter-spacing:0.1em;margin:0.75rem 0 0.25rem 0;">{label}</p>',
            unsafe_allow_html=True,
        )

    # URL param support
    _PAGE_MAP = {
        "dashboard": "🏠 Dashboard", "docker": "🐳 Docker",
        "kubernetes": "☸️ Kubernetes", "terraform": "🌍 Terraform",
        "jenkins": "⚙️ Jenkins", "sonarqube": "🔍 SonarQube",
        "argocd": "🔀 ArgoCD", "trivy": "🛡️ Trivy Scanner",
        "vault": "🔐 Vault Secrets", "prometheus": "📊 Prometheus & Grafana",
        "loki": "📜 Loki Logs", "helm": "⛵ Helm Manager",
        "registry": "📦 Container Registry", "minio": "🗄️ MinIO Storage",
        "nexus": "🏛️ Nexus Repository",
    }
    _qp = st.query_params.get("page", "")
    if _qp and _qp in _PAGE_MAP:
        st.session_state["active_page"] = _PAGE_MAP[_qp]

    # ── Radio groups — index=None on ALL so session state fully controls ─────
    # On first load, session state sets nav_overview="🏠 Dashboard" (see init).
    # _nav() clears all other groups → only one radio is ever checked at a time.

    _grp_header("Overview")
    st.radio("Overview", ["🏠 Dashboard"], key="nav_overview", index=None,
             label_visibility="collapsed", on_change=_nav, args=("nav_overview",))

    _grp_header("Infrastructure")
    st.radio("Infrastructure", ["🐳 Docker", "☸️ Kubernetes", "🌍 Terraform"],
             key="nav_infra", index=None, label_visibility="collapsed",
             on_change=_nav, args=("nav_infra",))

    _grp_header("CI / CD")
    st.radio("CI/CD",
             [f"{_dj} ⚙️ Jenkins", f"{_ds} 🔍 SonarQube", f"{_da} 🔀 ArgoCD"],
             key="nav_cicd", index=None, label_visibility="collapsed",
             on_change=_nav, args=("nav_cicd",))

    _grp_header("Security")
    st.radio("Security",
             [f"🔵 🛡️ Trivy Scanner", f"{_dv} 🔐 Vault Secrets"],
             key="nav_sec", index=None, label_visibility="collapsed",
             on_change=_nav, args=("nav_sec",))

    _grp_header("Observability")
    st.radio("Observability",
             [f"{_dp} 📊 Prometheus & Grafana", f"{_dl} 📜 Loki Logs"],
             key="nav_obs", index=None, label_visibility="collapsed",
             on_change=_nav, args=("nav_obs",))

    _grp_header("Deployment")
    st.radio("Deployment", ["🔵 ⛵ Helm Manager"],
             key="nav_dep", index=None, label_visibility="collapsed",
             on_change=_nav, args=("nav_dep",))

    _grp_header("Storage & Registry")
    st.radio("Storage",
             [f"{_dreg} 📦 Container Registry",
              f"{_dm} 🗄️ MinIO Storage",
              f"{_dn} 🏛️ Nexus Repository"],
             key="nav_stor", index=None, label_visibility="collapsed",
             on_change=_nav, args=("nav_stor",))

    active_page = st.session_state.get("active_page", "🏠 Dashboard")

    # ── MCP Services status + URL panel ──────────────────────────────────────
    st.divider()
    st.markdown(
        '<p style="font-size:0.68rem;color:#546e7a;text-transform:uppercase;'
        'letter-spacing:0.1em;margin:0 0 0.4rem 0;">🔌 MCP Services & URLs</p>',
        unsafe_allow_html=True,
    )

    _SVC_PANEL = [
        ("⚙️", "Jenkins",            30080, "http://localhost:30080",   "localhost"),
        ("🔍", "SonarQube",          30900, "http://localhost:30900",   "localhost"),
        ("🔀", "ArgoCD",             30085, "https://localhost:30085",  "localhost"),
        ("📊", "Prometheus",         30090, "http://localhost:30090",   "localhost"),
        ("📈", "Grafana",            30030, "http://localhost:30030",   "localhost"),
        ("🔐", "Vault",              30200, "http://localhost:30200",   "localhost"),
        ("📜", "Loki",               30310, "http://localhost:30310",   "localhost"),
        ("📦", "Harbor Registry",    30880, "http://127.0.0.1:30881",  "127.0.0.1"),
        ("🗄️", "MinIO Console",      30921, "http://localhost:30921",   "localhost"),
        ("🏛️", "Nexus",             30081, "http://localhost:30081",   "localhost"),
        ("☸️", "Kubernetes",         0,     "",                         ""),
        ("🐳", "Docker",             0,     "",                         ""),
        ("🌍", "Terraform",          0,     "",                         ""),
        ("🛡️", "Trivy",              0,     "",                         ""),
        ("⛵", "Helm",               0,     "",                         ""),
    ]

    _html = ""
    for _ico, _name, _port, _url, _host in _SVC_PANEL:
        if _port > 0:
            _up = port_up(_port, host=_host or "localhost")
            _dc  = "#4caf50" if _up else "#f44336"
            _stxt = "UP" if _up else "DOWN"
            _link = (f'<a href="{_url}" target="_blank" '
                     f'style="color:#64b5f6;font-size:0.6rem;text-decoration:none;">'
                     f'{_url.replace("http://","").replace("https://","")}</a>') if _url else ""
        else:
            _dc, _stxt, _link = "#78909c", "CLI", ""

        _html += f"""
        <div style="display:flex;align-items:center;justify-content:space-between;
                    padding:3px 6px;margin:2px 0;border-radius:6px;
                    background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.05);">
          <div style="display:flex;align-items:center;gap:5px;min-width:0;">
            <span style="width:7px;height:7px;border-radius:50%;background:{_dc};
                         display:inline-block;flex-shrink:0;"></span>
            <span style="font-size:0.78rem;color:#cfd8dc;white-space:nowrap;">{_ico} {_name}</span>
          </div>
          <div style="display:flex;flex-direction:column;align-items:flex-end;gap:0px;flex-shrink:0;">
            <span style="font-size:0.62rem;font-weight:bold;color:{_dc};">{_stxt}</span>
            {f'<span>{_link}</span>' if _link else ""}
          </div>
        </div>"""

    st.markdown(_html, unsafe_allow_html=True)

    st.divider()
    auto_refresh = st.toggle("⟳ Auto-refresh (30s)", value=False)

if auto_refresh:
    time.sleep(30)
    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — DASHBOARD (Enhanced)
# ══════════════════════════════════════════════════════════════════════════════
if active_page == "🏠 Dashboard":
    import pandas as pd

    # ── Cached data loaders ──────────────────────────────────────────────────
    @st.cache_data(ttl=30)
    def dash_jenkins():
        data = http_json(f"{JENKINS_URL}/api/json", auth=JENKINS_AUTH)
        up = data is not None
        jobs = len(data.get("jobs", [])) if data else 0
        return up, jobs

    @st.cache_data(ttl=30)
    def dash_sonar():
        data = http_json(f"{SONAR_URL}/api/projects/search", auth=SONAR_AUTH)
        up = data is not None
        count = data.get("paging", {}).get("total", 0) if data else 0
        return up, count

    @st.cache_data(ttl=30)
    def dash_k8s_pods(ns="devops"):
        r = kube("get pods --no-headers", ns=ns)
        if r["ok"] and r["out"]:
            return True, len([l for l in r["out"].splitlines() if l.strip()])
        return False, 0

    @st.cache_data(ttl=30)
    def dash_grafana():
        data = http_json(f"{GRAFANA_URL}/api/datasources", auth=GRAFANA_AUTH)
        up = data is not None
        count = len(data) if data else 0
        return up, count

    @st.cache_data(ttl=30)
    def dash_argocd():
        import httpx
        try:
            auth_r = httpx.post(f"{ARGOCD_URL}/api/v1/session",
                                json={"username": "admin", "password": "Admin@123456789@"},
                                timeout=6, verify=False)
            if auth_r.status_code == 200:
                token = auth_r.json().get("token", "")
                apps_r = httpx.get(f"{ARGOCD_URL}/api/v1/applications",
                                   headers={"Authorization": f"Bearer {token}"},
                                   timeout=6, verify=False)
                if apps_r.status_code == 200:
                    apps = apps_r.json().get("items", []) or []
                    return True, len(apps)
        except Exception:
            pass
        return False, 0

    @st.cache_data(ttl=30)
    def dash_prometheus():
        data = http_json(f"{PROM_URL}/api/v1/targets")
        if data and data.get("status") == "success":
            active = data.get("data", {}).get("activeTargets", [])
            return True, len(active)
        return port_up(30090), 0

    @st.cache_data(ttl=30)
    def dash_vault():
        data = http_json(f"{VAULT_URL}/v1/sys/health")
        if data:
            sealed = data.get("sealed", True)
            return True, "Sealed" if sealed else "Unsealed"
        return port_up(30200), "Unknown"

    @st.cache_data(ttl=30)
    def dash_loki():
        up = port_up(30310)
        return up, "Ready" if up else "Unreachable"

    @st.cache_data(ttl=30)
    def dash_minio():
        up = port_up(30920)
        data = http_json(f"{MINIO_URL}/minio/health/live") if up else None
        return up, "UP" if up else "DOWN"

    @st.cache_data(ttl=30)
    def dash_nexus():
        data = http_json(f"{NEXUS_URL}/service/rest/v1/repositories", auth=NEXUS_AUTH)
        up = data is not None
        count = len(data) if data else 0
        return up, count

    @st.cache_data(ttl=30)
    def dash_harbor():
        up = port_up(30880, host="127.0.0.1")
        data = http_json(f"http://127.0.0.1:30880/api/v2.0/systeminfo",
                         auth=("admin", "Admin@123456789@")) if up else None
        return up, data.get("harbor_version", "UP") if data else ("UP" if up else "DOWN")

    @st.cache_data(ttl=30)
    def get_pods_table():
        r = kube("get pods -o wide --no-headers", ns="devops")
        rows = []
        if r["ok"] and r["out"]:
            for line in r["out"].splitlines():
                parts = line.split()
                if len(parts) >= 4:
                    rows.append({
                        "Name":     parts[0],
                        "Ready":    parts[1],
                        "Status":   parts[2],
                        "Restarts": parts[3],
                        "Age":      parts[4] if len(parts) > 4 else "",
                    })
        return rows

    @st.cache_data(ttl=30)
    def get_jenkins_builds():
        jobs_data = http_json(
            f"{JENKINS_URL}/api/json?tree=jobs[name,lastBuild[number,result,timestamp,duration]]",
            auth=JENKINS_AUTH)
        builds = []
        if jobs_data:
            for job in (jobs_data.get("jobs") or [])[:10]:
                lb = job.get("lastBuild") or {}
                if lb:
                    builds.append({
                        "Job":      job.get("name", ""),
                        "Build #":  lb.get("number", ""),
                        "Result":   lb.get("result") or "BUILDING",
                        "Duration": f"{int(lb.get('duration', 0)/1000)}s",
                    })
        return builds

    @st.cache_data(ttl=60)
    def get_prom_metrics():
        cpu = http_json(f"{PROM_URL}/api/v1/query",
            params={"query": 'sum(rate(container_cpu_usage_seconds_total{namespace="devops",container!=""}[5m])) by (pod)'})
        mem = http_json(f"{PROM_URL}/api/v1/query",
            params={"query": 'sum(container_memory_working_set_bytes{namespace="devops",container!=""}) by (pod)'})
        return cpu, mem

    # ── Fetch all data ────────────────────────────────────────────────────────
    jen_up,  jen_jobs   = dash_jenkins()
    son_up,  son_proj   = dash_sonar()
    k8s_up,  k8s_pods   = dash_k8s_pods()
    graf_up, graf_ds    = dash_grafana()
    argo_up, argo_apps  = dash_argocd()
    prom_up, prom_tgts  = dash_prometheus()
    vault_up,vault_state= dash_vault()
    loki_up, loki_state = dash_loki()
    minio_up,minio_state= dash_minio()
    nex_up,  nex_repos  = dash_nexus()
    hrb_up,  hrb_ver    = dash_harbor()

    all_ups = [jen_up, son_up, k8s_up, graf_up, argo_up,
               prom_up, vault_up, loki_up, minio_up, nex_up, hrb_up]
    services_up   = sum(all_ups)
    services_total = len(all_ups)
    health_pct    = int(services_up / services_total * 100)

    # ── Header row ───────────────────────────────────────────────────────────
    hd_left, hd_right = st.columns([5, 1])
    with hd_left:
        st.markdown("""
        <div style="padding:0.8rem 0 0.5rem 0;">
          <h1 style="color:#fff;margin:0;font-size:1.9rem;font-weight:900;">
            🏠 DevOps Stack Dashboard
          </h1>
          <p style="color:#78909c;margin:0.3rem 0 0 0;font-size:0.88rem;">
            Real-time health monitor · Kubernetes cluster · 15 MCP servers
          </p>
        </div>""", unsafe_allow_html=True)
    with hd_right:
        st.markdown("<div style='height:0.9rem'></div>", unsafe_allow_html=True)
        if st.button("🔄 Refresh", type="primary", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # ── KPI summary strip ─────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    health_color = "#4caf50" if health_pct >= 80 else "#ff9800" if health_pct >= 50 else "#f44336"
    k1.markdown(f"""<div class="kpi-card">
      <div class="kpi-number" style="color:{health_color};">{health_pct}%</div>
      <div class="kpi-label">Cluster Health</div>
      <div class="kpi-sub" style="color:{health_color};">{services_up}/{services_total} services UP</div>
    </div>""", unsafe_allow_html=True)

    k2.markdown(f"""<div class="kpi-card">
      <div class="kpi-number" style="color:#64b5f6;">{k8s_pods}</div>
      <div class="kpi-label">Pods Running</div>
      <div class="kpi-sub" style="color:{'#4caf50' if k8s_up else '#f44336'};">devops namespace</div>
    </div>""", unsafe_allow_html=True)

    k3.markdown(f"""<div class="kpi-card">
      <div class="kpi-number" style="color:#ffb74d;">{jen_jobs}</div>
      <div class="kpi-label">Jenkins Jobs</div>
      <div class="kpi-sub" style="color:{'#4caf50' if jen_up else '#f44336'};">{'Online' if jen_up else 'Offline'} · :30080</div>
    </div>""", unsafe_allow_html=True)

    k4.markdown(f"""<div class="kpi-card">
      <div class="kpi-number" style="color:#ce93d8;">{prom_tgts}</div>
      <div class="kpi-label">Prom Targets</div>
      <div class="kpi-sub" style="color:{'#4caf50' if prom_up else '#f44336'};">{'Scraping' if prom_up else 'Offline'} · :30090</div>
    </div>""", unsafe_allow_html=True)

    k5.markdown(f"""<div class="kpi-card">
      <div class="kpi-number" style="color:#80cbc4;">{'🔓' if vault_state=='Unsealed' else '🔒'}</div>
      <div class="kpi-label">Vault</div>
      <div class="kpi-sub" style="color:{'#4caf50' if vault_state=='Unsealed' else '#ff9800'};">{vault_state} · :30200</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

    # ── Service tiles — helper ────────────────────────────────────────────────
    def svc_tile(icon, name, metric, detail, url, up):
        dot_color = "#4caf50" if up else "#f44336"
        cls = "svc-tile-up" if up else "svc-tile-down"
        link_html = f'<a href="{url}" target="_blank" class="svc-link">↗ Open</a>' if url else ""
        return f"""
        <div class="svc-tile {cls}">
          <div class="svc-header">
            <div class="svc-icon-name">
              <span class="svc-icon">{icon}</span>
              <span class="svc-name">{name}</span>
            </div>
            <div class="svc-status-dot pulse-{'up' if up else 'down'}"
                 style="background:{dot_color};width:10px;height:10px;border-radius:50%;"></div>
          </div>
          <div class="svc-metric">{metric}</div>
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:4px;">
            <span class="svc-detail">{detail}</span>
            {link_html}
          </div>
        </div>"""

    # ── Row 1: CI/CD + Infra ──────────────────────────────────────────────────
    st.markdown('<p style="font-size:0.72rem;color:#546e7a;text-transform:uppercase;letter-spacing:0.1em;margin:0.4rem 0 0.5rem 0;">● CI/CD & Infrastructure</p>', unsafe_allow_html=True)
    r1c1, r1c2, r1c3, r1c4, r1c5, r1c6 = st.columns(6)
    r1c1.markdown(svc_tile("⚙️","Jenkins",   f"{jen_jobs} Jobs",     ":30080", JENKINS_URL,    jen_up),  unsafe_allow_html=True)
    r1c2.markdown(svc_tile("🔍","SonarQube", f"{son_proj} Projects", ":30900", SONAR_URL,      son_up),  unsafe_allow_html=True)
    r1c3.markdown(svc_tile("🔀","ArgoCD",    f"{argo_apps} Apps",    ":30085", ARGOCD_URL,     argo_up), unsafe_allow_html=True)
    r1c4.markdown(svc_tile("☸️","Kubernetes", f"{k8s_pods} Pods",   "devops ns", "",           k8s_up),  unsafe_allow_html=True)
    r1c5.markdown(svc_tile("📈","Grafana",   f"{graf_ds} Sources",   ":30030", GRAFANA_URL,    graf_up), unsafe_allow_html=True)
    r1c6.markdown(svc_tile("📊","Prometheus",f"{prom_tgts} Targets", ":30090", PROM_URL,       prom_up), unsafe_allow_html=True)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ── Row 2: Storage + Security ──────────────────────────────────────────────
    st.markdown('<p style="font-size:0.72rem;color:#546e7a;text-transform:uppercase;letter-spacing:0.1em;margin:0.4rem 0 0.5rem 0;">● Storage, Security & Observability</p>', unsafe_allow_html=True)
    r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns(5)
    r2c1.markdown(svc_tile("🔐","Vault",     vault_state,            ":30200", VAULT_URL,      vault_up), unsafe_allow_html=True)
    r2c2.markdown(svc_tile("📜","Loki",      loki_state,             ":30310", LOKI_URL,       loki_up),  unsafe_allow_html=True)
    r2c3.markdown(svc_tile("🗄️","MinIO",    minio_state,             ":30921", MINIO_CONSOLE_URL, minio_up), unsafe_allow_html=True)
    r2c4.markdown(svc_tile("🏛️","Nexus",    f"{nex_repos} Repos",   ":30081", NEXUS_URL,      nex_up),   unsafe_allow_html=True)
    r2c5.markdown(svc_tile("📦","Harbor",   str(hrb_ver),            ":30880", "http://127.0.0.1:30881", hrb_up), unsafe_allow_html=True)

    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

    # ── Quick Actions ─────────────────────────────────────────────────────────
    st.markdown('<p style="font-size:0.72rem;color:#546e7a;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 0.5rem 0;">● Quick Actions</p>', unsafe_allow_html=True)
    qa1, qa2, qa3, qa4, qa5, qa6 = st.columns(6)

    with qa1:
        if st.button("🔄  Restart All Pods", use_container_width=True):
            with st.spinner("Restarting deployments..."):
                dep_r = kube("get deployments -o jsonpath='{.items[*].metadata.name}'", ns="devops")
                if dep_r["ok"] and dep_r["out"]:
                    deps = dep_r["out"].strip("'").split()
                    for d in deps:
                        kube(f"rollout restart deployment/{d}", ns="devops")
                    st.success(f"✅ Restarted {len(deps)} deployment(s)")
                else:
                    st.warning("No deployments found in devops namespace")
    with qa2:
        if st.button("🧹  Docker Prune", use_container_width=True):
            with st.spinner("Pruning Docker..."):
                r = docker("system prune -f")
            show(r, "✅ Docker system pruned")
    with qa3:
        st.link_button("📈  Open Grafana",    GRAFANA_URL,  use_container_width=True)
    with qa4:
        st.link_button("⚙️  Open Jenkins",    JENKINS_URL,  use_container_width=True)
    with qa5:
        st.link_button("🔍  Open SonarQube",  SONAR_URL,    use_container_width=True)
    with qa6:
        st.link_button("🔐  Open Vault",      VAULT_URL,    use_container_width=True)

    st.divider()

    # ── Activity section: K8s pods + Jenkins builds ───────────────────────────
    left_col, right_col = st.columns([3, 2])

    with left_col:
        st.markdown("##### ☸️ K8s Pods — devops namespace")
        pods_rows = get_pods_table()
        if pods_rows:
            df_pods = pd.DataFrame(pods_rows)

            def _pod_color(row):
                s = row.get("Status", "")
                if s == "Running":   return ["background-color:#0a2a0a"] * len(row)
                if s == "Pending":   return ["background-color:#2a2000"] * len(row)
                if "Error" in s or "CrashLoop" in s:
                    return ["background-color:#2a0a0a"] * len(row)
                return [""] * len(row)

            st.dataframe(
                df_pods.style.apply(_pod_color, axis=1),
                use_container_width=True, hide_index=True,
            )

            # Status summary badges
            statuses = [r["Status"] for r in pods_rows]
            running  = statuses.count("Running")
            pending  = sum(1 for s in statuses if "Pending" in s)
            errored  = sum(1 for s in statuses if "Error" in s or "Crash" in s)
            _badge_html = f'<span class="badge-up">{running} Running</span> '
            if pending: _badge_html += f'<span class="badge-warn">{pending} Pending</span> '
            if errored: _badge_html += f'<span class="badge-down">{errored} Error</span>'
            st.markdown(_badge_html, unsafe_allow_html=True)
        else:
            st.info("No pods found in devops namespace")

    with right_col:
        st.markdown("##### ⚙️ Recent Jenkins Builds")
        jbuilds = get_jenkins_builds()
        if jbuilds:
            feed_html = ""
            for b in jbuilds[:8]:
                result = b["Result"]
                if result == "SUCCESS":
                    icon, badge_cls = "✅", "fb-success"
                elif result == "FAILURE":
                    icon, badge_cls = "❌", "fb-failure"
                elif result == "BUILDING":
                    icon, badge_cls = "🔄", "fb-running"
                else:
                    icon, badge_cls = "⚪", "fb-info"
                feed_html += f"""
                <div class="feed-row">
                  <span class="feed-icon">{icon}</span>
                  <span class="feed-title">{b['Job']} <span style="color:#546e7a;font-size:0.72rem;">#{b['Build #']}</span></span>
                  <span class="feed-badge {badge_cls}">{result}</span>
                  <span style="font-size:0.7rem;color:#546e7a;">{b['Duration']}</span>
                </div>"""
            st.markdown(feed_html, unsafe_allow_html=True)
        else:
            st.info("Jenkins unreachable or no builds found")

    st.divider()

    # ── Prometheus resource charts (Plotly) ───────────────────────────────────
    st.markdown("##### 📈 Pod Resource Usage (live from Prometheus)")

    if prom_up:
        try:
            cpu_data, mem_data = get_prom_metrics()
            import plotly.graph_objects as go

            pc1, pc2 = st.columns(2)

            with pc1:
                if cpu_data and cpu_data.get("status") == "success":
                    results = cpu_data["data"]["result"]
                    if results:
                        pods   = [r["metric"].get("pod","?").split("-")[0] for r in results]
                        values = [round(float(r["value"][1])*1000, 2) for r in results]
                        fig = go.Figure(go.Bar(
                            x=values, y=pods, orientation="h",
                            marker=dict(
                                color=values,
                                colorscale=[[0,"#1b5e20"],[0.5,"#f9a825"],[1,"#b71c1c"]],
                                showscale=False,
                            ),
                            text=[f"{v} m" for v in values],
                            textposition="outside",
                        ))
                        fig.update_layout(
                            title=dict(text="CPU Usage (millicores)", font=dict(color="#90caf9",size=13)),
                            paper_bgcolor="#151f2e", plot_bgcolor="#151f2e",
                            font=dict(color="#cfd8dc", size=11),
                            xaxis=dict(showgrid=True, gridcolor="#243040", color="#78909c"),
                            yaxis=dict(showgrid=False, color="#cfd8dc"),
                            margin=dict(l=10,r=40,t=40,b=10),
                            height=280,
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No CPU data yet — Prometheus may still be scraping")
                else:
                    st.info("Waiting for Prometheus CPU data")

            with pc2:
                if mem_data and mem_data.get("status") == "success":
                    results = mem_data["data"]["result"]
                    if results:
                        pods   = [r["metric"].get("pod","?").split("-")[0] for r in results]
                        values = [round(float(r["value"][1])/(1024**2), 1) for r in results]
                        fig = go.Figure(go.Bar(
                            x=values, y=pods, orientation="h",
                            marker=dict(
                                color=values,
                                colorscale=[[0,"#0d47a1"],[0.5,"#6a1b9a"],[1,"#880e4f"]],
                                showscale=False,
                            ),
                            text=[f"{v} MB" for v in values],
                            textposition="outside",
                        ))
                        fig.update_layout(
                            title=dict(text="Memory Usage (MB)", font=dict(color="#90caf9",size=13)),
                            paper_bgcolor="#151f2e", plot_bgcolor="#151f2e",
                            font=dict(color="#cfd8dc", size=11),
                            xaxis=dict(showgrid=True, gridcolor="#243040", color="#78909c"),
                            yaxis=dict(showgrid=False, color="#cfd8dc"),
                            margin=dict(l=10,r=60,t=40,b=10),
                            height=280,
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No memory data yet")
                else:
                    st.info("Waiting for Prometheus memory data")
        except Exception as e:
            st.warning(f"Could not load Prometheus metrics: {e}")
    else:
        st.info("Prometheus unreachable — start with `kubectl apply -f k8s/prometheus/`")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — DOCKER
# ══════════════════════════════════════════════════════════════════════════════
elif active_page == "🐳 Docker":
    page_header("🐳", "Docker Manager", "Manage containers, images, volumes and networks")

    tab1, tab2, tab3, tab4 = st.tabs(["📦 Containers", "🖼️ Images", "💾 Volumes", "⚡ Actions"])

    with tab1:
        show_all = st.toggle("Show stopped containers", value=True)
        flag = "-a" if show_all else ""
        with st.spinner("Loading containers..."):
            out = docker(f"ps {flag} --format json")
        if out["ok"] and out["out"]:
            containers = [json.loads(l) for l in out["out"].splitlines() if l.strip()]
            import pandas as pd
            df = pd.DataFrame([{
                "Name":    c.get("Names", ""),
                "Image":   c.get("Image", ""),
                "Status":  c.get("Status", ""),
                "State":   c.get("State", ""),
                "Ports":   c.get("Ports", ""),
                "Created": c.get("CreatedAt", ""),
            } for c in containers])
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.divider()
            st.markdown("##### Container Actions")
            names = [c.get("Names", "") for c in containers]
            selected = st.selectbox("Select container", names, key="docker_sel")
            ca1, ca2, ca3, ca4, ca5 = st.columns(5)
            if ca1.button("▶ Start"):
                show(docker(f"start {selected}"))
            if ca2.button("⏹ Stop"):
                show(docker(f"stop {selected}"))
            if ca3.button("🔄 Restart"):
                show(docker(f"restart {selected}"))
            if ca4.button("📋 Logs"):
                r = docker(f"logs --tail 100 {selected}")
                st.code(r["out"] or r["err"], language="bash")
            if ca5.button("🗑 Remove"):
                show(docker(f"rm -f {selected}"))
        else:
            st.info("No containers found — Docker may not be running")

    with tab2:
        with st.spinner("Loading images..."):
            out = docker("images --format json")
        if out["ok"] and out["out"]:
            images = [json.loads(l) for l in out["out"].splitlines() if l.strip()]
            import pandas as pd
            df = pd.DataFrame([{
                "Repository": i.get("Repository", ""),
                "Tag":        i.get("Tag", ""),
                "ID":         i.get("ID", "")[:12],
                "Size":       i.get("Size", ""),
                "Created":    i.get("CreatedSince", ""),
            } for i in images])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No images found")

        st.divider()
        st.markdown("##### Pull Image")
        img_name = st.text_input("Image name (e.g. nginx:latest)")
        if st.button("⬇ Pull") and img_name:
            with st.spinner(f"Pulling {img_name}..."):
                r = docker(f"pull {img_name}")
            show(r, f"Pulled {img_name} successfully")

    with tab3:
        with st.spinner("Loading volumes..."):
            out = docker("volume ls --format json")
        if out["ok"] and out["out"]:
            vols = [json.loads(l) for l in out["out"].splitlines() if l.strip()]
            import pandas as pd
            st.dataframe(pd.DataFrame([{
                "Name":   v.get("Name", ""),
                "Driver": v.get("Driver", ""),
                "Scope":  v.get("Scope", ""),
            } for v in vols]), use_container_width=True, hide_index=True)
        else:
            st.info("No volumes found")

        out_nets = docker("network ls --format json")
        if out_nets["ok"] and out_nets["out"]:
            st.markdown("##### Networks")
            nets = [json.loads(l) for l in out_nets["out"].splitlines() if l.strip()]
            import pandas as pd
            st.dataframe(pd.DataFrame([{
                "Name":   n.get("Name", ""),
                "Driver": n.get("Driver", ""),
                "Scope":  n.get("Scope", ""),
            } for n in nets]), use_container_width=True, hide_index=True)

    with tab4:
        st.markdown("##### Run New Container")
        with st.form("run_container"):
            image  = st.text_input("Image", value="nginx:latest")
            name   = st.text_input("Container name (optional)")
            ports  = st.text_input("Port mapping (e.g. 8081:80)")
            detach = st.checkbox("Run detached", value=True)
            submitted = st.form_submit_button("🚀 Run Container")
            if submitted and image:
                cmd = "run"
                if detach: cmd += " -d"
                if name:   cmd += f" --name {name}"
                if ports:  cmd += f" -p {ports}"
                cmd += f" {image}"
                r = docker(cmd)
                show(r, f"Container started: {r['out'][:20]}")

        st.divider()
        st.markdown("##### System Prune")
        st.warning("Removes stopped containers, unused images, networks and build cache.")
        if st.button("🗑 Prune System", type="secondary"):
            with st.spinner("Pruning..."):
                r = docker("system prune -f")
            show(r, "System pruned successfully")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — KUBERNETES
# ══════════════════════════════════════════════════════════════════════════════
elif active_page == "☸️ Kubernetes":
    page_header("☸️", "Kubernetes Manager", "Pods, deployments, services, events — docker-desktop cluster")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🟢 Pods", "📦 Deployments", "🌐 Services", "📋 Events", "📜 Logs", "⚙️ Manage"])

    with tab1:
        ns_input = st.text_input("Namespace", value="devops", key="k8s_ns")
        if st.button("🔄 Refresh", key="k8s_refresh_pods"):
            st.cache_data.clear()

        @st.cache_data(ttl=30)
        def get_pods_wide(ns):
            r = kube("get pods -o wide --no-headers", ns=ns)
            return r

        r = get_pods_wide(ns_input)
        if r["ok"] and r["out"]:
            import pandas as pd
            rows = []
            for line in r["out"].splitlines():
                parts = line.split()
                if len(parts) >= 5:
                    restarts = int(parts[3]) if parts[3].isdigit() else 0
                    rows.append({
                        "Name":     parts[0],
                        "Ready":    parts[1],
                        "Status":   parts[2],
                        "Restarts": restarts,
                        "Age":      parts[4] if len(parts) > 4 else "",
                        "IP":       parts[5] if len(parts) > 5 else "",
                        "Node":     parts[6] if len(parts) > 6 else "",
                    })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            high_restart = [r for r in rows if r["Restarts"] > 3]
            if high_restart:
                st.warning(f"⚠️ {len(high_restart)} pod(s) with high restart count: {', '.join(p['Name'] for p in high_restart)}")
        else:
            st.info("No pods found or cluster unreachable")

        st.divider()
        pod_out = kube(f"get pods -o jsonpath='{{.items[*].metadata.name}}'", ns=ns_input)
        pod_names = pod_out["out"].strip("'").split() if pod_out["ok"] and pod_out["out"] else []
        if pod_names:
            sel_pod = st.selectbox("Select pod for actions", pod_names)
            pk1, pk2, pk3 = st.columns(3)
            if pk1.button("🔍 Describe"):
                r = kube(f"describe pod {sel_pod}", ns=ns_input)
                st.code(r["out"], language="bash")
            if pk2.button("🗑 Delete Pod"):
                show(kube(f"delete pod {sel_pod}", ns=ns_input))
            if pk3.button("📋 Previous Logs"):
                r = kube(f"logs {sel_pod} --previous --tail=50", ns=ns_input)
                st.code(r["out"] or r["err"], language="bash")

    with tab2:
        @st.cache_data(ttl=30)
        def get_deployments():
            r = kube("get deployments --no-headers", ns="devops")
            return r

        r = get_deployments()
        if r["ok"] and r["out"]:
            import pandas as pd
            rows = []
            for line in r["out"].splitlines():
                parts = line.split()
                if len(parts) >= 4:
                    rows.append({
                        "Name":     parts[0],
                        "Ready":    parts[1],
                        "Up-to-date": parts[2],
                        "Available": parts[3],
                        "Age":      parts[4] if len(parts) > 4 else "",
                    })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No deployments in devops namespace")

        st.divider()
        st.markdown("##### Scale Deployment")
        dep_out = kube("get deployments -o jsonpath='{.items[*].metadata.name}'", ns="devops")
        dep_names = dep_out["out"].strip("'").split() if dep_out["ok"] and dep_out["out"] else []
        if dep_names:
            sel_dep = st.selectbox("Deployment", dep_names)
            replicas = st.slider("Replicas", min_value=0, max_value=5, value=1)
            dk1, dk2 = st.columns(2)
            if dk1.button("⚖️ Scale"):
                r = kube(f"scale deployment {sel_dep} --replicas={replicas}", ns="devops")
                show(r, f"Scaled {sel_dep} to {replicas} replicas")
            if dk2.button("🔄 Rollout Restart"):
                r = kube(f"rollout restart deployment/{sel_dep}", ns="devops")
                show(r, f"Rollout restart triggered for {sel_dep}")

    with tab3:
        @st.cache_data(ttl=30)
        def get_services():
            r = kube("get svc --no-headers", ns="devops")
            return r

        r = get_services()
        if r["ok"] and r["out"]:
            import pandas as pd
            rows = []
            for line in r["out"].splitlines():
                parts = line.split()
                if len(parts) >= 5:
                    rows.append({
                        "Name":       parts[0],
                        "Type":       parts[1],
                        "ClusterIP":  parts[2],
                        "ExternalIP": parts[3],
                        "Ports":      parts[4],
                        "Age":        parts[5] if len(parts) > 5 else "",
                    })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No services found")

        st.divider()
        st.markdown("##### Persistent Volume Claims")
        r_pvc = kube("get pvc --no-headers", ns="devops")
        if r_pvc["ok"] and r_pvc["out"]:
            import pandas as pd
            rows_pvc = []
            for line in r_pvc["out"].splitlines():
                parts = line.split()
                if len(parts) >= 5:
                    rows_pvc.append({"Name": parts[0], "Status": parts[1], "Volume": parts[2], "Capacity": parts[3], "Access": parts[4]})
            st.dataframe(pd.DataFrame(rows_pvc), use_container_width=True, hide_index=True)
        else:
            st.info("No PVCs found")

    with tab4:
        @st.cache_data(ttl=30)
        def get_events():
            r = kube("get events --sort-by=.lastTimestamp --no-headers", ns="devops")
            return r

        r = get_events()
        if r["ok"] and r["out"]:
            lines = r["out"].splitlines()[-30:]
            import pandas as pd
            rows = []
            for line in lines:
                parts = line.split(None, 5)
                if len(parts) >= 5:
                    rows.append({
                        "Last Seen": parts[0],
                        "Type":      parts[1],
                        "Reason":    parts[2],
                        "Object":    parts[3],
                        "Message":   parts[4] if len(parts) > 4 else "",
                    })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No events found")

    with tab5:
        pod_out2 = kube("get pods -o jsonpath='{.items[*].metadata.name}'", ns="devops")
        pod_names2 = pod_out2["out"].strip("'").split() if pod_out2["ok"] and pod_out2["out"] else []
        if pod_names2:
            sel_pod_log = st.selectbox("Pod", pod_names2, key="log_pod")
            tail_lines = st.slider("Lines", 50, 500, 100)
            if st.button("📜 Fetch Logs"):
                with st.spinner("Fetching logs..."):
                    r = kube(f"logs {sel_pod_log} --tail={tail_lines}", ns="devops")
                st.code(r["out"] or r["err"], language="bash")
        else:
            st.info("No pods found")

    with tab6:
        import pandas as pd
        st.markdown("##### Apply YAML Manifest")
        yaml_content = st.text_area("Paste YAML manifest", height=200, key="apply_yaml",
                                     placeholder="apiVersion: apps/v1\nkind: Deployment\n...")
        apply_ns = st.text_input("Namespace", value="devops", key="apply_ns")
        if st.button("✅ Apply Manifest") and yaml_content:
            import tempfile, os
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
                tmp.write(yaml_content)
                tmp_path = tmp.name
            try:
                r = kube(f"apply -f {tmp_path}", ns=apply_ns)
                show(r, "Manifest applied successfully")
                if r["out"]: st.code(r["out"], language="bash")
            finally:
                os.unlink(tmp_path)

        st.divider()
        st.markdown("##### ConfigMaps")
        cm_ns = st.text_input("Namespace", value="devops", key="cm_ns")
        if st.button("📋 List ConfigMaps"):
            r = kube("get configmaps --no-headers", ns=cm_ns)
            if r["ok"] and r["out"]:
                rows = []
                for line in r["out"].splitlines():
                    parts = line.split()
                    if len(parts) >= 2:
                        rows.append({"Name": parts[0], "Data Keys": parts[1], "Age": parts[2] if len(parts) > 2 else ""})
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.info("No configmaps found")

        st.divider()
        st.markdown("##### Secrets")
        sec_ns = st.text_input("Namespace", value="devops", key="sec_ns")
        if st.button("🔐 List Secrets"):
            r = kube("get secrets --no-headers", ns=sec_ns)
            if r["ok"] and r["out"]:
                rows = []
                for line in r["out"].splitlines():
                    parts = line.split()
                    if len(parts) >= 2:
                        rows.append({"Name": parts[0], "Type": parts[1], "Data": parts[2] if len(parts) > 2 else "", "Age": parts[3] if len(parts) > 3 else ""})
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.info("No secrets found")

        st.divider()
        st.markdown("##### Namespaces")
        if st.button("🗂️ List All Namespaces"):
            r = kube("get namespaces --no-headers")
            if r["ok"] and r["out"]:
                rows = []
                for line in r["out"].splitlines():
                    parts = line.split()
                    if len(parts) >= 2:
                        rows.append({"Namespace": parts[0], "Status": parts[1], "Age": parts[2] if len(parts) > 2 else ""})
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        new_ns = st.text_input("New namespace name", key="new_ns", placeholder="my-namespace")
        if st.button("➕ Create Namespace") and new_ns:
            r = kube(f"create namespace {new_ns}")
            show(r, f"Namespace '{new_ns}' created")

        st.divider()
        st.markdown("##### Node Info")
        if st.button("🖥️ Show Nodes"):
            r = kube("get nodes -o wide --no-headers")
            if r["ok"] and r["out"]:
                rows = []
                for line in r["out"].splitlines():
                    parts = line.split()
                    if len(parts) >= 5:
                        rows.append({
                            "Name":    parts[0], "Status": parts[1], "Roles": parts[2],
                            "Age":     parts[3], "Version": parts[4],
                            "OS":      parts[7] if len(parts) > 7 else "",
                            "Runtime": parts[8] if len(parts) > 8 else "",
                        })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — JENKINS
# ══════════════════════════════════════════════════════════════════════════════
elif active_page == "⚙️ Jenkins":
    page_header("⚙️", "Jenkins CI/CD", f"Pipeline automation · {JENKINS_URL}")

    if not port_up(30080):
        st.info("Jenkins unreachable — check if the pod is running: `kubectl get pods -n devops`")
        st.stop()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Jobs", "🔨 Build History", "🚀 Trigger Build", "➕ Create Job", "🗑️ Delete Job"
    ])

    # ── shared job list (cached) ──────────────────────────────────────────────
    @st.cache_data(ttl=30)
    def get_jenkins_jobs():
        return http_json(
            f"{JENKINS_URL}/api/json?tree=jobs[name,color,lastBuild[number,result,timestamp,duration,url]]",
            auth=JENKINS_AUTH
        )

    @st.cache_data(ttl=30)
    def get_job_names():
        d = http_json(f"{JENKINS_URL}/api/json?tree=jobs[name]", auth=JENKINS_AUTH)
        return [j["name"] for j in (d.get("jobs") or [])] if d else []

    # ── TAB 1: Jobs ───────────────────────────────────────────────────────────
    with tab1:
        import pandas as pd
        data = get_jenkins_jobs()
        if data and data.get("jobs"):
            rows = []
            for job in data["jobs"]:
                lb     = job.get("lastBuild") or {}
                result = lb.get("result") or ("BUILDING" if lb else "—")
                color  = job.get("color", "")
                rows.append({
                    "Job Name": job.get("name", ""),
                    "Status":   result,
                    "Build #":  lb.get("number", ""),
                    "Duration": f"{int(lb.get('duration',0)/1000)}s" if lb.get("duration") else "—",
                    "Health":   "🟢" if color == "blue" else ("🔴" if color == "red" else "⚪"),
                })

            df = pd.DataFrame(rows)

            def _row_color(row):
                s = row.get("Status","")
                if s == "SUCCESS": return ["background-color:#0a2a0a"]*len(row)
                if s == "FAILURE": return ["background-color:#2a0a0a"]*len(row)
                if s == "BUILDING":return ["background-color:#1a1a00"]*len(row)
                return [""]*len(row)

            st.dataframe(df.style.apply(_row_color, axis=1),
                         use_container_width=True, hide_index=True)

            jm1, jm2, jm3, jm4 = st.columns(4)
            jm1.metric("Total Jobs", len(rows))
            jm2.metric("✅ SUCCESS", sum(1 for r in rows if r["Status"]=="SUCCESS"))
            jm3.metric("❌ FAILURE", sum(1 for r in rows if r["Status"]=="FAILURE"))
            jm4.metric("🔄 Building", sum(1 for r in rows if r["Status"]=="BUILDING"))

            st.divider()
            st.markdown("##### Job Console Output")
            sel_console = st.selectbox("Select job for last console log", [r["Job Name"] for r in rows], key="console_sel")
            if st.button("📄 View Console", key="view_console"):
                import httpx
                try:
                    r = httpx.get(f"{JENKINS_URL}/job/{sel_console}/lastBuild/consoleText",
                                  auth=JENKINS_AUTH, timeout=10, follow_redirects=True)
                    st.code(r.text[-4000:] if len(r.text) > 4000 else r.text, language="bash")
                except Exception as e:
                    st.error(f"Could not fetch console: {e}")
        else:
            st.info("No jobs found or Jenkins unreachable")

    # ── TAB 2: Build History ──────────────────────────────────────────────────
    with tab2:
        import pandas as pd, datetime as _dt

        @st.cache_data(ttl=30)
        def get_all_builds():
            jobs_data = http_json(
                f"{JENKINS_URL}/api/json?tree=jobs[name,builds[number,result,timestamp,duration]]",
                auth=JENKINS_AUTH
            )
            builds = []
            if jobs_data:
                for job in (jobs_data.get("jobs") or []):
                    for b in (job.get("builds") or [])[:5]:
                        ts = b.get("timestamp", 0) / 1000
                        builds.append({
                            "Job":      job.get("name", ""),
                            "Build #":  b.get("number", ""),
                            "Result":   b.get("result") or "BUILDING",
                            "Duration": f"{int(b.get('duration',0)/1000)}s",
                            "Started":  _dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "",
                        })
            return sorted(builds, key=lambda x: x.get("Started",""), reverse=True)[:50]

        builds = get_all_builds()
        if builds:
            bdf = pd.DataFrame(builds)

            # Filter controls
            fc1, fc2 = st.columns([2, 1])
            with fc1:
                filter_job = st.selectbox("Filter by job", ["All"] + list(bdf["Job"].unique()), key="bh_job")
            with fc2:
                filter_res = st.selectbox("Filter by result", ["All", "SUCCESS", "FAILURE", "BUILDING"], key="bh_res")

            if filter_job != "All":
                bdf = bdf[bdf["Job"] == filter_job]
            if filter_res != "All":
                bdf = bdf[bdf["Result"] == filter_res]

            def _build_color(row):
                s = row.get("Result","")
                if s == "SUCCESS": return ["background-color:#0a2a0a"]*len(row)
                if s == "FAILURE": return ["background-color:#2a0a0a"]*len(row)
                if s == "BUILDING":return ["background-color:#1a1a00"]*len(row)
                return [""]*len(row)

            st.dataframe(bdf.style.apply(_build_color, axis=1),
                         use_container_width=True, hide_index=True)

            b1, b2, b3 = st.columns(3)
            b1.metric("Total Shown", len(bdf))
            b2.metric("✅ Success",  int((bdf["Result"]=="SUCCESS").sum()))
            b3.metric("❌ Failure",  int((bdf["Result"]=="FAILURE").sum()))
        else:
            st.info("No build history found")

    # ── TAB 3: Trigger Build ──────────────────────────────────────────────────
    with tab3:
        job_names = get_job_names()
        if job_names:
            tc1, tc2 = st.columns([2, 1])
            with tc1:
                sel_job = st.selectbox("Select job to trigger", job_names, key="trig_sel")
            with tc2:
                st.markdown("<div style='height:1.9rem'></div>", unsafe_allow_html=True)
                open_job = st.link_button("🔗 Open in Jenkins", f"{JENKINS_URL}/job/{sel_job}" if sel_job else JENKINS_URL)

            params_input = st.text_area("Build parameters (KEY=VALUE per line, optional)",
                                        placeholder="BRANCH=main\nENV=staging", key="trig_params")

            t_col1, t_col2 = st.columns([1, 3])
            with t_col1:
                if st.button("🚀 Trigger Build", type="primary", use_container_width=True):
                    with st.spinner(f"Triggering {sel_job}..."):
                        crumb = jenkins_crumb()
                        params = {}
                        if params_input.strip():
                            for line in params_input.strip().splitlines():
                                if "=" in line:
                                    k, v = line.split("=", 1)
                                    params[k.strip()] = v.strip()
                        url = f"{JENKINS_URL}/job/{sel_job}/buildWithParameters" if params else f"{JENKINS_URL}/job/{sel_job}/build"
                        code, resp = http_post(url, auth=JENKINS_AUTH, data=params or {}, headers=crumb)
                    if code in (200, 201):
                        st.success(f"✅ Build triggered for **{sel_job}** — check Build History tab")
                        st.cache_data.clear()
                    else:
                        st.error(f"❌ Failed (HTTP {code}): {resp}")
        else:
            st.info("No jobs available")

    # ── TAB 4: Create Job ─────────────────────────────────────────────────────
    with tab4:
        st.markdown("##### ➕ Create a New Jenkins Job")

        cr1, cr2 = st.columns(2)
        with cr1:
            new_job_name = st.text_input("Job Name", placeholder="my-new-pipeline", key="new_job_name")
            job_type     = st.radio("Job Type", ["Freestyle", "Pipeline"], horizontal=True, key="new_job_type")
            description  = st.text_input("Description (optional)", key="new_job_desc")

        with cr2:
            if job_type == "Freestyle":
                shell_cmd = st.text_area("Shell command to run",
                                         placeholder="echo 'Hello from Jenkins'\nls -la",
                                         height=120, key="new_job_shell")
                git_url   = st.text_input("Git repo URL (optional)", key="new_job_git")
            else:
                pipeline_script = st.text_area(
                    "Pipeline script (Groovy)",
                    value="""pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                echo 'Building...'
            }
        }
        stage('Test') {
            steps {
                echo 'Testing...'
            }
        }
        stage('Deploy') {
            steps {
                echo 'Deploying...'
            }
        }
    }
}""",
                    height=240, key="new_job_pipeline")

        st.markdown("")
        if st.button("✅ Create Job", type="primary", key="create_job_btn"):
            if not new_job_name.strip():
                st.error("Job name is required")
            else:
                import xml.sax.saxutils as saxutils
                safe_desc = saxutils.escape(description)
                safe_name = new_job_name.strip()

                if job_type == "Freestyle":
                    scm_block = ""
                    if git_url.strip():
                        safe_git = saxutils.escape(git_url.strip())
                        scm_block = f"""<scm class="hudson.plugins.git.GitSCM" plugin="git">
  <configVersion>2</configVersion>
  <userRemoteConfigs>
    <hudson.plugins.git.UserRemoteConfig>
      <url>{safe_git}</url>
    </hudson.plugins.git.UserRemoteConfig>
  </userRemoteConfigs>
  <branches><hudson.plugins.git.BranchSpec><name>*/main</name></hudson.plugins.git.BranchSpec></branches>
  <doGenerateSubmoduleConfigurations>false</doGenerateSubmoduleConfigurations>
  <submoduleCfg class="empty-list"/>
  <extensions/>
</scm>"""
                    else:
                        scm_block = '<scm class="hudson.scm.NullSCM"/>'

                    builder_block = ""
                    if shell_cmd.strip():
                        safe_cmd = saxutils.escape(shell_cmd.strip())
                        builder_block = f"""<builders>
  <hudson.tasks.Shell>
    <command>{safe_cmd}</command>
  </hudson.tasks.Shell>
</builders>"""
                    else:
                        builder_block = "<builders/>"

                    xml_config = f"""<?xml version='1.1' encoding='UTF-8'?>
<project>
  <description>{safe_desc}</description>
  <keepDependencies>false</keepDependencies>
  <properties/>
  {scm_block}
  <canRoam>true</canRoam>
  <disabled>false</disabled>
  <blockBuildWhenDownstreamBuilding>false</blockBuildWhenDownstreamBuilding>
  <blockBuildWhenUpstreamBuilding>false</blockBuildWhenUpstreamBuilding>
  <triggers/>
  <concurrentBuild>false</concurrentBuild>
  {builder_block}
  <publishers/>
  <buildWrappers/>
</project>"""
                else:
                    safe_script = saxutils.escape(pipeline_script)
                    xml_config = f"""<?xml version='1.1' encoding='UTF-8'?>
<flow-definition plugin="workflow-job">
  <description>{safe_desc}</description>
  <keepDependencies>false</keepDependencies>
  <properties/>
  <definition class="org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition" plugin="workflow-cps">
    <script>{safe_script}</script>
    <sandbox>true</sandbox>
  </definition>
  <triggers/>
  <disabled>false</disabled>
</flow-definition>"""

                with st.spinner(f"Creating job '{safe_name}'..."):
                    import httpx
                    crumb = jenkins_crumb()
                    headers = {"Content-Type": "application/xml"}
                    headers.update(crumb)
                    try:
                        r = httpx.post(
                            f"{JENKINS_URL}/createItem?name={safe_name}",
                            auth=JENKINS_AUTH,
                            content=xml_config.encode("utf-8"),
                            headers=headers,
                            timeout=15,
                            follow_redirects=True,
                        )
                        if r.status_code in (200, 201):
                            st.success(f"✅ Job **{safe_name}** created successfully!")
                            st.link_button("Open Job", f"{JENKINS_URL}/job/{safe_name}")
                            st.cache_data.clear()
                        elif r.status_code == 400:
                            st.error(f"❌ Job already exists or invalid name: {r.text[:200]}")
                        else:
                            st.error(f"❌ Failed (HTTP {r.status_code}): {r.text[:300]}")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

    # ── TAB 5: Delete Job ─────────────────────────────────────────────────────
    with tab5:
        st.markdown("##### 🗑️ Delete a Jenkins Job")
        st.warning("⚠️ Deletion is permanent and cannot be undone.", icon="⚠️")

        job_names_del = get_job_names()
        if job_names_del:
            del1, del2 = st.columns([2, 1])
            with del1:
                del_job = st.selectbox("Select job to delete", job_names_del, key="del_job_sel")
            with del2:
                st.markdown("<div style='height:1.9rem'></div>", unsafe_allow_html=True)
                st.link_button("🔗 View Job", f"{JENKINS_URL}/job/{del_job}")

            # Show last build info before deletion
            if del_job:
                job_info = http_json(
                    f"{JENKINS_URL}/job/{del_job}/api/json?tree=name,description,lastBuild[number,result,timestamp]",
                    auth=JENKINS_AUTH
                )
                if job_info:
                    lb = job_info.get("lastBuild") or {}
                    di1, di2, di3 = st.columns(3)
                    di1.metric("Job", job_info.get("name",""))
                    di2.metric("Last Build #", lb.get("number","—"))
                    di3.metric("Last Result", lb.get("result") or "—")
                    if job_info.get("description"):
                        st.caption(f"Description: {job_info['description']}")

            confirm_name = st.text_input(
                f'Type **{del_job}** to confirm deletion',
                placeholder=del_job, key="del_confirm"
            )
            st.markdown("")

            if st.button("🗑️ Delete Job", type="primary", key="del_job_btn"):
                if confirm_name.strip() != del_job:
                    st.error(f"❌ Name mismatch — type the exact job name to confirm")
                else:
                    with st.spinner(f"Deleting '{del_job}'..."):
                        import httpx
                        crumb = jenkins_crumb()
                        try:
                            r = httpx.post(
                                f"{JENKINS_URL}/job/{del_job}/doDelete",
                                auth=JENKINS_AUTH,
                                headers=crumb,
                                timeout=15,
                                follow_redirects=True,
                            )
                            if r.status_code in (200, 201, 302):
                                st.success(f"✅ Job **{del_job}** deleted successfully")
                                st.cache_data.clear()
                            else:
                                st.error(f"❌ Failed (HTTP {r.status_code}): {r.text[:200]}")
                        except Exception as e:
                            st.error(f"❌ Error: {e}")
        else:
            st.info("No jobs available")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — SONARQUBE
# ══════════════════════════════════════════════════════════════════════════════
elif active_page == "🔍 SonarQube":
    page_header("🔍", "SonarQube", f"Code quality & security analysis · {SONAR_URL}")

    if not port_up(30900):
        st.info("SonarQube unreachable — check if the pod is running: `kubectl get pods -n devops`")
        st.stop()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Projects", "🐛 Issues", "⚙️ System", "🗂️ Manage", "▶ Scanner"])

    with tab1:
        @st.cache_data(ttl=60)
        def get_sonar_projects():
            return http_json(f"{SONAR_URL}/api/projects/search", auth=SONAR_AUTH)

        data = get_sonar_projects()
        if data and data.get("components"):
            import pandas as pd
            projs = data["components"]
            rows = []
            for p in projs:
                qg = http_json(f"{SONAR_URL}/api/qualitygates/project_status?projectKey={p['key']}", auth=SONAR_AUTH)
                qg_status = (qg or {}).get("projectStatus", {}).get("status", "—")
                rows.append({
                    "Project":      p.get("name", ""),
                    "Key":          p.get("key", ""),
                    "Visibility":   p.get("visibility", ""),
                    "Quality Gate": qg_status,
                    "Last Analysis": p.get("lastAnalysisDate", "")[:10] if p.get("lastAnalysisDate") else "—",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            total = data.get("paging", {}).get("total", len(projs))
            st.metric("Total Projects", total)

            st.divider()
            st.markdown("##### Project Metrics")
            project_keys = [p["key"] for p in projs]
            sel_proj = st.selectbox("Select project", project_keys)
            if sel_proj:
                metrics_data = http_json(
                    f"{SONAR_URL}/api/measures/component?component={sel_proj}"
                    f"&metricKeys=bugs,vulnerabilities,code_smells,coverage,duplicated_lines_density,ncloc",
                    auth=SONAR_AUTH
                )
                if metrics_data:
                    measures = {m["metric"]: m.get("value", "—")
                                for m in metrics_data.get("component", {}).get("measures", [])}
                    m1, m2, m3, m4, m5, m6 = st.columns(6)
                    m1.metric("Bugs",         measures.get("bugs", "—"))
                    m2.metric("Vulnerabilities", measures.get("vulnerabilities", "—"))
                    m3.metric("Code Smells",  measures.get("code_smells", "—"))
                    m4.metric("Coverage",     measures.get("coverage", "—") + "%" if measures.get("coverage") else "—")
                    m5.metric("Duplication",  measures.get("duplicated_lines_density", "—") + "%" if measures.get("duplicated_lines_density") else "—")
                    m6.metric("Lines",        measures.get("ncloc", "—"))
        else:
            st.info("No projects found — run a scan first")

    with tab2:
        @st.cache_data(ttl=60)
        def get_sonar_issues():
            return http_json(f"{SONAR_URL}/api/issues/search?ps=50", auth=SONAR_AUTH)

        data = get_sonar_issues()
        if data and data.get("issues"):
            import pandas as pd
            rows = []
            for issue in data["issues"][:50]:
                rows.append({
                    "Project":   issue.get("project", ""),
                    "Type":      issue.get("type", ""),
                    "Severity":  issue.get("severity", ""),
                    "Message":   issue.get("message", "")[:80],
                    "Status":    issue.get("status", ""),
                    "Component": issue.get("component", "").split(":")[-1],
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.caption(f"Showing {len(rows)} of {data.get('paging', {}).get('total', '?')} total issues")
        else:
            st.info("No issues found")

    with tab3:
        health_data = http_json(f"{SONAR_URL}/api/system/health", auth=SONAR_AUTH)
        info_data   = http_json(f"{SONAR_URL}/api/system/info", auth=SONAR_AUTH)

        if health_data:
            st.markdown(f"**System Health:** {status_badge(health_data.get('health') == 'GREEN', 'HEALTHY', 'DEGRADED')}", unsafe_allow_html=True)
        if info_data:
            st.markdown(f"**Version:** `{info_data.get('System', {}).get('Version', '?')}`")
            st.markdown(f"**Edition:** `{info_data.get('System', {}).get('Edition', '?')}`")

        # Quality Gates
        st.divider()
        st.markdown("##### Quality Gates")
        qg_data = http_json(f"{SONAR_URL}/api/qualitygates/list", auth=SONAR_AUTH)
        if qg_data and qg_data.get("qualitygates"):
            import pandas as pd
            qg_rows = []
            for qg in qg_data["qualitygates"]:
                qg_rows.append({
                    "Name":    qg.get("name", ""),
                    "ID":      qg.get("id", ""),
                    "Default": "✅" if qg.get("isDefault") else "",
                    "Built-in": "✅" if qg.get("isBuiltIn") else "",
                })
            st.dataframe(pd.DataFrame(qg_rows), use_container_width=True, hide_index=True)

    # extra tab for project management
    with tab4:
        import pandas as pd
        st.markdown("##### Create New Project")
        with st.form("sonar_create_project"):
            new_proj_key  = st.text_input("Project Key", placeholder="my-project")
            new_proj_name = st.text_input("Display Name", placeholder="My Project")
            new_proj_vis  = st.selectbox("Visibility", ["public", "private"])
            if st.form_submit_button("➕ Create Project"):
                import httpx
                r = httpx.post(
                    f"{SONAR_URL}/api/projects/create",
                    auth=SONAR_AUTH,
                    params={"name": new_proj_name, "project": new_proj_key, "visibility": new_proj_vis},
                    timeout=10,
                )
                if r.status_code == 200:
                    st.success(f"Project '{new_proj_name}' created")
                    st.cache_data.clear()
                else:
                    st.error(f"Failed (HTTP {r.status_code}): {r.text[:200]}")

        st.divider()
        st.markdown("##### Delete Project")
        proj_list_del = http_json(f"{SONAR_URL}/api/projects/search", auth=SONAR_AUTH)
        if proj_list_del and proj_list_del.get("components"):
            del_proj_keys = [p["key"] for p in proj_list_del["components"]]
            del_proj_key = st.selectbox("Project to delete", del_proj_keys, key="del_sonar_proj")
            del_proj_confirm = st.text_input("Type project key to confirm", key="del_sonar_confirm")
            if st.button("🗑 Delete Project", type="secondary"):
                if del_proj_confirm.strip() == del_proj_key:
                    import httpx
                    r = httpx.post(
                        f"{SONAR_URL}/api/projects/delete",
                        auth=SONAR_AUTH,
                        params={"project": del_proj_key},
                        timeout=10,
                    )
                    if r.status_code == 204:
                        st.success(f"Project '{del_proj_key}' deleted")
                        st.cache_data.clear()
                    else:
                        st.error(f"Failed (HTTP {r.status_code}): {r.text[:200]}")
                else:
                    st.error("Project key doesn't match")

        st.divider()
        st.markdown("##### Generate User Token")
        token_name = st.text_input("Token name", placeholder="my-scan-token")
        if st.button("🔑 Generate Token") and token_name:
            import httpx
            r = httpx.post(
                f"{SONAR_URL}/api/user_tokens/generate",
                auth=SONAR_AUTH,
                params={"name": token_name},
                timeout=10,
            )
            if r.status_code == 200:
                tok = r.json()
                st.success(f"Token generated: `{tok.get('token', '?')}`")
                st.caption("Save this token — it won't be shown again")
            else:
                st.error(f"Failed (HTTP {r.status_code}): {r.text[:200]}")

    with tab5:
        st.markdown("##### Run SonarScanner")
        if shutil.which("sonar-scanner"):
            sc1, sc2 = st.columns(2)
            scan_proj_key  = sc1.text_input("Project Key", placeholder="my-project")
            scan_src_dir   = sc2.text_input("Source directory", value=".", placeholder="/path/to/src")
            scan_extra     = st.text_area("Extra sonar properties (KEY=VALUE per line)", placeholder="sonar.java.binaries=target/classes")
            if st.button("▶ Run Scanner", type="primary") and scan_proj_key:
                extra_props = ""
                for line in scan_extra.strip().splitlines():
                    if "=" in line:
                        extra_props += f" -D{line.strip()}"
                cmd = (f"sonar-scanner -Dsonar.projectKey={scan_proj_key}"
                       f" -Dsonar.sources={scan_src_dir}"
                       f" -Dsonar.host.url={SONAR_URL}"
                       f" -Dsonar.login={SONAR_AUTH[0]}"
                       f" -Dsonar.password={SONAR_AUTH[1]}"
                       f"{extra_props}")
                with st.spinner("Running sonar-scanner..."):
                    r = shell(cmd)
                if r["ok"]:
                    st.success("Scanner completed successfully")
                    st.code(r["out"][-3000:], language="bash")
                else:
                    st.error("Scanner failed")
                    st.code(r["err"][-2000:] or r["out"][-2000:], language="bash")
        else:
            st.info("`sonar-scanner` not installed")
            st.code("brew install sonar-scanner", language="bash")
            st.markdown("##### Manual Scan via Docker")
            st.code(f"""docker run --rm -v "$(pwd):/usr/src" sonarsource/sonar-scanner-cli \\
  -Dsonar.projectKey=my-project \\
  -Dsonar.sources=/usr/src \\
  -Dsonar.host.url={SONAR_URL} \\
  -Dsonar.login=admin \\
  -Dsonar.password=Admin@123456789@""", language="bash")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — TERRAFORM
# ══════════════════════════════════════════════════════════════════════════════
elif active_page == "🌍 Terraform":
    page_header("🌍", "Terraform Manager", f"Infrastructure as Code · {TF_WORKDIR}")

    if not shutil.which("terraform"):
        st.warning("Terraform not installed — run `brew install terraform`")
        st.stop()

    import pandas as pd

    # version + workspace strip
    ver_r = tf("terraform version -json")
    ws_r  = tf("terraform workspace show")
    tf_ver_str = "?"
    if ver_r["ok"]:
        try: tf_ver_str = json.loads(ver_r["out"]).get("terraform_version","?")
        except: pass
    cur_ws = ws_r["out"].strip() if ws_r["ok"] else "default"

    tv1, tv2, tv3 = st.columns(3)
    tv1.metric("Version",   tf_ver_str)
    tv2.metric("Workspace", cur_ws)
    tv3.metric("Directory", TF_WORKDIR.split("/")[-1])

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 State", "🔨 Operations", "📤 Outputs", "🗂️ Workspaces", "🔬 Plan Preview"
    ])

    with tab1:
        c_ref, c_clr, _ = st.columns([1,1,4])
        if c_ref.button("🔄 Refresh State"):
            st.cache_data.clear()
        if c_clr.button("🔃 tf refresh"):
            with st.spinner("Refreshing state..."): r = tf("terraform refresh -auto-approve")
            show(r, "State refreshed")

        state_r = tf("terraform state list")
        if state_r["ok"] and state_r["out"]:
            lines = [l.strip() for l in state_r["out"].splitlines() if l.strip()]
            st.metric("Resources in state", len(lines))
            st.dataframe(pd.DataFrame({"Resource": lines}), use_container_width=True, hide_index=True)

            st.divider()
            st.markdown("##### Show resource details")
            sel_res = st.selectbox("Resource", lines, key="tf_res_sel")
            if st.button("🔍 Show Resource"):
                r = tf(f"terraform state show '{sel_res}'")
                st.code(r["out"] or r["err"], language="hcl")
        else:
            st.info("No state — run **Init** first (Operations tab)")

    with tab2:
        st.markdown("##### Core Operations")
        op1, op2, op3, op4 = st.columns(4)
        if op1.button("⚙️ Init", use_container_width=True):
            with st.spinner("Initialising..."): r = tf("terraform init -input=false")
            show(r, "✅ Initialised")
            if r["ok"]: st.code(r["out"][-2000:], language="bash")
        if op2.button("✅ Validate", use_container_width=True):
            with st.spinner("Validating..."): r = tf("terraform validate")
            show(r, "✅ Config is valid")
        if op3.button("🚀 Apply", use_container_width=True):
            with st.spinner("Applying..."): r = tf("terraform apply -auto-approve -input=false")
            show(r)
            if r["ok"]: st.code(r["out"][-2000:], language="bash")
        if op4.button("🔄 Format", use_container_width=True):
            with st.spinner("Formatting..."): r = tf("terraform fmt -recursive")
            show(r, "✅ Files formatted")

        st.divider()
        st.markdown("##### Targeted Apply")
        target_res = st.text_input("Resource target", placeholder="module.vpc.aws_vpc.main", key="tf_target")
        tc1, tc2 = st.columns(2)
        if tc1.button("📋 Plan Target") and target_res:
            with st.spinner("Planning target..."): r = tf(f"terraform plan -target='{target_res}'")
            st.code(r["out"] or r["err"], language="bash")
        if tc2.button("🚀 Apply Target") and target_res:
            with st.spinner("Applying target..."): r = tf(f"terraform apply -target='{target_res}' -auto-approve")
            show(r)

        st.divider()
        st.markdown("##### Destroy")
        st.error("⚠️ Destroys ALL managed resources — cannot be undone!")
        dest_confirm = st.text_input("Type **destroy** to confirm", key="tf_dest_confirm")
        if st.button("💥 Destroy", type="secondary"):
            if dest_confirm.strip().lower() == "destroy":
                with st.spinner("Destroying..."): r = tf("terraform destroy -auto-approve -input=false")
                show(r)
            else:
                st.error("Type 'destroy' to confirm")

    with tab3:
        if st.button("📤 Fetch Outputs", type="primary"):
            with st.spinner("Fetching..."): r = tf("terraform output -json")
            if r["ok"] and r["out"]:
                try:
                    out_data = json.loads(r["out"])
                    rows = [{"Output": k, "Value": str(v.get("value","")), "Type": v.get("type","")}
                            for k, v in out_data.items()]
                    if rows:
                        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                    st.json(out_data)
                except Exception: st.code(r["out"])
            else:
                st.info("No outputs defined or state is empty")

    with tab4:
        st.markdown("##### Workspace Management")
        ws_list_r = tf("terraform workspace list")
        if ws_list_r["ok"]:
            workspaces = [w.strip().lstrip("* ") for w in ws_list_r["out"].splitlines() if w.strip()]
            st.dataframe(pd.DataFrame({"Workspace": workspaces,
                                       "Active": ["✅" if w==cur_ws else "" for w in workspaces]}),
                         use_container_width=True, hide_index=True)

        w1, w2 = st.columns(2)
        with w1:
            sel_ws = st.selectbox("Switch workspace", workspaces if ws_list_r["ok"] else ["default"])
            if st.button("🔄 Switch"):
                r = tf(f"terraform workspace select {sel_ws}")
                show(r, f"Switched to workspace '{sel_ws}'")
                st.rerun()
        with w2:
            new_ws = st.text_input("New workspace name", key="new_ws")
            if st.button("➕ Create"):
                r = tf(f"terraform workspace new {new_ws}")
                show(r, f"Workspace '{new_ws}' created")
                st.rerun()

    with tab5:
        st.markdown("##### Terraform Plan Preview")
        extra_vars = st.text_area("Extra vars (KEY=VALUE per line)", key="tf_plan_vars",
                                   placeholder="environment=staging\nregion=us-east-1")
        plan_target = st.text_input("Target (optional)", key="tf_plan_target2")
        if st.button("📋 Run Plan", type="primary"):
            cmd = "terraform plan -input=false"
            if extra_vars.strip():
                for line in extra_vars.strip().splitlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        cmd += f" -var '{k.strip()}={v.strip()}'"
            if plan_target.strip():
                cmd += f" -target='{plan_target.strip()}'"
            with st.spinner("Running plan..."): r = tf(cmd)
            out = r["out"] or r["err"]
            if "Plan:" in out or "No changes" in out:
                # parse summary
                for line in out.splitlines():
                    if "Plan:" in line or "No changes" in line:
                        st.info(line.strip())
                        break
            st.code(out[-4000:] if len(out)>4000 else out, language="bash")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 7 — PROMETHEUS & GRAFANA
# ══════════════════════════════════════════════════════════════════════════════
elif active_page == "📊 Prometheus & Grafana":
    page_header("📊", "Prometheus & Grafana", f"Metrics, alerting and dashboards · Prom:{PROM_URL}  Grafana:{GRAFANA_URL}")

    prom_alive  = port_up(30090)
    graf_alive  = port_up(30030)
    pm1, pm2 = st.columns(2)
    pm1.markdown(f"**Prometheus:** {status_badge(prom_alive)}", unsafe_allow_html=True)
    pm2.markdown(f"**Grafana:** {status_badge(graf_alive)}", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎯 Targets", "🚨 Alerts", "🔍 Query", "📊 Grafana", "⚙️ Manage"])

    with tab1:
        if prom_alive:
            @st.cache_data(ttl=30)
            def get_prom_targets():
                return http_json(f"{PROM_URL}/api/v1/targets")

            data = get_prom_targets()
            if data and data.get("status") == "success":
                active = data["data"].get("activeTargets", [])
                import pandas as pd
                rows = []
                for t in active:
                    rows.append({
                        "Job":      t.get("labels", {}).get("job", ""),
                        "Instance": t.get("labels", {}).get("instance", ""),
                        "State":    t.get("health", ""),
                        "Last Scrape": t.get("lastScrape", "")[:19],
                        "Endpoint": t.get("scrapeUrl", ""),
                    })
                if rows:
                    df = pd.DataFrame(rows)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    up_count = sum(1 for r in rows if r["State"] == "up")
                    st.metric(f"Targets UP / Total", f"{up_count} / {len(rows)}")
                else:
                    st.info("No active targets")
            else:
                st.warning("Could not fetch targets from Prometheus")
        else:
            st.info("Prometheus unreachable on port 30090")

    with tab2:
        if prom_alive:
            @st.cache_data(ttl=30)
            def get_prom_alerts():
                return http_json(f"{PROM_URL}/api/v1/alerts")

            data = get_prom_alerts()
            if data and data.get("status") == "success":
                alerts = data["data"].get("alerts", [])
                if alerts:
                    import pandas as pd
                    rows = []
                    for a in alerts:
                        rows.append({
                            "Name":    a.get("labels", {}).get("alertname", ""),
                            "State":   a.get("state", ""),
                            "Severity": a.get("labels", {}).get("severity", ""),
                            "Summary": a.get("annotations", {}).get("summary", ""),
                        })
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                else:
                    st.success("No active alerts — all systems nominal")
            else:
                st.info("No alert data")
        else:
            st.info("Prometheus unreachable")

    with tab3:
        query = st.text_input("PromQL Query", value="up", placeholder="e.g. rate(http_requests_total[5m])")
        if st.button("▶ Execute Query") and prom_alive:
            with st.spinner("Querying Prometheus..."):
                data = http_json(f"{PROM_URL}/api/v1/query", params={"query": query})
            if data and data.get("status") == "success":
                results = data["data"].get("result", [])
                if results:
                    import pandas as pd
                    rows = []
                    for r in results:
                        row = {k: v for k, v in r.get("metric", {}).items()}
                        row["value"] = r.get("value", [None, None])[1]
                        rows.append(row)
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                else:
                    st.info("Query returned no results")
            else:
                st.error("Query failed or Prometheus unreachable")

    with tab4:
        if graf_alive:
            @st.cache_data(ttl=60)
            def get_grafana_dashboards():
                return http_json(f"{GRAFANA_URL}/api/search?type=dash-db", auth=GRAFANA_AUTH)

            @st.cache_data(ttl=60)
            def get_grafana_datasources():
                return http_json(f"{GRAFANA_URL}/api/datasources", auth=GRAFANA_AUTH)

            gds = get_grafana_datasources()
            gdbs = get_grafana_dashboards()

            gm1, gm2 = st.columns(2)
            gm1.metric("Datasources", len(gds) if gds else 0)
            gm2.metric("Dashboards", len(gdbs) if gdbs else 0)

            if gds:
                st.markdown("##### Datasources")
                import pandas as pd
                st.dataframe(pd.DataFrame([{
                    "Name":     d.get("name", ""),
                    "Type":     d.get("type", ""),
                    "URL":      d.get("url", ""),
                    "Default":  d.get("isDefault", False),
                } for d in gds]), use_container_width=True, hide_index=True)

            if gdbs:
                st.markdown("##### Dashboards")
                st.dataframe(pd.DataFrame([{
                    "Title":   d.get("title", ""),
                    "Folder":  d.get("folderTitle", "General"),
                    "UID":     d.get("uid", ""),
                    "URL":     GRAFANA_URL + d.get("url", ""),
                } for d in gdbs]), use_container_width=True, hide_index=True)

            st.link_button("🌐 Open Grafana", GRAFANA_URL, use_container_width=True)
        else:
            st.info("Grafana unreachable on port 30030")

    with tab5:
        import pandas as pd
        st.markdown("##### Prometheus — Reload Config")
        if prom_alive:
            if st.button("🔄 Reload Prometheus Config"):
                import httpx
                try:
                    r = httpx.post(f"{PROM_URL}/-/reload", timeout=8)
                    if r.status_code == 200:
                        st.success("Prometheus config reloaded")
                    else:
                        st.error(f"Failed (HTTP {r.status_code})")
                except Exception as e:
                    st.error(str(e))

            st.divider()
            st.markdown("##### Prometheus — Series & Labels")
            metric_match = st.text_input("Match selector", placeholder="{job='jenkins'}", key="prom_match")
            if st.button("🔍 List Series") and metric_match:
                data = http_json(f"{PROM_URL}/api/v1/series", params={"match[]": metric_match})
                if data and data.get("status") == "success":
                    series = data["data"]
                    st.metric("Series found", len(series))
                    if series:
                        st.dataframe(pd.DataFrame(series[:50]), use_container_width=True, hide_index=True)
                else:
                    st.info("No series found")

            st.divider()
            st.markdown("##### Prometheus — Range Query")
            rq1, rq2, rq3 = st.columns(3)
            range_query = rq1.text_input("PromQL", value="up", key="range_query")
            range_mins  = rq2.slider("Minutes back", 5, 120, 30, key="range_mins")
            range_step  = rq3.text_input("Step", value="60s", key="range_step")
            if st.button("📈 Run Range Query"):
                import time as _time
                end_ts   = int(_time.time())
                start_ts = end_ts - range_mins * 60
                data = http_json(f"{PROM_URL}/api/v1/query_range",
                                 params={"query": range_query, "start": start_ts,
                                         "end": end_ts, "step": range_step})
                if data and data.get("status") == "success":
                    results = data["data"].get("result", [])
                    if results:
                        import plotly.graph_objects as go
                        fig = go.Figure()
                        for series in results[:10]:
                            label = str(series.get("metric", {}))[:40]
                            vals  = series.get("values", [])
                            xs    = [v[0] for v in vals]
                            ys    = [float(v[1]) for v in vals]
                            fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name=label))
                        fig.update_layout(
                            template="plotly_dark", height=350,
                            margin=dict(l=0,r=0,t=20,b=0),
                            xaxis_title="Time (Unix)", yaxis_title="Value"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No data returned")
                else:
                    st.error("Range query failed")

        st.divider()
        st.markdown("##### Grafana — Create Dashboard")
        if graf_alive:
            dash_title = st.text_input("Dashboard title", placeholder="My Dashboard", key="dash_title")
            dash_tags  = st.text_input("Tags (comma-separated)", placeholder="devops, k8s", key="dash_tags")
            if st.button("➕ Create Blank Dashboard") and dash_title:
                tags_list = [t.strip() for t in dash_tags.split(",") if t.strip()]
                dashboard_json = {
                    "dashboard": {
                        "id": None, "uid": None, "title": dash_title,
                        "tags": tags_list, "timezone": "browser",
                        "schemaVersion": 36, "version": 0,
                        "panels": [],
                    },
                    "overwrite": False, "folderId": 0,
                }
                import httpx
                r = httpx.post(f"{GRAFANA_URL}/api/dashboards/db",
                               json=dashboard_json, auth=GRAFANA_AUTH, timeout=10)
                if r.status_code == 200:
                    result = r.json()
                    st.success(f"Dashboard created: [{dash_title}]({GRAFANA_URL}{result.get('url','')})")
                else:
                    st.error(f"Failed (HTTP {r.status_code}): {r.text[:200]}")

            st.divider()
            st.markdown("##### Grafana — Manage Users")
            users_data = http_json(f"{GRAFANA_URL}/api/users", auth=GRAFANA_AUTH)
            if users_data:
                st.dataframe(pd.DataFrame([{
                    "Login":   u.get("login", ""),
                    "Name":    u.get("name", ""),
                    "Email":   u.get("email", ""),
                    "Role":    u.get("isGrafanaAdmin") and "Admin" or "Viewer",
                    "Last Active": u.get("lastSeenAt", "")[:10],
                } for u in users_data]), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 8 — ARGOCD
# ══════════════════════════════════════════════════════════════════════════════
elif active_page == "🔀 ArgoCD":
    page_header("🔀", "ArgoCD", f"GitOps continuous delivery · {ARGOCD_URL}")

    @st.cache_data(ttl=60)
    def argocd_token():
        import httpx
        try:
            r = httpx.post(f"{ARGOCD_URL}/api/v1/session",
                           json={"username": "admin", "password": "Admin@123456789@"},
                           timeout=6, verify=False)
            if r.status_code == 200:
                return r.json().get("token", "")
        except Exception:
            pass
        return None

    token = argocd_token()
    if not token:
        st.info("ArgoCD unreachable — check if the pod is running in argocd namespace")
        st.link_button("🌐 Open ArgoCD UI", ARGOCD_URL)
        st.stop()

    def argo_get(path):
        import httpx
        try:
            r = httpx.get(f"{ARGOCD_URL}{path}",
                          headers={"Authorization": f"Bearer {token}"},
                          timeout=10, verify=False)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    def argo_post(path, payload=None):
        import httpx
        try:
            r = httpx.post(f"{ARGOCD_URL}{path}",
                           json=payload or {},
                           headers={"Authorization": f"Bearer {token}"},
                           timeout=15, verify=False)
            return r.status_code, r.json() if r.text else {}
        except Exception as e:
            return 0, str(e)

    import pandas as pd

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📱 Applications", "📁 Repositories", "🔄 Sync & Rollback", "➕ Create App", "⚙️ Settings"
    ])

    with tab1:
        if st.button("🔄 Refresh", key="argo_ref"):
            st.cache_data.clear()
        apps_data = argo_get("/api/v1/applications")
        if apps_data and apps_data.get("items"):
            apps = apps_data["items"]
            rows = []
            for app in apps:
                status = app.get("status", {})
                rows.append({
                    "Name":        app.get("metadata", {}).get("name", ""),
                    "Project":     app.get("spec", {}).get("project", ""),
                    "Sync Status": status.get("sync", {}).get("status", ""),
                    "Health":      status.get("health", {}).get("status", ""),
                    "Repo":        app.get("spec", {}).get("source", {}).get("repoURL", ""),
                    "Path":        app.get("spec", {}).get("source", {}).get("path", ""),
                    "Namespace":   app.get("spec", {}).get("destination", {}).get("namespace", ""),
                    "Revision":    status.get("sync", {}).get("revision", "")[:8],
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            synced  = sum(1 for r in rows if r["Sync Status"] == "Synced")
            healthy = sum(1 for r in rows if r["Health"]      == "Healthy")
            oosync  = sum(1 for r in rows if r["Sync Status"] == "OutOfSync")
            am1, am2, am3, am4 = st.columns(4)
            am1.metric("Total Apps",    len(rows))
            am2.metric("Synced",        synced)
            am3.metric("Healthy",       healthy)
            am4.metric("Out of Sync",   oosync)

            st.divider()
            sel_app_detail = st.selectbox("View app details", [r["Name"] for r in rows], key="argo_detail_sel")
            if st.button("🔍 Get App Details"):
                detail = argo_get(f"/api/v1/applications/{sel_app_detail}")
                if detail:
                    spec   = detail.get("spec", {})
                    status = detail.get("status", {})
                    d1, d2 = st.columns(2)
                    d1.markdown(f"**Source Repo:** `{spec.get('source',{}).get('repoURL','?')}`")
                    d1.markdown(f"**Path:** `{spec.get('source',{}).get('path','?')}`")
                    d1.markdown(f"**Target Rev:** `{spec.get('source',{}).get('targetRevision','HEAD')}`")
                    d2.markdown(f"**Dest Server:** `{spec.get('destination',{}).get('server','?')}`")
                    d2.markdown(f"**Dest Namespace:** `{spec.get('destination',{}).get('namespace','?')}`")
                    d2.markdown(f"**Health:** `{status.get('health',{}).get('status','?')}`")

                    resources = status.get("resources", [])
                    if resources:
                        st.markdown("##### Resources")
                        st.dataframe(pd.DataFrame([{
                            "Kind":      r.get("kind", ""),
                            "Name":      r.get("name", ""),
                            "Namespace": r.get("namespace", ""),
                            "Status":    r.get("status", ""),
                            "Health":    r.get("health", {}).get("status", "") if isinstance(r.get("health"), dict) else "",
                        } for r in resources]), use_container_width=True, hide_index=True)
        else:
            st.info("No ArgoCD applications found")

    with tab2:
        repos_data = argo_get("/api/v1/repositories")
        if repos_data and repos_data.get("items"):
            repos = repos_data["items"]
            st.dataframe(pd.DataFrame([{
                "Repo":         r.get("repo", ""),
                "Type":         r.get("type", "git"),
                "Connected":    r.get("connectionState", {}).get("status", ""),
                "Message":      r.get("connectionState", {}).get("message", "")[:60],
            } for r in repos]), use_container_width=True, hide_index=True)
        else:
            st.info("No repositories configured")

        st.divider()
        st.markdown("##### Add Repository")
        with st.form("argo_add_repo"):
            repo_url  = st.text_input("Repository URL", placeholder="https://github.com/org/repo.git")
            repo_user = st.text_input("Username (optional)")
            repo_pass = st.text_input("Password / Token (optional)", type="password")
            if st.form_submit_button("➕ Add Repository"):
                payload = {"repo": repo_url}
                if repo_user:
                    payload["username"] = repo_user
                if repo_pass:
                    payload["password"] = repo_pass
                code, resp = argo_post("/api/v1/repositories", payload)
                if code in (200, 201):
                    st.success(f"Repository added: {repo_url}")
                else:
                    st.error(f"Failed (HTTP {code}): {resp}")

    with tab3:
        apps_data2 = argo_get("/api/v1/applications")
        if apps_data2 and apps_data2.get("items"):
            app_names = [a["metadata"]["name"] for a in apps_data2["items"]]

            st.markdown("##### Sync Application")
            sel_app = st.selectbox("Application", app_names, key="sync_app_sel")
            sc1, sc2, sc3 = st.columns(3)
            dry_run = sc1.checkbox("Dry run")
            prune   = sc2.checkbox("Prune resources")
            force   = sc3.checkbox("Force replace")
            if st.button("🔀 Sync", type="primary"):
                payload = {"dryRun": dry_run, "prune": prune, "strategy": {"apply": {"force": force}}, "revision": "HEAD"}
                code, resp = argo_post(f"/api/v1/applications/{sel_app}/sync", payload)
                if code == 200:
                    st.success(f"Sync triggered for '{sel_app}'")
                else:
                    st.error(f"Sync failed (HTTP {code}): {resp}")

            if st.button("🔁 Sync All Apps"):
                for app_name in app_names:
                    code, _ = argo_post(f"/api/v1/applications/{app_name}/sync", {"revision": "HEAD"})
                    st.write(f"{'✅' if code == 200 else '❌'} {app_name}")

            st.divider()
            st.markdown("##### Rollback Application")
            rb_app = st.selectbox("Application to rollback", app_names, key="rb_app_sel")
            rb_rev = st.number_input("Rollback to history ID", min_value=0, value=0, step=1)
            if st.button("⏪ Rollback"):
                code, resp = argo_post(f"/api/v1/applications/{rb_app}/rollback", {"id": int(rb_rev)})
                if code == 200:
                    st.success(f"Rollback initiated for '{rb_app}' to history #{rb_rev}")
                else:
                    st.error(f"Rollback failed (HTTP {code}): {resp}")

            st.divider()
            st.markdown("##### Delete Application")
            del_app = st.selectbox("Application to delete", app_names, key="del_app_sel")
            cascade = st.checkbox("Cascade delete (also remove K8s resources)", value=True)
            del_confirm = st.text_input("Type app name to confirm", key="del_app_confirm")
            if st.button("🗑 Delete App", type="secondary"):
                if del_confirm.strip() == del_app:
                    import httpx
                    try:
                        r = httpx.delete(
                            f"{ARGOCD_URL}/api/v1/applications/{del_app}",
                            params={"cascade": str(cascade).lower()},
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=15, verify=False
                        )
                        if r.status_code in (200, 204):
                            st.success(f"Application '{del_app}' deleted")
                        else:
                            st.error(f"Failed (HTTP {r.status_code}): {r.text[:200]}")
                    except Exception as e:
                        st.error(str(e))
                else:
                    st.error("App name doesn't match")
        else:
            st.info("No applications found")

    with tab4:
        st.markdown("##### Create ArgoCD Application")
        with st.form("argo_create_app"):
            ca1, ca2 = st.columns(2)
            app_name_new = ca1.text_input("Application Name", placeholder="my-app")
            app_project  = ca2.text_input("Project", value="default")
            ca3, ca4 = st.columns(2)
            app_repo_url = ca3.text_input("Git Repo URL", placeholder="https://github.com/org/repo.git")
            app_path     = ca4.text_input("Path in repo", placeholder="manifests/")
            ca5, ca6, ca7 = st.columns(3)
            app_target_rev = ca5.text_input("Target Revision", value="HEAD")
            app_dest_ns    = ca6.text_input("Destination Namespace", value="devops")
            app_dest_srv   = ca7.text_input("Destination Server", value="https://kubernetes.default.svc")
            ca8, ca9 = st.columns(2)
            sync_policy = ca8.selectbox("Sync Policy", ["Manual", "Automatic"])
            auto_prune  = ca9.checkbox("Auto Prune", value=False)

            if st.form_submit_button("🚀 Create Application"):
                payload = {
                    "metadata": {"name": app_name_new},
                    "spec": {
                        "project": app_project,
                        "source": {
                            "repoURL":        app_repo_url,
                            "path":           app_path,
                            "targetRevision": app_target_rev,
                        },
                        "destination": {
                            "server":    app_dest_srv,
                            "namespace": app_dest_ns,
                        },
                    },
                }
                if sync_policy == "Automatic":
                    payload["spec"]["syncPolicy"] = {
                        "automated": {"prune": auto_prune, "selfHeal": True}
                    }
                code, resp = argo_post("/api/v1/applications", payload)
                if code in (200, 201):
                    st.success(f"Application '{app_name_new}' created successfully")
                else:
                    st.error(f"Failed (HTTP {code}): {resp}")

    with tab5:
        # Projects
        projs_data = argo_get("/api/v1/projects")
        if projs_data and projs_data.get("items"):
            st.markdown("##### Projects")
            st.dataframe(pd.DataFrame([{
                "Name":        p.get("metadata", {}).get("name", ""),
                "Description": p.get("spec", {}).get("description", ""),
                "Namespaces":  str(p.get("spec", {}).get("destinations", [{}])[0].get("namespace", "") if p.get("spec", {}).get("destinations") else ""),
            } for p in projs_data["items"]]), use_container_width=True, hide_index=True)

        st.divider()
        # Cluster info
        clusters = argo_get("/api/v1/clusters")
        if clusters and clusters.get("items"):
            st.markdown("##### Clusters")
            st.dataframe(pd.DataFrame([{
                "Name":    c.get("name", ""),
                "Server":  c.get("server", ""),
                "Version": c.get("info", {}).get("serverVersion", ""),
                "Status":  c.get("connectionState", {}).get("status", ""),
            } for c in clusters["items"]]), use_container_width=True, hide_index=True)

        st.link_button("🌐 Open ArgoCD UI", ARGOCD_URL, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 9 — TRIVY SCANNER
# ══════════════════════════════════════════════════════════════════════════════
elif active_page == "🛡️ Trivy Scanner":
    page_header("🛡️", "Trivy Security Scanner", "Container image and IaC vulnerability scanning")

    if not shutil.which("trivy"):
        st.warning("Trivy not installed — run `brew install trivy`")
        st.stop()

    ver_r = shell("trivy --version")
    if ver_r["ok"]:
        st.caption(f"Trivy {ver_r['out'].splitlines()[0]}")

    import pandas as pd
    tab1, tab2, tab3, tab4 = st.tabs(["🖼️ Image Scan", "📁 IaC / Config Scan", "☸️ K8s Scan", "📦 SBOM"])

    def _sev_color(row):
        s = row.get("Severity","")
        if s == "CRITICAL": return ["background-color:#3a0a0a"]*len(row)
        if s == "HIGH":     return ["background-color:#2a1500"]*len(row)
        if s == "MEDIUM":   return ["background-color:#1a1a00"]*len(row)
        return [""]*len(row)

    with tab1:
        i1, i2 = st.columns([3,1])
        image_input = i1.text_input("Image to scan", value="nginx:latest",
                                     placeholder="nginx:latest  |  python:3.11-slim")
        severity = i2.multiselect("Severity filter", ["CRITICAL","HIGH","MEDIUM","LOW"],
                                   default=["CRITICAL","HIGH"])
        sc1, sc2 = st.columns([1,1])
        scan_os   = sc1.checkbox("OS packages", value=True)
        scan_lang = sc2.checkbox("Language pkgs", value=True)

        if st.button("🔍 Scan Image", type="primary") and image_input:
            sev_str  = ",".join(severity) if severity else "CRITICAL,HIGH,MEDIUM,LOW"
            scanners = ",".join(filter(None, ["vuln"]))
            with st.spinner(f"Scanning {image_input} …"):
                r = shell(f"trivy image --format json --severity {sev_str} {image_input}")
            if r["out"]:
                try:
                    data = json.loads(r["out"])
                    results = data.get("Results", [])
                    all_vulns = []
                    for res in results:
                        for v in (res.get("Vulnerabilities") or []):
                            all_vulns.append({
                                "Target":    res.get("Target","")[:30],
                                "CVE":       v.get("VulnerabilityID",""),
                                "Package":   v.get("PkgName",""),
                                "Installed": v.get("InstalledVersion",""),
                                "Fixed":     v.get("FixedVersion","") or "—",
                                "Severity":  v.get("Severity",""),
                                "Title":     (v.get("Title","") or "")[:70],
                            })
                    if all_vulns:
                        counts = {s: sum(1 for v in all_vulns if v["Severity"]==s)
                                  for s in ["CRITICAL","HIGH","MEDIUM","LOW"]}
                        sm1,sm2,sm3,sm4 = st.columns(4)
                        sm1.metric("🔴 Critical", counts.get("CRITICAL",0))
                        sm2.metric("🟠 High",     counts.get("HIGH",0))
                        sm3.metric("🟡 Medium",   counts.get("MEDIUM",0))
                        sm4.metric("🔵 Low",      counts.get("LOW",0))
                        df_v = pd.DataFrame(all_vulns)
                        st.dataframe(df_v.style.apply(_sev_color, axis=1),
                                     use_container_width=True, hide_index=True)
                    else:
                        st.success(f"✅ No vulnerabilities found in {image_input}!")
                except Exception as e:
                    st.code(r["out"][:4000], language="bash")
            else:
                st.error(r["err"][:500] if r["err"] else "Scan failed — is the image pullable?")

    with tab2:
        path_input = st.text_input("Directory / file to scan", value=TF_WORKDIR,
                                    placeholder="/path/to/k8s-manifests")
        iac_sev = st.multiselect("Severity", ["CRITICAL","HIGH","MEDIUM","LOW"],
                                  default=["CRITICAL","HIGH"], key="iac_sev")
        if st.button("🔍 Scan Config / IaC", type="primary"):
            sev_str = ",".join(iac_sev) if iac_sev else "CRITICAL,HIGH,MEDIUM,LOW"
            with st.spinner("Scanning …"):
                r = shell(f"trivy config --format json --severity {sev_str} {path_input}")
            if r["out"]:
                try:
                    data = json.loads(r["out"])
                    results = data.get("Results", [])
                    all_mc = []
                    for res in results:
                        for m in (res.get("Misconfigurations") or []):
                            all_mc.append({
                                "File":     res.get("Target",""),
                                "ID":       m.get("ID",""),
                                "Severity": m.get("Severity",""),
                                "Title":    m.get("Title","")[:70],
                                "Status":   m.get("Status",""),
                                "Fix":      (m.get("Resolution","") or "")[:60],
                            })
                    if all_mc:
                        mc_counts = {s: sum(1 for m in all_mc if m["Severity"]==s)
                                     for s in ["CRITICAL","HIGH","MEDIUM","LOW"]}
                        mc1,mc2,mc3,mc4 = st.columns(4)
                        mc1.metric("🔴 Critical", mc_counts.get("CRITICAL",0))
                        mc2.metric("🟠 High",     mc_counts.get("HIGH",0))
                        mc3.metric("🟡 Medium",   mc_counts.get("MEDIUM",0))
                        mc4.metric("🔵 Low",      mc_counts.get("LOW",0))
                        st.dataframe(pd.DataFrame(all_mc).style.apply(_sev_color, axis=1),
                                     use_container_width=True, hide_index=True)
                    else:
                        st.success("✅ No misconfigurations found!")
                except Exception:
                    st.code(r["out"][:3000])
            else:
                st.error(r["err"][:500] if r["err"] else "Scan failed")

    with tab3:
        st.info("Scans the running K8s cluster — may take 1–3 minutes.")
        k8s_ns = st.text_input("Namespace (leave blank for all)", value="devops", key="trivy_k8s_ns")
        k8s_sev = st.multiselect("Severity", ["CRITICAL","HIGH","MEDIUM","LOW"],
                                  default=["CRITICAL","HIGH"], key="k8s_sev")
        if st.button("🔍 Scan Cluster", type="primary"):
            sev_str = ",".join(k8s_sev) if k8s_sev else "CRITICAL,HIGH"
            ns_flag = f"--include-namespaces {k8s_ns}" if k8s_ns.strip() else ""
            with st.spinner("Scanning cluster …"):
                r = shell(f"trivy k8s --report summary --severity {sev_str} {ns_flag} cluster")
            if r["out"]:
                # Try JSON, else show raw
                try:
                    data = json.loads(r["out"])
                    st.json(data)
                except Exception:
                    st.code(r["out"][:5000], language="bash")
            else:
                st.error(r["err"][:500] if r["err"] else "Scan failed")

        st.divider()
        st.markdown("##### Scan K8s Manifest File")
        manifest_path = st.text_input("Manifest file / directory", placeholder="/path/to/deployment.yaml")
        if st.button("🔍 Scan Manifest") and manifest_path:
            with st.spinner("Scanning manifest …"):
                r = shell(f"trivy config --format json {manifest_path}")
            if r["out"]:
                try:
                    data = json.loads(r["out"])
                    rows = []
                    for res in data.get("Results",[]):
                        for m in (res.get("Misconfigurations") or []):
                            rows.append({"File": res.get("Target",""), "ID": m.get("ID",""),
                                         "Severity": m.get("Severity",""), "Title": m.get("Title","")[:60]})
                    if rows:
                        st.dataframe(pd.DataFrame(rows).style.apply(_sev_color, axis=1),
                                     use_container_width=True, hide_index=True)
                    else:
                        st.success("✅ No issues found in manifest")
                except Exception:
                    st.code(r["out"][:3000])
            else:
                st.error(r["err"][:300] if r["err"] else "Scan failed")

    with tab4:
        st.markdown("##### Generate Software Bill of Materials (SBOM)")
        sbom_image = st.text_input("Image for SBOM", value="nginx:latest", key="sbom_img")
        sbom_fmt   = st.radio("Format", ["cyclonedx", "spdx-json"], horizontal=True)
        if st.button("📦 Generate SBOM", type="primary") and sbom_image:
            with st.spinner(f"Generating {sbom_fmt} SBOM …"):
                r = shell(f"trivy image --format {sbom_fmt} {sbom_image}")
            if r["out"]:
                try:
                    sbom_data = json.loads(r["out"])
                    comps = sbom_data.get("components", sbom_data.get("packages", []))
                    if isinstance(comps, list):
                        st.metric("Components", len(comps))
                    st.json(sbom_data)
                except Exception:
                    st.code(r["out"][:5000])
            else:
                st.error(r["err"][:300] if r["err"] else "SBOM generation failed")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 10 — VAULT
# ══════════════════════════════════════════════════════════════════════════════
elif active_page == "🔐 Vault Secrets":
    page_header("🔐", "Vault Secrets Manager", f"HashiCorp Vault · {VAULT_URL}")

    if not port_up(30200):
        st.info("Vault unreachable on port 30200 — check if the pod is running")
        st.stop()

    def vault_get(path):
        return http_json(f"{VAULT_URL}/{path}", headers={"X-Vault-Token": VAULT_TOKEN} if False else None)

    def vault_api(path):
        import httpx
        try:
            r = httpx.get(f"{VAULT_URL}/{path}",
                          headers={"X-Vault-Token": VAULT_TOKEN}, timeout=6)
            if r.status_code < 400:
                return r.json()
        except Exception:
            pass
        return None

    import pandas as pd, httpx as _hx

    def vault_post(path, payload):
        try:
            r = _hx.post(f"{VAULT_URL}/{path}", json=payload,
                         headers={"X-Vault-Token": VAULT_TOKEN}, timeout=8)
            return r.status_code, r.text
        except Exception as e:
            return 0, str(e)

    def vault_delete(path):
        try:
            r = _hx.delete(f"{VAULT_URL}/{path}",
                           headers={"X-Vault-Token": VAULT_TOKEN}, timeout=8)
            return r.status_code
        except Exception:
            return 0

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏥 Health", "🔑 Read / List", "✏️ Write Secret", "🗑️ Delete Secret", "⚙️ Auth & Policies"
    ])

    with tab1:
        health = vault_api("v1/sys/health")
        if health:
            sealed = health.get("sealed", True)
            h1,h2,h3,h4 = st.columns(4)
            h1.metric("Status",      "🔓 Unsealed" if not sealed else "🔒 Sealed")
            h2.metric("Initialized", "✅" if health.get("initialized") else "❌")
            h3.metric("Version",     health.get("version","?"))
            h4.metric("Cluster",     health.get("cluster_name","—"))
            if sealed:
                st.warning("Vault is sealed — unseal it to read/write secrets")
        else:
            st.warning("Could not fetch Vault health")

        st.divider()
        st.markdown("##### Secret Engines (Mounts)")
        mounts_h = vault_api("v1/sys/mounts")
        if mounts_h:
            mdata = mounts_h.get("data", mounts_h)
            rows_m = [{"Path": k, "Type": v.get("type",""), "Description": v.get("description","")}
                      for k, v in mdata.items()]
            st.dataframe(pd.DataFrame(rows_m), use_container_width=True, hide_index=True)

    with tab2:
        mounts = vault_api("v1/sys/mounts")
        kv_mounts = []
        if mounts:
            mdata = mounts.get("data", mounts)
            kv_mounts = [k.rstrip("/") for k, v in mdata.items()
                         if v.get("type","") in ("kv","generic") and not k.startswith("sys")]
        if not kv_mounts:
            kv_mounts = ["secret"]

        sel_mount  = st.selectbox("KV Mount", kv_mounts, key="v_mount_r")
        secret_path = st.text_input("Secret path", placeholder="myapp/config", key="v_path_r")

        rc1, rc2 = st.columns(2)
        if rc1.button("📋 List", use_container_width=True):
            data = vault_api(f"v1/{sel_mount}/metadata/{secret_path}?list=true") or \
                   vault_api(f"v1/{sel_mount}/{secret_path}?list=true")
            keys = (data or {}).get("data", {}).get("keys", [])
            if keys:
                st.dataframe(pd.DataFrame({"Key": keys}), use_container_width=True, hide_index=True)
            else:
                st.info("No keys at this path")
        if rc2.button("🔓 Read", use_container_width=True):
            data = vault_api(f"v1/{sel_mount}/data/{secret_path}") or \
                   vault_api(f"v1/{sel_mount}/{secret_path}")
            if data:
                secret_data = data.get("data", {})
                if isinstance(secret_data, dict) and "data" in secret_data:
                    secret_data = secret_data["data"]
                st.json(secret_data)
            else:
                st.error("Secret not found or access denied")

    with tab3:
        st.markdown("##### Write / Update a Secret")
        mounts2 = vault_api("v1/sys/mounts")
        kv2 = ["secret"]
        if mounts2:
            kv2 = [k.rstrip("/") for k, v in mounts2.get("data", mounts2).items()
                   if v.get("type","") in ("kv","generic") and not k.startswith("sys")] or ["secret"]

        wm = st.selectbox("KV Mount", kv2, key="v_mount_w")
        wp = st.text_input("Secret path", placeholder="myapp/db", key="v_path_w")
        st.markdown("Key-Value pairs:")
        kv_rows = st.data_editor(
            pd.DataFrame({"Key": ["username","password"], "Value": ["",""]}).astype(str),
            use_container_width=True, hide_index=True, num_rows="dynamic", key="v_kv_editor"
        )
        if st.button("💾 Write Secret", type="primary"):
            if not wp.strip():
                st.error("Secret path is required")
            else:
                kv_data = {row["Key"]: row["Value"]
                           for _, row in kv_rows.iterrows() if row["Key"]}
                # Try KV v2 first, then v1
                code, resp = vault_post(f"v1/{wm}/data/{wp}", {"data": kv_data})
                if code not in (200, 204):
                    code, resp = vault_post(f"v1/{wm}/{wp}", kv_data)
                if code in (200, 204):
                    st.success(f"✅ Secret written to {wm}/{wp}")
                else:
                    st.error(f"❌ Failed (HTTP {code}): {resp[:200]}")

    with tab4:
        st.warning("⚠️ Deleted secrets cannot be recovered.", icon="⚠️")
        mounts3 = vault_api("v1/sys/mounts")
        kv3 = ["secret"]
        if mounts3:
            kv3 = [k.rstrip("/") for k, v in mounts3.get("data", mounts3).items()
                   if v.get("type","") in ("kv","generic") and not k.startswith("sys")] or ["secret"]
        dm  = st.selectbox("KV Mount", kv3, key="v_mount_d")
        dp  = st.text_input("Secret path to delete", placeholder="myapp/old-config", key="v_path_d")
        dc  = st.text_input("Type the path to confirm", key="v_del_confirm")
        if st.button("🗑️ Delete Secret", type="primary"):
            if dc.strip() != dp.strip():
                st.error("Path mismatch — type the exact path to confirm")
            elif not dp.strip():
                st.error("Path required")
            else:
                # Try KV v2 metadata (permanent delete), then v1
                code = vault_delete(f"v1/{dm}/metadata/{dp}")
                if code not in (200,204):
                    code = vault_delete(f"v1/{dm}/{dp}")
                if code in (200, 204):
                    st.success(f"✅ Secret '{dp}' deleted")
                else:
                    st.error(f"❌ Failed (HTTP {code})")

    with tab5:
        st.markdown("##### Authentication Methods")
        auth_data = vault_api("v1/sys/auth")
        if auth_data:
            rows_a = [{"Path": k, "Type": v.get("type",""), "Description": v.get("description","")}
                      for k, v in auth_data.get("data", auth_data).items()]
            st.dataframe(pd.DataFrame(rows_a), use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("##### Policies")
        pol_data = vault_api("v1/sys/policy")
        if pol_data:
            policies = pol_data.get("data", {}).get("policies",
                       pol_data.get("policies", []))
            if policies:
                sel_pol = st.selectbox("View Policy", policies)
                if st.button("📄 Read Policy"):
                    p = vault_api(f"v1/sys/policy/{sel_pol}")
                    if p:
                        st.code(p.get("data",{}).get("rules", p.get("rules","")), language="hcl")
        st.divider()
        st.markdown("##### Create Policy")
        pol_name  = st.text_input("Policy name", placeholder="readonly-secrets")
        pol_rules = st.text_area("HCL Rules",
            value='path "secret/*" {\n  capabilities = ["read","list"]\n}', height=120)
        if st.button("💾 Save Policy") and pol_name:
            code, resp = vault_post(f"v1/sys/policy/{pol_name}", {"policy": pol_rules})
            if code in (200,204):
                st.success(f"✅ Policy '{pol_name}' saved")
            else:
                st.error(f"❌ Failed (HTTP {code}): {resp[:200]}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 11 — LOKI LOGS
# ══════════════════════════════════════════════════════════════════════════════
elif active_page == "📜 Loki Logs":
    page_header("📜", "Loki Log Aggregation", f"Distributed log management · {LOKI_URL}")

    if not port_up(30310):
        st.info("Loki unreachable on port 30310 — check if the pod is running")
        st.stop()

    import pandas as pd, datetime as _dt, time as _time

    tab1, tab2, tab3 = st.tabs(["🔍 Query Logs", "⚡ Quick Queries", "🏷️ Labels & Values"])

    def _loki_query(query, hours=1, limit=200):
        now_ns   = int(_time.time() * 1e9)
        start_ns = now_ns - int(hours * 3600 * 1e9)
        return http_json(f"{LOKI_URL}/loki/api/v1/query_range",
                         params={"query": query, "start": start_ns,
                                 "end": now_ns, "limit": limit})

    def _render_logs(data):
        if not data or data.get("status") != "success":
            st.warning("No data returned from Loki")
            return
        results = data.get("data", {}).get("result", [])
        if not results:
            st.info("No log streams matched")
            return
        rows = []
        for stream in results:
            labels_str = ", ".join(f"{k}={v}" for k, v in stream.get("stream",{}).items())
            for ts, line in stream.get("values", []):
                dt = _dt.datetime.fromtimestamp(int(ts)/1e9).strftime("%Y-%m-%d %H:%M:%S")
                rows.append({"Time": dt, "Stream": labels_str[:50], "Log": line})
        if rows:
            rows.sort(key=lambda x: x["Time"])
            st.metric("Log lines", len(rows))
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with tab1:
        lq1, lq2, lq3 = st.columns([4,1,1])
        query  = lq1.text_input("LogQL Query", value='{namespace="devops"}',
                                 placeholder='{app="jenkins"} |= "error"')
        hours  = lq2.number_input("Hours back", 1, 72, 1)
        limit  = lq3.number_input("Lines",      10, 2000, 200)

        if st.button("🔍 Run Query", type="primary"):
            with st.spinner("Querying Loki …"):
                data = _loki_query(query, hours, limit)
            _render_logs(data)

        st.divider()
        st.markdown("##### LogQL Cheatsheet")
        st.code("""{namespace="devops"}                     # all logs in namespace
{app="jenkins"} |= "ERROR"              # filter by string
{app="sonarqube"} | json                # parse JSON logs
{namespace="devops"} | logfmt           # parse logfmt
rate({namespace="devops"}[5m])          # log rate metric
count_over_time({app="jenkins"}[1h])    # count over time""", language="logql")

    with tab2:
        QUICK = [
            ("Jenkins Errors",         '{namespace="devops",app="jenkins"} |= "ERROR"'),
            ("SonarQube Warnings",      '{namespace="devops",app="sonarqube"} |~ "WARN|ERROR"'),
            ("All devops namespace",    '{namespace="devops"}'),
            ("Kubernetes events",       '{job="kube-events"}'),
            ("OOMKilled / crashloops",  '{namespace="devops"} |= "OOMKilled"'),
            ("HTTP 5xx errors",         '{namespace="devops"} |= "500"'),
            ("Slow queries >1s",        '{namespace="devops"} |= "slow"'),
            ("ArgoCD sync logs",        '{namespace="argocd"}'),
        ]
        qq1, qq2 = st.columns([2,1])
        sel_quick = qq1.selectbox("Pre-built query", [q[0] for q in QUICK])
        qq_hours  = qq2.number_input("Hours back", 1, 24, 1, key="qq_h")
        sel_logql = next(q[1] for q in QUICK if q[0]==sel_quick)
        st.code(sel_logql, language="logql")
        if st.button("▶️ Run Quick Query", type="primary"):
            with st.spinner("Querying …"):
                data = _loki_query(sel_logql, qq_hours, 500)
            _render_logs(data)

    with tab3:
        label_data = http_json(f"{LOKI_URL}/loki/api/v1/labels")
        labels = (label_data or {}).get("data", [])
        if labels:
            st.metric("Available labels", len(labels))
            sel_label = st.selectbox("Select label", labels)
            if sel_label:
                val_data = http_json(f"{LOKI_URL}/loki/api/v1/label/{sel_label}/values")
                vals = (val_data or {}).get("data", [])
                if vals:
                    st.dataframe(pd.DataFrame({"Value": vals}), use_container_width=True, hide_index=True)
                    # Quick jump
                    sel_val = st.selectbox("Filter by value", vals)
                    if st.button("🔍 Query this label=value"):
                        with st.spinner("Querying …"):
                            data = _loki_query(f'{{{sel_label}="{sel_val}"}}', 2, 300)
                        _render_logs(data)
        else:
            st.info("No labels found — Loki may not have received logs yet")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 12 — HELM
# ══════════════════════════════════════════════════════════════════════════════
elif active_page == "⛵ Helm Manager":
    page_header("⛵", "Helm Manager", "Kubernetes application package manager")

    if not shutil.which("helm"):
        st.warning("Helm not installed — run `brew install helm`")
        st.stop()

    ver_r = shell("helm version --short")
    if ver_r["ok"]:
        st.caption(ver_r["out"])

    import pandas as pd
    tab1, tab2, tab3, tab4 = st.tabs(["📦 Releases", "⬆️ Install / Upgrade", "🗂️ Repos", "🔍 Search Charts"])

    with tab1:
        ns_h = st.text_input("Namespace", value="devops", key="helm_ns")
        r = shell(f"helm list -n {ns_h} --output json")
        if r["ok"] and r["out"] and r["out"] != "[]":
            try:
                releases = json.loads(r["out"])
                df = pd.DataFrame([{
                    "Name":      rel.get("name",""), "Namespace": rel.get("namespace",""),
                    "Revision":  rel.get("revision",""), "Status": rel.get("status",""),
                    "Chart":     rel.get("chart",""), "App Ver": rel.get("app_version",""),
                    "Updated":   rel.get("updated","")[:16],
                } for rel in releases])
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.metric("Total releases", len(releases))

                sel_rel = st.selectbox("Select release for actions", [r["name"] for r in releases])
                ha1, ha2, ha3, ha4 = st.columns(4)
                if ha1.button("📜 History"):
                    r2 = shell(f"helm history {sel_rel} -n {ns_h} --output json")
                    if r2["ok"] and r2["out"]:
                        st.dataframe(pd.DataFrame(json.loads(r2["out"])), use_container_width=True, hide_index=True)
                if ha2.button("⚙️ Values"):
                    r2 = shell(f"helm get values {sel_rel} -n {ns_h}")
                    st.code(r2["out"] or r2["err"], language="yaml")
                if ha3.button("🔄 Rollback"):
                    rev = st.number_input("To revision", 0, key="helm_rollback_rev")
                    r2  = shell(f"helm rollback {sel_rel} {rev} -n {ns_h}")
                    show(r2, f"Rolled back {sel_rel}")
                if ha4.button("🗑️ Uninstall"):
                    r2 = shell(f"helm uninstall {sel_rel} -n {ns_h}")
                    show(r2, f"Uninstalled {sel_rel}")
                    st.rerun()
            except Exception:
                st.code(r["out"])
        else:
            st.info(f"No Helm releases in namespace '{ns_h}'")

    with tab2:
        st.markdown("##### Install or Upgrade a Chart")
        ic1, ic2 = st.columns(2)
        release_name = ic1.text_input("Release name", placeholder="my-nginx")
        chart_ref    = ic2.text_input("Chart", placeholder="bitnami/nginx  or  ./charts/myapp")
        ic3, ic4, ic5 = st.columns(3)
        ns_install = ic3.text_input("Namespace", value="devops", key="helm_inst_ns")
        chart_ver  = ic4.text_input("Version (optional)", placeholder="15.3.1")
        create_ns  = ic5.checkbox("Create namespace", value=True)

        values_yaml = st.text_area("values.yaml overrides (YAML)", height=120,
                                    placeholder="replicaCount: 2\nservice:\n  type: NodePort")
        is_upgrade = st.checkbox("Upgrade if already installed (--install)", value=True)

        if st.button("🚀 Install / Upgrade", type="primary"):
            if not release_name or not chart_ref:
                st.error("Release name and chart are required")
            else:
                # write values file if provided
                import tempfile, os
                val_flag = ""
                if values_yaml.strip():
                    tmp = tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w")
                    tmp.write(values_yaml); tmp.close()
                    val_flag = f"-f {tmp.name}"
                ver_flag = f"--version {chart_ver}" if chart_ver.strip() else ""
                ns_flag  = f"--create-namespace" if create_ns else ""
                cmd_base = "upgrade --install" if is_upgrade else "install"
                cmd = f"helm {cmd_base} {release_name} {chart_ref} -n {ns_install} {ns_flag} {ver_flag} {val_flag} --wait --timeout 5m"
                with st.spinner(f"Running: helm {cmd_base} {release_name} …"):
                    r = shell(cmd)
                if val_flag:
                    try: os.unlink(tmp.name)
                    except: pass
                show(r, f"✅ Release '{release_name}' deployed")
                if r["ok"]: st.code(r["out"][-2000:], language="bash")

    with tab3:
        r = shell("helm repo list --output json")
        if r["ok"] and r["out"] and r["out"] != "[]":
            try:
                repos = json.loads(r["out"])
                st.dataframe(pd.DataFrame([{"Name": rp.get("name",""), "URL": rp.get("url","")}
                                           for rp in repos]),
                             use_container_width=True, hide_index=True)
                sel_repo = st.selectbox("Remove repo", [rp["name"] for rp in repos])
                rc1, rc2 = st.columns(2)
                if rc1.button("🔄 Update All Repos"):
                    show(shell("helm repo update"), "✅ Repos updated")
                if rc2.button("🗑️ Remove Repo"):
                    show(shell(f"helm repo remove {sel_repo}"), f"✅ Repo '{sel_repo}' removed")
                    st.rerun()
            except Exception:
                st.code(r["out"])
        else:
            st.info("No repos configured")

        st.divider()
        st.markdown("##### Add Repository")
        ra1, ra2 = st.columns(2)
        repo_name = ra1.text_input("Name", placeholder="bitnami")
        repo_url  = ra2.text_input("URL", placeholder="https://charts.bitnami.com/bitnami")
        if st.button("➕ Add & Update"):
            if repo_name and repo_url:
                with st.spinner("Adding …"):
                    res = shell(f"helm repo add {repo_name} {repo_url} && helm repo update")
                show(res, f"✅ Repo '{repo_name}' added")
            else:
                st.error("Name and URL required")

    with tab4:
        st.markdown("##### Search Charts")
        sc1, sc2 = st.columns([3,1])
        search_term = sc1.text_input("Chart name", placeholder="nginx, prometheus, postgres …")
        search_src  = sc2.radio("Source", ["repo", "hub"], horizontal=True)
        if st.button("🔍 Search") and search_term:
            cmd = (f"helm search repo {search_term} --output json" if search_src=="repo"
                   else f"helm search hub {search_term} --output json")
            r = shell(cmd)
            if r["ok"] and r["out"] and r["out"] not in ("[]","null"):
                try:
                    charts = json.loads(r["out"]) or []
                    st.dataframe(pd.DataFrame([{
                        "Name": c.get("name",""), "Version": c.get("version",""),
                        "App Version": c.get("app_version",""),
                        "Description": (c.get("description","") or "")[:80],
                    } for c in charts[:40]]), use_container_width=True, hide_index=True)
                except Exception:
                    st.code(r["out"][:2000])
            else:
                st.info(f"No charts found for '{search_term}' — try adding a repo first")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 13 — CONTAINER REGISTRY
# ══════════════════════════════════════════════════════════════════════════════
elif active_page == "📦 Container Registry":
    page_header("📦", "Container Registry", f"Harbor private registry · {HARBOR_URL}")

    import pandas as pd

    reg_up = port_up(30880, "127.0.0.1")
    h1, h2, h3 = st.columns(3)
    h1.markdown(f"**Harbor API:** {status_badge(reg_up)}", unsafe_allow_html=True)
    if reg_up:
        h2.link_button("🌐 Open Harbor UI", HARBOR_URL)

    def harbor_get(path, params=None):
        return http_json(f"{HARBOR_URL}/api/v2.0{path}", auth=HARBOR_AUTH, params=params)

    def harbor_delete(path):
        try:
            import httpx
            r = httpx.delete(f"{HARBOR_URL}/api/v2.0{path}", auth=HARBOR_AUTH, timeout=10, verify=False)
            return r.status_code, r.text
        except Exception as e:
            return 0, str(e)

    def harbor_post(path, payload):
        try:
            import httpx
            r = httpx.post(f"{HARBOR_URL}/api/v2.0{path}", json=payload, auth=HARBOR_AUTH, timeout=10, verify=False)
            return r.status_code, r.text
        except Exception as e:
            return 0, str(e)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏗️ Projects", "📦 Repositories", "🏷️ Tags & Images", "⬆️ Push Guide", "⚙️ System"
    ])

    with tab1:
        if reg_up:
            c_ref, c_create, _ = st.columns([1, 1, 4])
            if c_ref.button("🔄 Refresh", key="harbor_proj_ref"):
                st.cache_data.clear()

            @st.cache_data(ttl=30)
            def get_harbor_projects():
                return harbor_get("/projects", params={"page_size": 100})

            projs = get_harbor_projects()
            if projs:
                rows = []
                for p in projs:
                    rows.append({
                        "Name":       p.get("name", ""),
                        "Public":     p.get("metadata", {}).get("public", "false"),
                        "Repos":      p.get("repo_count", 0),
                        "Created":    (p.get("creation_time", "")[:10] if p.get("creation_time") else ""),
                        "Owner":      p.get("owner_name", ""),
                    })
                st.metric("Total Projects", len(rows))
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                st.divider()
                st.markdown("##### Create New Project")
                with st.form("harbor_create_proj"):
                    new_proj_name = st.text_input("Project Name", placeholder="my-project")
                    new_proj_public = st.checkbox("Public", value=False)
                    if st.form_submit_button("➕ Create Project"):
                        code, resp = harbor_post("/projects", {"project_name": new_proj_name, "metadata": {"public": str(new_proj_public).lower()}})
                        if code in (200, 201):
                            st.success(f"Project '{new_proj_name}' created")
                            st.cache_data.clear()
                        else:
                            st.error(f"Failed (HTTP {code}): {resp}")

                st.divider()
                st.markdown("##### Delete Project")
                proj_names = [p["name"] for p in projs]
                del_proj = st.selectbox("Select project to delete", proj_names, key="del_proj_sel")
                del_confirm = st.text_input("Type project name to confirm", key="del_proj_confirm")
                if st.button("🗑 Delete Project", type="secondary"):
                    if del_confirm.strip() == del_proj:
                        code, resp = harbor_delete(f"/projects/{del_proj}")
                        if code in (200, 202):
                            st.success(f"Project '{del_proj}' deleted")
                            st.cache_data.clear()
                        else:
                            st.error(f"Failed (HTTP {code}): {resp}")
                    else:
                        st.error("Project name doesn't match")
            else:
                st.info("No projects found or Harbor unreachable")
        else:
            st.info("Harbor unreachable on port 30880")

    with tab2:
        if reg_up:
            projs2 = harbor_get("/projects", params={"page_size": 100})
            proj_names2 = [p["name"] for p in projs2] if projs2 else []
            if proj_names2:
                sel_proj2 = st.selectbox("Project", proj_names2, key="repo_proj_sel")
                if st.button("📦 List Repositories", key="list_repos_btn"):
                    repos = harbor_get(f"/projects/{sel_proj2}/repositories", params={"page_size": 100})
                    if repos:
                        rows = []
                        for r in repos:
                            repo_name_short = r.get("name", "").split("/")[-1]
                            rows.append({
                                "Repository":  r.get("name", ""),
                                "Short Name":  repo_name_short,
                                "Pull Count":  r.get("pull_count", 0),
                                "Artifact Count": r.get("artifact_count", 0),
                                "Updated":     (r.get("update_time", "")[:10] if r.get("update_time") else ""),
                            })
                        st.metric("Repositories", len(rows))
                        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                    else:
                        st.info(f"No repositories in project '{sel_proj2}'")
            else:
                st.info("No projects found")
        else:
            st.info("Harbor unreachable on port 30880")

    with tab3:
        if reg_up:
            projs3 = harbor_get("/projects", params={"page_size": 100})
            proj_names3 = [p["name"] for p in projs3] if projs3 else []
            if proj_names3:
                tp1, tp2 = st.columns(2)
                sel_proj3 = tp1.selectbox("Project", proj_names3, key="tag_proj_sel")
                repo_name_in = tp2.text_input("Repository name", placeholder="myapp", key="tag_repo_in")

                if st.button("🏷️ List Tags / Artifacts"):
                    if repo_name_in:
                        artifacts = harbor_get(f"/projects/{sel_proj3}/repositories/{repo_name_in}/artifacts",
                                               params={"with_tag": True, "with_scan_overview": True})
                        if artifacts:
                            rows = []
                            for a in artifacts:
                                tags = [t["name"] for t in a.get("tags") or []]
                                scan = a.get("scan_overview", {})
                                vuln_summary = ""
                                if scan:
                                    for _, sv in scan.items():
                                        summary = sv.get("summary", {}).get("summary", {})
                                        vuln_summary = f"C:{summary.get('CRITICAL',0)} H:{summary.get('HIGH',0)}"
                                rows.append({
                                    "Tags":      ", ".join(tags) if tags else "(untagged)",
                                    "Digest":    a.get("digest", "")[:20],
                                    "Size (MB)": round((a.get("size", 0) or 0) / 1024 / 1024, 1),
                                    "Pushed":    (a.get("push_time", "")[:10] if a.get("push_time") else ""),
                                    "Vulnerabilities": vuln_summary or "—",
                                })
                            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                            # Delete tag
                            st.divider()
                            st.markdown("##### Delete Tag")
                            all_tags = []
                            for a in artifacts:
                                for t in (a.get("tags") or []):
                                    all_tags.append(t["name"])
                            if all_tags:
                                del_tag = st.selectbox("Tag to delete", all_tags, key="del_tag_sel")
                                if st.button("🗑 Delete Tag", type="secondary"):
                                    digest_for_tag = next(
                                        (a["digest"] for a in artifacts
                                         if any(t["name"] == del_tag for t in (a.get("tags") or []))), None)
                                    if digest_for_tag:
                                        code, resp = harbor_delete(
                                            f"/projects/{sel_proj3}/repositories/{repo_name_in}/artifacts/{digest_for_tag}/tags/{del_tag}")
                                        if code in (200, 202):
                                            st.success(f"Tag '{del_tag}' deleted")
                                        else:
                                            st.error(f"Failed (HTTP {code}): {resp}")
                        else:
                            st.info(f"No artifacts in '{sel_proj3}/{repo_name_in}'")
                    else:
                        st.warning("Enter a repository name")
        else:
            st.info("Harbor unreachable on port 30880")

    with tab4:
        st.markdown("##### Push an Image to Harbor")
        col_proj, col_repo, col_tag = st.columns(3)
        pg_proj = col_proj.text_input("Project", value="library", key="pg_proj")
        pg_repo = col_repo.text_input("Image name", value="myapp", key="pg_repo")
        pg_tag  = col_tag.text_input("Tag", value="latest", key="pg_tag")

        registry_host = "localhost:30880"
        full_image = f"{registry_host}/{pg_proj}/{pg_repo}:{pg_tag}"

        st.code(f"""# 1. Log in to Harbor
docker login {registry_host} -u admin -p Admin@123456789@

# 2. Tag your local image
docker tag myapp:latest {full_image}

# 3. Push the image
docker push {full_image}

# 4. Pull it back (verify)
docker pull {full_image}""", language="bash")

        st.divider()
        st.markdown("##### Configure containerd / K8s to use Harbor")
        st.code(f"""# Create imagePullSecret for Kubernetes
kubectl create secret docker-registry harbor-secret \\
  --docker-server={registry_host} \\
  --docker-username=admin \\
  --docker-password=Admin@123456789@ \\
  -n devops

# Reference in your Pod spec:
# spec:
#   imagePullSecrets:
#   - name: harbor-secret""", language="bash")

    with tab5:
        if reg_up:
            sys_info = harbor_get("/systeminfo")
            stats    = harbor_get("/statistics")

            if sys_info:
                sv1, sv2, sv3, sv4 = st.columns(4)
                sv1.metric("Harbor Version",  sys_info.get("harbor_version", "?"))
                sv2.metric("Registry URL",    sys_info.get("registry_url", "?"))
                sv3.metric("Auth Mode",       sys_info.get("auth_mode", "?"))
                sv4.metric("Self-Signed Cert", "Yes" if sys_info.get("has_ca_root") else "No")

            if stats:
                s1, s2, s3, s4 = st.columns(4)
                s1.metric("Public Projects",    stats.get("public_project_count", 0))
                s2.metric("Private Projects",   stats.get("private_project_count", 0))
                s3.metric("Public Repos",       stats.get("public_repo_count", 0))
                s4.metric("Total Repos",        stats.get("total_repo_count", 0))

            # Users list
            users = harbor_get("/users")
            if users:
                st.markdown("##### Users")
                st.dataframe(pd.DataFrame([{
                    "Username": u.get("username", ""),
                    "Email":    u.get("email", ""),
                    "Admin":    u.get("sysadmin_flag", False),
                    "Created":  (u.get("creation_time", "")[:10] if u.get("creation_time") else ""),
                } for u in users]), use_container_width=True, hide_index=True)
        else:
            st.info("Harbor unreachable on port 30880")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 14 — MINIO
# ══════════════════════════════════════════════════════════════════════════════
elif active_page == "🗄️ MinIO Storage":
    page_header("🗄️", "MinIO Object Storage", f"S3-compatible storage · {MINIO_URL}")

    import pandas as pd

    minio_alive = port_up(30920)
    mm1, mm2, mm3 = st.columns(3)
    mm1.markdown(f"**MinIO API:** {status_badge(minio_alive)}", unsafe_allow_html=True)
    if minio_alive:
        mm2.link_button("🌐 Open MinIO Console", MINIO_CONSOLE_URL)

    # MinIO uses S3-compatible REST API with AWS Signature — use mc CLI or boto3
    # We'll use mc CLI if available, otherwise fallback to direct REST with httpx
    MC = shutil.which("mc")

    def mc(cmd):
        return shell(f"mc {cmd}")

    def minio_ensure_alias():
        """Set up mc alias pointing to local MinIO."""
        r = shell(f"mc alias set localmin {MINIO_URL} {MINIO_ACCESS_KEY} {MINIO_SECRET_KEY} --api s3v4")
        return r["ok"]

    tab1, tab2, tab3, tab4 = st.tabs([
        "🪣 Buckets", "📂 Objects", "⬆️ Upload", "⚙️ System"
    ])

    with tab1:
        if minio_alive:
            if MC:
                minio_ensure_alias()
                c_ref, c_new, _ = st.columns([1, 1, 4])
                if c_ref.button("🔄 Refresh", key="minio_bkt_ref"):
                    pass

                r = mc("ls localmin/ --json")
                if r["ok"] and r["out"]:
                    try:
                        lines = [json.loads(l) for l in r["out"].splitlines() if l.strip()]
                        buckets = [l.get("key", "").rstrip("/") for l in lines if l.get("type") == "folder" or l.get("key","").endswith("/")]
                        if not buckets:
                            buckets = [l.get("key", "").rstrip("/") for l in lines]

                        if buckets:
                            st.metric("Buckets", len(buckets))
                            # Get size per bucket
                            bucket_rows = []
                            for b in buckets:
                                du = mc(f"du --depth 1 localmin/{b} --json")
                                size_str = "—"
                                obj_count = "—"
                                if du["ok"] and du["out"]:
                                    try:
                                        du_data = json.loads(du["out"].strip().splitlines()[-1])
                                        size_bytes = du_data.get("size", 0)
                                        size_str = f"{size_bytes/1024/1024:.1f} MB" if size_bytes > 0 else "0 B"
                                        obj_count = str(du_data.get("objects", 0))
                                    except Exception:
                                        pass
                                bucket_rows.append({"Bucket": b, "Objects": obj_count, "Size": size_str})
                            st.dataframe(pd.DataFrame(bucket_rows), use_container_width=True, hide_index=True)
                        else:
                            st.info("No buckets yet")
                    except Exception as ex:
                        st.code(r["out"])
                else:
                    st.info("No buckets found or alias not configured")

                st.divider()
                bc1, bc2 = st.columns(2)
                with bc1:
                    st.markdown("##### Create Bucket")
                    new_bucket = st.text_input("Bucket name", key="new_bucket", placeholder="my-bucket")
                    if st.button("➕ Create Bucket"):
                        if new_bucket:
                            r2 = mc(f"mb localmin/{new_bucket}")
                            if r2["ok"]:
                                st.success(f"Bucket '{new_bucket}' created")
                            else:
                                st.error(r2["err"] or "Failed to create bucket")
                        else:
                            st.warning("Enter a bucket name")

                with bc2:
                    st.markdown("##### Delete Bucket")
                    del_bucket = st.text_input("Bucket to delete", key="del_bucket", placeholder="old-bucket")
                    force_del = st.checkbox("Force (delete non-empty)", value=False)
                    if st.button("🗑 Delete Bucket", type="secondary"):
                        if del_bucket:
                            flag = " --force" if force_del else ""
                            r3 = mc(f"rb localmin/{del_bucket}{flag}")
                            if r3["ok"]:
                                st.success(f"Bucket '{del_bucket}' deleted")
                            else:
                                st.error(r3["err"] or "Failed — bucket may not be empty (use Force)")
                        else:
                            st.warning("Enter a bucket name")
            else:
                st.info("`mc` (MinIO Client) not installed")
                st.code("brew install minio/stable/mc", language="bash")
                st.code(f"mc alias set localmin {MINIO_URL} {MINIO_ACCESS_KEY} {MINIO_SECRET_KEY}", language="bash")
        else:
            st.info("MinIO unreachable on port 30920")

    with tab2:
        if minio_alive and MC:
            minio_ensure_alias()
            ot1, ot2 = st.columns([2, 1])
            bucket_sel = ot1.text_input("Bucket name", placeholder="my-bucket", key="obj_bucket")
            prefix_sel = ot2.text_input("Prefix (optional)", placeholder="folder/", key="obj_prefix")
            if st.button("📂 List Objects"):
                if bucket_sel:
                    path = f"localmin/{bucket_sel}/{prefix_sel}" if prefix_sel else f"localmin/{bucket_sel}"
                    r = mc(f"ls {path} --json")
                    if r["ok"] and r["out"]:
                        try:
                            lines = [json.loads(l) for l in r["out"].splitlines() if l.strip()]
                            obj_rows = []
                            for l in lines:
                                obj_rows.append({
                                    "Name":     l.get("key", ""),
                                    "Size":     f"{(l.get('size',0) or 0)/1024:.1f} KB",
                                    "Modified": (l.get("lastModified", "")[:19] if l.get("lastModified") else ""),
                                    "Type":     l.get("type", ""),
                                })
                            st.metric("Objects", len(obj_rows))
                            st.dataframe(pd.DataFrame(obj_rows), use_container_width=True, hide_index=True)
                        except Exception:
                            st.code(r["out"])
                    else:
                        st.info("No objects found or bucket doesn't exist")
                else:
                    st.warning("Enter a bucket name")

            st.divider()
            st.markdown("##### Delete Object")
            del_obj_bucket = st.text_input("Bucket", key="del_obj_bkt", placeholder="my-bucket")
            del_obj_key    = st.text_input("Object key", key="del_obj_key", placeholder="path/to/file.txt")
            if st.button("🗑 Delete Object", type="secondary"):
                if del_obj_bucket and del_obj_key:
                    r = mc(f"rm localmin/{del_obj_bucket}/{del_obj_key}")
                    if r["ok"]:
                        st.success(f"Deleted '{del_obj_key}'")
                    else:
                        st.error(r["err"] or "Delete failed")
                else:
                    st.warning("Enter bucket and object key")
        elif not MC:
            st.info("`mc` not installed — `brew install minio/stable/mc`")
        else:
            st.info("MinIO unreachable on port 30920")

    with tab3:
        if minio_alive and MC:
            minio_ensure_alias()
            st.markdown("##### Upload File to MinIO")
            up_bucket = st.text_input("Destination bucket", placeholder="my-bucket", key="up_bucket")
            up_prefix = st.text_input("Object prefix / folder (optional)", placeholder="uploads/", key="up_prefix")
            up_file   = st.file_uploader("Choose file to upload", key="up_file_widget")
            if st.button("⬆️ Upload") and up_file and up_bucket:
                import tempfile, os
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(up_file.name)[1]) as tmp:
                    tmp.write(up_file.getvalue())
                    tmp_path = tmp.name
                try:
                    dest_key = f"{up_prefix}{up_file.name}" if up_prefix else up_file.name
                    r = mc(f"cp '{tmp_path}' localmin/{up_bucket}/{dest_key}")
                    if r["ok"]:
                        st.success(f"Uploaded '{up_file.name}' → {up_bucket}/{dest_key}")
                    else:
                        st.error(r["err"] or "Upload failed")
                finally:
                    os.unlink(tmp_path)
        elif not MC:
            st.info("`mc` not installed — `brew install minio/stable/mc`")
        else:
            st.info("MinIO unreachable on port 30920")

    with tab4:
        if minio_alive:
            m1, m2 = st.columns(2)
            m1.markdown(f"**API URL:** `{MINIO_URL}`")
            m2.markdown(f"**Console URL:** `{MINIO_CONSOLE_URL}`")
            m1.markdown(f"**Access Key:** `{MINIO_ACCESS_KEY}`")
            m2.markdown(f"**Secret Key:** `{MINIO_SECRET_KEY}`")

            st.divider()
            st.markdown("##### Python SDK Example")
            st.code(f"""import boto3

s3 = boto3.client(
    "s3",
    endpoint_url="{MINIO_URL}",
    aws_access_key_id="{MINIO_ACCESS_KEY}",
    aws_secret_access_key="{MINIO_SECRET_KEY}",
)

# List buckets
buckets = s3.list_buckets()["Buckets"]

# Upload a file
s3.upload_file("local.txt", "my-bucket", "remote.txt")

# Download a file
s3.download_file("my-bucket", "remote.txt", "local_copy.txt")
""", language="python")
        else:
            st.info("MinIO unreachable on port 30920")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 15 — NEXUS
# ══════════════════════════════════════════════════════════════════════════════
elif active_page == "🏛️ Nexus Repository":
    page_header("🏛️", "Nexus Repository Manager", f"Artifact repository · {NEXUS_URL}")

    import pandas as pd

    nexus_alive = port_up(30081)
    nm1, nm2, nm3 = st.columns(3)
    nm1.markdown(f"**Nexus:** {status_badge(nexus_alive)}", unsafe_allow_html=True)
    if nexus_alive:
        nm2.link_button("🌐 Open Nexus UI", NEXUS_URL)

    def nexus_get(path, params=None):
        return http_json(f"{NEXUS_URL}/service/rest{path}", auth=NEXUS_AUTH, params=params)

    def nexus_post(path, payload):
        try:
            import httpx
            r = httpx.post(f"{NEXUS_URL}/service/rest{path}", json=payload, auth=NEXUS_AUTH, timeout=10)
            return r.status_code, r.text
        except Exception as e:
            return 0, str(e)

    def nexus_delete(path):
        try:
            import httpx
            r = httpx.delete(f"{NEXUS_URL}/service/rest{path}", auth=NEXUS_AUTH, timeout=10)
            return r.status_code, r.text
        except Exception as e:
            return 0, str(e)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📦 Repositories", "🔍 Search", "⬆️ Upload", "🗑 Manage", "⚙️ System"
    ])

    with tab1:
        if nexus_alive:
            if st.button("🔄 Refresh", key="nexus_repo_ref"):
                st.cache_data.clear()

            @st.cache_data(ttl=60)
            def get_nexus_repos():
                return nexus_get("/v1/repositories")

            data = get_nexus_repos()
            if data:
                st.metric("Total Repositories", len(data))
                rows = []
                for r in data:
                    rows.append({
                        "Name":   r.get("name", ""),
                        "Format": r.get("format", ""),
                        "Type":   r.get("type", ""),
                        "URL":    r.get("url", ""),
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                # Group by format
                formats = {}
                for r in data:
                    fmt = r.get("format", "other")
                    formats[fmt] = formats.get(fmt, 0) + 1
                fv_cols = st.columns(min(len(formats), 5))
                for i, (fmt, count) in enumerate(sorted(formats.items(), key=lambda x: -x[1])):
                    fv_cols[i % len(fv_cols)].metric(fmt.capitalize(), count)

                st.divider()
                st.markdown("##### Create Repository")
                with st.form("nexus_create_repo"):
                    nr_name   = st.text_input("Repository name", placeholder="my-npm-hosted")
                    nr_format = st.selectbox("Format", ["maven2", "npm", "pypi", "docker", "raw", "helm"])
                    nr_type   = st.selectbox("Type", ["hosted", "proxy", "group"])
                    nr_version = st.selectbox("Version Policy (Maven)", ["RELEASE", "SNAPSHOT", "MIXED"])
                    if st.form_submit_button("➕ Create Repository"):
                        if nr_format == "maven2":
                            payload = {
                                "name": nr_name,
                                "online": True,
                                "storage": {"blobStoreName": "default", "strictContentTypeValidation": True, "writePolicy": "allow_once"},
                                "maven": {"versionPolicy": nr_version, "layoutPolicy": "STRICT"},
                            }
                            code, resp = nexus_post(f"/v1/repositories/{nr_format}/{nr_type}", payload)
                        else:
                            payload = {
                                "name": nr_name,
                                "online": True,
                                "storage": {"blobStoreName": "default", "strictContentTypeValidation": True},
                            }
                            if nr_type == "hosted":
                                payload["storage"]["writePolicy"] = "allow_once"
                            code, resp = nexus_post(f"/v1/repositories/{nr_format}/{nr_type}", payload)
                        if code in (200, 201, 204):
                            st.success(f"Repository '{nr_name}' created")
                            st.cache_data.clear()
                        else:
                            st.error(f"Failed (HTTP {code}): {resp}")
            else:
                st.info("No repositories found or access denied")
        else:
            st.info("Nexus unreachable on port 30081")

    with tab2:
        if nexus_alive:
            sq1, sq2, sq3 = st.columns([2, 1, 1])
            search_q   = sq1.text_input("Search components", placeholder="e.g. spring-boot, junit")
            search_fmt = sq2.selectbox("Format filter", ["(all)", "maven2", "npm", "pypi", "raw"])
            search_ver = sq3.text_input("Version", placeholder="1.0.0")
            if st.button("🔍 Search", type="primary"):
                params = {"q": search_q}
                if search_fmt != "(all)":
                    params["format"] = search_fmt
                if search_ver:
                    params["version"] = search_ver
                data = nexus_get("/v1/search", params=params)
                if data and data.get("items"):
                    rows = []
                    for item in data["items"][:100]:
                        rows.append({
                            "Repository": item.get("repository", ""),
                            "Format":     item.get("format", ""),
                            "Group":      item.get("group", ""),
                            "Name":       item.get("name", ""),
                            "Version":    item.get("version", ""),
                        })
                    st.metric("Results", len(rows))
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                else:
                    st.info("No components found")
        else:
            st.info("Nexus unreachable")

    with tab3:
        if nexus_alive:
            st.markdown("##### Upload Artifact (Raw / Maven)")
            upload_format = st.selectbox("Repository format", ["raw", "maven2"], key="up_fmt")

            repos_for_upload = nexus_get("/v1/repositories")
            if repos_for_upload:
                fmt_repos = [r["name"] for r in repos_for_upload if r.get("format") == upload_format and r.get("type") == "hosted"]
            else:
                fmt_repos = []

            sel_upload_repo = st.selectbox("Target repository", fmt_repos if fmt_repos else ["(no hosted repos found)"], key="up_repo")
            up_artifact = st.file_uploader("Choose artifact file", key="nexus_up_file")

            if upload_format == "raw":
                up_dir = st.text_input("Directory path in repo", placeholder="releases/myapp/1.0", key="up_dir")
                if st.button("⬆️ Upload") and up_artifact and sel_upload_repo and sel_upload_repo != "(no hosted repos found)":
                    import tempfile, os
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(up_artifact.name)[1]) as tmp:
                        tmp.write(up_artifact.getvalue())
                        tmp_path = tmp.name
                    try:
                        import httpx
                        with open(tmp_path, "rb") as f:
                            r = httpx.post(
                                f"{NEXUS_URL}/service/rest/v1/components?repository={sel_upload_repo}",
                                auth=NEXUS_AUTH,
                                data={"raw.directory": up_dir or "/", "raw.asset1.filename": up_artifact.name},
                                files={"raw.asset1": (up_artifact.name, f)},
                                timeout=30,
                            )
                        if r.status_code in (200, 201, 204):
                            st.success(f"Uploaded '{up_artifact.name}' to '{sel_upload_repo}'")
                        else:
                            st.error(f"Failed (HTTP {r.status_code}): {r.text[:200]}")
                    finally:
                        os.unlink(tmp_path)
            else:
                ug1, ug2, ug3 = st.columns(3)
                mvn_group   = ug1.text_input("Group ID",    placeholder="com.example")
                mvn_art     = ug2.text_input("Artifact ID", placeholder="my-app")
                mvn_ver     = ug3.text_input("Version",     placeholder="1.0.0")
                if st.button("⬆️ Upload Maven") and up_artifact and sel_upload_repo and sel_upload_repo != "(no hosted repos found)":
                    import tempfile, os
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jar") as tmp:
                        tmp.write(up_artifact.getvalue())
                        tmp_path = tmp.name
                    try:
                        import httpx
                        with open(tmp_path, "rb") as f:
                            r = httpx.post(
                                f"{NEXUS_URL}/service/rest/v1/components?repository={sel_upload_repo}",
                                auth=NEXUS_AUTH,
                                data={
                                    "maven2.groupId":    mvn_group,
                                    "maven2.artifactId": mvn_art,
                                    "maven2.version":    mvn_ver,
                                    "maven2.asset1.extension": "jar",
                                },
                                files={"maven2.asset1": (up_artifact.name, f)},
                                timeout=30,
                            )
                        if r.status_code in (200, 201, 204):
                            st.success(f"Uploaded Maven artifact to '{sel_upload_repo}'")
                        else:
                            st.error(f"Failed (HTTP {r.status_code}): {r.text[:200]}")
                    finally:
                        os.unlink(tmp_path)
        else:
            st.info("Nexus unreachable on port 30081")

    with tab4:
        if nexus_alive:
            repos_del = nexus_get("/v1/repositories")
            if repos_del:
                all_repo_names = [r["name"] for r in repos_del]
                st.markdown("##### Delete Repository")
                del_repo = st.selectbox("Repository to delete", all_repo_names, key="del_repo_sel")
                del_repo_confirm = st.text_input("Type repository name to confirm", key="del_repo_confirm")
                if st.button("🗑 Delete Repository", type="secondary"):
                    if del_repo_confirm.strip() == del_repo:
                        code, resp = nexus_delete(f"/v1/repositories/{del_repo}")
                        if code in (200, 204):
                            st.success(f"Repository '{del_repo}' deleted")
                            st.cache_data.clear()
                        else:
                            st.error(f"Failed (HTTP {code}): {resp}")
                    else:
                        st.error("Repository name doesn't match")

                st.divider()
                st.markdown("##### Delete Component")
                comp_repo = st.selectbox("Repository", all_repo_names, key="comp_repo_del")
                comp_name = st.text_input("Component name (exact)", key="comp_name_del", placeholder="my-app")
                if st.button("🔍 Find & Delete Component") and comp_name:
                    data = nexus_get("/v1/search", params={"repository": comp_repo, "name": comp_name})
                    if data and data.get("items"):
                        for item in data["items"]:
                            comp_id = item.get("id", "")
                            if comp_id:
                                code, resp = nexus_delete(f"/v1/components/{comp_id}")
                                st.write(f"{'✅' if code in (200,204) else '❌'} {item.get('name','')}:{item.get('version','')} (HTTP {code})")
                    else:
                        st.info("Component not found")
        else:
            st.info("Nexus unreachable on port 30081")

    with tab5:
        if nexus_alive:
            status_data = nexus_get("/v1/status/writable")
            if status_data is not None:
                st.success("Nexus is writable and healthy")
            else:
                status_ro = nexus_get("/v1/status")
                if status_ro is not None:
                    st.warning("Nexus is up but in read-only mode")
                else:
                    st.error("Cannot reach Nexus status endpoint")

            # Blob stores
            blobs = nexus_get("/v1/blobstores")
            if blobs:
                st.markdown("##### Blob Stores")
                st.dataframe(pd.DataFrame([{
                    "Name":         b.get("name", ""),
                    "Type":         b.get("type", ""),
                    "Available MB": round((b.get("availableSpaceInBytes", 0) or 0) / 1024 / 1024),
                    "Blob Count":   b.get("blobCount", 0),
                    "Total MB":     round((b.get("totalSizeInBytes", 0) or 0) / 1024 / 1024),
                } for b in blobs]), use_container_width=True, hide_index=True)

            # Active tasks
            tasks = nexus_get("/v1/tasks")
            if tasks and tasks.get("items"):
                st.markdown("##### Scheduled Tasks")
                task_rows = []
                for t in tasks["items"][:20]:
                    task_rows.append({
                        "Name":        t.get("name", ""),
                        "Type":        t.get("type", ""),
                        "State":       t.get("currentState", ""),
                        "Last Run":    (t.get("lastRun", "")[:19] if t.get("lastRun") else "—"),
                        "Next Run":    (t.get("nextRun", "")[:19] if t.get("nextRun") else "—"),
                    })
                st.dataframe(pd.DataFrame(task_rows), use_container_width=True, hide_index=True)
        else:
            st.info("Nexus unreachable on port 30081")
