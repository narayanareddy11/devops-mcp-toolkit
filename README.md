# DevOps MCP Toolkit

> 6 open-source MCP servers that let Claude control a full local DevOps stack running on Kubernetes — no cloud account required.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.32-326CE5?logo=kubernetes&logoColor=white)](https://kubernetes.io)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-blueviolet)](https://modelcontextprotocol.io)
[![Jenkins](https://img.shields.io/badge/Jenkins-2.541-D24939?logo=jenkins&logoColor=white)](https://jenkins.io)
[![SonarQube](https://img.shields.io/badge/SonarQube-Community-4E9BCD?logo=sonarqube&logoColor=white)](https://sonarqube.org)
[![Terraform](https://img.shields.io/badge/Terraform-1.5%2B-7B42BC?logo=terraform&logoColor=white)](https://terraform.io)

---

## Streamlit Control Panel

> Visual browser UI to control all 6 MCP servers — run with `python3 -m streamlit run streamlit_app/app.py`

| Dashboard | Docker Manager |
|-----------|---------------|
| ![Dashboard](docs/screenshots/01_dashboard.png) | ![Docker](docs/screenshots/02_docker.png) |

| Jenkins Manager | SonarQube Manager |
|----------------|------------------|
| ![Jenkins](docs/screenshots/03_jenkins.png) | ![SonarQube](docs/screenshots/04_sonarqube.png) |

---

## What It Does

This toolkit exposes your entire local DevOps stack as MCP tools that Claude can call directly. Instead of switching between terminals and UIs, you interact with Jenkins, SonarQube, Docker, Terraform, and Kubernetes through natural language.

**Example prompts:**
- *"Trigger the k8s-demo build in Jenkins and show me the console log"*
- *"Create a SonarQube project called my-app and generate a scanner token"*
- *"Run terraform plan on the local example and apply it to staging workspace"*
- *"Show me CPU and memory stats for all pods in the devops namespace"*
- *"What is the health of all DevOps services?"*

---

## Architecture

```
Claude (claude.ai / Claude Code CLI)
        │
        │  MCP (stdio)
        ▼
┌───────────────────────────────────────────────────┐
│                 MCP Servers (Python)               │
│                                                   │
│  01 docker-manager      → Docker CLI              │
│  02 terraform-manager   → Terraform CLI           │
│  03 sonarqube-manager   → SonarQube REST API      │
│  04 jenkins-manager     → Jenkins REST API        │
│  05 devops-dashboard    → Unified health check    │
│  06 kubernetes-manager  → kubectl / K8s API       │
└───────────────────────────────────────────────────┘
        │
        │  Kubernetes (Docker Desktop)
        ▼
┌───────────────────────────────────────────────────┐
│              devops namespace                      │
│                                                   │
│  Jenkins      NodePort :30080                     │
│  SonarQube    NodePort :30900                     │
│  PostgreSQL   ClusterIP (internal)                │
└───────────────────────────────────────────────────┘
```

---

## MCP Servers

| # | Server | Tools | Description |
|---|--------|-------|-------------|
| 1 | `docker-manager` | 15 | Containers, images, volumes, compose, stats, logs |
| 2 | `terraform-manager` | 12 | init, plan, apply, destroy, state, workspaces |
| 3 | `sonarqube-manager` | 12 | Projects, metrics, issues, quality gates, tokens |
| 4 | `jenkins-manager` | 14 | Jobs, builds, logs, queue, plugins, nodes |
| 5 | `devops-dashboard` | 7 | Unified health, port checks, service summaries |
| 6 | `kubernetes-manager` | 18 | Pods, deployments, services, PVCs, events, rollouts |

---

## Prerequisites

| Tool | Install |
|------|---------|
| Docker Desktop (with K8s enabled) | [docker.com](https://www.docker.com/products/docker-desktop/) |
| Python 3.11+ | `brew install python` |
| Claude Code CLI | [claude.ai/code](https://claude.ai/code) |
| kubectl | bundled with Docker Desktop |
| Terraform | `brew install terraform` |

---

## Quick Start

### 1. Clone & install
```bash
git clone https://github.com/narayanareddy11/devops-mcp-toolkit.git
cd devops-mcp-toolkit
pip3 install -r requirements.txt
```

### 2. Deploy to Kubernetes
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/postgres/
kubectl apply -f k8s/jenkins/
kubectl apply -f k8s/sonarqube/

# Wait for all pods to be ready
kubectl wait --for=condition=ready pod --all -n devops --timeout=300s
```

### 3. Verify services
```bash
kubectl get pods -n devops
# Jenkins   → http://localhost:30080  (admin / admin)
# SonarQube → http://localhost:30900  (admin / admin)
```

### 4. Register MCP servers with Claude Code
```bash
claude mcp add docker-manager \
  -- python3 servers/01_docker_manager.py

claude mcp add terraform-manager \
  -- python3 servers/02_terraform_manager.py

claude mcp add sonarqube-manager \
  -e SONAR_URL=http://localhost:30900 \
  -e SONAR_USER=admin \
  -e SONAR_PASS=admin \
  -- python3 servers/03_sonarqube_manager.py

claude mcp add jenkins-manager \
  -e JENKINS_URL=http://localhost:30080 \
  -e JENKINS_USER=admin \
  -e JENKINS_PASS=admin \
  -- python3 servers/04_jenkins_manager.py

claude mcp add devops-dashboard \
  -e JENKINS_URL=http://localhost:30080 \
  -e JENKINS_USER=admin \
  -e JENKINS_PASS=admin \
  -e SONAR_URL=http://localhost:30900 \
  -e SONAR_USER=admin \
  -e SONAR_PASS=admin \
  -- python3 servers/05_devops_dashboard.py

claude mcp add kubernetes-manager \
  -- python3 servers/06_kubernetes_manager.py
```

### 5. (Optional) Terraform local example
```bash
cd terraform/local
terraform init
terraform apply -auto-approve
```

---

## Project Structure

```
devops-mcp-toolkit/
├── LICENSE
├── README.md
├── CLAUDE.md                        ← context for Claude Code
├── requirements.txt
├── claude_mcp_config.json           ← MCP config reference
├── servers/
│   ├── 01_docker_manager.py
│   ├── 02_terraform_manager.py
│   ├── 03_sonarqube_manager.py
│   ├── 04_jenkins_manager.py
│   ├── 05_devops_dashboard.py
│   └── 06_kubernetes_manager.py
├── k8s/
│   ├── namespace.yaml
│   ├── jenkins/                     ← NodePort 30080
│   ├── sonarqube/                   ← NodePort 30900
│   └── postgres/                    ← ClusterIP
└── terraform/
    └── local/                       ← local + null providers
```

---

## Known Issues & Fixes

| Issue | Fix Applied |
|-------|------------|
| SonarQube readiness probe returns 401 | Changed to `tcpSocket` probe |
| SonarQube Elasticsearch OOM on Docker Desktop | `SONAR_SEARCH_JAVAOPTS=-Dnode.store.allow_mmap=false` |
| Jenkins POST requests return 403 | Fetch fresh CSRF crumb per session |

---

## GitHub Actions

This repo includes two Claude-powered workflows:

- **`claude.yml`** — mention `@claude` in any issue or PR comment to invoke Claude Code
- **`claude-code-review.yml`** — automatically reviews every pull request with Claude

Both require `CLAUDE_CODE_OAUTH_TOKEN` to be set in repository secrets.

---

## Contributing

Pull requests are welcome. For major changes, open an issue first.

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/new-mcp-server`)
3. Commit your changes
4. Open a PR — Claude will auto-review it

---

## License

[MIT](LICENSE) © 2026 Narayana Reddy
