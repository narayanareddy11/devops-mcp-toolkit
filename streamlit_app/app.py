"""
DevOps MCP Toolkit — Streamlit Control Panel
Visual interface for all 15 MCP servers.
Run: streamlit run streamlit_app/app.py
"""

import streamlit as st
import json
import subprocess
import sys
import time
from pathlib import Path


def show(result: dict, success_msg: str = None):
    """Display success/error based on shell result dict {ok, out, err}."""
    msg = success_msg or result.get("out") or "Done"
    if result["ok"]:
        st.success(msg)
    else:
        st.error(result.get("err") or result.get("out") or "Unknown error")

sys.path.insert(0, str(Path(__file__).parent))
from utils import (
    docker, kube, tf, http_get, http_post, jenkins_crumb,
    service_health, JENKINS_URL, SONAR_URL, JENKINS_AUTH, SONAR_AUTH, TF_WORKDIR,
)

PROM_URL    = "http://localhost:30090"
GRAFANA_URL = "http://localhost:30030"
GRAFANA_AUTH = ("admin", "Admin@123456789@")
ARGOCD_URL  = "https://localhost:30085"
VAULT_URL   = "http://localhost:30200"
VAULT_TOKEN = "root"
LOKI_URL    = "http://localhost:30310"
REGISTRY_URL = "http://127.0.0.1:30880"
REGISTRY_UI_URL = "http://127.0.0.1:30881"
MINIO_URL   = "http://localhost:30920"
MINIO_CONSOLE_URL = "http://localhost:30921"
NEXUS_URL   = "http://localhost:30081"
NEXUS_AUTH  = ("admin", "Admin@123456789@")

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DevOps MCP Toolkit",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.title("🛠️ DevOps MCP Toolkit")
st.sidebar.caption("Control your local DevOps stack via MCP")

page = st.sidebar.radio(
    "Navigate",
    [
        "🏠 Dashboard",
        "🐳 Docker",
        "☸️ Kubernetes",
        "⚙️ Jenkins",
        "🔍 SonarQube",
        "🌍 Terraform",
        "📊 Prometheus & Grafana",
        "🔀 ArgoCD",
        "🛡️ Trivy Scanner",
        "⛵ Helm Manager",
        "🔐 Vault Secrets",
        "📜 Loki Logs",
        "📦 Container Registry",
        "🗄️ MinIO Storage",
        "🏛️ Nexus Repository",
    ],
)

st.sidebar.divider()
st.sidebar.markdown("**🔧 Core Services**")
st.sidebar.markdown(f"[🔧 Jenkins](http://localhost:30080) · [🔍 SonarQube](http://localhost:30900)")
st.sidebar.markdown(f"[📊 Grafana](http://localhost:30030) · [📈 Prometheus](http://localhost:30090)")
st.sidebar.markdown(f"[🔀 ArgoCD](https://localhost:30085)")
st.sidebar.divider()
st.sidebar.markdown("**🆕 New Services**")
st.sidebar.markdown(f"[🔐 Vault](http://localhost:30200) · [📜 Loki](http://localhost:30310)")
st.sidebar.markdown(f"[📦 Registry](http://127.0.0.1:30881) · [🗄️ MinIO](http://localhost:30921)")
st.sidebar.markdown(f"[🏛️ Nexus](http://localhost:30081)")
st.sidebar.divider()
st.sidebar.caption("admin / Admin@123456789@")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Dashboard":
    st.title("🏠 DevOps Stack Dashboard")
    st.caption("Live health status of all services")

    if st.button("🔄 Refresh Health", type="primary"):
        st.cache_data.clear()

    @st.cache_data(ttl=15)
    def get_health():
        return service_health()

    health = get_health()

    # Status cards — row 1: core services
    def status_icon(up): return "🟢" if up else "🔴"
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Docker",     health["docker"]["version"],        delta=status_icon(health["docker"]["up"]))
    col2.metric("Jenkins",    f"{health['jenkins']['jobs']} jobs", delta=status_icon(health["jenkins"]["up"]))
    col3.metric("SonarQube",  health["sonarqube"]["health"],      delta=status_icon(health["sonarqube"]["up"]))
    col4.metric("Kubernetes", health["kubernetes"]["node"],       delta=status_icon(health["kubernetes"]["up"]))
    col5.metric("Terraform",  health["terraform"]["version"],     delta=status_icon(health["terraform"]["up"]))

    # Status cards — row 2: observability + GitOps
    def _port_up(port, ipv4=False):
        import socket
        host = "127.0.0.1" if ipv4 else "localhost"
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        ok = s.connect_ex((host, port)) == 0
        s.close()
        return ok

    import shutil as _sh
    col6, col7, col8, col9 = st.columns(4)
    prom_up  = _port_up(30090)
    col6.metric("Prometheus", ":30090", delta=status_icon(prom_up))
    graf_up  = _port_up(30030)
    col7.metric("Grafana", ":30030", delta=status_icon(graf_up))
    argo_up  = _port_up(30085)
    col8.metric("ArgoCD", ":30085", delta=status_icon(argo_up))
    trivy_ok = bool(_sh.which("trivy"))
    col9.metric("Trivy", "installed" if trivy_ok else "missing", delta=status_icon(trivy_ok))

    # Row 3: new services
    st.divider()
    st.subheader("🆕 New Services")
    col10, col11, col12, col13, col14, col15 = st.columns(6)
    vault_up   = _port_up(30200)
    col10.metric("Vault",    ":30200", delta=status_icon(vault_up))
    loki_up    = _port_up(30310)
    col11.metric("Loki",     ":30310", delta=status_icon(loki_up))
    reg_up     = _port_up(30880, ipv4=True)
    col12.metric("Registry", ":30880", delta=status_icon(reg_up))
    minio_up   = _port_up(30920)
    col13.metric("MinIO",    ":30920", delta=status_icon(minio_up))
    nexus_up   = _port_up(30081)
    col14.metric("Nexus",    ":30081", delta=status_icon(nexus_up))
    helm_ok    = bool(_sh.which("helm"))
    col15.metric("Helm",     "installed" if helm_ok else "missing", delta=status_icon(helm_ok))

    st.divider()

    # Port status — all services
    st.subheader("Port Status — All Services")
    all_ports = {
        "Jenkins:30080":    health["ports"].get("Jenkins:30080", False),
        "SonarQube:30900":  health["ports"].get("SonarQube:30900", False),
        "Prometheus:30090": prom_up,
        "Grafana:30030":    graf_up,
        "ArgoCD:30085":     argo_up,
        "Vault:30200":      vault_up,
        "Loki:30310":       loki_up,
        "Registry:30880":   reg_up,
        "MinIO:30920":      minio_up,
        "Nexus:30081":      nexus_up,
    }
    pcols = st.columns(5)
    for i, (name, open_) in enumerate(all_ports.items()):
        pcols[i % 5].markdown(f"{'🟢' if open_ else '🔴'} **{name}**")

    st.divider()

    # K8s pods
    st.subheader("☸️ K8s Pods — devops namespace")
    pods = kube("get pods -o wide")
    if pods["ok"]:
        st.code(pods["out"], language="bash")
    else:
        st.error(pods["err"])

    # Running containers
    st.subheader("🐳 Running Docker Containers")
    out = docker("ps --format json")
    if out["ok"] and out["out"]:
        containers = [json.loads(l) for l in out["out"].splitlines() if l.strip()]
        if containers:
            st.dataframe(
                [{"Name": c.get("Names"), "Image": c.get("Image"), "Status": c.get("Status")} for c in containers],
                use_container_width=True,
            )
    else:
        st.info("No running containers")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — DOCKER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🐳 Docker":
    st.title("🐳 Docker Manager")

    tab1, tab2, tab3, tab4 = st.tabs(["Containers", "Images", "Volumes", "Actions"])

    # ── Containers tab
    with tab1:
        st.subheader("All Containers")
        show_all = st.toggle("Show stopped containers", value=True)
        flag = "-a" if show_all else ""
        out = docker(f"ps {flag} --format json")
        if out["ok"] and out["out"]:
            containers = [json.loads(l) for l in out["out"].splitlines() if l.strip()]
            df = [{"Name": c.get("Names"), "Image": c.get("Image"),
                   "Status": c.get("Status"), "Ports": c.get("Ports", "")} for c in containers]
            st.dataframe(df, use_container_width=True)

            st.divider()
            st.subheader("Container Actions")
            names = [c.get("Names") for c in containers]
            selected = st.selectbox("Select container", names)
            c1, c2, c3, c4 = st.columns(4)
            if c1.button("▶ Start"):
                r = docker(f"start {selected}")
                show(r)
            if c2.button("⏹ Stop"):
                r = docker(f"stop {selected}")
                show(r)
            if c3.button("🔄 Restart"):
                r = docker(f"restart {selected}")
                show(r)
            if c4.button("📋 Logs"):
                r = docker(f"logs --tail 50 {selected}")
                st.code(r["out"] or r["err"], language="bash")

            st.subheader("Container Stats")
            if st.button("📊 Get Stats"):
                r = docker(f"stats --no-stream --format json {selected}")
                if r["ok"]:
                    st.json(json.loads(r["out"]))

        else:
            st.info("No containers found")

    # ── Images tab
    with tab2:
        st.subheader("Local Images")
        out = docker("images --format json")
        if out["ok"] and out["out"]:
            images = [json.loads(l) for l in out["out"].splitlines() if l.strip()]
            st.dataframe(
                [{"Repository": i.get("Repository"), "Tag": i.get("Tag"), "Size": i.get("Size"), "ID": i.get("ID", "")[:12]} for i in images],
                use_container_width=True,
            )
        st.divider()
        st.subheader("Pull Image")
        img_name = st.text_input("Image name (e.g. nginx:latest)")
        if st.button("⬇ Pull") and img_name:
            with st.spinner(f"Pulling {img_name}..."):
                r = docker(f"pull {img_name}")
            show(r)

    # ── Volumes tab
    with tab3:
        st.subheader("Volumes")
        out = docker("volume ls --format json")
        if out["ok"] and out["out"]:
            vols = [json.loads(l) for l in out["out"].splitlines() if l.strip()]
            st.dataframe(
                [{"Name": v.get("Name"), "Driver": v.get("Driver"), "Scope": v.get("Scope")} for v in vols],
                use_container_width=True,
            )

    # ── Actions tab
    with tab4:
        st.subheader("Run New Container")
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
                show(r, f"Started: {r['out']}")

        st.divider()
        st.subheader("System Prune")
        st.warning("Removes stopped containers, unused images, and build cache.")
        if st.button("🗑 Prune System"):
            r = docker("system prune -f")
            if r["ok"]:
                st.code(r["out"])
            else:
                st.error(r["err"])


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — KUBERNETES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "☸️ Kubernetes":
    st.title("☸️ Kubernetes Manager")
    st.caption("Namespace: **devops** | Cluster: **docker-desktop**")

    tab1, tab2, tab3, tab4 = st.tabs(["Pods", "Deployments", "Services & PVCs", "Events & Logs"])

    with tab1:
        st.subheader("Pods")
        ns = st.text_input("Namespace", value="devops")
        if st.button("🔄 Refresh Pods", key="refresh_pods"):
            st.cache_data.clear()
        out = kube("get pods -o wide", ns=ns)
        st.code(out["out"] or out["err"], language="bash")

        st.divider()
        st.subheader("Pod Actions")
        pod_out = kube("get pods -o jsonpath='{.items[*].metadata.name}'", ns=ns)
        pod_names = pod_out["out"].strip("'").split() if pod_out["ok"] else []
        if pod_names:
            sel_pod = st.selectbox("Select pod", pod_names)
            c1, c2 = st.columns(2)
            if c1.button("🗑 Delete Pod (will restart)"):
                r = kube(f"delete pod {sel_pod}", ns=ns)
                show(r)
            if c2.button("🔍 Describe Pod"):
                r = kube(f"describe pod {sel_pod}", ns=ns)
                st.code(r["out"], language="bash")

    with tab2:
        st.subheader("Deployments")
        out = kube("get deployments", ns="devops")
        st.code(out["out"] or out["err"], language="bash")

        st.divider()
        st.subheader("Scale Deployment")
        dep_out = kube("get deployments -o jsonpath='{.items[*].metadata.name}'", ns="devops")
        dep_names = dep_out["out"].strip("'").split() if dep_out["ok"] else []
        if dep_names:
            sel_dep = st.selectbox("Deployment", dep_names)
            replicas = st.slider("Replicas", min_value=0, max_value=5, value=1)
            if st.button("⚖️ Scale"):
                r = kube(f"scale deployment {sel_dep} --replicas={replicas}", ns="devops")
                show(r)

            st.divider()
            if st.button("🔄 Rollout Restart"):
                r = kube(f"rollout restart deployment/{sel_dep}", ns="devops")
                show(r)

            if st.button("📋 Rollout Status"):
                r = kube(f"rollout status deployment/{sel_dep}", ns="devops")
                st.code(r["out"] or r["err"], language="bash")

    with tab3:
        st.subheader("Services")
        out = kube("get services", ns="devops")
        st.code(out["out"] or out["err"], language="bash")

        st.subheader("PersistentVolumeClaims")
        out = kube("get pvc", ns="devops")
        st.code(out["out"] or out["err"], language="bash")

    with tab4:
        st.subheader("Recent Events")
        out = kube("get events --sort-by=.lastTimestamp", ns="devops")
        st.code(out["out"] or "No events", language="bash")

        st.divider()
        st.subheader("Pod Logs")
        pod_out2 = kube("get pods -o jsonpath='{.items[*].metadata.name}'", ns="devops")
        pod_names2 = pod_out2["out"].strip("'").split() if pod_out2["ok"] else []
        if pod_names2:
            sel_pod2 = st.selectbox("Pod", pod_names2, key="log_pod")
            tail = st.slider("Tail lines", 10, 200, 50)
            if st.button("📋 Fetch Logs"):
                r = kube(f"logs {sel_pod2} --tail={tail}", ns="devops")
                st.code(r["out"] or r["err"], language="bash")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — JENKINS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚙️ Jenkins":
    st.title("⚙️ Jenkins Manager")
    st.caption(f"Connected to: **{JENKINS_URL}**")

    tab1, tab2, tab3 = st.tabs(["Jobs & Builds", "Create Job", "Nodes & Queue"])

    with tab1:
        st.subheader("All Jobs")
        if st.button("🔄 Refresh", key="j_refresh"):
            st.cache_data.clear()

        data = http_get(f"{JENKINS_URL}/api/json", JENKINS_AUTH,
                        params={"tree": "jobs[name,color,buildable]"})

        if data:
            jobs = data.get("jobs", [])
            color_map = {"blue": "🟢", "red": "🔴", "notbuilt": "⚪", "disabled": "⛔", "yellow": "🟡"}
            if jobs:
                st.dataframe(
                    [{"Status": color_map.get(j.get("color",""), "❓"),
                      "Name": j["name"], "Buildable": j.get("buildable")} for j in jobs],
                    use_container_width=True,
                )

                st.divider()
                st.subheader("Build Actions")
                job_names = [j["name"] for j in jobs]
                sel_job = st.selectbox("Select job", job_names)

                c1, c2, c3 = st.columns(3)
                if c1.button("🚀 Trigger Build"):
                    crumb = jenkins_crumb()
                    status, _ = http_post(f"{JENKINS_URL}/job/{sel_job}/build", JENKINS_AUTH, headers=crumb)
                    if status in (200, 201):
                        st.success(f"Build triggered for **{sel_job}**")
                    else:
                        st.error(f"Failed (HTTP {status})")

                if c2.button("📊 Build Status"):
                    d = http_get(f"{JENKINS_URL}/job/{sel_job}/lastBuild/api/json", JENKINS_AUTH)
                    if d:
                        result_icon = {"SUCCESS": "🟢", "FAILURE": "🔴", "UNSTABLE": "🟡"}.get(d.get("result"), "⚪")
                        st.metric("Result", f"{result_icon} {d.get('result', 'RUNNING')}", delta=f"Build #{d.get('number')}")
                        st.json({"number": d.get("number"), "result": d.get("result"),
                                 "building": d.get("building"), "durationMs": d.get("duration")})

                if c3.button("📋 Console Log"):
                    import httpx as _httpx
                    try:
                        r = _httpx.get(f"{JENKINS_URL}/job/{sel_job}/lastBuild/consoleText",
                                       auth=JENKINS_AUTH, timeout=10)
                        lines = r.text.splitlines()
                        st.code("\n".join(lines[-80:]), language="bash")
                    except Exception as e:
                        st.error(str(e))

                st.subheader(f"Recent Builds — {sel_job}")
                builds_data = http_get(f"{JENKINS_URL}/job/{sel_job}/api/json", JENKINS_AUTH,
                                       params={"tree": "builds[number,result,duration,building]{0,10}"})
                if builds_data:
                    builds = builds_data.get("builds", [])
                    if builds:
                        st.dataframe(builds, use_container_width=True)
            else:
                st.info("No jobs found. Create one in the **Create Job** tab.")
        else:
            st.error(f"Cannot connect to Jenkins at {JENKINS_URL}")

    with tab2:
        st.subheader("Create Freestyle Job")
        with st.form("create_job"):
            job_name    = st.text_input("Job name", value="new-job")
            description = st.text_input("Description", value="Created via MCP Streamlit")
            shell_cmd   = st.text_area("Shell command", value='echo "Hello from Jenkins K8s!"\ndate\nhostname')
            submitted = st.form_submit_button("✅ Create Job")

        if submitted and job_name:
            config_xml = f"""<?xml version="1.1" encoding="UTF-8"?>
<project>
  <description>{description}</description>
  <keepDependencies>false</keepDependencies>
  <properties/><scm class="hudson.scm.NullSCM"/>
  <canRoam>true</canRoam><disabled>false</disabled>
  <builders>
    <hudson.tasks.Shell><command>{shell_cmd}</command></hudson.tasks.Shell>
  </builders>
  <publishers/><buildWrappers/>
</project>""".encode("utf-8")
            crumb = jenkins_crumb()
            headers = {"Content-Type": "application/xml;charset=UTF-8", **crumb}
            status, resp = http_post(f"{JENKINS_URL}/createItem?name={job_name}",
                                     JENKINS_AUTH, content=config_xml, headers=headers)
            if status in (200, 201):
                st.success(f"✅ Job **{job_name}** created!")
            else:
                st.error(f"Failed HTTP {status}: {str(resp)[:200]}")

    with tab3:
        st.subheader("Build Nodes")
        data = http_get(f"{JENKINS_URL}/computer/api/json", JENKINS_AUTH,
                        params={"tree": "computer[displayName,offline,numExecutors,description]"})
        if data:
            nodes = data.get("computer", [])
            st.dataframe(
                [{"Node": n.get("displayName"), "Executors": n.get("numExecutors"),
                  "Offline": n.get("offline")} for n in nodes],
                use_container_width=True,
            )

        st.divider()
        st.subheader("Build Queue")
        q = http_get(f"{JENKINS_URL}/queue/api/json", JENKINS_AUTH)
        if q:
            items = q.get("items", [])
            if items:
                st.dataframe(
                    [{"Job": i.get("task", {}).get("name"), "Why": i.get("why")} for i in items],
                    use_container_width=True,
                )
            else:
                st.success("Queue is empty")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — SONARQUBE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 SonarQube":
    st.title("🔍 SonarQube Manager")
    st.caption(f"Connected to: **{SONAR_URL}**")

    # Health check
    health = http_get(f"{SONAR_URL}/api/system/health", SONAR_AUTH, timeout=5)
    if health:
        h = health.get("health", "UNKNOWN")
        if h == "GREEN":
            st.success(f"🟢 SonarQube Health: **{h}**")
        else:
            st.warning(f"⚠️ Health: {h}")
    else:
        st.error(f"🔴 SonarQube unreachable at {SONAR_URL}")
        st.stop()

    tab1, tab2, tab3, tab4 = st.tabs(["Projects", "Quality Gates", "Issues", "Tokens"])

    with tab1:
        st.subheader("Projects")
        if st.button("🔄 Refresh Projects"):
            st.cache_data.clear()

        data = http_get(f"{SONAR_URL}/api/projects/search", SONAR_AUTH, params={"ps": 50})
        components = data.get("components", []) if data else []

        if components:
            st.dataframe(
                [{"Key": c["key"], "Name": c["name"],
                  "Last Analysis": c.get("lastAnalysisDate", "never")} for c in components],
                use_container_width=True,
            )

            st.divider()
            st.subheader("Project Metrics")
            proj_keys = [c["key"] for c in components]
            sel_proj = st.selectbox("Select project", proj_keys)
            if st.button("📊 Get Metrics"):
                metrics = "bugs,vulnerabilities,code_smells,coverage,duplicated_lines_density,ncloc"
                m_data = http_get(
                    f"{SONAR_URL}/api/measures/component", SONAR_AUTH,
                    params={"component": sel_proj, "metricKeys": metrics},
                )
                if m_data:
                    measures = {m["metric"]: m.get("value", "N/A")
                                for m in m_data.get("component", {}).get("measures", [])}
                    cols = st.columns(len(measures))
                    for i, (k, v) in enumerate(measures.items()):
                        cols[i].metric(k.replace("_", " ").title(), v)

            if st.button("🔒 Quality Gate Status"):
                qg = http_get(f"{SONAR_URL}/api/qualitygates/project_status", SONAR_AUTH,
                              params={"projectKey": sel_proj})
                if qg:
                    status = qg.get("projectStatus", {}).get("status", "NONE")
                    icon = "🟢" if status == "OK" else "🔴" if status == "ERROR" else "⚪"
                    st.metric("Quality Gate", f"{icon} {status}")
        else:
            st.info("No projects found.")

        st.divider()
        st.subheader("Create Project")
        with st.form("create_project"):
            pkey  = st.text_input("Project Key", value="my-app")
            pname = st.text_input("Project Name", value="My Application")
            submitted = st.form_submit_button("➕ Create Project")
        if submitted and pkey:
            status, resp = http_post(f"{SONAR_URL}/api/projects/create", SONAR_AUTH,
                                     data={"project": pkey, "name": pname, "visibility": "public"})
            if status == 200:
                st.success(f"✅ Project **{pkey}** created!")
            else:
                st.error(f"Failed: {str(resp)[:200]}")

    with tab2:
        st.subheader("Quality Gates")
        data = http_get(f"{SONAR_URL}/api/qualitygates/list", SONAR_AUTH)
        if data:
            gates = data.get("qualitygates", [])
            st.dataframe(
                [{"Name": g["name"], "Default": g.get("isDefault", False)} for g in gates],
                use_container_width=True,
            )

    with tab3:
        st.subheader("Open Issues")
        data = http_get(f"{SONAR_URL}/api/projects/search", SONAR_AUTH, params={"ps": 50})
        components = data.get("components", []) if data else []
        if components:
            sel_proj2 = st.selectbox("Project", [c["key"] for c in components], key="issue_proj")
            severity  = st.selectbox("Severity", ["", "BLOCKER", "CRITICAL", "MAJOR", "MINOR", "INFO"])
            itype     = st.selectbox("Type", ["", "BUG", "VULNERABILITY", "CODE_SMELL"])
            if st.button("🔍 Search Issues"):
                params = {"componentKeys": sel_proj2, "ps": 20, "resolved": "false"}
                if severity: params["severities"] = severity
                if itype:    params["types"] = itype
                idata = http_get(f"{SONAR_URL}/api/issues/search", SONAR_AUTH, params=params)
                if idata:
                    issues = idata.get("issues", [])
                    if issues:
                        st.dataframe(
                            [{"Type": i["type"], "Severity": i["severity"],
                              "Message": i["message"][:80], "Line": i.get("line")} for i in issues],
                            use_container_width=True,
                        )
                        st.caption(f"Total: {idata.get('total', 0)} issues")
                    else:
                        st.success("No open issues found!")

    with tab4:
        st.subheader("Generate User Token")
        with st.form("gen_token"):
            tname = st.text_input("Token name", value="my-scanner-token")
            submitted = st.form_submit_button("🔑 Generate Token")
        if submitted and tname:
            status, resp = http_post(f"{SONAR_URL}/api/user_tokens/generate", SONAR_AUTH,
                                     data={"name": tname, "login": "admin"})
            if status == 200 and isinstance(resp, dict):
                token_val = resp.get("token", "")
                st.success("Token generated!")
                st.code(token_val, language="text")
                st.caption("⚠️ Copy this token now — it won't be shown again.")
            else:
                st.error(f"Failed: {str(resp)[:200]}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6 — TERRAFORM
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🌍 Terraform":
    st.title("🌍 Terraform Manager")
    st.caption(f"Workdir: `{TF_WORKDIR}`")

    tab1, tab2, tab3 = st.tabs(["Plan & Apply", "State", "Workspaces"])

    with tab1:
        st.subheader("Variables")
        col1, col2, col3, col4 = st.columns(4)
        app_name    = col1.text_input("App Name",    value="my-devops-app")
        environment = col2.selectbox("Environment",  ["dev", "staging", "prod"])
        app_port    = col3.number_input("Port",       value=3000, min_value=1000, max_value=65535)
        log_level   = col4.selectbox("Log Level",    ["debug", "info", "warn", "error"])

        var_flags = (f'-var "app_name={app_name}" -var "environment={environment}" '
                     f'-var "app_port={app_port}" -var "log_level={log_level}"')

        c1, c2, c3, c4 = st.columns(4)
        if c1.button("🔧 Init"):
            with st.spinner("Running terraform init..."):
                r = tf("terraform init -no-color")
            st.code(f"{r['out']}\n{r['err']}", language="bash")

        if c2.button("📋 Validate"):
            r = tf("terraform validate -json")
            try:
                d = json.loads(r["out"])
                if d.get("valid"):
                    st.success("✅ Configuration is valid!")
                else:
                    st.error(f"Invalid: {d.get('diagnostics')}")
            except Exception:
                st.code(r["out"] or r["err"])

        if c3.button("🔍 Plan"):
            with st.spinner("Running terraform plan..."):
                r = tf(f"terraform plan -no-color {var_flags}")
            st.code(f"{r['out']}\n{r['err']}", language="bash")

        if c4.button("🚀 Apply", type="primary"):
            with st.spinner("Running terraform apply..."):
                r = tf(f"terraform apply -no-color -auto-approve {var_flags}")
            combined = f"{r['out']}\n{r['err']}"
            if "Apply complete!" in combined:
                st.success("✅ Apply complete!")
            else:
                st.error("Apply may have failed")
            st.code(combined, language="bash")

        st.divider()
        if st.button("💥 Destroy", type="secondary"):
            with st.spinner("Running terraform destroy..."):
                r = tf(f"terraform destroy -no-color -auto-approve {var_flags}")
            st.code(f"{r['out']}\n{r['err']}", language="bash")

    with tab2:
        st.subheader("State Resources")
        if st.button("🔄 Refresh State"):
            r = tf("terraform state list")
            if r["ok"] and r["out"]:
                resources = r["out"].splitlines()
                st.write(f"**{len(resources)} resources tracked**")
                for res in resources:
                    st.code(res)
            else:
                st.info("State is empty — run Apply first.")

        st.divider()
        st.subheader("Outputs")
        if st.button("📤 Show Outputs"):
            r = tf("terraform output -json")
            if r["ok"] and r["out"]:
                try:
                    data = json.loads(r["out"])
                    for k, v in data.items():
                        st.metric(k.replace("_", " ").title(), str(v.get("value"))[:60])
                except Exception:
                    st.code(r["out"])
            else:
                st.info("No outputs — run Apply first.")

    with tab3:
        st.subheader("Workspaces")
        r = tf("terraform workspace list")
        if r["ok"]:
            lines = r["out"].splitlines()
            current = next((l.replace("*", "").strip() for l in lines if "*" in l), "default")
            st.info(f"Active workspace: **{current}**")
            for line in lines:
                icon = "✅" if "*" in line else "  "
                st.markdown(f"{icon} `{line.replace('*','').strip()}`")

        st.divider()
        with st.form("new_workspace"):
            ws_name = st.text_input("New workspace name")
            submitted = st.form_submit_button("➕ Create Workspace")
        if submitted and ws_name:
            r = tf(f"terraform workspace new {ws_name}")
            show(r, f"Workspace **{ws_name}** created!")

        with st.form("select_workspace"):
            sel_ws = st.text_input("Switch to workspace")
            submitted2 = st.form_submit_button("🔀 Select Workspace")
        if submitted2 and sel_ws:
            r = tf(f"terraform workspace select {sel_ws}")
            show(r, f"Switched to **{sel_ws}**")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 7 — PROMETHEUS & GRAFANA
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Prometheus & Grafana":
    st.title("📊 Prometheus & Grafana")

    # Health row
    col1, col2 = st.columns(2)
    with col1:
        try:
            import httpx as _hx
            r = _hx.get(f"{PROM_URL}/-/ready", timeout=4)
            if r.status_code == 200:
                st.success(f"🟢 Prometheus ready — {PROM_URL}")
            else:
                st.error(f"🔴 Prometheus not ready ({r.status_code})")
        except Exception as e:
            st.error(f"🔴 Prometheus unreachable: {e}")

    with col2:
        g = http_get(f"{GRAFANA_URL}/api/health", GRAFANA_AUTH, timeout=4)
        if g and "error" not in g:
            st.success(f"🟢 Grafana {g.get('version', '')} — {GRAFANA_URL}")
        else:
            st.error(f"🔴 Grafana unreachable")

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(["Query Metrics", "Alerts & Targets", "Dashboards", "Datasources"])

    with tab1:
        st.subheader("PromQL Query")
        promql = st.text_input("PromQL expression", value="up")
        if st.button("▶ Run Query"):
            data = http_get(f"{PROM_URL}/api/v1/query", params={"query": promql}, timeout=10)
            if data and data.get("status") == "success":
                results = data.get("data", {}).get("result", [])
                if results:
                    st.dataframe(
                        [{"metric": str(r.get("metric")), "value": r.get("value", [None, None])[1]}
                         for r in results],
                        use_container_width=True,
                    )
                else:
                    st.info("No data returned.")
            else:
                st.error(f"Query failed: {data}")

        st.divider()
        st.subheader("Quick Metrics")
        col1, col2 = st.columns(2)
        ns_q = col1.text_input("Namespace", value="devops", key="prom_ns")
        if col2.button("📈 CPU Usage"):
            q = f"sum(rate(container_cpu_usage_seconds_total{{namespace='{ns_q}',container!=''}}[5m])) by (pod)"
            data = http_get(f"{PROM_URL}/api/v1/query", params={"query": q}, timeout=10)
            if data and data.get("status") == "success":
                results = data.get("data", {}).get("result", [])
                if results:
                    cpu_data = {r["metric"].get("pod", "?"): float(r["value"][1]) for r in results}
                    st.bar_chart(cpu_data)
                else:
                    st.info("No CPU data.")

        if st.button("💾 Memory Usage"):
            q = f"sum(container_memory_usage_bytes{{namespace='{ns_q}',container!=''}}) by (pod)"
            data = http_get(f"{PROM_URL}/api/v1/query", params={"query": q}, timeout=10)
            if data and data.get("status") == "success":
                results = data.get("data", {}).get("result", [])
                if results:
                    mem_data = {r["metric"].get("pod", "?"): int(r["value"][1]) // (1024*1024) for r in results}
                    st.bar_chart(mem_data)
                    st.caption("Memory in MiB")
                else:
                    st.info("No memory data.")

    with tab2:
        st.subheader("Active Alerts")
        if st.button("🔄 Refresh Alerts"):
            data = http_get(f"{PROM_URL}/api/v1/alerts", timeout=8)
            if data:
                alerts = data.get("data", {}).get("alerts", [])
                if alerts:
                    st.dataframe(
                        [{"name": a.get("labels", {}).get("alertname"),
                          "state": a.get("state"),
                          "severity": a.get("labels", {}).get("severity"),
                          "summary": a.get("annotations", {}).get("summary", "")} for a in alerts],
                        use_container_width=True,
                    )
                else:
                    st.success("No active alerts.")

        st.divider()
        st.subheader("Scrape Targets")
        if st.button("🔄 Refresh Targets"):
            data = http_get(f"{PROM_URL}/api/v1/targets", timeout=8)
            if data:
                active = data.get("data", {}).get("activeTargets", [])
                st.dataframe(
                    [{"job": t.get("labels", {}).get("job"),
                      "instance": t.get("labels", {}).get("instance"),
                      "health": t.get("health"),
                      "lastError": t.get("lastError", "")} for t in active],
                    use_container_width=True,
                )

    with tab3:
        st.subheader("Grafana Dashboards")
        if st.button("🔄 Refresh Dashboards"):
            st.cache_data.clear()

        @st.cache_data(ttl=30)
        def get_dashboards():
            return http_get(f"{GRAFANA_URL}/api/search?type=dash-db", GRAFANA_AUTH)

        dashboards = get_dashboards()
        if dashboards and not isinstance(dashboards, dict):
            st.dataframe(
                [{"Title": d.get("title"), "UID": d.get("uid"), "URL": d.get("url", "")} for d in dashboards],
                use_container_width=True,
            )
        else:
            st.info("No dashboards found.")

        st.divider()
        st.subheader("Create Dashboard")
        with st.form("create_dashboard"):
            dash_title  = st.text_input("Dashboard title", value="K8s Pod CPU")
            prom_query  = st.text_input("PromQL", value="rate(container_cpu_usage_seconds_total[5m])")
            panel_title = st.text_input("Panel title", value="CPU Usage")
            submitted   = st.form_submit_button("➕ Create")
        if submitted and dash_title:
            dashboard = {
                "dashboard": {
                    "title": dash_title,
                    "panels": [{
                        "id": 1, "title": panel_title, "type": "timeseries",
                        "gridPos": {"x": 0, "y": 0, "w": 24, "h": 8},
                        "targets": [{"datasource": {"type": "prometheus", "uid": "prometheus"},
                                     "expr": prom_query, "legendFormat": "{{pod}}"}],
                    }],
                    "time": {"from": "now-1h", "to": "now"}, "refresh": "30s",
                },
                "overwrite": True, "folderId": 0,
            }
            status, resp = http_post(f"{GRAFANA_URL}/api/dashboards/db", GRAFANA_AUTH, json_data=dashboard)
            if status == 200:
                st.success(f"Dashboard **{dash_title}** created!")
            else:
                st.error(f"Failed: {str(resp)[:200]}")

    with tab4:
        st.subheader("Grafana Datasources")
        data = http_get(f"{GRAFANA_URL}/api/datasources", GRAFANA_AUTH)
        if data and isinstance(data, list):
            st.dataframe(
                [{"Name": d.get("name"), "Type": d.get("type"), "URL": d.get("url"),
                  "Default": d.get("isDefault")} for d in data],
                use_container_width=True,
            )
        else:
            st.info("No datasources configured.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 8 — ARGOCD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔀 ArgoCD":
    st.title("🔀 ArgoCD GitOps Manager")
    st.caption(f"Connected to: **{ARGOCD_URL}**")

    # Health
    try:
        import httpx as _hx
        r = _hx.get(f"{ARGOCD_URL}/api/version", verify=False, timeout=5)
        v = r.json()
        st.success(f"🟢 ArgoCD {v.get('Version', '')} ready")
    except Exception as e:
        st.error(f"🔴 ArgoCD unreachable: {e}")
        st.stop()

    def _argocd_token() -> str:
        try:
            pw_proc = subprocess.run(
                "kubectl get secret argocd-initial-admin-secret -n argocd "
                "-o jsonpath='{.data.password}' | base64 --decode",
                shell=True, capture_output=True, text=True,
            )
            password = pw_proc.stdout.strip().strip("'")
            import httpx as _hx
            resp = _hx.post(
                f"{ARGOCD_URL}/api/v1/session",
                json={"username": "admin", "password": password},
                verify=False, timeout=10,
            )
            return resp.json().get("token", "")
        except Exception:
            return ""

    def argocd_api(method: str, path: str, data: dict = None) -> dict:
        token = _argocd_token()
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            import httpx as _hx
            r = getattr(_hx, method)(
                f"{ARGOCD_URL}/api/v1/{path}",
                json=data, headers=headers, verify=False, timeout=15,
            )
            return r.json() if r.text else {"status": "ok"}
        except Exception as e:
            return {"error": str(e)}

    tab1, tab2, tab3 = st.tabs(["Applications", "Create App", "Repositories"])

    with tab1:
        if st.button("🔄 Refresh Apps"):
            st.cache_data.clear()

        data = argocd_api("get", "applications")
        apps = data.get("items", []) if "error" not in data else []

        if apps:
            app_rows = []
            for a in apps:
                sync   = a["status"].get("sync", {}).get("status", "Unknown")
                health = a["status"].get("health", {}).get("status", "Unknown")
                app_rows.append({
                    "Name":      a["metadata"]["name"],
                    "Project":   a["spec"].get("project", "default"),
                    "Repo":      a["spec"]["source"].get("repoURL", "")[-40:],
                    "Namespace": a["spec"]["destination"].get("namespace"),
                    "Sync":      sync,
                    "Health":    health,
                })
            st.dataframe(app_rows, use_container_width=True)

            st.divider()
            app_names = [a["metadata"]["name"] for a in apps]
            sel_app = st.selectbox("Select application", app_names)

            c1, c2, c3 = st.columns(3)
            if c1.button("🔄 Sync App"):
                result = argocd_api("post", f"applications/{sel_app}/sync",
                                    {"prune": False, "dryRun": False, "force": False})
                if "error" not in result:
                    st.success(f"Sync triggered for **{sel_app}**")
                else:
                    st.error(f"Error: {result['error']}")

            if c2.button("🔍 App Details"):
                result = argocd_api("get", f"applications/{sel_app}")
                if "error" not in result:
                    status = result.get("status", {})
                    st.json({
                        "syncStatus":   status.get("sync", {}).get("status"),
                        "healthStatus": status.get("health", {}).get("status"),
                        "revision":     status.get("sync", {}).get("revision", "")[:8],
                        "resources":    len(status.get("resources", [])),
                    })

            if c3.button("🗑 Delete App"):
                import httpx as _hx
                token = _argocd_token()
                headers = {"Authorization": f"Bearer {token}"} if token else {}
                r = _hx.delete(
                    f"{ARGOCD_URL}/api/v1/applications/{sel_app}",
                    headers=headers, params={"cascade": "true"}, verify=False, timeout=15,
                )
                if r.status_code in (200, 204):
                    st.success(f"Deleted **{sel_app}**")
                else:
                    st.error(f"Error: {r.text[:200]}")
        else:
            if "error" in data:
                st.error(f"API error: {data['error']}")
            else:
                st.info("No applications found. Create one in **Create App** tab.")

    with tab2:
        st.subheader("Create ArgoCD Application")
        with st.form("create_argo_app"):
            app_name    = st.text_input("App name", value="my-app")
            repo_url    = st.text_input("Git repo URL", value="https://github.com/argoproj/argocd-example-apps")
            app_path    = st.text_input("Path in repo", value="guestbook")
            dest_ns     = st.text_input("Destination namespace", value="default")
            target_rev  = st.text_input("Target revision", value="HEAD")
            auto_sync   = st.checkbox("Enable auto-sync", value=True)
            submitted   = st.form_submit_button("🚀 Create Application")

        if submitted and app_name and repo_url:
            sync_policy = {"automated": {"prune": True, "selfHeal": True}} if auto_sync else {}
            payload = {
                "metadata": {"name": app_name},
                "spec": {
                    "project": "default",
                    "source": {"repoURL": repo_url, "path": app_path, "targetRevision": target_rev},
                    "destination": {"server": "https://kubernetes.default.svc", "namespace": dest_ns},
                    "syncPolicy": sync_policy,
                },
            }
            result = argocd_api("post", "applications", payload)
            if "error" not in result:
                st.success(f"Application **{app_name}** created!")
            else:
                st.error(f"Error: {result.get('error')}")

    with tab3:
        st.subheader("Registered Repositories")
        data = argocd_api("get", "repositories")
        repos = data.get("items", []) if "error" not in data else []
        if repos:
            st.dataframe(
                [{"Repo": r.get("repo"), "Type": r.get("type", "git"),
                  "Status": r.get("connectionState", {}).get("status")} for r in repos],
                use_container_width=True,
            )
        else:
            st.info("No repositories registered.")

        st.divider()
        st.subheader("Add Repository")
        with st.form("add_repo"):
            repo_url2 = st.text_input("Repository URL")
            repo_user = st.text_input("Username (optional)")
            repo_pass = st.text_input("Password (optional)", type="password")
            submitted = st.form_submit_button("➕ Add Repository")
        if submitted and repo_url2:
            result = argocd_api("post", "repositories",
                                {"repo": repo_url2, "username": repo_user,
                                 "password": repo_pass, "insecure": True})
            if "error" not in result:
                st.success(f"Repository **{repo_url2}** added!")
            else:
                st.error(f"Error: {result.get('error')}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 9 — TRIVY SCANNER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🛡️ Trivy Scanner":
    st.title("🛡️ Trivy Security Scanner")
    st.caption("Scan container images and K8s workloads for CVEs and misconfigurations")

    # Check trivy installed
    import shutil as _shutil
    trivy_ok = bool(_shutil.which("trivy"))
    if trivy_ok:
        r = subprocess.run(["trivy", "--version"], capture_output=True, text=True)
        st.success(f"🟢 {r.stdout.strip().splitlines()[0] if r.stdout else 'trivy ready'}")
    else:
        st.error("🔴 trivy not installed. Run: `brew install trivy`")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["Image Scan", "K8s Namespace Scan", "Config/IaC Scan"])

    with tab1:
        st.subheader("Scan Container Image")
        col1, col2 = st.columns([3, 1])
        image_name = col1.text_input("Image name", value="nginx:latest", key="trivy_img")
        severity   = col2.multiselect("Severity", ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                                       default=["CRITICAL", "HIGH"])

        if st.button("🔍 Scan Image", type="primary"):
            sev_str = ",".join(severity) if severity else "CRITICAL,HIGH,MEDIUM,LOW"
            with st.spinner(f"Scanning {image_name}..."):
                proc = subprocess.run(
                    ["trivy", "--quiet", "--format", "json", "image",
                     "--severity", sev_str, image_name],
                    capture_output=True, text=True, timeout=120,
                )
            try:
                data = json.loads(proc.stdout) if proc.stdout.strip() else {}
            except json.JSONDecodeError:
                st.error(f"Parse error: {proc.stderr[:200]}")
                data = {}

            if data:
                results = data.get("Results", [])
                total = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
                all_vulns = []
                for r in results:
                    for v in (r.get("Vulnerabilities") or []):
                        sev = v.get("Severity", "UNKNOWN")
                        total[sev] = total.get(sev, 0) + 1
                        all_vulns.append({
                            "ID":      v.get("VulnerabilityID"),
                            "Package": v.get("PkgName"),
                            "Version": v.get("InstalledVersion"),
                            "Fixed":   v.get("FixedVersion", "no fix"),
                            "Severity": v.get("Severity"),
                            "Title":   v.get("Title", "")[:60],
                        })

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("CRITICAL", total.get("CRITICAL", 0), delta="🔴" if total.get("CRITICAL") else None)
                c2.metric("HIGH",     total.get("HIGH", 0),     delta="🟠" if total.get("HIGH") else None)
                c3.metric("MEDIUM",   total.get("MEDIUM", 0))
                c4.metric("LOW",      total.get("LOW", 0))

                if all_vulns:
                    st.divider()
                    st.subheader(f"Vulnerabilities ({len(all_vulns)} found)")
                    st.dataframe(all_vulns, use_container_width=True)
                else:
                    st.success(f"No vulnerabilities found matching filter in **{image_name}**")
            elif proc.returncode not in (0, 1):
                st.error(f"Scan failed: {proc.stderr[:300]}")

    with tab2:
        st.subheader("Scan All Images in K8s Namespace")
        ns_scan = st.text_input("Namespace", value="devops", key="trivy_ns")

        if st.button("🔍 Scan Namespace"):
            # Get pod images
            get_imgs = subprocess.run(
                ["kubectl", "get", "pods", "-n", ns_scan,
                 "-o", "jsonpath={.items[*].spec.containers[*].image}"],
                capture_output=True, text=True,
            )
            if get_imgs.returncode != 0:
                st.error(f"kubectl error: {get_imgs.stderr[:200]}")
            else:
                images_list = list(set(get_imgs.stdout.split()))
                if not images_list:
                    st.info(f"No pods in namespace '{ns_scan}'")
                else:
                    st.info(f"Found {len(images_list)} unique images. Scanning...")
                    scan_results = {}
                    progress = st.progress(0)
                    for i, img in enumerate(images_list):
                        proc = subprocess.run(
                            ["trivy", "--quiet", "--format", "json", "image",
                             "--severity", "CRITICAL,HIGH", img],
                            capture_output=True, text=True, timeout=120,
                        )
                        try:
                            d = json.loads(proc.stdout) if proc.stdout.strip() else {}
                            total = {"CRITICAL": 0, "HIGH": 0}
                            for r in d.get("Results", []):
                                for v in (r.get("Vulnerabilities") or []):
                                    sev = v.get("Severity", "")
                                    total[sev] = total.get(sev, 0) + 1
                            scan_results[img] = total
                        except Exception:
                            scan_results[img] = {"error": "parse failed"}
                        progress.progress((i + 1) / len(images_list))

                    st.dataframe(
                        [{"Image": img, **counts} for img, counts in scan_results.items()],
                        use_container_width=True,
                    )

    with tab3:
        st.subheader("Scan IaC / Config Files")
        scan_path = st.text_input("Path to scan", value="k8s/")
        if st.button("🔍 Scan Configs"):
            with st.spinner(f"Scanning {scan_path}..."):
                proc = subprocess.run(
                    ["trivy", "--quiet", "--format", "json", "config", scan_path],
                    capture_output=True, text=True, timeout=60,
                )
            try:
                data = json.loads(proc.stdout) if proc.stdout.strip() else {}
            except json.JSONDecodeError:
                st.error(f"Parse error: {proc.stderr[:200]}")
                data = {}

            findings = []
            for r in data.get("Results", []):
                for m in (r.get("Misconfigurations") or []):
                    findings.append({
                        "File":       r.get("Target"),
                        "ID":         m.get("ID"),
                        "Title":      m.get("Title"),
                        "Severity":   m.get("Severity"),
                        "Message":    m.get("Message", "")[:100],
                        "Resolution": m.get("Resolution", "")[:80],
                    })

            if findings:
                st.warning(f"{len(findings)} misconfiguration(s) found")
                st.dataframe(findings, use_container_width=True)
            else:
                st.success("No misconfigurations found!")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 10 — HELM MANAGER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⛵ Helm Manager":
    import shutil as _sh
    st.title("⛵ Helm Manager")
    st.caption("Manage Helm charts and releases")

    if not _sh.which("helm"):
        st.error("Helm not installed. Run: `brew install helm`")
        st.stop()

    def helm(args): return subprocess.run(["helm"] + args.split(), capture_output=True, text=True, timeout=60)

    tab1, tab2, tab3, tab4 = st.tabs(["Releases", "Repositories", "Install / Upgrade", "History"])

    with tab1:
        st.subheader("All Helm Releases")
        ns_h = st.text_input("Namespace", value="default", key="helm_ns")
        all_ns = st.checkbox("All namespaces", key="helm_all_ns")
        if st.button("🔄 List Releases", type="primary"):
            cmd = f"list {'--all-namespaces' if all_ns else f'-n {ns_h}'}"
            r = helm(cmd)
            st.code(r.stdout or r.stderr, language="bash")

    with tab2:
        st.subheader("Configured Repositories")
        if st.button("📋 List Repos"):
            r = helm("repo list")
            st.code(r.stdout or "No repositories configured", language="bash")

        st.divider()
        st.subheader("Add Repository")
        with st.form("add_repo"):
            repo_name = st.text_input("Repo name", placeholder="bitnami")
            repo_url  = st.text_input("Repo URL", placeholder="https://charts.bitnami.com/bitnami")
            if st.form_submit_button("➕ Add & Update"):
                with st.spinner("Adding repo..."):
                    r = helm(f"repo add {repo_name} {repo_url}")
                    helm("repo update")
                if r.returncode == 0:
                    st.success(f"Repo '{repo_name}' added")
                else:
                    st.error(r.stderr)

        st.divider()
        st.subheader("Search Charts")
        keyword = st.text_input("Search keyword", key="helm_search")
        if st.button("🔍 Search") and keyword:
            r = helm(f"search repo {keyword}")
            st.code(r.stdout or "No results", language="bash")

    with tab3:
        st.subheader("Install / Upgrade Chart")
        with st.form("helm_install"):
            col1, col2 = st.columns(2)
            rel_name  = col1.text_input("Release name", placeholder="my-nginx")
            chart     = col2.text_input("Chart", placeholder="bitnami/nginx")
            col3, col4 = st.columns(2)
            ns_i      = col3.text_input("Namespace", value="default")
            version   = col4.text_input("Version (optional)")
            values_yaml = st.text_area("Values override (YAML)", height=100,
                                       placeholder="replicaCount: 2\nservice:\n  type: NodePort")
            upgrade   = st.checkbox("Upgrade if exists (--install)", value=True)
            submitted = st.form_submit_button("🚀 Deploy")
            if submitted and rel_name and chart:
                import tempfile, os as _os
                args = ["upgrade" if upgrade else "install", rel_name, chart, "-n", ns_i]
                if upgrade: args.append("--install")
                if version: args += ["--version", version]
                tmp = None
                if values_yaml.strip():
                    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                        f.write(values_yaml); tmp = f.name
                    args += ["-f", tmp]
                with st.spinner(f"Deploying {rel_name}..."):
                    r = subprocess.run(["helm"] + args, capture_output=True, text=True, timeout=120)
                if tmp: _os.unlink(tmp)
                if r.returncode == 0:
                    st.success(f"Release '{rel_name}' deployed!")
                    st.code(r.stdout, language="bash")
                else:
                    st.error(r.stderr)

        st.divider()
        st.subheader("Uninstall Release")
        with st.form("helm_uninstall"):
            del_name = st.text_input("Release name to uninstall")
            del_ns   = st.text_input("Namespace", value="default")
            if st.form_submit_button("🗑 Uninstall", type="primary"):
                r = subprocess.run(["helm", "uninstall", del_name, "-n", del_ns],
                                   capture_output=True, text=True, timeout=60)
                if r.returncode == 0:
                    st.success(f"Release '{del_name}' uninstalled")
                else:
                    st.error(r.stderr)

    with tab4:
        st.subheader("Release History & Rollback")
        with st.form("helm_history"):
            hist_name = st.text_input("Release name")
            hist_ns   = st.text_input("Namespace", value="default")
            if st.form_submit_button("📜 Get History"):
                r = subprocess.run(["helm", "history", hist_name, "-n", hist_ns],
                                   capture_output=True, text=True, timeout=30)
                st.code(r.stdout or r.stderr, language="bash")

        with st.form("helm_rollback"):
            rb_name = st.text_input("Release name", key="rb_name")
            rb_rev  = st.number_input("Revision (0 = previous)", min_value=0, value=0)
            rb_ns   = st.text_input("Namespace", value="default", key="rb_ns")
            if st.form_submit_button("⏮ Rollback"):
                r = subprocess.run(["helm", "rollback", rb_name, str(rb_rev), "-n", rb_ns],
                                   capture_output=True, text=True, timeout=60)
                if r.returncode == 0:
                    st.success(f"Rolled back '{rb_name}' to revision {rb_rev or 'previous'}")
                else:
                    st.error(r.stderr)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 11 — VAULT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔐 Vault Secrets":
    st.title("🔐 HashiCorp Vault")
    st.caption(f"Endpoint: {VAULT_URL} | Token: `root` (dev mode)")

    import httpx as _hx
    _vh = {"X-Vault-Token": VAULT_TOKEN, "Content-Type": "application/json"}

    def v_get(path):
        try:
            r = _hx.get(f"{VAULT_URL}/v1/{path}", headers=_vh, timeout=8)
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def v_post(path, data):
        try:
            r = _hx.post(f"{VAULT_URL}/v1/{path}", headers=_vh, json=data, timeout=8)
            return r.json() if r.text else {"status": r.status_code}
        except Exception as e:
            return {"error": str(e)}

    # Health check
    try:
        _vr = _hx.get(f"{VAULT_URL}/v1/sys/health", timeout=5)
        _vd = _vr.json()
        if not _vd.get("sealed", True):
            st.success(f"🟢 Vault Unsealed | Version: {_vd.get('version')} | Cluster: {_vd.get('cluster_name','dev')}")
        else:
            st.error("🔴 Vault is sealed")
    except Exception as _e:
        st.error(f"🔴 Vault unreachable: {_e}")
        st.stop()

    tab1, tab2, tab3, tab4 = st.tabs(["Secrets", "Write Secret", "Policies", "Auth & Tokens"])

    with tab1:
        st.subheader("Browse Secrets")
        secret_path = st.text_input("Path (list)", value="secret", key="v_list_path")
        if st.button("📋 List", key="v_list"):
            res = v_get(f"{secret_path}?list=true")
            keys = res.get("data", {}).get("keys", [])
            if keys:
                for k in keys:
                    st.markdown(f"- `{k}`")
            else:
                st.info(f"No secrets at '{secret_path}'")

        st.divider()
        st.subheader("Read Secret")
        read_path = st.text_input("Full path", value="secret/myapp", key="v_read_path")
        if st.button("🔍 Read", key="v_read"):
            res = v_get(read_path)
            data = res.get("data", {})
            if "data" in data: data = data["data"]
            if data and "error" not in res:
                for k, v in data.items():
                    st.code(f"{k} = {v}")
            else:
                st.warning(res.get("errors", ["Secret not found"])[0] if "errors" in res else "Not found")

    with tab2:
        st.subheader("Write Secret")
        with st.form("vault_write"):
            w_path = st.text_input("Path", value="secret/data/myapp",
                                   help="KV v2: secret/data/myapp | KV v1: secret/myapp")
            w_key   = st.text_input("Key")
            w_value = st.text_input("Value", type="password")
            if st.form_submit_button("💾 Write"):
                payload = {"data": {w_key: w_value}} if "secret/data/" in w_path else {w_key: w_value}
                res = v_post(w_path, payload)
                if "error" not in res:
                    st.success(f"Secret written to `{w_path}`")
                else:
                    st.error(res["error"])

        st.divider()
        st.subheader("Secret Engines")
        if st.button("📋 List Engines"):
            res = v_get("sys/mounts")
            for path, info in res.items():
                if isinstance(info, dict) and "type" in info:
                    st.markdown(f"- `{path}` → **{info['type']}** {info.get('description','')}")

    with tab3:
        st.subheader("Policies")
        if st.button("📋 List Policies"):
            res = v_get("sys/policy")
            for p in res.get("policies", []):
                st.markdown(f"- `{p}`")

        st.divider()
        st.subheader("Read Policy")
        pol_name = st.text_input("Policy name", value="default")
        if st.button("🔍 Read Policy"):
            res = v_get(f"sys/policy/{pol_name}")
            st.code(res.get("rules", "No rules"), language="hcl")

        st.divider()
        st.subheader("Write Policy")
        with st.form("vault_policy"):
            np_name  = st.text_input("Policy name")
            np_rules = st.text_area("HCL rules",
                value='path "secret/*" {\n  capabilities = ["read", "list"]\n}', height=150)
            if st.form_submit_button("💾 Save Policy"):
                import httpx as _hx2
                r = _hx2.put(f"{VAULT_URL}/v1/sys/policy/{np_name}",
                             headers=_vh, json={"rules": np_rules}, timeout=8)
                if r.status_code == 204:
                    st.success(f"Policy '{np_name}' saved")
                else:
                    st.error(r.text)

    with tab4:
        st.subheader("Create Token")
        with st.form("vault_token"):
            t_policies = st.multiselect("Policies", ["default", "root"], default=["default"])
            t_ttl      = st.text_input("TTL", value="24h")
            t_name     = st.text_input("Display name", value="mcp-token")
            if st.form_submit_button("🔑 Create Token"):
                res = v_post("auth/token/create", {"policies": t_policies, "ttl": t_ttl, "display_name": t_name})
                if "auth" in res:
                    st.success("Token created!")
                    st.code(res["auth"]["client_token"])
                    st.info(f"TTL: {res['auth']['lease_duration']}s | Policies: {res['auth']['policies']}")
                else:
                    st.error(str(res))

        st.divider()
        st.subheader("Auth Methods")
        if st.button("📋 List Auth Methods"):
            res = v_get("sys/auth")
            for path, info in res.items():
                if isinstance(info, dict) and "type" in info:
                    st.markdown(f"- `{path}` → **{info['type']}**")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 12 — LOKI LOGS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📜 Loki Logs":
    st.title("📜 Loki Log Explorer")
    st.caption(f"Endpoint: {LOKI_URL}")

    import httpx as _hx
    import time as _time

    try:
        _lr = _hx.get(f"{LOKI_URL}/ready", timeout=5)
        if _lr.status_code == 200:
            st.success("🟢 Loki is ready")
        else:
            st.error(f"🔴 Loki not ready: HTTP {_lr.status_code}")
    except Exception as _e:
        st.error(f"🔴 Loki unreachable: {_e}")
        st.stop()

    def loki_query(logql, limit=100, since_h=1):
        end = int(_time.time() * 1e9)
        start = int((_time.time() - since_h * 3600) * 1e9)
        try:
            r = _hx.get(f"{LOKI_URL}/loki/api/v1/query_range",
                        params={"query": logql, "limit": limit, "start": start,
                                "end": end, "direction": "backward"}, timeout=20)
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    tab1, tab2, tab3 = st.tabs(["Query Logs", "Labels", "Error Monitor"])

    with tab1:
        st.subheader("LogQL Query")
        col1, col2, col3 = st.columns([3, 1, 1])
        logql   = col1.text_input("LogQL", value='{namespace="devops"}', key="loki_q")
        since_h = col2.number_input("Hours back", 1, 72, value=1)
        limit   = col3.number_input("Limit", 10, 500, value=50)

        if st.button("🔍 Query Logs", type="primary"):
            with st.spinner("Querying Loki..."):
                res = loki_query(logql, limit=int(limit), since_h=int(since_h))
            if "error" in res:
                st.error(res["error"])
            else:
                streams = res.get("data", {}).get("result", [])
                if not streams:
                    st.info("No logs found")
                else:
                    lines = []
                    for stream in streams:
                        labels = stream.get("stream", {})
                        ns  = labels.get("namespace", "?")
                        pod = labels.get("pod", labels.get("app", "?"))
                        for ts, log in stream.get("values", []):
                            t = _time.strftime("%H:%M:%S", _time.localtime(int(ts) // 1_000_000_000))
                            lines.append(f"{t} [{ns}/{pod}] {log}")
                    st.code("\n".join(lines[:int(limit)]), language="bash")

        st.divider()
        st.subheader("Quick Filters")
        col_a, col_b = st.columns(2)
        app_filter = col_a.text_input("App label", placeholder="jenkins")
        kw_filter  = col_b.text_input("Keyword filter", placeholder="error")

        if st.button("🔍 Quick Search"):
            base = f'{{namespace="devops"{f", app=\"{app_filter}\"" if app_filter else ""}}}'
            q = f'{base} |= "{kw_filter}"' if kw_filter else base
            with st.spinner("Searching..."):
                res = loki_query(q, limit=50, since_h=2)
            streams = res.get("data", {}).get("result", [])
            lines = []
            for stream in streams:
                labels = stream.get("stream", {})
                for ts, log in stream.get("values", []):
                    t = _time.strftime("%H:%M:%S", _time.localtime(int(ts) // 1_000_000_000))
                    lines.append(f"{t} [{labels.get('pod','?')}] {log}")
            if lines:
                st.code("\n".join(lines), language="bash")
            else:
                st.info("No matching logs")

    with tab2:
        st.subheader("Available Labels")
        if st.button("📋 List Labels"):
            try:
                r = _hx.get(f"{LOKI_URL}/loki/api/v1/labels", timeout=8)
                labels = r.json().get("data", [])
                cols = st.columns(4)
                for i, l in enumerate(labels):
                    cols[i % 4].markdown(f"- `{l}`")
            except Exception as e:
                st.error(str(e))

        st.divider()
        label_sel = st.text_input("Get values for label", value="namespace")
        if st.button("🔍 Get Values"):
            try:
                r = _hx.get(f"{LOKI_URL}/loki/api/v1/label/{label_sel}/values", timeout=8)
                vals = r.json().get("data", [])
                for v in vals:
                    st.markdown(f"- `{v}`")
            except Exception as e:
                st.error(str(e))

    with tab3:
        st.subheader("Error Monitor — Last 1h")
        if st.button("🚨 Check Errors", type="primary"):
            with st.spinner("Scanning for errors..."):
                res = loki_query('{namespace="devops"} |~ "(?i)(error|exception|fatal|panic)"', limit=100, since_h=1)
            streams = res.get("data", {}).get("result", [])
            if not streams:
                st.success("✅ No errors in the last hour!")
            else:
                lines = []
                for stream in streams:
                    labels = stream.get("stream", {})
                    pod = labels.get("pod", labels.get("app", "?"))
                    for ts, log in stream.get("values", []):
                        t = _time.strftime("%H:%M:%S", _time.localtime(int(ts) // 1_000_000_000))
                        lines.append(f"{t} [{pod}] {log}")
                st.warning(f"⚠️ {len(lines)} error log entries found")
                st.code("\n".join(lines), language="bash")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 13 — CONTAINER REGISTRY
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📦 Container Registry":
    st.title("📦 Container Registry")
    st.caption(f"API: {REGISTRY_URL} | UI: {REGISTRY_UI_URL}")

    import httpx as _hx

    try:
        r = _hx.get(f"{REGISTRY_URL}/v2/", timeout=5)
        st.success(f"🟢 Registry healthy | UI: [{REGISTRY_UI_URL}]({REGISTRY_UI_URL})")
    except Exception as e:
        st.error(f"🔴 Registry unreachable: {e}")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["Browse", "Delete Image", "Push Instructions"])

    with tab1:
        st.subheader("Repositories")
        if st.button("📋 List Repositories", type="primary"):
            r = _hx.get(f"{REGISTRY_URL}/v2/_catalog", timeout=8)
            repos = r.json().get("repositories", [])
            if repos:
                for repo in repos:
                    with st.expander(f"📦 {repo}"):
                        tr = _hx.get(f"{REGISTRY_URL}/v2/{repo}/tags/list", timeout=8)
                        tags = tr.json().get("tags", []) or []
                        for tag in tags:
                            st.markdown(f"  - `{repo}:{tag}`")
            else:
                st.info("No images pushed yet")
                st.markdown("**Push your first image:**")
                st.code(f"docker tag myapp:latest 127.0.0.1:30880/myapp:latest\ndocker push 127.0.0.1:30880/myapp:latest", language="bash")

        st.divider()
        st.subheader("Image Tags")
        repo_name = st.text_input("Repository name", placeholder="myapp")
        if st.button("🔍 List Tags") and repo_name:
            r = _hx.get(f"{REGISTRY_URL}/v2/{repo_name}/tags/list", timeout=8)
            tags = r.json().get("tags", []) or []
            if tags:
                st.dataframe([{"Tag": t, "Pull": f"docker pull 127.0.0.1:30880/{repo_name}:{t}"} for t in tags],
                             use_container_width=True)
            else:
                st.info("No tags found")

    with tab2:
        st.subheader("Delete Image Tag")
        st.warning("Deletion removes the manifest. Run garbage-collect to free disk space.")
        with st.form("del_image"):
            del_repo = st.text_input("Repository")
            del_tag  = st.text_input("Tag", value="latest")
            if st.form_submit_button("🗑 Delete", type="primary"):
                # Get digest first
                mr = _hx.get(f"{REGISTRY_URL}/v2/{del_repo}/manifests/{del_tag}",
                             headers={"Accept": "application/vnd.docker.distribution.manifest.v2+json"},
                             timeout=8)
                digest = mr.headers.get("Docker-Content-Digest")
                if digest:
                    dr = _hx.delete(f"{REGISTRY_URL}/v2/{del_repo}/manifests/{digest}", timeout=8)
                    if dr.status_code == 202:
                        st.success(f"Deleted `{del_repo}:{del_tag}`")
                    else:
                        st.error(f"Delete failed: HTTP {dr.status_code}")
                else:
                    st.error("Could not get image digest")

    with tab3:
        st.subheader("How to Push Images")
        st.info("This registry runs without TLS — add it as an insecure registry in Docker Desktop settings.")
        st.code("""# 1. Add to Docker Desktop → Settings → Docker Engine:
{
  "insecure-registries": ["127.0.0.1:30880"]
}

# 2. Tag & push
docker tag myapp:latest 127.0.0.1:30880/myapp:latest
docker push 127.0.0.1:30880/myapp:latest

# 3. Pull in K8s pod spec
image: 127.0.0.1:30880/myapp:latest""", language="bash")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 14 — MINIO
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🗄️ MinIO Storage":
    st.title("🗄️ MinIO Object Storage")
    st.caption(f"API: {MINIO_URL} | Console: [{MINIO_CONSOLE_URL}]({MINIO_CONSOLE_URL})")

    import httpx as _hx

    try:
        r = _hx.get(f"{MINIO_URL}/minio/health/ready", timeout=5)
        if r.status_code == 200:
            st.success(f"🟢 MinIO healthy | Console: {MINIO_CONSOLE_URL}")
        else:
            st.error(f"🔴 MinIO not ready: HTTP {r.status_code}")
            st.stop()
    except Exception as e:
        st.error(f"🔴 MinIO unreachable: {e}")
        st.stop()

    def mc(args):
        import subprocess as _sp
        _sp.run(["mc", "alias", "set", "myminio", MINIO_URL, "admin", "Admin@123456789@"],
                capture_output=True, timeout=10)
        r = _sp.run(["mc", "--json"] + args.split(), capture_output=True, text=True, timeout=30)
        return r.stdout, r.stderr, r.returncode

    mc_ok = bool(__import__("shutil").which("mc"))

    tab1, tab2, tab3 = st.tabs(["Buckets", "Objects", "Settings"])

    with tab1:
        st.subheader("Buckets")
        if st.button("📋 List Buckets", type="primary"):
            if mc_ok:
                out, err, rc = mc("ls myminio")
                import json as _j
                lines = []
                for line in out.splitlines():
                    try:
                        d = _j.loads(line)
                        lines.append({"Bucket": d.get("key",""), "Type": d.get("type","")})
                    except Exception:
                        if line.strip(): lines.append({"Bucket": line, "Type": ""})
                if lines:
                    st.dataframe(lines, use_container_width=True)
                else:
                    st.info("No buckets found")
            else:
                st.warning("`mc` not installed. Run: `brew install minio-mc`")
                st.markdown(f"Open the MinIO Console at [{MINIO_CONSOLE_URL}]({MINIO_CONSOLE_URL}) to manage buckets.")

        st.divider()
        st.subheader("Create Bucket")
        with st.form("create_bucket"):
            bucket_name = st.text_input("Bucket name")
            if st.form_submit_button("➕ Create"):
                if mc_ok:
                    _, err, rc = mc(f"mb myminio/{bucket_name}")
                    if rc == 0:
                        st.success(f"Bucket '{bucket_name}' created")
                    else:
                        st.error(err)
                else:
                    st.warning("Install `mc` to create buckets via CLI")

    with tab2:
        st.subheader("Browse Objects")
        b_name = st.text_input("Bucket name", key="minio_browse")
        if st.button("📂 List Objects") and b_name:
            if mc_ok:
                out, err, rc = mc(f"ls myminio/{b_name}")
                import json as _j
                lines = []
                for line in out.splitlines():
                    try:
                        d = _j.loads(line)
                        lines.append({"Object": d.get("key",""), "Size": d.get("size",0), "Modified": d.get("lastModified","")[:19]})
                    except Exception:
                        if line.strip(): lines.append({"Object": line, "Size": 0, "Modified": ""})
                if lines:
                    st.dataframe(lines, use_container_width=True)
                else:
                    st.info("No objects in bucket")
            else:
                st.warning("Install `mc`: `brew install minio-mc`")

    with tab3:
        st.subheader("Connection Info")
        st.code(f"""# MinIO credentials
Access Key: admin
Secret Key: Admin@123456789@
API:        {MINIO_URL}
Console:    {MINIO_CONSOLE_URL}

# Configure mc client
mc alias set myminio {MINIO_URL} admin Admin@123456789@

# S3 compatible endpoint (for Terraform, etc.)
endpoint = "{MINIO_URL}"
access_key = "admin"
secret_key = "Admin@123456789@"
""", language="bash")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 15 — NEXUS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏛️ Nexus Repository":
    st.title("🏛️ Nexus Repository Manager")
    st.caption(f"URL: {NEXUS_URL}")

    import httpx as _hx

    try:
        r = _hx.get(f"{NEXUS_URL}/service/rest/v1/status", auth=NEXUS_AUTH, timeout=8)
        if r.status_code == 200:
            st.success("🟢 Nexus is healthy")
        else:
            st.error(f"🔴 Nexus: HTTP {r.status_code}")
            st.stop()
    except Exception as e:
        st.error(f"🔴 Nexus unreachable: {e}")
        st.stop()

    def nx_get(path, params={}):
        try:
            r = _hx.get(f"{NEXUS_URL}/service/rest{path}", auth=NEXUS_AUTH, params=params, timeout=10)
            return r.json() if r.text else {}
        except Exception as e:
            return {"error": str(e)}

    def nx_post(path, data):
        try:
            r = _hx.post(f"{NEXUS_URL}/service/rest{path}", auth=NEXUS_AUTH, json=data,
                         headers={"Content-Type": "application/json"}, timeout=10)
            return r.status_code, r.text
        except Exception as e:
            return 0, str(e)

    tab1, tab2, tab3, tab4 = st.tabs(["Repositories", "Search", "Create Repo", "Users"])

    with tab1:
        st.subheader("All Repositories")
        if st.button("📋 List Repositories", type="primary"):
            res = nx_get("/v1/repositories")
            repos = res if isinstance(res, list) else []
            if repos:
                df = [{"Name": r["name"], "Format": r.get("format","?"),
                       "Type": r.get("type","?"), "URL": r.get("url","")} for r in repos]
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No repositories or error loading")

    with tab2:
        st.subheader("Search Components")
        col1, col2 = st.columns(2)
        repo_s   = col1.text_input("Repository (optional)")
        keyword  = col2.text_input("Keyword")
        if st.button("🔍 Search") and keyword:
            params = {"keyword": keyword}
            if repo_s: params["repository"] = repo_s
            res = nx_get("/v1/search", params)
            items = res.get("items", [])
            if items:
                df = [{"Group": c.get("group",""), "Name": c.get("name",""),
                       "Version": c.get("version",""), "Repository": c.get("repository","")}
                      for c in items[:30]]
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No components found")

    with tab3:
        st.subheader("Create Hosted Repository")
        with st.form("nexus_create_repo"):
            rn = st.text_input("Repository name")
            rf = st.selectbox("Format", ["maven2", "npm", "pypi", "raw", "docker", "helm"])
            if st.form_submit_button("➕ Create"):
                payload = {
                    "name": rn, "online": True,
                    "storage": {"blobStoreName": "default", "strictContentTypeValidation": True, "writePolicy": "allow"},
                }
                if rf == "maven2":
                    payload["maven"] = {"versionPolicy": "MIXED", "layoutPolicy": "STRICT"}
                code, resp = nx_post(f"/v1/repositories/{rf}/hosted", payload)
                if code in [200, 201]:
                    st.success(f"Repository '{rn}' ({rf}) created!")
                else:
                    st.error(f"HTTP {code}: {resp[:300]}")

        st.divider()
        st.subheader("Create Proxy Repository")
        with st.form("nexus_proxy_repo"):
            pn = st.text_input("Repository name", placeholder="npm-proxy")
            pf = st.selectbox("Format", ["npm", "maven2", "pypi", "raw"], key="pf")
            pu = st.text_input("Remote URL", placeholder="https://registry.npmjs.org")
            if st.form_submit_button("➕ Create Proxy"):
                payload = {
                    "name": pn, "online": True,
                    "storage": {"blobStoreName": "default", "strictContentTypeValidation": True},
                    "proxy": {"remoteUrl": pu, "contentMaxAge": 1440, "metadataMaxAge": 1440},
                    "negativeCache": {"enabled": True, "timeToLive": 1440},
                    "httpClient": {"blocked": False, "autoBlock": True},
                }
                code, resp = nx_post(f"/v1/repositories/{pf}/proxy", payload)
                if code in [200, 201]:
                    st.success(f"Proxy repository '{pn}' created!")
                else:
                    st.error(f"HTTP {code}: {resp[:300]}")

    with tab4:
        st.subheader("Users")
        if st.button("📋 List Users"):
            res = nx_get("/v1/security/users")
            users = res if isinstance(res, list) else []
            if users:
                df = [{"User": u.get("userId",""), "Name": f"{u.get('firstName','')} {u.get('lastName','')}",
                       "Email": u.get("emailAddress",""), "Status": u.get("status","")} for u in users]
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No users found")
