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

    if "active_page" not in st.session_state:
        st.session_state["active_page"] = "🏠 Dashboard"

    # ── Strip status-dot prefix from radio labels ─────────────────────────────
    def _strip_dot(label):
        if not label:
            return label
        for dot in ("🟢 ", "🔴 ", "🔵 "):
            if label.startswith(dot):
                return label[len(dot):]
        return label

    # ── on_change: only update active_page when a real value is selected ──────
    def _nav(key):
        val = st.session_state.get(key)
        if val:
            st.session_state["active_page"] = _strip_dot(val)

    # ── Live status dots ──────────────────────────────────────────────────────
    def _dot(port, host="localhost"):
        if port == 0:
            return "🔵"
        return "🟢" if port_up(port, host=host) else "🔴"

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

    # URL param support (screenshot automation)
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

    # ── Navigation radio groups ───────────────────────────────────────────────
    # Overview: index=0  →  Dashboard selected by default
    # All others: index=None  →  nothing selected (unchecked) by default

    _grp_header("Overview")
    st.radio("Overview", ["🏠 Dashboard"], key="nav_overview", index=0,
             label_visibility="collapsed", on_change=_nav, args=("nav_overview",))

    _grp_header("Infrastructure")
    st.radio("Infrastructure", ["🐳 Docker", "☸️ Kubernetes", "🌍 Terraform"],
             key="nav_infra", index=None,
             label_visibility="collapsed", on_change=_nav, args=("nav_infra",))

    _grp_header("CI / CD")
    st.radio("CI/CD",
             [f"{_dj} ⚙️ Jenkins", f"{_ds} 🔍 SonarQube", f"{_da} 🔀 ArgoCD"],
             key="nav_cicd", index=None,
             label_visibility="collapsed", on_change=_nav, args=("nav_cicd",))

    _grp_header("Security")
    st.radio("Security",
             [f"🔵 🛡️ Trivy Scanner", f"{_dv} 🔐 Vault Secrets"],
             key="nav_sec", index=None,
             label_visibility="collapsed", on_change=_nav, args=("nav_sec",))

    _grp_header("Observability")
    st.radio("Observability",
             [f"{_dp} 📊 Prometheus & Grafana", f"{_dl} 📜 Loki Logs"],
             key="nav_obs", index=None,
             label_visibility="collapsed", on_change=_nav, args=("nav_obs",))

    _grp_header("Deployment")
    st.radio("Deployment", ["🔵 ⛵ Helm Manager"],
             key="nav_dep", index=None,
             label_visibility="collapsed", on_change=_nav, args=("nav_dep",))

    _grp_header("Storage & Registry")
    st.radio("Storage",
             [f"{_dreg} 📦 Container Registry",
              f"{_dm} 🗄️ MinIO Storage",
              f"{_dn} 🏛️ Nexus Repository"],
             key="nav_stor", index=None,
             label_visibility="collapsed", on_change=_nav, args=("nav_stor",))

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

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🟢 Pods", "📦 Deployments", "🌐 Services", "📋 Events", "📜 Logs"])

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


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — JENKINS
# ══════════════════════════════════════════════════════════════════════════════
elif active_page == "⚙️ Jenkins":
    page_header("⚙️", "Jenkins CI/CD", f"Pipeline automation · {JENKINS_URL}")

    if not port_up(30080):
        st.info("Jenkins unreachable — check if the pod is running: `kubectl get pods -n devops`")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["📋 Jobs", "🔨 Build History", "⚡ Trigger"])

    with tab1:
        @st.cache_data(ttl=30)
        def get_jenkins_jobs():
            return http_json(
                f"{JENKINS_URL}/api/json?tree=jobs[name,color,lastBuild[number,result,timestamp,duration,url]]",
                auth=JENKINS_AUTH
            )

        data = get_jenkins_jobs()
        if data and data.get("jobs"):
            import pandas as pd
            rows = []
            for job in data["jobs"]:
                lb = job.get("lastBuild") or {}
                result = lb.get("result") or ("BUILDING" if lb else "—")
                rows.append({
                    "Job Name":   job.get("name", ""),
                    "Status":     result,
                    "Build #":    lb.get("number", ""),
                    "Duration":   f"{int(lb.get('duration', 0)/1000)}s" if lb.get("duration") else "",
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            success = sum(1 for r in rows if r["Status"] == "SUCCESS")
            failed  = sum(1 for r in rows if r["Status"] == "FAILURE")
            jm1, jm2, jm3 = st.columns(3)
            jm1.metric("Total Jobs", len(rows))
            jm2.metric("SUCCESS", success)
            jm3.metric("FAILURE", failed)
        else:
            st.info("No jobs found or Jenkins unreachable")

    with tab2:
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
                        import datetime
                        ts = b.get("timestamp", 0) / 1000
                        builds.append({
                            "Job":      job.get("name", ""),
                            "Build #":  b.get("number", ""),
                            "Result":   b.get("result") or "BUILDING",
                            "Duration": f"{int(b.get('duration', 0)/1000)}s",
                            "Started":  datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "",
                        })
            return sorted(builds, key=lambda x: x.get("Started", ""), reverse=True)[:30]

        builds = get_all_builds()
        if builds:
            import pandas as pd
            st.dataframe(pd.DataFrame(builds), use_container_width=True, hide_index=True)
        else:
            st.info("No build history found")

    with tab3:
        data2 = http_json(f"{JENKINS_URL}/api/json?tree=jobs[name]", auth=JENKINS_AUTH)
        job_names = [j["name"] for j in (data2.get("jobs") or [])] if data2 else []
        if job_names:
            sel_job = st.selectbox("Select job to trigger", job_names)
            params_input = st.text_area("Build parameters (KEY=VALUE per line, optional)")
            if st.button("🚀 Trigger Build", type="primary"):
                crumb = jenkins_crumb()
                params = {}
                if params_input.strip():
                    for line in params_input.strip().splitlines():
                        if "=" in line:
                            k, v = line.split("=", 1)
                            params[k.strip()] = v.strip()
                if params:
                    code, resp = http_post(
                        f"{JENKINS_URL}/job/{sel_job}/buildWithParameters",
                        auth=JENKINS_AUTH, data=params, headers=crumb
                    )
                else:
                    code, resp = http_post(
                        f"{JENKINS_URL}/job/{sel_job}/build",
                        auth=JENKINS_AUTH, data={}, headers=crumb
                    )
                if code in (200, 201):
                    st.success(f"Build triggered for {sel_job}")
                else:
                    st.error(f"Failed to trigger build (HTTP {code}): {resp}")
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

    tab1, tab2, tab3 = st.tabs(["📊 Projects", "🐛 Issues", "⚙️ System"])

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


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — TERRAFORM
# ══════════════════════════════════════════════════════════════════════════════
elif active_page == "🌍 Terraform":
    page_header("🌍", "Terraform Manager", f"Infrastructure as Code · {TF_WORKDIR}")

    if not shutil.which("terraform"):
        st.warning("Terraform not installed — run `brew install terraform`")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["📋 State", "🔨 Operations", "📤 Outputs"])

    with tab1:
        @st.cache_data(ttl=60)
        def tf_state():
            return tf("terraform state list")

        r = tf_state()
        if r["ok"] and r["out"]:
            lines = r["out"].splitlines()
            st.metric("Resources in state", len(lines))
            import pandas as pd
            st.dataframe(pd.DataFrame({"Resource": lines}), use_container_width=True, hide_index=True)
        else:
            st.info("No state found — run `terraform init` first")

        @st.cache_data(ttl=60)
        def tf_ver():
            return tf("terraform version -json")

        ver_r = tf_ver()
        if ver_r["ok"]:
            try:
                ver_data = json.loads(ver_r["out"])
                st.markdown(f"**Terraform Version:** `{ver_data.get('terraform_version', '?')}`")
            except Exception:
                pass

    with tab2:
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("⚙️ Init"):
            with st.spinner("Running terraform init..."):
                r = tf("terraform init")
            show(r, "Initialized successfully")
        if c2.button("✅ Validate"):
            with st.spinner("Validating..."):
                r = tf("terraform validate")
            show(r, "Configuration is valid")
        if c3.button("📋 Plan"):
            with st.spinner("Planning..."):
                r = tf("terraform plan")
            st.code(r["out"] or r["err"], language="bash")
        if c4.button("🚀 Apply"):
            with st.spinner("Applying (auto-approve)..."):
                r = tf("terraform apply -auto-approve")
            show(r)

        st.divider()
        st.markdown("##### Destroy")
        st.warning("This will destroy all managed resources.")
        if st.button("💥 Destroy (auto-approve)", type="secondary"):
            with st.spinner("Destroying..."):
                r = tf("terraform destroy -auto-approve")
            show(r)

    with tab3:
        if st.button("📤 Fetch Outputs"):
            with st.spinner("Fetching outputs..."):
                r = tf("terraform output -json")
            if r["ok"] and r["out"]:
                try:
                    st.json(json.loads(r["out"]))
                except Exception:
                    st.code(r["out"])
            else:
                st.info("No outputs defined or state is empty")


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

    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Targets", "🚨 Alerts", "🔍 Query", "📊 Grafana"])

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

    tab1, tab2, tab3 = st.tabs(["📱 Applications", "📁 Repositories", "🔄 Sync"])

    with tab1:
        apps_data = argo_get("/api/v1/applications")
        if apps_data and apps_data.get("items"):
            apps = apps_data["items"]
            import pandas as pd
            rows = []
            for app in apps:
                status = app.get("status", {})
                rows.append({
                    "Name":        app.get("metadata", {}).get("name", ""),
                    "Project":     app.get("spec", {}).get("project", ""),
                    "Sync Status": status.get("sync", {}).get("status", ""),
                    "Health":      status.get("health", {}).get("status", ""),
                    "Repo":        app.get("spec", {}).get("source", {}).get("repoURL", ""),
                    "Namespace":   app.get("spec", {}).get("destination", {}).get("namespace", ""),
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            synced = sum(1 for r in rows if r["Sync Status"] == "Synced")
            healthy = sum(1 for r in rows if r["Health"] == "Healthy")
            am1, am2, am3 = st.columns(3)
            am1.metric("Total Apps", len(rows))
            am2.metric("Synced", synced)
            am3.metric("Healthy", healthy)
        else:
            st.info("No ArgoCD applications found")

    with tab2:
        repos_data = argo_get("/api/v1/repositories")
        if repos_data and repos_data.get("items"):
            import pandas as pd
            repos = repos_data["items"]
            st.dataframe(pd.DataFrame([{
                "Repo": r.get("repo", ""),
                "Type": r.get("type", "git"),
                "Connected": r.get("connectionState", {}).get("status", ""),
            } for r in repos]), use_container_width=True, hide_index=True)
        else:
            st.info("No repositories configured")

    with tab3:
        apps_data2 = argo_get("/api/v1/applications")
        if apps_data2 and apps_data2.get("items"):
            app_names = [a["metadata"]["name"] for a in apps_data2["items"]]
            sel_app = st.selectbox("Select application to sync", app_names)
            dry_run = st.checkbox("Dry run", value=False)
            prune = st.checkbox("Prune resources", value=False)
            if st.button("🔀 Sync Application", type="primary"):
                payload = {"dryRun": dry_run, "prune": prune, "revision": "HEAD"}
                code, resp = argo_post(f"/api/v1/applications/{sel_app}/sync", payload)
                if code == 200:
                    st.success(f"Sync triggered for {sel_app}")
                else:
                    st.error(f"Sync failed (HTTP {code}): {resp}")

            if st.button("🔁 Sync All Apps"):
                for app_name in app_names:
                    code, _ = argo_post(f"/api/v1/applications/{app_name}/sync", {"revision": "HEAD"})
                    if code == 200:
                        st.success(f"✓ {app_name}")
                    else:
                        st.error(f"✗ {app_name} (HTTP {code})")
        else:
            st.info("No applications to sync")


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

    tab1, tab2, tab3 = st.tabs(["🖼️ Image Scan", "📁 IaC Scan", "☸️ K8s Scan"])

    with tab1:
        image_input = st.text_input("Image to scan", value="nginx:latest", placeholder="e.g. nginx:latest, python:3.11")
        severity = st.multiselect("Severity", ["CRITICAL", "HIGH", "MEDIUM", "LOW"], default=["CRITICAL", "HIGH"])
        if st.button("🔍 Scan Image", type="primary") and image_input:
            sev_str = ",".join(severity) if severity else "CRITICAL,HIGH"
            with st.spinner(f"Scanning {image_input}..."):
                r = shell(f"trivy image --format json --severity {sev_str} {image_input}")
            if r["ok"] or r["out"]:
                try:
                    data = json.loads(r["out"])
                    results = data.get("Results", [])
                    total_vulns = 0
                    for result in results:
                        vulns = result.get("Vulnerabilities") or []
                        total_vulns += len(vulns)
                        if vulns:
                            st.markdown(f"**{result.get('Target', '')}** — {len(vulns)} vulnerabilities")
                            import pandas as pd
                            rows = [{
                                "CVE":         v.get("VulnerabilityID", ""),
                                "Package":     v.get("PkgName", ""),
                                "Installed":   v.get("InstalledVersion", ""),
                                "Fixed":       v.get("FixedVersion", ""),
                                "Severity":    v.get("Severity", ""),
                                "Title":       v.get("Title", "")[:60],
                            } for v in vulns]
                            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                    if total_vulns == 0:
                        st.success(f"No vulnerabilities found in {image_input}")
                    else:
                        st.warning(f"Found {total_vulns} total vulnerabilities")
                except Exception:
                    st.code(r["out"][:3000], language="bash")
            else:
                st.error(r["err"][:500] if r["err"] else "Scan failed")

    with tab2:
        path_input = st.text_input("Directory/file to scan", value=TF_WORKDIR)
        if st.button("🔍 Scan IaC"):
            with st.spinner("Scanning IaC configuration..."):
                r = shell(f"trivy config --format json {path_input}")
            if r["out"]:
                try:
                    data = json.loads(r["out"])
                    results = data.get("Results", [])
                    for result in results:
                        misconfigs = result.get("Misconfigurations") or []
                        if misconfigs:
                            import pandas as pd
                            st.markdown(f"**{result.get('Target', '')}** — {len(misconfigs)} findings")
                            rows = [{
                                "ID":       m.get("ID", ""),
                                "Type":     m.get("Type", ""),
                                "Severity": m.get("Severity", ""),
                                "Title":    m.get("Title", "")[:60],
                                "Status":   m.get("Status", ""),
                            } for m in misconfigs]
                            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                    if not any((r.get("Misconfigurations") or []) for r in results):
                        st.success("No misconfigurations found")
                except Exception:
                    st.code(r["out"][:2000])
            else:
                st.error(r["err"][:500] if r["err"] else "Scan failed")

    with tab3:
        st.info("K8s cluster scanning requires cluster access and can take several minutes.")
        if st.button("🔍 Scan K8s Cluster"):
            with st.spinner("Scanning cluster (this may take a while)..."):
                r = shell("trivy k8s --report summary --format json cluster")
            if r["out"]:
                st.code(r["out"][:5000], language="json")
            else:
                st.error(r["err"][:500] if r["err"] else "Scan failed")


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

    tab1, tab2, tab3 = st.tabs(["🏥 Health", "🔑 Secrets", "⚙️ Auth Methods"])

    with tab1:
        health = vault_api("v1/sys/health")
        if health:
            st.markdown(f"**Status:** {status_badge(not health.get('sealed', True), 'Unsealed', 'Sealed')}", unsafe_allow_html=True)
            vm1, vm2, vm3 = st.columns(3)
            vm1.metric("Initialized", str(health.get("initialized", "?")))
            vm2.metric("Sealed",      str(health.get("sealed", "?")))
            vm3.metric("Version",     health.get("version", "?"))

            cluster = vault_api("v1/sys/leader")
            if cluster:
                st.markdown(f"**HA Enabled:** `{cluster.get('ha_enabled', False)}`")
        else:
            st.warning("Could not fetch Vault health")

    with tab2:
        mounts = vault_api("v1/sys/mounts")
        if mounts:
            mount_paths = [k.rstrip("/") for k in mounts.get("data", mounts).keys()
                           if not k.startswith("sys") and not k.startswith("auth")]
            if mount_paths:
                sel_mount = st.selectbox("Secret mount", mount_paths)
                secret_path = st.text_input("Secret path (relative to mount)", value="")
                sp1, sp2 = st.columns(2)
                if sp1.button("🔍 List Secrets"):
                    data = vault_api(f"v1/{sel_mount}/metadata/{secret_path}?list=true")
                    if data:
                        keys = data.get("data", {}).get("keys", [])
                        if keys:
                            import pandas as pd
                            st.dataframe(pd.DataFrame({"Secret Keys": keys}), use_container_width=True, hide_index=True)
                        else:
                            st.info("No keys found at this path")
                    else:
                        st.info("Could not list secrets (check path/permissions)")
                if sp2.button("🔓 Read Secret") and secret_path:
                    data = vault_api(f"v1/{sel_mount}/data/{secret_path}")
                    if data:
                        st.json(data.get("data", {}).get("data", {}))
                    else:
                        st.error("Secret not found or access denied")
            else:
                st.info("No KV mounts found")
        else:
            st.info("Could not list secret mounts")

    with tab3:
        auth_methods = vault_api("v1/sys/auth")
        if auth_methods:
            data = auth_methods.get("data", auth_methods)
            import pandas as pd
            rows = []
            for path, info in data.items():
                rows.append({
                    "Path":        path,
                    "Type":        info.get("type", ""),
                    "Description": info.get("description", ""),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("Could not fetch auth methods")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 11 — LOKI LOGS
# ══════════════════════════════════════════════════════════════════════════════
elif active_page == "📜 Loki Logs":
    page_header("📜", "Loki Log Aggregation", f"Distributed log management · {LOKI_URL}")

    if not port_up(30310):
        st.info("Loki unreachable on port 30310 — check if the pod is running")
        st.stop()

    tab1, tab2 = st.tabs(["🔍 Query Logs", "📊 Labels"])

    with tab1:
        label_data = http_json(f"{LOKI_URL}/loki/api/v1/labels")
        labels = (label_data or {}).get("data", [])

        col_q, col_t = st.columns([3, 1])
        with col_q:
            query = st.text_input("LogQL Query", value='{namespace="devops"}', placeholder='{app="jenkins"}')
        with col_t:
            limit = st.number_input("Limit", min_value=10, max_value=1000, value=100)

        if st.button("🔍 Query", type="primary"):
            import time as _time
            now_ns = int(_time.time() * 1e9)
            start_ns = now_ns - 3600 * int(1e9)
            data = http_json(
                f"{LOKI_URL}/loki/api/v1/query_range",
                params={"query": query, "start": start_ns, "end": now_ns, "limit": limit}
            )
            if data and data.get("status") == "success":
                results = data.get("data", {}).get("result", [])
                if results:
                    all_lines = []
                    for stream in results:
                        labels_str = str(stream.get("stream", {}))
                        for ts, line in stream.get("values", []):
                            import datetime
                            dt = datetime.datetime.fromtimestamp(int(ts) / 1e9).strftime("%H:%M:%S")
                            all_lines.append({"Time": dt, "Labels": labels_str[:40], "Log": line[:200]})
                    if all_lines:
                        import pandas as pd
                        all_lines.sort(key=lambda x: x["Time"])
                        st.dataframe(pd.DataFrame(all_lines), use_container_width=True, hide_index=True)
                    else:
                        st.info("No log lines in the result")
                else:
                    st.info("No streams matched the query")
            else:
                st.warning("Query returned no data or Loki is not ready")

    with tab2:
        label_data = http_json(f"{LOKI_URL}/loki/api/v1/labels")
        if label_data and label_data.get("data"):
            labels = label_data["data"]
            sel_label = st.selectbox("Label", labels)
            if sel_label:
                val_data = http_json(f"{LOKI_URL}/loki/api/v1/label/{sel_label}/values")
                if val_data and val_data.get("data"):
                    import pandas as pd
                    st.dataframe(pd.DataFrame({"Values": val_data["data"]}), use_container_width=True, hide_index=True)
        else:
            st.info("No labels found — Loki may not have received any logs yet")


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

    tab1, tab2, tab3 = st.tabs(["📦 Releases", "🗂️ Repos", "🔍 Search"])

    with tab1:
        ns_h = st.text_input("Namespace", value="devops", key="helm_ns")
        r = shell(f"helm list -n {ns_h} --output json")
        if r["ok"] and r["out"] and r["out"] != "[]":
            try:
                releases = json.loads(r["out"])
                import pandas as pd
                df = pd.DataFrame([{
                    "Name":      rel.get("name", ""),
                    "Namespace": rel.get("namespace", ""),
                    "Revision":  rel.get("revision", ""),
                    "Status":    rel.get("status", ""),
                    "Chart":     rel.get("chart", ""),
                    "App Ver":   rel.get("app_version", ""),
                    "Updated":   rel.get("updated", "")[:16],
                } for rel in releases])
                st.dataframe(df, use_container_width=True, hide_index=True)

                sel_rel = st.selectbox("Release for actions", [r["name"] for r in releases])
                hc1, hc2 = st.columns(2)
                if hc1.button("🗑 Uninstall"):
                    with st.spinner(f"Uninstalling {sel_rel}..."):
                        res = shell(f"helm uninstall {sel_rel} -n {ns_h}")
                    show(res)
                if hc2.button("🔄 Rollback"):
                    res = shell(f"helm rollback {sel_rel} -n {ns_h}")
                    show(res)
            except Exception:
                st.code(r["out"])
        else:
            st.info(f"No Helm releases in namespace '{ns_h}'")

    with tab2:
        r = shell("helm repo list --output json")
        if r["ok"] and r["out"] and r["out"] != "[]":
            try:
                repos = json.loads(r["out"])
                import pandas as pd
                st.dataframe(pd.DataFrame([{
                    "Name": repo.get("name", ""),
                    "URL":  repo.get("url", ""),
                } for repo in repos]), use_container_width=True, hide_index=True)
            except Exception:
                st.code(r["out"])
        else:
            st.info("No Helm repos configured")

        st.divider()
        st.markdown("##### Add Repository")
        with st.form("add_repo"):
            repo_name = st.text_input("Repo name")
            repo_url  = st.text_input("Repo URL", placeholder="https://charts.helm.sh/stable")
            if st.form_submit_button("➕ Add Repo") and repo_name and repo_url:
                with st.spinner("Adding repo..."):
                    res = shell(f"helm repo add {repo_name} {repo_url} && helm repo update")
                show(res, f"Repo '{repo_name}' added successfully")

    with tab3:
        search_term = st.text_input("Search charts", placeholder="nginx, prometheus, postgres...")
        if st.button("🔍 Search") and search_term:
            r = shell(f"helm search hub {search_term} --max-col-width=60 --output json")
            if r["ok"] and r["out"] and r["out"] != "null":
                try:
                    charts = json.loads(r["out"])
                    import pandas as pd
                    st.dataframe(pd.DataFrame([{
                        "URL":         c.get("url", ""),
                        "Version":     c.get("version", ""),
                        "App Version": c.get("app_version", ""),
                        "Description": c.get("description", "")[:80],
                    } for c in (charts or [])[:30]]), use_container_width=True, hide_index=True)
                except Exception:
                    st.code(r["out"][:2000])
            else:
                st.info("No charts found")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 13 — CONTAINER REGISTRY
# ══════════════════════════════════════════════════════════════════════════════
elif active_page == "📦 Container Registry":
    page_header("📦", "Container Registry", f"Private Docker registry · {REGISTRY_URL}")

    reg_up = port_up(30880, "127.0.0.1")
    st.markdown(f"**Registry API:** {status_badge(reg_up)}", unsafe_allow_html=True)

    if reg_up:
        st.link_button("🌐 Open Registry UI", REGISTRY_UI_URL)

    tab1, tab2 = st.tabs(["📦 Repositories", "🏷️ Tags"])

    with tab1:
        if reg_up:
            @st.cache_data(ttl=30)
            def get_registry_repos():
                return http_json(f"{REGISTRY_URL}/v2/_catalog")

            data = get_registry_repos()
            if data and data.get("repositories"):
                repos = data["repositories"]
                st.metric("Repositories", len(repos))
                import pandas as pd
                st.dataframe(pd.DataFrame({"Repository": repos}), use_container_width=True, hide_index=True)
            else:
                st.info("No repositories in registry yet — push an image to get started")
                st.code(f"""# Push an image to the registry:
docker tag myapp:latest 127.0.0.1:30880/myapp:latest
docker push 127.0.0.1:30880/myapp:latest""", language="bash")
        else:
            st.info("Registry unreachable on port 30880")

    with tab2:
        repo_name = st.text_input("Repository name", placeholder="myapp")
        if st.button("🏷️ List Tags") and repo_name and reg_up:
            data = http_json(f"{REGISTRY_URL}/v2/{repo_name}/tags/list")
            if data and data.get("tags"):
                import pandas as pd
                st.dataframe(pd.DataFrame({"Tag": data["tags"]}), use_container_width=True, hide_index=True)
            else:
                st.info(f"No tags found for '{repo_name}'")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 14 — MINIO
# ══════════════════════════════════════════════════════════════════════════════
elif active_page == "🗄️ MinIO Storage":
    page_header("🗄️", "MinIO Object Storage", f"S3-compatible storage · {MINIO_URL}")

    minio_alive = port_up(30920)
    st.markdown(f"**MinIO API:** {status_badge(minio_alive)}", unsafe_allow_html=True)

    if minio_alive:
        st.link_button("🌐 Open MinIO Console", MINIO_CONSOLE_URL)

    tab1, tab2 = st.tabs(["🪣 Buckets", "ℹ️ Info"])

    with tab1:
        if shutil.which("mc"):
            if st.button("📋 List Buckets"):
                with st.spinner("Fetching buckets..."):
                    r = shell("mc ls local/ --json")
                if r["ok"] and r["out"]:
                    try:
                        lines = [json.loads(l) for l in r["out"].splitlines() if l.strip()]
                        import pandas as pd
                        st.dataframe(pd.DataFrame([{
                            "Bucket":    l.get("key", ""),
                            "Modified":  l.get("lastModified", ""),
                        } for l in lines]), use_container_width=True, hide_index=True)
                    except Exception:
                        st.code(r["out"])
                else:
                    st.info("No buckets found or mc not configured")
        else:
            st.info("MinIO Client (`mc`) not installed — `brew install minio/stable/mc`")
            if minio_alive:
                st.code("""# Configure mc:
mc alias set local http://localhost:30920 minioadmin minioadmin""", language="bash")

    with tab2:
        if minio_alive:
            health = http_json(f"{MINIO_URL}/minio/health/live")
            st.markdown("**API Health:** " + status_badge(health is not None or port_up(30920)), unsafe_allow_html=True)
        st.markdown(f"""
**API Endpoint:** `{MINIO_URL}`
**Console:** `{MINIO_CONSOLE_URL}`
**Default Credentials:** `minioadmin / minioadmin`
        """)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 15 — NEXUS
# ══════════════════════════════════════════════════════════════════════════════
elif active_page == "🏛️ Nexus Repository":
    page_header("🏛️", "Nexus Repository Manager", f"Artifact repository · {NEXUS_URL}")

    nexus_alive = port_up(30081)
    st.markdown(f"**Nexus:** {status_badge(nexus_alive)}", unsafe_allow_html=True)

    if nexus_alive:
        st.link_button("🌐 Open Nexus UI", NEXUS_URL)

    tab1, tab2, tab3 = st.tabs(["📦 Repositories", "🔍 Search", "ℹ️ System"])

    with tab1:
        if nexus_alive:
            @st.cache_data(ttl=60)
            def get_nexus_repos():
                return http_json(f"{NEXUS_URL}/service/rest/v1/repositories", auth=NEXUS_AUTH)

            data = get_nexus_repos()
            if data:
                import pandas as pd
                st.metric("Total Repositories", len(data))
                st.dataframe(pd.DataFrame([{
                    "Name":   r.get("name", ""),
                    "Format": r.get("format", ""),
                    "Type":   r.get("type", ""),
                    "URL":    r.get("url", ""),
                } for r in data]), use_container_width=True, hide_index=True)
            else:
                st.info("No repositories found or access denied")
        else:
            st.info("Nexus unreachable on port 30081")

    with tab2:
        if nexus_alive:
            search_q = st.text_input("Search components", placeholder="e.g. spring-boot, junit")
            if st.button("🔍 Search") and search_q:
                data = http_json(f"{NEXUS_URL}/service/rest/v1/search?q={search_q}", auth=NEXUS_AUTH)
                if data and data.get("items"):
                    import pandas as pd
                    rows = []
                    for item in data["items"][:50]:
                        rows.append({
                            "Repository": item.get("repository", ""),
                            "Format":     item.get("format", ""),
                            "Group":      item.get("group", ""),
                            "Name":       item.get("name", ""),
                            "Version":    item.get("version", ""),
                        })
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                else:
                    st.info("No components found")
        else:
            st.info("Nexus unreachable")

    with tab3:
        if nexus_alive:
            data = http_json(f"{NEXUS_URL}/service/rest/v1/status", auth=NEXUS_AUTH)
            if data:
                st.json(data)
            else:
                system_info = http_json(f"{NEXUS_URL}/service/rest/v1/status/check", auth=NEXUS_AUTH)
                if system_info:
                    st.json(system_info)
                else:
                    st.info("Could not fetch system info")
