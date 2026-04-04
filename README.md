# DevOps MCP Toolkit

> **15 MCP servers** that let Claude AI control a complete local DevOps stack running on Kubernetes (Docker Desktop) — no cloud account required.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Docker%20Desktop-326CE5?logo=kubernetes&logoColor=white)](https://kubernetes.io)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-blueviolet)](https://modelcontextprotocol.io)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)

---

## What Is This?

Claude can talk directly to your local DevOps tools — start Jenkins builds, query Prometheus metrics, scan images with Trivy, manage Vault secrets, deploy with ArgoCD, and much more — all through natural language via the Model Context Protocol (MCP).

A **Streamlit control panel** provides a visual interface to all 15 tools.

---

## Streamlit Control Panel

> Run: `python3 -m streamlit run streamlit_app/app.py --server.port 8501`

### Dashboard Overview
| Dashboard | Docker Manager |
|:---------:|:--------------:|
| ![Dashboard](docs/screenshots/st_01_dashboard.png) | ![Docker](docs/screenshots/st_02_docker.png) |

### Infrastructure
| Kubernetes Manager | Terraform Manager |
|:-----------------:|:----------------:|
| ![Kubernetes](docs/screenshots/st_03_kubernetes.png) | ![Terraform](docs/screenshots/st_06_terraform.png) |

### CI / CD
| Jenkins Manager | SonarQube Manager | ArgoCD GitOps |
|:--------------:|:----------------:|:-------------:|
| ![Jenkins](docs/screenshots/st_04_jenkins.png) | ![SonarQube](docs/screenshots/st_05_sonarqube.png) | ![ArgoCD](docs/screenshots/st_08_argocd.png) |

### Security
| Trivy Scanner | Vault Secrets |
|:------------:|:------------:|
| ![Trivy](docs/screenshots/st_09_trivy.png) | ![Vault](docs/screenshots/st_11_vault.png) |

### Observability
| Prometheus & Grafana | Loki Logs |
|:-------------------:|:---------:|
| ![Prometheus](docs/screenshots/st_07_prometheus.png) | ![Loki](docs/screenshots/st_12_loki.png) |

### Storage & Deployment
| Helm Manager | Container Registry | MinIO Storage | Nexus Repository |
|:-----------:|:-----------------:|:------------:|:----------------:|
| ![Helm](docs/screenshots/st_10_helm.png) | ![Registry](docs/screenshots/st_13_registry.png) | ![MinIO](docs/screenshots/st_14_minio.png) | ![Nexus](docs/screenshots/st_15_nexus.png) |

---

## Live Tool UIs

Each tool runs natively in Kubernetes and is accessible from your browser.

### Jenkins — CI/CD Pipelines
> `http://localhost:30080` &nbsp;·&nbsp; admin / Admin@123456789@

![Jenkins UI](docs/screenshots/tool_jenkins.png)

---

### SonarQube — Code Quality
> `http://localhost:30900` &nbsp;·&nbsp; admin / Admin@123456789@

![SonarQube UI](docs/screenshots/tool_sonarqube.png)

---

### Grafana — Dashboards & Visualization
> `http://localhost:30030` &nbsp;·&nbsp; admin / Admin@123456789@

![Grafana UI](docs/screenshots/tool_grafana.png)

---

### Prometheus — Metrics & Alerting
> `http://localhost:30090` &nbsp;·&nbsp; no auth required

![Prometheus UI](docs/screenshots/tool_prometheus.png)

---

### ArgoCD — GitOps Deployments
> `https://localhost:30085` &nbsp;·&nbsp; admin / Admin@123456789@

![ArgoCD UI](docs/screenshots/tool_argocd.png)

---

### HashiCorp Vault — Secrets Management
> `http://localhost:30200` &nbsp;·&nbsp; Token: `root`

![Vault UI](docs/screenshots/tool_vault.png)

---

### MinIO — S3-Compatible Object Storage
> `http://localhost:30921` (Console) &nbsp;·&nbsp; admin / Admin@123456789@

![MinIO UI](docs/screenshots/tool_minio.png)

---

### Nexus Repository — Artifact Management
> `http://localhost:30081` &nbsp;·&nbsp; admin / Admin@123456789@

![Nexus UI](docs/screenshots/tool_nexus.png)

---

### Container Registry — Docker Image Registry
> `http://localhost:30881` (UI) &nbsp;·&nbsp; no auth

![Registry UI](docs/screenshots/tool_registry.png)

---

## MCP Servers — 185+ Tools

| # | Server | MCP Name | Tools | Controls |
|---|--------|----------|------:|----------|
| 1 | `servers/01_docker_manager.py` | `docker-manager` | 15 | Containers, images, volumes, networks |
| 2 | `servers/02_terraform_manager.py` | `terraform-manager` | 14 | Plan, apply, destroy, workspace mgmt |
| 3 | `servers/03_sonarqube_manager.py` | `sonarqube-manager` | 14 | Projects, issues, quality gates |
| 4 | `servers/04_jenkins_manager.py` | `jenkins-manager` | 15 | Jobs, builds, nodes, plugins, queue |
| 5 | `servers/05_devops_dashboard.py` | `devops-dashboard` | 7 | Unified health across all services |
| 6 | `servers/06_kubernetes_manager.py` | `kubernetes-manager` | 20 | Pods, deployments, services, namespaces |
| 7 | `servers/07_prometheus_grafana.py` | `prometheus-grafana` | 15 | PromQL queries, dashboards, datasources |
| 8 | `servers/08_argocd_manager.py` | `argocd-manager` | 12 | GitOps apps, sync, rollback, repos |
| 9 | `servers/09_trivy_scanner.py` | `trivy-scanner` | 10 | CVE scans, IaC checks, SBOM, K8s |
| 10 | `servers/10_helm_manager.py` | `helm-manager` | 14 | Install, upgrade, rollback, lint |
| 11 | `servers/11_vault_manager.py` | `vault-manager` | 16 | Secrets, policies, auth, tokens |
| 12 | `servers/12_loki_manager.py` | `loki-manager` | 10 | LogQL queries, pod logs, error detection |
| 13 | `servers/13_harbor_manager.py` | `harbor-manager` | 8 | Registry repos, tags, manifests |
| 14 | `servers/14_minio_manager.py` | `minio-manager` | 15 | Buckets, objects, policies, users |
| 15 | `servers/15_nexus_manager.py` | `nexus-manager` | 13 | Repos, components, assets, blob stores |

---

## Service Credentials

| Service | URL | Username | Password / Token |
|---------|-----|----------|:----------------:|
| Jenkins | http://localhost:30080 | admin | Admin@123456789@ |
| SonarQube | http://localhost:30900 | admin | Admin@123456789@ |
| Grafana | http://localhost:30030 | admin | Admin@123456789@ |
| Prometheus | http://localhost:30090 | — | no auth |
| ArgoCD | https://localhost:30085 | admin | Admin@123456789@ |
| HashiCorp Vault | http://localhost:30200 | — | token: `root` |
| MinIO API | http://localhost:30920 | admin | Admin@123456789@ |
| MinIO Console | http://localhost:30921 | admin | Admin@123456789@ |
| Nexus | http://localhost:30081 | admin | Admin@123456789@ |
| Container Registry | http://localhost:30880 | — | no auth |
| Registry UI | http://localhost:30881 | — | no auth |
| Loki | http://localhost:30310 | — | no auth |
| PostgreSQL (internal) | ClusterIP only | sonar | sonar |

---

## Prerequisites

```bash
# Required
# 1. Docker Desktop with Kubernetes enabled (Settings → Kubernetes → Enable)
pip3 install -r requirements.txt    # mcp[cli], httpx, streamlit, playwright
playwright install chromium

# Optional CLI tools (for full functionality)
brew install terraform              # Terraform manager
brew install trivy                  # Trivy scanner
brew install helm                   # Helm manager
brew install minio/stable/mc        # MinIO CLI
```

---

## Quick Start

### 1 — Deploy the full stack

```bash
# Core services
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/postgres/
kubectl apply -f k8s/jenkins/
kubectl apply -f k8s/sonarqube/

# Observability
kubectl apply -f k8s/prometheus/
kubectl apply -f k8s/grafana/
kubectl apply -f k8s/loki/

# Security & Secrets
kubectl apply -f k8s/vault/

# Storage
kubectl apply -f k8s/harbor/
kubectl apply -f k8s/minio/
kubectl apply -f k8s/nexus/

# ArgoCD (GitOps)
kubectl apply -f k8s/argocd/namespace.yaml
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl patch svc argocd-server -n argocd --patch "$(cat k8s/argocd/nodeport-patch.yaml)"

# Verify everything is running
kubectl get pods -n devops
kubectl get pods -n argocd
```

### 2 — Register all MCP servers with Claude

```bash
claude mcp add docker-manager    -- python3 servers/01_docker_manager.py
claude mcp add terraform-manager -- python3 servers/02_terraform_manager.py
claude mcp add sonarqube-manager \
  -e SONAR_URL=http://localhost:30900 \
  -e SONAR_USER=admin \
  -e SONAR_PASS='Admin@123456789@' \
  -- python3 servers/03_sonarqube_manager.py
claude mcp add jenkins-manager \
  -e JENKINS_URL=http://localhost:30080 \
  -e JENKINS_USER=admin \
  -e JENKINS_PASS='Admin@123456789@' \
  -- python3 servers/04_jenkins_manager.py
claude mcp add devops-dashboard \
  -e JENKINS_URL=http://localhost:30080 -e JENKINS_USER=admin -e JENKINS_PASS='Admin@123456789@' \
  -e SONAR_URL=http://localhost:30900 -e SONAR_USER=admin -e SONAR_PASS='Admin@123456789@' \
  -- python3 servers/05_devops_dashboard.py
claude mcp add kubernetes-manager -- python3 servers/06_kubernetes_manager.py
claude mcp add prometheus-grafana \
  -e PROMETHEUS_URL=http://localhost:30090 \
  -e GRAFANA_URL=http://localhost:30030 \
  -e GRAFANA_USER=admin \
  -e GRAFANA_PASS='Admin@123456789@' \
  -- python3 servers/07_prometheus_grafana.py
claude mcp add argocd-manager \
  -e ARGOCD_URL=https://localhost:30085 \
  -e ARGOCD_USER=admin \
  -e ARGOCD_PASS='Admin@123456789@' \
  -- python3 servers/08_argocd_manager.py
claude mcp add trivy-scanner     -- python3 servers/09_trivy_scanner.py
claude mcp add helm-manager      -- python3 servers/10_helm_manager.py
claude mcp add vault-manager \
  -e VAULT_URL=http://localhost:30200 \
  -e VAULT_TOKEN=root \
  -- python3 servers/11_vault_manager.py
claude mcp add loki-manager \
  -e LOKI_URL=http://localhost:30310 \
  -- python3 servers/12_loki_manager.py
claude mcp add harbor-manager \
  -e HARBOR_URL=http://127.0.0.1:30880 \
  -- python3 servers/13_harbor_manager.py
claude mcp add minio-manager \
  -e MINIO_URL=http://localhost:30920 \
  -e MINIO_ACCESS_KEY=admin \
  -e MINIO_SECRET_KEY='Admin@123456789@' \
  -- python3 servers/14_minio_manager.py
claude mcp add nexus-manager \
  -e NEXUS_URL=http://localhost:30081 \
  -e NEXUS_USER=admin \
  -e NEXUS_PASS='Admin@123456789@' \
  -- python3 servers/15_nexus_manager.py
```

### 3 — Launch the Streamlit dashboard

```bash
python3 -m streamlit run streamlit_app/app.py --server.port 8501
# Open http://localhost:8501
```

---

## Example Claude Prompts

Once MCP servers are registered, try these in Claude:

```
"Show me all running Kubernetes pods in the devops namespace"
"Trigger the Jenkins pipeline named 'build-app'"
"Scan the nginx:latest Docker image for critical CVEs with Trivy"
"Create a SonarQube project called my-service"
"Query Prometheus: average CPU usage across all pods last 5 minutes"
"List all ArgoCD applications and their sync status"
"Write a secret to Vault at path secret/myapp/config with key=value"
"List all MinIO buckets and show their sizes"
"Show recent error logs from Loki for the sonarqube pod"
"Install the ingress-nginx Helm chart in the devops namespace"
"List all Docker images larger than 500MB"
"Run a Terraform plan in the local workdir"
```

---

## Project Structure

```
mcp-server-01/
├── servers/                        ← 15 MCP server Python files
│   ├── 01_docker_manager.py
│   ├── 02_terraform_manager.py
│   ├── 03_sonarqube_manager.py
│   ├── 04_jenkins_manager.py
│   ├── 05_devops_dashboard.py
│   ├── 06_kubernetes_manager.py
│   ├── 07_prometheus_grafana.py
│   ├── 08_argocd_manager.py
│   ├── 09_trivy_scanner.py
│   ├── 10_helm_manager.py
│   ├── 11_vault_manager.py
│   ├── 12_loki_manager.py
│   ├── 13_harbor_manager.py
│   ├── 14_minio_manager.py
│   └── 15_nexus_manager.py
├── streamlit_app/
│   ├── app.py                      ← 15-page visual control panel
│   └── utils.py                    ← shared http/shell helpers
├── k8s/                            ← Kubernetes manifests
│   ├── namespace.yaml
│   ├── jenkins/
│   ├── sonarqube/
│   ├── postgres/
│   ├── prometheus/
│   ├── grafana/
│   ├── argocd/
│   ├── vault/
│   ├── loki/
│   ├── harbor/
│   ├── minio/
│   └── nexus/
├── terraform/local/                ← Example Terraform (local + null providers)
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── docs/screenshots/               ← Tool UI + Streamlit dashboard screenshots
├── tests/                          ← pytest test suite
├── claude_mcp_config.json          ← MCP server configuration
├── requirements.txt
├── LICENSE                         ← MIT
└── README.md
```

---

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                     Claude AI  (MCP Client)                    │
│                  + Streamlit Control Panel                     │
└─────────────────────┬──────────────────────────────────────────┘
                      │  MCP  (stdio transport)
          ┌───────────┴──────────────────────────┐
          │        15 MCP Server Processes        │
          └───────────┬──────────────────────────┘
                      │  HTTP / kubectl / CLI subprocess
┌─────────────────────▼──────────────────────────────────────────┐
│                Kubernetes  (Docker Desktop)                     │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐  ┌────────────┐  │
│  │ Jenkins  │  │SonarQube │  │ Prometheus │  │  Grafana   │  │
│  │ :30080   │  │  :30900  │  │   :30090   │  │   :30030   │  │
│  └──────────┘  └──────────┘  └────────────┘  └────────────┘  │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐  ┌────────────┐  │
│  │  ArgoCD  │  │  Vault   │  │    Loki    │  │ Container  │  │
│  │  :30085  │  │  :30200  │  │   :30310   │  │  Registry  │  │
│  └──────────┘  └──────────┘  └────────────┘  │   :30880   │  │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐  └────────────┘  │
│  │  MinIO   │  │  Nexus   │  │ PostgreSQL │                   │
│  │  :30920  │  │  :30081  │  │ (internal) │                   │
│  └──────────┘  └──────────┘  └────────────┘                   │
└────────────────────────────────────────────────────────────────┘
```

---

## Known Issues & Fixes

| Issue | Fix Applied |
|-------|-------------|
| SonarQube readiness probe returns 401 | Uses `tcpSocket` probe instead of HTTP |
| SonarQube Elasticsearch mmap error | `SONAR_SEARCH_JAVAOPTS=-Dnode.store.allow_mmap=false` |
| ArgoCD redirects HTTP → HTTPS | Use `https://localhost:30085` with `verify=False` |
| Registry returns empty reply on `localhost` | Use `http://127.0.0.1:30880` (IPv4 explicit) |
| Vault persistence | Dev mode only — data resets on pod restart |

---

## License

MIT © 2026 Narayana Reddy — see [LICENSE](LICENSE)
