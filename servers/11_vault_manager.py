"""Vault Manager MCP Server — manage HashiCorp Vault secrets and policies."""

import os
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("vault-manager")

VAULT_URL = os.environ.get("VAULT_URL", "http://localhost:30200")
VAULT_TOKEN = os.environ.get("VAULT_TOKEN", "root")


def _headers() -> dict:
    return {"X-Vault-Token": VAULT_TOKEN, "Content-Type": "application/json"}


def _get(path: str) -> dict:
    try:
        r = httpx.get(f"{VAULT_URL}/v1/{path}", headers=_headers(), timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def _post(path: str, data: dict) -> dict:
    try:
        r = httpx.post(f"{VAULT_URL}/v1/{path}", headers=_headers(), json=data, timeout=10)
        return r.json() if r.text else {"status": r.status_code}
    except Exception as e:
        return {"error": str(e)}


def _put(path: str, data: dict) -> dict:
    try:
        r = httpx.put(f"{VAULT_URL}/v1/{path}", headers=_headers(), json=data, timeout=10)
        return r.json() if r.text else {"status": r.status_code}
    except Exception as e:
        return {"error": str(e)}


def _delete(path: str) -> dict:
    try:
        r = httpx.delete(f"{VAULT_URL}/v1/{path}", headers=_headers(), timeout=10)
        return {"status": r.status_code, "deleted": path}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def vault_health() -> str:
    """Check Vault server health and seal status."""
    try:
        r = httpx.get(f"{VAULT_URL}/v1/sys/health", timeout=10)
        data = r.json()
        return (
            f"Status: {'Unsealed' if not data.get('sealed') else 'Sealed'}\n"
            f"Initialized: {data.get('initialized')}\n"
            f"Version: {data.get('version')}\n"
            f"Cluster: {data.get('cluster_name', 'N/A')}"
        )
    except Exception as e:
        return f"Vault unreachable: {e}"


@mcp.tool()
def vault_status() -> str:
    """Get detailed Vault server status including HA mode, storage backend."""
    result = _get("sys/seal-status")
    return "\n".join(f"{k}: {v}" for k, v in result.items())


@mcp.tool()
def list_secrets(path: str = "secret") -> str:
    """List secrets at a given path. Default path is 'secret'. For KV v2 use 'secret/metadata'."""
    result = _get(f"{path}?list=true")
    if "errors" in result:
        return f"Error: {result['errors']}"
    keys = result.get("data", {}).get("keys", [])
    return f"Secrets at '{path}':\n" + "\n".join(f"  - {k}" for k in keys) if keys else f"No secrets at '{path}'"


@mcp.tool()
def read_secret(path: str) -> str:
    """Read a secret from Vault. For KV v2: path='secret/data/myapp'. For KV v1: path='secret/myapp'."""
    result = _get(path)
    if "errors" in result:
        return f"Error: {result['errors']}"
    data = result.get("data", {})
    if "data" in data:
        data = data["data"]
    return "\n".join(f"  {k}: {v}" for k, v in data.items()) if data else str(result)


@mcp.tool()
def write_secret(path: str, secret_data: dict) -> str:
    """Write a secret to Vault. For KV v2: path='secret/data/myapp', secret_data={'key':'value'}.
    For KV v1: path='secret/myapp'."""
    if "secret/data/" in path:
        payload = {"data": secret_data}
    else:
        payload = secret_data
    result = _post(path, payload)
    if "errors" in result:
        return f"Error: {result['errors']}"
    return f"Secret written to '{path}' successfully"


@mcp.tool()
def delete_secret(path: str) -> str:
    """Delete a secret from Vault."""
    result = _delete(path)
    return f"Deleted '{path}'" if "error" not in result else f"Error: {result['error']}"


@mcp.tool()
def list_mounts() -> str:
    """List all secret engine mounts (KV, PKI, AWS, etc.)."""
    result = _get("sys/mounts")
    if "error" in result:
        return f"Error: {result['error']}"
    mounts = []
    for path, info in result.items():
        if isinstance(info, dict) and "type" in info:
            mounts.append(f"  {path} ({info['type']}) — {info.get('description', '')}")
    return "Secret Engine Mounts:\n" + "\n".join(mounts)


@mcp.tool()
def enable_secret_engine(path: str, engine_type: str = "kv", options: dict = {}) -> str:
    """Enable a new secret engine. engine_type: kv, pki, aws, database, ssh, transit."""
    payload = {"type": engine_type, "options": options}
    result = _post(f"sys/mounts/{path}", payload)
    return f"Enabled '{engine_type}' at '{path}'" if "error" not in str(result) else str(result)


@mcp.tool()
def list_policies() -> str:
    """List all Vault policies."""
    result = _get("sys/policy")
    policies = result.get("policies", [])
    return "Policies:\n" + "\n".join(f"  - {p}" for p in policies)


@mcp.tool()
def read_policy(name: str) -> str:
    """Read a Vault policy's rules."""
    result = _get(f"sys/policy/{name}")
    return result.get("rules", str(result))


@mcp.tool()
def write_policy(name: str, rules: str) -> str:
    """Create or update a Vault policy. rules is HCL policy string.
    Example rules: 'path \"secret/*\" { capabilities = [\"read\", \"list\"] }'"""
    result = _put(f"sys/policy/{name}", {"rules": rules})
    return f"Policy '{name}' written" if "error" not in str(result) else str(result)


@mcp.tool()
def delete_policy(name: str) -> str:
    """Delete a Vault policy."""
    result = _delete(f"sys/policy/{name}")
    return f"Policy '{name}' deleted" if "error" not in str(result) else str(result)


@mcp.tool()
def list_auth_methods() -> str:
    """List enabled authentication methods (token, userpass, kubernetes, etc.)."""
    result = _get("sys/auth")
    if "error" in result:
        return f"Error: {result['error']}"
    methods = []
    for path, info in result.items():
        if isinstance(info, dict) and "type" in info:
            methods.append(f"  {path} ({info['type']}) — {info.get('description', '')}")
    return "Auth Methods:\n" + "\n".join(methods)


@mcp.tool()
def create_token(policies: list = ["default"], ttl: str = "24h", display_name: str = "mcp-token") -> str:
    """Create a new Vault token with given policies and TTL."""
    result = _post("auth/token/create", {
        "policies": policies,
        "ttl": ttl,
        "display_name": display_name
    })
    if "auth" in result:
        return f"Token: {result['auth']['client_token']}\nTTL: {result['auth']['lease_duration']}s\nPolicies: {result['auth']['policies']}"
    return str(result)


@mcp.tool()
def lookup_token(token: str = "") -> str:
    """Look up token info. Leave token empty to look up the current token."""
    if token:
        result = _post("auth/token/lookup", {"token": token})
    else:
        result = _get("auth/token/lookup-self")
    data = result.get("data", result)
    return "\n".join(f"  {k}: {v}" for k, v in data.items() if k in ["id", "display_name", "policies", "ttl", "expire_time"])


@mcp.tool()
def enable_kubernetes_auth(kubernetes_host: str = "https://kubernetes.default.svc") -> str:
    """Enable Kubernetes auth method for pod authentication."""
    result = _post("sys/auth/kubernetes", {"type": "kubernetes"})
    if "error" not in str(result):
        _post("auth/kubernetes/config", {"kubernetes_host": kubernetes_host})
        return f"Kubernetes auth enabled and configured with host: {kubernetes_host}"
    return str(result)


if __name__ == "__main__":
    mcp.run(transport="stdio")
