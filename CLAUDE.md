# CLAUDE.md — DevOps MCP Server Project

## What This Project Is
6 Python MCP servers that let Claude control a local DevOps stack running on Kubernetes (Docker Desktop).
All services live in the `devops` namespace. No cloud account required.

---

## K8s Services

| Service     | Container          | NodePort                   | Credentials              |
|-------------|--------------------|----------------------------|--------------------------|
| Jenkins     | `deploy/jenkins`   | http://localhost:30080     | admin / admin            |
| SonarQube   | `deploy/sonarqube` | http://localhost:30900     | admin / Aa75696462461@   |
| PostgreSQL  | `deploy/postgres`  | ClusterIP only (internal)  | sonar / sonar            |

---

## MCP Servers

| # | File                            | MCP Name             | Controls                  |
|---|---------------------------------|----------------------|---------------------------|
| 1 | `servers/01_docker_manager.py`  | docker-manager       | Docker containers & images |
| 2 | `servers/02_terraform_manager.py` | terraform-manager  | Terraform CLI (local example) |
| 3 | `servers/03_sonarqube_manager.py` | sonarqube-manager  | SonarQube REST API        |
| 4 | `servers/04_jenkins_manager.py` | jenkins-manager      | Jenkins REST API          |
| 5 | `servers/05_devops_dashboard.py`| devops-dashboard     | Unified health across all |
| 6 | `servers/06_kubernetes_manager.py` | kubernetes-manager | kubectl / K8s resources  |

---

## Project Structure

```
mcp-server-01/
├── CLAUDE.md                        ← this file
├── requirements.txt                 ← pip deps: mcp[cli], httpx
├── claude_mcp_config.json           ← MCP server config (all 6 servers)
├── servers/
│   ├── 01_docker_manager.py
│   ├── 02_terraform_manager.py
│   ├── 03_sonarqube_manager.py
│   ├── 04_jenkins_manager.py
│   ├── 05_devops_dashboard.py
│   └── 06_kubernetes_manager.py
├── k8s/
│   ├── namespace.yaml
│   ├── jenkins/
│   │   ├── deployment.yaml
│   │   ├── service.yaml          ← NodePort 30080
│   │   └── pvc.yaml
│   ├── sonarqube/
│   │   ├── deployment.yaml       ← includes mmap fix + TCP readiness probe
│   │   ├── service.yaml          ← NodePort 30900
│   │   └── pvc.yaml
│   └── postgres/
│       ├── deployment.yaml
│       ├── service.yaml          ← ClusterIP
│       ├── pvc.yaml
│       └── secret.yaml
└── terraform/
    └── local/
        ├── main.tf               ← local + null providers (no cloud needed)
        ├── variables.tf
        ├── outputs.tf
        ├── terraform.tfvars
        ├── .gitignore
        └── templates/
            └── app.conf.tpl
```

---

## Environment Variables

| Variable       | Value                | Used by                              |
|----------------|----------------------|--------------------------------------|
| JENKINS_URL    | http://localhost:30080 | jenkins-manager, devops-dashboard  |
| JENKINS_USER   | admin                | jenkins-manager, devops-dashboard    |
| JENKINS_PASS   | admin                | jenkins-manager, devops-dashboard    |
| SONAR_URL      | http://localhost:30900 | sonarqube-manager, devops-dashboard|
| SONAR_USER     | admin                | sonarqube-manager, devops-dashboard  |
| SONAR_PASS     | Aa75696462461@       | sonarqube-manager, devops-dashboard  |
| SONAR_TOKEN    | (optional)           | sonarqube-manager (preferred over pw)|

---

## Key Commands

### Deploy the full stack
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/postgres/
kubectl apply -f k8s/jenkins/
kubectl apply -f k8s/sonarqube/
```

### Check stack status
```bash
kubectl get pods -n devops
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
```

### Terraform local example
```bash
cd terraform/local
terraform init
terraform apply -auto-approve
terraform workspace new staging
```

### Jenkins — get initial admin password
```bash
kubectl exec -n devops deploy/jenkins -- cat /var/jenkins_home/secrets/initialAdminPassword
```

### Install dependencies
```bash
pip3 install -r requirements.txt
brew install terraform          # for terraform-manager
brew install sonar-scanner      # optional, for running analysis
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

## Known Fixes Applied
- **SonarQube readiness probe**: uses `tcpSocket` (not HTTP) because `/api/system/ping` returns 401
- **SonarQube Elasticsearch**: `SONAR_SEARCH_JAVAOPTS=-Dnode.store.allow_mmap=false` required for Docker Desktop (no sysctl access)

## Adding a New MCP Server
1. Create `servers/0N_name.py` using `FastMCP` pattern
2. Add `@mcp.tool()` functions with clear docstrings
3. End with `if __name__ == "__main__": mcp.run(transport="stdio")`
4. Register: `claude mcp add name -- python3 servers/0N_name.py`
5. Add entry to `claude_mcp_config.json`
