"""
MCP Server 3 — SonarQube Manager
Interact with SonarQube running locally on http://localhost:9000.
Default credentials: admin / admin (change after first login).
"""

import httpx
import json
import subprocess
import os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("sonarqube-manager")

SONAR_URL = os.environ.get("SONAR_URL", "http://localhost:30900")


def _auth() -> tuple:
    token = os.environ.get("SONAR_TOKEN", "")
    if token:
        return (token, "")
    return (os.environ.get("SONAR_USER", "admin"), os.environ.get("SONAR_PASS", "admin"))


def _get(path: str, params: dict = None) -> dict:
    try:
        r = httpx.get(f"{SONAR_URL}/api/{path}", auth=_auth(), params=params or {}, timeout=15)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        return {"error": str(e), "body": e.response.text}
    except Exception as e:
        return {"error": str(e)}


def _post(path: str, data: dict = None) -> dict:
    try:
        r = httpx.post(f"{SONAR_URL}/api/{path}", auth=_auth(), data=data or {}, timeout=30)
        r.raise_for_status()
        return r.json() if r.text else {"status": "ok"}
    except httpx.HTTPStatusError as e:
        return {"error": str(e), "body": e.response.text}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def sonar_health() -> str:
    """Check if SonarQube is up and return system health status."""
    try:
        r = httpx.get(f"{SONAR_URL}/api/system/health", auth=_auth(), timeout=10)
        return json.dumps(r.json(), indent=2)
    except Exception as e:
        return f"SonarQube unreachable at {SONAR_URL}: {e}"


@mcp.tool()
def sonar_ping() -> str:
    """Simple ping to check if SonarQube API is responding."""
    try:
        r = httpx.get(f"{SONAR_URL}/api/system/ping", auth=_auth(), timeout=5)
        return r.text
    except Exception as e:
        return f"Ping failed: {e}"


@mcp.tool()
def sonar_system_info() -> str:
    """Return SonarQube version and system info."""
    data = _get("system/info")
    return json.dumps(data, indent=2)


@mcp.tool()
def list_projects(page_size: int = 20) -> str:
    """List all SonarQube projects."""
    data = _get("projects/search", {"ps": page_size})
    if "error" in data:
        return f"Error: {data}"
    components = data.get("components", [])
    result = [
        {"key": c["key"], "name": c["name"], "lastAnalysis": c.get("lastAnalysisDate", "never")}
        for c in components
    ]
    return json.dumps(result, indent=2) if result else "No projects found."


@mcp.tool()
def create_project(project_key: str, project_name: str) -> str:
    """Create a new SonarQube project."""
    data = _post("projects/create", {
        "project": project_key,
        "name": project_name,
        "visibility": "public",
    })
    return json.dumps(data, indent=2)


@mcp.tool()
def delete_project(project_key: str) -> str:
    """Delete a SonarQube project by key."""
    data = _post("projects/delete", {"project": project_key})
    return json.dumps(data, indent=2)


@mcp.tool()
def get_quality_gate(project_key: str) -> str:
    """Get quality gate status (PASSED / FAILED) for a project."""
    data = _get("qualitygates/project_status", {"projectKey": project_key})
    if "error" in data:
        return f"Error: {data}"
    status = data.get("projectStatus", {})
    return json.dumps({
        "status": status.get("status"),
        "conditions": status.get("conditions", []),
    }, indent=2)


@mcp.tool()
def list_quality_gates() -> str:
    """List all quality gate definitions."""
    data = _get("qualitygates/list")
    return json.dumps(data.get("qualitygates", []), indent=2)


@mcp.tool()
def get_project_metrics(
    project_key: str,
    metrics: str = "bugs,vulnerabilities,code_smells,coverage,duplicated_lines_density,ncloc",
) -> str:
    """
    Get key metrics for a project.
    metrics: comma-separated metric keys.
    """
    data = _get("measures/component", {
        "component": project_key,
        "metricKeys": metrics,
    })
    if "error" in data:
        return f"Error: {data}"
    measures = data.get("component", {}).get("measures", [])
    result = {m["metric"]: m.get("value", "N/A") for m in measures}
    return json.dumps(result, indent=2)


@mcp.tool()
def list_issues(
    project_key: str,
    severity: str = "",
    issue_type: str = "",
    page_size: int = 20,
) -> str:
    """
    List open issues for a project.
    severity: BLOCKER, CRITICAL, MAJOR, MINOR, INFO
    issue_type: BUG, VULNERABILITY, CODE_SMELL
    """
    params: dict = {"componentKeys": project_key, "ps": page_size, "resolved": "false"}
    if severity:
        params["severities"] = severity.upper()
    if issue_type:
        params["types"] = issue_type.upper()
    data = _get("issues/search", params)
    if "error" in data:
        return f"Error: {data}"
    issues = data.get("issues", [])
    result = [
        {
            "key": i["key"],
            "type": i["type"],
            "severity": i["severity"],
            "message": i["message"],
            "component": i["component"],
            "line": i.get("line"),
        }
        for i in issues
    ]
    return json.dumps(result, indent=2) if result else "No issues found."


@mcp.tool()
def get_issue_count(project_key: str) -> str:
    """Get total count of open issues for a project."""
    data = _get("issues/search", {"componentKeys": project_key, "ps": 1, "resolved": "false"})
    if "error" in data:
        return f"Error: {data}"
    return json.dumps({"total": data.get("total", 0)}, indent=2)


@mcp.tool()
def get_analysis_activity(project_key: str = "", max_results: int = 10) -> str:
    """List recent analysis tasks. Optionally filter by project key."""
    params: dict = {"ps": max_results}
    if project_key:
        params["project"] = project_key
    data = _get("ce/activity", params)
    if "error" in data:
        return f"Error: {data}"
    tasks = data.get("tasks", [])
    result = [
        {
            "id": t["id"],
            "project": t.get("componentKey"),
            "status": t["status"],
            "submittedAt": t.get("submittedAt"),
            "executionTimeMs": t.get("executionTimeMs"),
        }
        for t in tasks
    ]
    return json.dumps(result, indent=2) if result else "No recent analysis tasks."


@mcp.tool()
def run_sonar_scanner(
    project_key: str,
    project_name: str,
    source_path: str,
    sonar_token: str = "",
) -> str:
    """
    Run sonar-scanner CLI on a local directory.
    Requires: brew install sonar-scanner
    """
    token = sonar_token or os.environ.get("SONAR_TOKEN", "")
    auth_flag = f"-Dsonar.token={token}" if token else (
        f"-Dsonar.login={os.environ.get('SONAR_USER','admin')} "
        f"-Dsonar.password={os.environ.get('SONAR_PASS','admin')}"
    )
    cmd = (
        f"sonar-scanner "
        f"-Dsonar.projectKey={project_key} "
        f"-Dsonar.projectName='{project_name}' "
        f"-Dsonar.sources={source_path} "
        f"-Dsonar.host.url={SONAR_URL} "
        f"{auth_flag}"
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return f"{result.stdout}\n{result.stderr}".strip()


@mcp.tool()
def generate_token(token_name: str, user_login: str = "admin") -> str:
    """Generate a SonarQube user token for API/scanner access."""
    data = _post("user_tokens/generate", {"name": token_name, "login": user_login})
    return json.dumps(data, indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
