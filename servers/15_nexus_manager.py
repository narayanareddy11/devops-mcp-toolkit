"""Nexus Manager MCP Server — manage Sonatype Nexus Repository."""

import os
import httpx
import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("nexus-manager")

NEXUS_URL = os.environ.get("NEXUS_URL", "http://localhost:30081")
NEXUS_USER = os.environ.get("NEXUS_USER", "admin")
NEXUS_PASS = os.environ.get("NEXUS_PASS", "Admin@123456789@")


def _auth() -> tuple:
    return (NEXUS_USER, NEXUS_PASS)


def _get(path: str, params: dict = {}) -> dict | list:
    try:
        r = httpx.get(f"{NEXUS_URL}/service/rest{path}", auth=_auth(), params=params, timeout=15)
        if r.status_code == 404:
            return {"error": "Not found"}
        if r.status_code == 401:
            return {"error": "Unauthorized - check credentials"}
        return r.json() if r.text else {}
    except Exception as e:
        return {"error": str(e)}


def _post(path: str, data: dict) -> dict:
    try:
        r = httpx.post(f"{NEXUS_URL}/service/rest{path}", auth=_auth(), json=data,
                       headers={"Content-Type": "application/json"}, timeout=15)
        return {"status": r.status_code, "response": r.text[:500] if r.text else ""}
    except Exception as e:
        return {"error": str(e)}


def _delete(path: str) -> dict:
    try:
        r = httpx.delete(f"{NEXUS_URL}/service/rest{path}", auth=_auth(), timeout=15)
        return {"status": r.status_code}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def nexus_health() -> str:
    """Check Nexus Repository health and version."""
    try:
        r = httpx.get(f"{NEXUS_URL}/service/rest/v1/status", auth=_auth(), timeout=10)
        if r.status_code == 200:
            sys_r = httpx.get(f"{NEXUS_URL}/service/rest/v1/system/information", auth=_auth(), timeout=10)
            info = sys_r.json() if sys_r.status_code == 200 else {}
            nexus_info = info.get("nexus-properties", {})
            return (
                f"Nexus Status: Healthy\n"
                f"URL: {NEXUS_URL}\n"
                f"Version: {nexus_info.get('nexus.version', 'N/A')}\n"
                f"Edition: {nexus_info.get('nexus.edition', 'N/A')}"
            )
        return f"Nexus not ready: HTTP {r.status_code}"
    except Exception as e:
        return f"Nexus unreachable at {NEXUS_URL}: {e}"


@mcp.tool()
def list_repositories(repo_type: str = "") -> str:
    """List all Nexus repositories. repo_type: hosted, proxy, group (or empty for all)."""
    result = _get("/v1/repositories")
    if "error" in result:
        return f"Error: {result['error']}"
    repos = result if isinstance(result, list) else result.get("items", [])
    if repo_type:
        repos = [r for r in repos if r.get("type") == repo_type]
    lines = [f"  [{r.get('type', '?')}] {r['name']} ({r.get('format', '?')}) — {r.get('url', '')}" for r in repos]
    return f"Repositories ({len(lines)}):\n" + "\n".join(lines) if lines else "No repositories found"


@mcp.tool()
def create_hosted_repo(name: str, format: str = "maven2", blob_store: str = "default") -> str:
    """Create a hosted repository. format: maven2, npm, docker, pypi, raw, helm, apt, yum."""
    format_configs = {
        "maven2": {"maven": {"versionPolicy": "MIXED", "layoutPolicy": "STRICT"}},
        "npm": {},
        "docker": {"docker": {"v1Enabled": True, "forceBasicAuth": True}},
        "pypi": {},
        "raw": {},
        "helm": {},
    }
    payload = {
        "name": name,
        "online": True,
        "storage": {"blobStoreName": blob_store, "strictContentTypeValidation": True, "writePolicy": "allow"},
        **format_configs.get(format, {})
    }
    result = _post(f"/v1/repositories/{format}/hosted", payload)
    if result.get("status") in [200, 201]:
        return f"Hosted repository '{name}' ({format}) created successfully"
    return f"Result: {result}"


@mcp.tool()
def create_proxy_repo(name: str, remote_url: str, format: str = "maven2", blob_store: str = "default") -> str:
    """Create a proxy repository pointing to a remote URL.
    Example: create_proxy_repo('maven-central', 'https://repo1.maven.org/maven2/', 'maven2')"""
    payload = {
        "name": name,
        "online": True,
        "storage": {"blobStoreName": blob_store, "strictContentTypeValidation": True},
        "proxy": {"remoteUrl": remote_url, "contentMaxAge": 1440, "metadataMaxAge": 1440},
        "negativeCache": {"enabled": True, "timeToLive": 1440},
        "httpClient": {"blocked": False, "autoBlock": True},
    }
    if format == "maven2":
        payload["maven"] = {"versionPolicy": "RELEASE", "layoutPolicy": "PERMISSIVE"}
    result = _post(f"/v1/repositories/{format}/proxy", payload)
    if result.get("status") in [200, 201]:
        return f"Proxy repository '{name}' created pointing to {remote_url}"
    return f"Result: {result}"


@mcp.tool()
def delete_repository(name: str) -> str:
    """Delete a Nexus repository."""
    result = _delete(f"/v1/repositories/{name}")
    return f"Repository '{name}' deleted" if result.get("status") == 204 else str(result)


@mcp.tool()
def search_components(repository: str = "", keyword: str = "", format: str = "") -> str:
    """Search for components/artifacts in Nexus."""
    params = {}
    if repository:
        params["repository"] = repository
    if keyword:
        params["keyword"] = keyword
    if format:
        params["format"] = format
    result = _get("/v1/search", params)
    if "error" in result:
        return f"Error: {result['error']}"
    items = result.get("items", [])
    lines = [f"  {c.get('group', '')}/{c.get('name', '')}:{c.get('version', '')} [{c.get('repository', '')}]" for c in items[:20]]
    total = len(items)
    return f"Components found ({total}):\n" + "\n".join(lines) if lines else "No components found"


@mcp.tool()
def list_components(repository: str) -> str:
    """List all components in a specific repository."""
    result = _get("/v1/components", {"repository": repository})
    if "error" in result:
        return f"Error: {result['error']}"
    items = result.get("items", [])
    lines = [f"  {c.get('group', '')}/{c.get('name', '')}:{c.get('version', '')} — {c.get('id', '')}" for c in items[:30]]
    return f"Components in '{repository}':\n" + "\n".join(lines) if lines else f"No components in '{repository}'"


@mcp.tool()
def delete_component(component_id: str) -> str:
    """Delete a component by its ID. Get IDs from list_components or search_components."""
    result = _delete(f"/v1/components/{component_id}")
    return f"Component '{component_id}' deleted" if result.get("status") == 204 else str(result)


@mcp.tool()
def list_assets(repository: str, component_id: str = "") -> str:
    """List assets (files) in a repository or for a specific component."""
    params = {"repository": repository}
    if component_id:
        params["componentId"] = component_id
    result = _get("/v1/assets", params)
    if "error" in result:
        return f"Error: {result['error']}"
    items = result.get("items", [])
    lines = [f"  {a.get('path', '')} ({a.get('contentType', '')}) — {a.get('downloadUrl', '')}" for a in items[:20]]
    return f"Assets in '{repository}':\n" + "\n".join(lines) if lines else "No assets found"


@mcp.tool()
def list_blob_stores() -> str:
    """List all blob stores used for artifact storage."""
    result = _get("/v1/blobstores")
    if "error" in result:
        return f"Error: {result['error']}"
    items = result if isinstance(result, list) else result.get("items", [])
    lines = [f"  {b.get('name', '')} ({b.get('type', '')}) — size: {b.get('blobCount', 0)} blobs, {b.get('totalSizeInBytes', 0) // (1024*1024)}MB" for b in items]
    return "Blob Stores:\n" + "\n".join(lines) if lines else "No blob stores"


@mcp.tool()
def list_users() -> str:
    """List all Nexus users."""
    result = _get("/v1/security/users")
    if "error" in result:
        return f"Error: {result['error']}"
    items = result if isinstance(result, list) else []
    lines = [f"  {u.get('userId', '')} — {u.get('firstName', '')} {u.get('lastName', '')} [{u.get('status', '')}] roles: {u.get('roles', [])}" for u in items]
    return "Users:\n" + "\n".join(lines) if lines else "No users"


@mcp.tool()
def create_user(user_id: str, password: str, first_name: str, last_name: str, email: str, roles: list = ["nx-anonymous"]) -> str:
    """Create a Nexus user."""
    result = _post("/v1/security/users", {
        "userId": user_id,
        "firstName": first_name,
        "lastName": last_name,
        "emailAddress": email,
        "password": password,
        "status": "active",
        "roles": roles
    })
    if result.get("status") in [200, 201]:
        return f"User '{user_id}' created"
    return f"Result: {result}"


@mcp.tool()
def get_nexus_status() -> str:
    """Get Nexus system status, license, and node info."""
    result = _get("/v1/status/check")
    if "error" in result:
        return f"Error: {result['error']}"
    return "\n".join(f"  {k}: {v}" for k, v in result.items())


if __name__ == "__main__":
    mcp.run(transport="stdio")
