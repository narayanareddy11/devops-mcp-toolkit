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

/* Nav buttons — look like plain list items */
[data-testid="stSidebar"] [data-testid="stButton"] > button {
    width: 100% !important;
    text-align: left !important;
    justify-content: flex-start !important;
    background: transparent !important;
    border: 1px solid transparent !important;
    color: #b0c4de !important;
    padding: 4px 10px !important;
    border-radius: 6px !important;
    font-size: 0.83rem !important;
    line-height: 1.5 !important;
    min-height: 0 !important;
    box-shadow: none !important;
    margin: 1px 0 !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] > button:hover {
    background: rgba(79,195,247,0.12) !important;
    border-color: rgba(79,195,247,0.25) !important;
    color: #e0f7fa !important;
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

    # ── Single flat nav: all tools with live status ──────────────────────────────
    # (page_name, port, url, host)
    _NAV_ITEMS = [
        ("🏠 Dashboard",             0,     "",                        ""),
        ("⚙️ Jenkins",              30080, "http://localhost:30080",  "localhost"),
        ("🔍 SonarQube",            30900, "http://localhost:30900",  "localhost"),
        ("🔀 ArgoCD",               30085, "https://localhost:30085", "localhost"),
        ("🛡️ Trivy Scanner",        0,     "",                        ""),
        ("🔐 Vault Secrets",        30200, "http://localhost:30200",  "localhost"),
        ("📊 Prometheus & Grafana", 30090, "http://localhost:30090",  "localhost"),
        ("📜 Loki Logs",            30310, "http://localhost:30310",  "localhost"),
        ("📦 Container Registry",   30880, "http://localhost:30881",  "127.0.0.1"),
        ("🗄️ MinIO Storage",        30921, "http://localhost:30921",  "localhost"),
        ("🏛️ Nexus Repository",     30081, "http://localhost:30081",  "localhost"),
        ("☸️ Kubernetes",           0,     "",                        ""),
        ("🐳 Docker",               0,     "",                        ""),
        ("🌍 Terraform",            0,     "",                        ""),
        ("⛵ Helm Manager",         0,     "",                        ""),
    ]

    st.markdown('<p style="font-size:0.7rem;color:#546e7a;text-transform:uppercase;letter-spacing:0.1em;margin:0.2rem 0 0.4rem 0;">MCP Tools & Services</p>', unsafe_allow_html=True)

    for _page, _port, _url, _host in _NAV_ITEMS:
        if _port > 0:
            _up = port_up(_port, host=_host or "localhost")
            _dot = "🟢" if _up else "🔴"
        else:
            _dot = "🔵"

        _label = f"{_dot}  {_page}"
        if st.button(_label, key=f"nav_{_page}", use_container_width=True):
            st.session_state["active_page"] = _page
            st.rerun()

        # Show URL as a tiny link below web-service buttons
        if _url:
            _short = _url.replace("http://","").replace("https://","")
            st.markdown(
                f'<div style="margin:-6px 0 2px 28px;">'
                f'<a href="{_url}" target="_blank" '
                f'style="color:#546e7a;font-size:0.62rem;text-decoration:none;">{_short}</a>'
                f'</div>',
                unsafe_allow_html=True,
            )

    active_page = st.session_state["active_page"]

    st.divider()
    auto_refresh = st.toggle("⟳ Auto-refresh (30s)", value=False)

if auto_refresh:
    time.sleep(30)
    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if active_page == "🏠 Dashboard":
    page_header("🏠", "DevOps Stack Dashboard", "Live health status of all 15 services running on Kubernetes")

    col_refresh, col_clear, _ = st.columns([1, 1, 5])
    with col_refresh:
        if st.button("🔄 Refresh", type="primary"):
            st.cache_data.clear()
            st.rerun()

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
        r = kube(f"get pods --no-headers", ns=ns)
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
        data = http_json(f"{LOKI_URL}/ready")
        up = port_up(30310)
        return up, "Ready" if up else "Unreachable"

    @st.cache_data(ttl=30)
    def dash_nexus():
        data = http_json(f"{NEXUS_URL}/service/rest/v1/repositories", auth=NEXUS_AUTH)
        up = data is not None
        count = len(data) if data else 0
        return up, count

    # ── Row 1: Core services (5 cols) ─────────────────────────────────────────
    st.markdown("#### Core Services")
    c1, c2, c3, c4, c5 = st.columns(5)

    jen_up, jen_jobs = dash_jenkins()
    c1.markdown(service_card("Jenkins", f"{jen_jobs} Jobs", "CI/CD Server · :30080", jen_up), unsafe_allow_html=True)

    son_up, son_proj = dash_sonar()
    c2.markdown(service_card("SonarQube", f"{son_proj} Projects", "Code Quality · :30900", son_up), unsafe_allow_html=True)

    k8s_up, k8s_pods = dash_k8s_pods()
    c3.markdown(service_card("Kubernetes", f"{k8s_pods} Pods", "devops namespace", k8s_up), unsafe_allow_html=True)

    graf_up, graf_ds = dash_grafana()
    c4.markdown(service_card("Grafana", f"{graf_ds} Datasources", "Visualization · :30030", graf_up), unsafe_allow_html=True)

    argo_up, argo_apps = dash_argocd()
    c5.markdown(service_card("ArgoCD", f"{argo_apps} Apps", "GitOps · :30085", argo_up), unsafe_allow_html=True)

    st.markdown("")

    # ── Row 2: Observability + extras (5 cols) ─────────────────────────────────
    st.markdown("#### Observability & Storage")
    c6, c7, c8, c9, c10 = st.columns(5)

    prom_up, prom_tgts = dash_prometheus()
    c6.markdown(service_card("Prometheus", f"{prom_tgts} Targets", "Metrics · :30090", prom_up), unsafe_allow_html=True)

    vault_up, vault_state = dash_vault()
    c7.markdown(service_card("Vault", vault_state, "Secrets · :30200", vault_up), unsafe_allow_html=True)

    loki_up, loki_state = dash_loki()
    c8.markdown(service_card("Loki", loki_state, "Logs · :30310", loki_up), unsafe_allow_html=True)

    minio_up = port_up(30920)
    c9.markdown(service_card("MinIO", "UP" if minio_up else "DOWN", "Object Storage · :30920", minio_up), unsafe_allow_html=True)

    nex_up, nex_repos = dash_nexus()
    c10.markdown(service_card("Nexus", f"{nex_repos} Repos" if nex_repos else "UP" if nex_up else "DOWN", "Artifacts · :30081", nex_up), unsafe_allow_html=True)

    st.markdown("")

    # ── Row 3: Quick actions ──────────────────────────────────────────────────
    st.markdown("#### Quick Actions")
    qa1, qa2, qa3, qa4, qa5 = st.columns(5)

    with qa1:
        if st.button("🔄 Restart All Pods", use_container_width=True):
            with st.spinner("Restarting deployments..."):
                dep_r = kube("get deployments -o jsonpath='{.items[*].metadata.name}'", ns="devops")
                if dep_r["ok"] and dep_r["out"]:
                    deps = dep_r["out"].strip("'").split()
                    for d in deps:
                        kube(f"rollout restart deployment/{d}", ns="devops")
                    st.success(f"Restarted {len(deps)} deployment(s)")
                else:
                    st.warning("No deployments found in devops namespace")

    with qa2:
        st.link_button("📊 Open Grafana", GRAFANA_URL, use_container_width=True)

    with qa3:
        if st.button("🔀 Sync ArgoCD Apps", use_container_width=True):
            st.info(f"ArgoCD has {argo_apps} app(s). Use ArgoCD page for sync.")

    with qa4:
        if st.button("🧹 Docker Prune", use_container_width=True):
            with st.spinner("Pruning Docker system..."):
                r = docker("system prune -f")
            show(r, "Docker system pruned successfully")

    with qa5:
        st.link_button("🔧 Open Jenkins", JENKINS_URL, use_container_width=True)

    st.divider()

    # ── Row 4: K8s pods table + Jenkins builds ─────────────────────────────────
    left_col, right_col = st.columns(2)

    with left_col:
        st.markdown("##### ☸️ K8s Pods — devops namespace")

        @st.cache_data(ttl=30)
        def get_pods_table():
            r = kube("get pods -o wide --no-headers", ns="devops")
            rows = []
            if r["ok"] and r["out"]:
                for line in r["out"].splitlines():
                    parts = line.split()
                    if len(parts) >= 4:
                        rows.append({
                            "Name":    parts[0],
                            "Status":  parts[2],
                            "Ready":   parts[1],
                            "Restarts": parts[3],
                            "Age":     parts[4] if len(parts) > 4 else "",
                            "Node":    parts[6] if len(parts) > 6 else "",
                        })
            return rows

        pods_rows = get_pods_table()
        if pods_rows:
            import pandas as pd
            df_pods = pd.DataFrame(pods_rows)
            st.dataframe(df_pods, use_container_width=True, hide_index=True)
        else:
            st.info("No pods found in devops namespace — check if cluster is running")

    with right_col:
        st.markdown("##### ⚙️ Recent Jenkins Builds")

        @st.cache_data(ttl=30)
        def get_jenkins_builds():
            jobs_data = http_json(f"{JENKINS_URL}/api/json?tree=jobs[name,lastBuild[number,result,timestamp,duration]]", auth=JENKINS_AUTH)
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

        jbuilds = get_jenkins_builds()
        if jbuilds:
            import pandas as pd
            df_builds = pd.DataFrame(jbuilds[:8])
            st.dataframe(df_builds, use_container_width=True, hide_index=True)
        else:
            st.info("Jenkins unreachable or no builds found")

    st.divider()

    # ── Row 5: Prometheus metrics chart ───────────────────────────────────────
    st.markdown("##### 📈 Pod Resource Usage (Prometheus)")

    @st.cache_data(ttl=60)
    def get_prom_metrics():
        cpu_data = http_json(f"{PROM_URL}/api/v1/query",
                             params={"query": 'sum(rate(container_cpu_usage_seconds_total{namespace="devops",container!=""}[5m])) by (pod)'})
        mem_data = http_json(f"{PROM_URL}/api/v1/query",
                             params={"query": 'sum(container_memory_working_set_bytes{namespace="devops",container!=""}) by (pod)'})
        return cpu_data, mem_data

    if prom_up:
        try:
            cpu_data, mem_data = get_prom_metrics()
            import pandas as pd

            mc1, mc2 = st.columns(2)
            with mc1:
                if cpu_data and cpu_data.get("status") == "success":
                    results = cpu_data["data"]["result"]
                    if results:
                        cpu_df = pd.DataFrame({
                            r["metric"].get("pod", "unknown"): [float(r["value"][1])]
                            for r in results
                        })
                        st.markdown("**CPU Usage (cores)**")
                        st.bar_chart(cpu_df.T, use_container_width=True)
                    else:
                        st.info("No CPU data from Prometheus yet")
                else:
                    st.info("Waiting for Prometheus CPU data")

            with mc2:
                if mem_data and mem_data.get("status") == "success":
                    results = mem_data["data"]["result"]
                    if results:
                        mem_df = pd.DataFrame({
                            r["metric"].get("pod", "unknown"): [float(r["value"][1]) / (1024**2)]
                            for r in results
                        })
                        st.markdown("**Memory Usage (MB)**")
                        st.bar_chart(mem_df.T, use_container_width=True)
                    else:
                        st.info("No memory data from Prometheus yet")
                else:
                    st.info("Waiting for Prometheus memory data")
        except Exception as e:
            st.warning(f"Could not load Prometheus metrics: {e}")
    else:
        st.info("Prometheus unreachable — start it with `kubectl apply -f k8s/prometheus/`")


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
