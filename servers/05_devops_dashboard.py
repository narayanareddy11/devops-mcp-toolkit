"""
MCP Server 5 — DevOps Dashboard
Unified health check and summary across Docker, Jenkins, SonarQube, and Terraform.
One place to see the status of your entire local DevOps stack.
"""

import subprocess
import httpx
import json
import os
import shutil
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("devops-dashboard")

JENKINS_URL = os.environ.get("JENKINS_URL", "http://localhost:8080")
SONAR_URL = os.environ.get("SONAR_URL", "http://localhost:9000")
SONAR_AUTH = (os.environ.get("SONAR_USER", "admin"), os.environ.get("SONAR_PASS", "admin"))
JENKINS_AUTH = (os.environ.get("JENKINS_USER", "admin"), os.environ.get("JENKINS_PASS", "admin"))


def _http_get(url: str, auth: tuple, timeout: int = 8) -> dict | None:
    try:
        r = httpx.get(url, auth=auth, timeout=timeout, follow_redirects=True)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _retry_http_get(url: str, auth: tuple, retries: int = 3, timeout: int = 8) -> dict | None:
    """HTTP GET with simple retry logic for transient failures."""
    for attempt in range(retries):
        result = _http_get(url, auth, timeout)
        if result is not None:
            return result
    return None


def _run(cmd: str) -> str:
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()


# ── Full stack health ─────────────────────────────────────────────────────────

@mcp.tool()
def full_stack_health() -> str:
    """
    Check the health of all DevOps services in one call:
    Docker, Jenkins, SonarQube, and Terraform.
    Returns a unified status report.
    """
    report = {}

    # Docker
    docker_out = _run("docker info --format '{{.ServerVersion}}'")
    report["docker"] = {
        "status": "up" if docker_out else "down",
        "version": docker_out or "unavailable",
    }

    # Running containers
    containers_out = _run("docker ps --format json")
    containers = [json.loads(l) for l in containers_out.splitlines() if l.strip()]
    report["docker"]["running_containers"] = len(containers)

    # Jenkins
    jenkins_data = _http_get(f"{JENKINS_URL}/api/json", JENKINS_AUTH)
    if jenkins_data:
        report["jenkins"] = {
            "status": "up",
            "url": JENKINS_URL,
            "jobs": len(jenkins_data.get("jobs", [])),
            "mode": jenkins_data.get("mode"),
        }
    else:
        report["jenkins"] = {"status": "down", "url": JENKINS_URL}

    # SonarQube
    sonar_data = _http_get(f"{SONAR_URL}/api/system/health", SONAR_AUTH)
    if sonar_data:
        report["sonarqube"] = {
            "status": "up",
            "url": SONAR_URL,
            "health": sonar_data.get("health", "unknown"),
        }
    else:
        report["sonarqube"] = {"status": "down", "url": SONAR_URL}

    # Terraform
    tf_out = _run("terraform version -json 2>/dev/null")
    try:
        tf_data = json.loads(tf_out)
        report["terraform"] = {
            "status": "installed",
            "version": tf_data.get("terraform_version"),
        }
    except Exception:
        report["terraform"] = {
            "status": "not installed" if not shutil.which("terraform") else "error",
        }

    # Overall
    services_up = sum(1 for k, v in report.items() if v.get("status") in ("up", "installed"))
    report["summary"] = {
        "services_up": services_up,
        "total_services": 4,
        "overall": "healthy" if services_up == 4 else "degraded",
    }

    return json.dumps(report, indent=2)


# ── Docker summary ────────────────────────────────────────────────────────────

@mcp.tool()
def docker_summary() -> str:
    """Show running containers with resource usage snapshot."""
    out = _run("docker stats --no-stream --format json")
    stats = [json.loads(l) for l in out.splitlines() if l.strip()]
    if not stats:
        ps = _run("docker ps --format json")
        containers = [json.loads(l) for l in ps.splitlines() if l.strip()]
        if not containers:
            return "No running containers."
        return json.dumps([{"name": c.get("Names"), "status": c.get("Status")} for c in containers], indent=2)
    return json.dumps(stats, indent=2)


@mcp.tool()
def list_devops_containers() -> str:
    """List only the DevOps stack containers (Jenkins, SonarQube, Postgres)."""
    out = _run("docker ps -a --format json")
    containers = [json.loads(l) for l in out.splitlines() if l.strip()]
    devops_names = {"devops_jenkins", "devops_sonarqube", "devops_sonar_db"}
    filtered = [
        {
            "name": c.get("Names"),
            "image": c.get("Image"),
            "status": c.get("Status"),
            "ports": c.get("Ports"),
        }
        for c in containers
        if c.get("Names") in devops_names
    ]
    return json.dumps(filtered, indent=2) if filtered else "DevOps containers not found. Run: docker compose up -d"


# ── Jenkins summary ───────────────────────────────────────────────────────────

@mcp.tool()
def jenkins_summary() -> str:
    """Show Jenkins jobs and last build status for each."""
    data = _http_get(f"{JENKINS_URL}/api/json", JENKINS_AUTH)
    if not data:
        return f"Jenkins unreachable at {JENKINS_URL}"

    jobs = data.get("jobs", [])
    result = []
    for job in jobs[:20]:  # cap at 20
        job_data = _http_get(f"{job['url']}api/json", JENKINS_AUTH)
        if job_data:
            last = job_data.get("lastBuild")
            last_result = None
            if last:
                build = _http_get(f"{last['url']}api/json", JENKINS_AUTH)
                if build:
                    last_result = build.get("result")
            result.append({
                "name": job["name"],
                "color": job.get("color"),
                "lastBuildNumber": last.get("number") if last else None,
                "lastBuildResult": last_result,
            })
    return json.dumps(result, indent=2) if result else "No jobs configured."


# ── SonarQube summary ─────────────────────────────────────────────────────────

@mcp.tool()
def sonarqube_summary() -> str:
    """Show all SonarQube projects with quality gate status and key metrics."""
    projects_data = _http_get(f"{SONAR_URL}/api/projects/search?ps=20", SONAR_AUTH)
    if not projects_data:
        return f"SonarQube unreachable at {SONAR_URL}"

    components = projects_data.get("components", [])
    if not components:
        return "No SonarQube projects found."

    result = []
    for project in components:
        key = project["key"]
        qg = _http_get(f"{SONAR_URL}/api/qualitygates/project_status?projectKey={key}", SONAR_AUTH)
        metrics = _http_get(
            f"{SONAR_URL}/api/measures/component?component={key}&metricKeys=bugs,vulnerabilities,code_smells,coverage",
            SONAR_AUTH,
        )
        m = {}
        if metrics:
            for measure in metrics.get("component", {}).get("measures", []):
                m[measure["metric"]] = measure.get("value", "N/A")

        result.append({
            "project": key,
            "name": project["name"],
            "lastAnalysis": project.get("lastAnalysisDate", "never"),
            "qualityGate": qg.get("projectStatus", {}).get("status") if qg else "unknown",
            "metrics": m,
        })

    return json.dumps(result, indent=2)


# ── Terraform summary ─────────────────────────────────────────────────────────

@mcp.tool()
def terraform_summary(
    workdir: str = str(Path(__file__).parent.parent / "terraform" / "local"),
) -> str:
    """Show Terraform state summary for the local example."""
    if not shutil.which("terraform"):
        return "Terraform not installed. Run: brew install terraform"

    state = subprocess.run(
        "terraform state list",
        shell=True,
        capture_output=True,
        text=True,
        cwd=workdir,
    )
    output = subprocess.run(
        "terraform output -json",
        shell=True,
        capture_output=True,
        text=True,
        cwd=workdir,
    )
    resources = state.stdout.strip().splitlines() if state.returncode == 0 else []
    try:
        outputs = json.loads(output.stdout) if output.returncode == 0 else {}
    except Exception:
        outputs = {}

    return json.dumps({
        "workdir": workdir,
        "resources": resources,
        "resource_count": len(resources),
        "outputs": {k: v.get("value") for k, v in outputs.items()},
    }, indent=2)


# ── Port availability ─────────────────────────────────────────────────────────

@mcp.tool()
def check_service_ports() -> str:
    """Check if the standard DevOps service ports are open on localhost."""
    ports = {
        "Jenkins": 8080,
        "SonarQube": 9000,
        "SonarQube-DB": 5433,
        "Jenkins-Agent": 50000,
    }
    import socket
    results = {}
    for name, port in ports.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(("localhost", port))
        sock.close()
        results[name] = {"port": port, "open": result == 0}
    return json.dumps(results, indent=2)


# ── Quick start helper ────────────────────────────────────────────────────────

@mcp.tool()
def get_quickstart_commands() -> str:
    """Return the commands needed to start the entire DevOps stack."""
    compose_file = str(Path(__file__).parent.parent / "docker-compose.yml")
    return json.dumps({
        "start_all": f"docker compose -f {compose_file} up -d",
        "stop_all": f"docker compose -f {compose_file} down",
        "view_logs": f"docker compose -f {compose_file} logs -f",
        "jenkins_url": f"{JENKINS_URL}",
        "sonarqube_url": f"{SONAR_URL}",
        "terraform_init": "cd terraform/local && terraform init",
        "terraform_apply": "cd terraform/local && terraform apply -auto-approve",
        "credentials": {
            "jenkins": "admin / admin (change at first login)",
            "sonarqube": "admin / admin (change at first login)",
        },
        "notes": [
            "SonarQube takes ~2 minutes to start on first run.",
            "Jenkins initial admin password: docker exec devops_jenkins cat /var/jenkins_home/secrets/initialAdminPassword",
        ],
    }, indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
