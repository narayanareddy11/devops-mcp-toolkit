"""
MCP Server 8 — ArgoCD Manager
Manage GitOps deployments via ArgoCD.
ArgoCD UI  → http://localhost:30085
ArgoCD API → http://localhost:30085/api/v1
"""

import httpx
import json
import os
import subprocess
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("argocd-manager")

ARGOCD_URL  = os.environ.get("ARGOCD_URL",  "http://localhost:30085")
ARGOCD_USER = os.environ.get("ARGOCD_USER", "admin")
ARGOCD_PASS = os.environ.get("ARGOCD_PASS", "")   # set after first login


def _get_token() -> str:
    """Get ArgoCD JWT token via login."""
    password = ARGOCD_PASS or _get_initial_password()
    try:
        r = httpx.post(
            f"{ARGOCD_URL}/api/v1/session",
            json={"username": ARGOCD_USER, "password": password},
            verify=False, timeout=10,
        )
        return r.json().get("token", "")
    except Exception:
        return ""


def _get_initial_password() -> str:
    """Fetch ArgoCD initial admin password from K8s secret."""
    result = subprocess.run(
        "kubectl get secret argocd-initial-admin-secret -n argocd "
        "-o jsonpath='{.data.password}' | base64 --decode",
        shell=True, capture_output=True, text=True,
    )
    return result.stdout.strip().strip("'")


def _api(method: str, path: str, data: dict = None) -> dict:
    token = _get_token()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        r = getattr(httpx, method)(
            f"{ARGOCD_URL}/api/v1/{path}",
            json=data, headers=headers,
            verify=False, timeout=15,
        )
        r.raise_for_status()
        return r.json() if r.text else {"status": "ok"}
    except httpx.HTTPStatusError as e:
        return {"error": str(e), "body": e.response.text[:300]}
    except Exception as e:
        return {"error": str(e)}


# ── Server health ──────────────────────────────────────────────────────────────

@mcp.tool()
def argocd_health() -> str:
    """Check if ArgoCD server is reachable and return version info."""
    try:
        r = httpx.get(f"{ARGOCD_URL}/api/version", verify=False, timeout=8)
        return json.dumps({"url": ARGOCD_URL, **r.json()}, indent=2)
    except Exception as e:
        return f"ArgoCD unreachable at {ARGOCD_URL}: {e}"


@mcp.tool()
def get_initial_password() -> str:
    """Retrieve the ArgoCD initial admin password from K8s secret."""
    pw = _get_initial_password()
    return pw if pw else "Secret not found — ArgoCD may still be starting."


# ── Applications ───────────────────────────────────────────────────────────────

@mcp.tool()
def list_apps() -> str:
    """List all ArgoCD applications with sync and health status."""
    data = _api("get", "applications")
    if "error" in data:
        return f"Error: {data}"
    apps = data.get("items", [])
    return json.dumps([
        {
            "name":        a["metadata"]["name"],
            "project":     a["spec"].get("project", "default"),
            "repo":        a["spec"]["source"].get("repoURL"),
            "path":        a["spec"]["source"].get("path"),
            "targetRevision": a["spec"]["source"].get("targetRevision", "HEAD"),
            "namespace":   a["spec"]["destination"].get("namespace"),
            "syncStatus":  a["status"].get("sync", {}).get("status"),
            "healthStatus": a["status"].get("health", {}).get("status"),
        }
        for a in apps
    ], indent=2) if apps else "No applications found."


@mcp.tool()
def get_app(app_name: str) -> str:
    """Get detailed status of an ArgoCD application."""
    data = _api("get", f"applications/{app_name}")
    if "error" in data:
        return f"Error: {data}"
    status = data.get("status", {})
    return json.dumps({
        "name":         data["metadata"]["name"],
        "syncStatus":   status.get("sync", {}).get("status"),
        "healthStatus": status.get("health", {}).get("status"),
        "revision":     status.get("sync", {}).get("revision", "")[:8],
        "conditions":   status.get("conditions", []),
        "resources":    len(status.get("resources", [])),
    }, indent=2)


@mcp.tool()
def sync_app(app_name: str, prune: bool = False) -> str:
    """Trigger a sync for an ArgoCD application."""
    payload = {"prune": prune, "dryRun": False, "force": False}
    data = _api("post", f"applications/{app_name}/sync", payload)
    return json.dumps(data, indent=2) if "error" not in data else f"Error: {data}"


@mcp.tool()
def create_app(
    app_name: str,
    repo_url: str,
    path: str,
    dest_namespace: str = "default",
    target_revision: str = "HEAD",
    project: str = "default",
) -> str:
    """
    Create a new ArgoCD application from a Git repo.
    repo_url: Git repository URL
    path: path within the repo containing K8s manifests
    dest_namespace: K8s namespace to deploy into
    """
    payload = {
        "metadata": {"name": app_name},
        "spec": {
            "project": project,
            "source": {
                "repoURL": repo_url,
                "path": path,
                "targetRevision": target_revision,
            },
            "destination": {
                "server": "https://kubernetes.default.svc",
                "namespace": dest_namespace,
            },
            "syncPolicy": {
                "automated": {"prune": True, "selfHeal": True},
            },
        },
    }
    data = _api("post", "applications", payload)
    return json.dumps(data, indent=2) if "error" not in data else f"Error: {data}"


@mcp.tool()
def delete_app(app_name: str, cascade: bool = True) -> str:
    """Delete an ArgoCD application (and optionally its K8s resources)."""
    try:
        token = _get_token()
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        params = {"cascade": str(cascade).lower()}
        r = httpx.delete(
            f"{ARGOCD_URL}/api/v1/applications/{app_name}",
            headers=headers, params=params, verify=False, timeout=15,
        )
        return f"Deleted {app_name}" if r.status_code in (200, 204) else f"Error: {r.text[:200]}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def get_app_logs(app_name: str, container: str = "", tail: int = 50) -> str:
    """Get logs from pods managed by an ArgoCD application."""
    params = f"?tailLines={tail}"
    if container:
        params += f"&container={container}"
    data = _api("get", f"applications/{app_name}/logs{params}")
    if "error" in data:
        return f"Error: {data}"
    entries = data.get("result", {}).get("content", [])
    return "\n".join(e.get("content", "") for e in entries) if entries else "No logs."


@mcp.tool()
def rollback_app(app_name: str, revision_id: int) -> str:
    """Rollback an application to a specific revision ID."""
    data = _api("post", f"applications/{app_name}/rollback", {"id": revision_id})
    return json.dumps(data, indent=2) if "error" not in data else f"Error: {data}"


@mcp.tool()
def list_projects() -> str:
    """List all ArgoCD projects."""
    data = _api("get", "projects")
    if "error" in data:
        return f"Error: {data}"
    projects = data.get("items", [])
    return json.dumps([
        {"name": p["metadata"]["name"], "description": p["spec"].get("description", "")}
        for p in projects
    ], indent=2)


@mcp.tool()
def list_repositories() -> str:
    """List all Git repositories registered in ArgoCD."""
    data = _api("get", "repositories")
    if "error" in data:
        return f"Error: {data}"
    repos = data.get("items", [])
    return json.dumps([
        {"repo": r.get("repo"), "type": r.get("type", "git"),
         "connectionState": r.get("connectionState", {}).get("status")}
        for r in repos
    ], indent=2) if repos else "No repositories registered."


@mcp.tool()
def add_repository(repo_url: str, username: str = "", password: str = "") -> str:
    """Register a Git repository in ArgoCD."""
    payload = {"repo": repo_url, "username": username, "password": password, "insecure": True}
    data = _api("post", "repositories", payload)
    return json.dumps(data, indent=2) if "error" not in data else f"Error: {data}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
