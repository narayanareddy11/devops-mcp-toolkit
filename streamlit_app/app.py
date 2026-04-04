"""
DevOps MCP Toolkit — Streamlit Control Panel
Visual interface for all 9 MCP servers.
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
GRAFANA_AUTH = ("admin", "admin")
ARGOCD_URL  = "http://localhost:30085"

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
    ],
)

st.sidebar.divider()
st.sidebar.markdown("**Services**")
st.sidebar.markdown(f"Jenkins → [localhost:30080]({JENKINS_URL})")
st.sidebar.markdown(f"SonarQube → [localhost:30900]({SONAR_URL})")
st.sidebar.markdown(f"Prometheus → [localhost:30090]({PROM_URL})")
st.sidebar.markdown(f"Grafana → [localhost:30030]({GRAFANA_URL})")
st.sidebar.markdown(f"ArgoCD → [localhost:30085]({ARGOCD_URL})")

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
    import httpx as _hx
    def _port_up(port):
        import socket; s = socket.socket(); s.settimeout(2)
        ok = s.connect_ex(("localhost", port)) == 0; s.close(); return ok

    col6, col7, col8, col9 = st.columns(4)
    prom_up = _port_up(30090)
    col6.metric("Prometheus", "localhost:30090", delta=status_icon(prom_up))
    graf_up = _port_up(30030)
    col7.metric("Grafana", "localhost:30030", delta=status_icon(graf_up))
    argo_up = _port_up(30085)
    col8.metric("ArgoCD", "localhost:30085", delta=status_icon(argo_up))
    import shutil as _sh
    trivy_ok = bool(_sh.which("trivy"))
    col9.metric("Trivy", "installed" if trivy_ok else "not installed", delta=status_icon(trivy_ok))

    st.divider()

    # Port status
    st.subheader("Port Status")
    all_ports = {
        **health["ports"],
        "Prometheus:30090": prom_up,
        "Grafana:30030":    graf_up,
        "ArgoCD:30085":     argo_up,
    }
    pcols = st.columns(len(all_ports))
    for i, (name, open_) in enumerate(all_ports.items()):
        pcols[i].markdown(f"{'🟢' if open_ else '🔴'} **{name}**")

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
