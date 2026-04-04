# CLAUDE.md — DevOps MCP Server Project

## What This Project Is
9 Python MCP servers that let Claude control a local DevOps stack running on Kubernetes (Docker Desktop).
All services live in the `devops` or `argocd` namespace. No cloud account required.

---

## K8s Services

| Service      | Container           | NodePort                   | Credentials              |
|--------------|---------------------|----------------------------|--------------------------|
| Jenkins      | `deploy/jenkins`    | http://localhost:30080     | admin / admin1234@       |
| SonarQube    | `deploy/sonarqube`  | http://localhost:30900     | admin / Aa75696462461@   |
| PostgreSQL   | `deploy/postgres`   | ClusterIP only (internal)  | sonar / sonar            |
| Prometheus   | `deploy/prometheus` | http://localhost:30090     | no auth                  |
| Grafana      | `deploy/grafana`    | http://localhost:30030     | admin / admin1234@       |
| ArgoCD       | `argocd-server`     | http://localhost:30085     | admin / admin1234@       |

---

## MCP Servers

| # | File                               | MCP Name             | Controls                          |
|---|------------------------------------|----------------------|-----------------------------------|
| 1 | `servers/01_docker_manager.py`     | docker-manager       | Docker containers & images        |
| 2 | `servers/02_terraform_manager.py`  | terraform-manager    | Terraform CLI (local example)     |
| 3 | `servers/03_sonarqube_manager.py`  | sonarqube-manager    | SonarQube REST API                |
| 4 | `servers/04_jenkins_manager.py`    | jenkins-manager      | Jenkins REST API                  |
| 5 | `servers/05_devops_dashboard.py`   | devops-dashboard     | Unified health across all         |
| 6 | `servers/06_kubernetes_manager.py` | kubernetes-manager   | kubectl / K8s resources           |
| 7 | `servers/07_prometheus_grafana.py` | prometheus-grafana   | Prometheus PromQL + Grafana API   |
| 8 | `servers/08_argocd_manager.py`     | argocd-manager       | ArgoCD GitOps deployments         |
| 9 | `servers/09_trivy_scanner.py`      | trivy-scanner        | Trivy CVE & IaC scanning          |

---

## Project Structure

```
mcp-server-01/
├── CLAUDE.md                        ← this file
├── requirements.txt                 ← pip deps: mcp[cli], httpx
├── claude_mcp_config.json           ← MCP server config (all 9 servers)
├── servers/
│   ├── 01_docker_manager.py
│   ├── 02_terraform_manager.py
│   ├── 03_sonarqube_manager.py
│   ├── 04_jenkins_manager.py
│   ├── 05_devops_dashboard.py
│   ├── 06_kubernetes_manager.py
│   ├── 07_prometheus_grafana.py
│   ├── 08_argocd_manager.py
│   └── 09_trivy_scanner.py
├── k8s/
│   ├── namespace.yaml
│   ├── jenkins/
│   ├── sonarqube/
│   ├── postgres/
│   ├── prometheus/
│   │   ├── configmap.yaml        ← scrape configs (K8s, Jenkins, Sonar)
│   │   ├── rbac.yaml             ← ClusterRole for K8s discovery
│   │   └── deployment.yaml       ← NodePort 30090
│   ├── grafana/
│   │   ├── configmap.yaml        ← datasource provisioning
│   │   ├── deployment.yaml       ← NodePort 30030
│   │   └── service.yaml
│   └── argocd/
│       ├── namespace.yaml
│       └── nodeport-patch.yaml   ← exposes argocd-server on 30085/30086
├── streamlit_app/
│   ├── app.py                    ← 9-page control panel
│   └── utils.py                  ← shared http/shell helpers
├── tests/
│   ├── conftest.py
│   ├── test_01_docker_manager.py
│   ├── test_02_terraform_manager.py
│   ├── test_03_sonarqube_manager.py
│   └── test_04_jenkins_manager.py
└── terraform/
    └── local/
        ├── main.tf               ← local + null providers (no cloud needed)
        ├── variables.tf
        ├── outputs.tf
        └── terraform.tfvars
```

---

## Environment Variables

| Variable        | Value                  | Used by                                      |
|-----------------|------------------------|----------------------------------------------|
| JENKINS_URL     | http://localhost:30080 | jenkins-manager, devops-dashboard            |
| JENKINS_USER    | admin                  | jenkins-manager, devops-dashboard            |
| JENKINS_PASS    | admin1234@             | jenkins-manager, devops-dashboard            |
| SONAR_URL       | http://localhost:30900 | sonarqube-manager, devops-dashboard          |
| SONAR_USER      | admin                  | sonarqube-manager, devops-dashboard          |
| SONAR_PASS      | Aa75696462461@         | sonarqube-manager, devops-dashboard          |
| PROMETHEUS_URL  | http://localhost:30090 | prometheus-grafana                           |
| GRAFANA_URL     | http://localhost:30030 | prometheus-grafana                           |
| GRAFANA_USER    | admin                  | prometheus-grafana                           |
| GRAFANA_PASS    | admin1234@             | prometheus-grafana                           |
| ARGOCD_URL      | http://localhost:30085 | argocd-manager                               |
| ARGOCD_USER     | admin                  | argocd-manager                               |

---

## Key Commands

### Deploy the full stack
```bash
# Core namespace + services
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/postgres/
kubectl apply -f k8s/jenkins/
kubectl apply -f k8s/sonarqube/

# Observability
kubectl apply -f k8s/prometheus/
kubectl apply -f k8s/grafana/

# ArgoCD
kubectl apply -f k8s/argocd/namespace.yaml
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl patch svc argocd-server -n argocd --patch "$(cat k8s/argocd/nodeport-patch.yaml)"
```

### Check stack status
```bash
kubectl get pods -n devops
kubectl get pods -n argocd
kubectl get svc -n devops
```

### Re-register all MCP servers
```bash
claude mcp add docker-manager    -- python3 servers/01_docker_manager.py
claude mcp add terraform-manager -- python3 servers/02_terraform_manager.py
claude mcp add sonarqube-manager -e SONAR_URL=http://localhost:30900 -e SONAR_USER=admin -e SONAR_PASS='Aa75696462461@' -- python3 servers/03_sonarqube_manager.py
claude mcp add jenkins-manager   -e JENKINS_URL=http://localhost:30080 -e JENKINS_USER=admin -e JENKINS_PASS=admin -- python3 servers/04_jenkins_manager.py
claude mcp add devops-dashboard  -e JENKINS_URL=http://localhost:30080 -e JENKINS_USER=admin -e JENKINS_PASS=admin -e SONAR_URL=http://localhost:30900 -e SONAR_USER=admin -e SONAR_PASS='Aa75696462461@' -- python3 servers/05_devops_dashboard.py
claude mcp add kubernetes-manager -- python3 servers/06_kubernetes_manager.py
claude mcp add prometheus-grafana -e PROMETHEUS_URL=http://localhost:30090 -e GRAFANA_URL=http://localhost:30030 -- python3 servers/07_prometheus_grafana.py
claude mcp add argocd-manager    -e ARGOCD_URL=http://localhost:30085 -- python3 servers/08_argocd_manager.py
claude mcp add trivy-scanner     -- python3 servers/09_trivy_scanner.py
```

### ArgoCD admin password
```bash
kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath='{.data.password}' | base64 --decode
```

### Install dependencies
```bash
pip3 install -r requirements.txt
brew install terraform          # for terraform-manager
brew install trivy              # for trivy-scanner
brew install sonar-scanner      # optional, for running analysis
```

### Run Streamlit dashboard
```bash
python3 -m streamlit run streamlit_app/app.py --server.port 8501
```

---

## Coding Rules
- All MCP servers use `FastMCP` from `mcp.server.fastmcp`
- Transport is always `stdio` — never change to SSE or HTTP
- Credentials come from environment variables only — never hardcoded
- HTTP calls use `httpx` (not `requests`)
- Jenkins POST requests require a fresh CSRF crumb — always call `_crumb()` in a new session before posting
- Terraform runs via `subprocess` with `cwd=workdir` and `TF_IN_AUTOMATION=1`
- K8s commands run via `subprocess` wrapping `kubectl`
- ArgoCD uses JWT token auth — `_get_token()` fetches fresh token via `/api/v1/session` on each request
- Trivy runs via subprocess; `verify=False` on ArgoCD httpx calls (self-signed cert)

## Known Fixes Applied
- **SonarQube readiness probe**: uses `tcpSocket` (not HTTP) because `/api/system/ping` returns 401
- **SonarQube Elasticsearch**: `SONAR_SEARCH_JAVAOPTS=-Dnode.store.allow_mmap=false` required for Docker Desktop (no sysctl access)
- **Streamlit ternary bug**: `st.success(...) if x else st.error(...)` raises `StreamlitAPIException`. Always use `if/else` blocks with the `show(result, msg)` helper.

## Adding a New MCP Server
1. Create `servers/0N_name.py` using `FastMCP` pattern
2. Add `@mcp.tool()` functions with clear docstrings
3. End with `if __name__ == "__main__": mcp.run(transport="stdio")`
4. Register: `claude mcp add name -- python3 servers/0N_name.py`
5. Add entry to `claude_mcp_config.json`
6. Add a page to `streamlit_app/app.py`
