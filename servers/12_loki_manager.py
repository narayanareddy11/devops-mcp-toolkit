"""Loki Manager MCP Server — query logs from Grafana Loki."""

import os
import httpx
import time
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("loki-manager")

LOKI_URL = os.environ.get("LOKI_URL", "http://localhost:30310")


def _get(path: str, params: dict = {}) -> dict:
    try:
        r = httpx.get(f"{LOKI_URL}{path}", params=params, timeout=30)
        if r.status_code != 200:
            return {"error": f"HTTP {r.status_code}: {r.text}"}
        return r.json()
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def loki_health() -> str:
    """Check if Loki is healthy and ready to accept queries."""
    try:
        r = httpx.get(f"{LOKI_URL}/ready", timeout=10)
        if r.status_code == 200:
            return "Loki is healthy and ready"
        return f"Loki not ready: HTTP {r.status_code}"
    except Exception as e:
        return f"Loki unreachable at {LOKI_URL}: {e}"


@mcp.tool()
def query_logs(
    query: str,
    limit: int = 50,
    since: str = "1h",
    namespace: str = "",
    pod: str = "",
    app: str = "",
) -> str:
    """Query logs from Loki using LogQL.
    Examples:
      query='{namespace="devops"}' — all devops namespace logs
      query='{app="jenkins"}' — Jenkins logs
      query='{pod="grafana-xxx"} |= "error"' — filter for errors
    since: how far back to look (e.g. 5m, 1h, 24h)
    """
    if not query:
        filters = []
        if namespace:
            filters.append(f'namespace="{namespace}"')
        if pod:
            filters.append(f'pod=~"{pod}.*"')
        if app:
            filters.append(f'app="{app}"')
        query = "{" + ", ".join(filters) + "}" if filters else '{namespace="devops"}'

    end = int(time.time() * 1e9)
    duration_map = {"m": 60, "h": 3600, "d": 86400}
    unit = since[-1]
    val = int(since[:-1]) * duration_map.get(unit, 3600)
    start = int((time.time() - val) * 1e9)

    result = _get("/loki/api/v1/query_range", {
        "query": query, "limit": limit, "start": start, "end": end, "direction": "backward"
    })
    if "error" in result:
        return f"Error: {result['error']}"

    streams = result.get("data", {}).get("result", [])
    if not streams:
        return f"No logs found for query: {query}"

    lines = []
    for stream in streams:
        labels = stream.get("stream", {})
        label_str = f"[{labels.get('namespace','?')}/{labels.get('pod', labels.get('app','?'))}]"
        for ts, log in stream.get("values", []):
            ts_s = int(ts) // 1_000_000_000
            t = time.strftime("%H:%M:%S", time.localtime(ts_s))
            lines.append(f"{t} {label_str} {log}")

    return "\n".join(lines[:limit]) if lines else "No log entries"


@mcp.tool()
def query_logs_instant(query: str, limit: int = 20) -> str:
    """Run an instant LogQL query (current point in time)."""
    result = _get("/loki/api/v1/query", {"query": query, "limit": limit})
    if "error" in result:
        return f"Error: {result['error']}"
    streams = result.get("data", {}).get("result", [])
    if not streams:
        return "No results"
    lines = []
    for stream in streams:
        for ts, log in stream.get("values", []):
            lines.append(log)
    return "\n".join(lines)


@mcp.tool()
def list_labels() -> str:
    """List all available log label names in Loki."""
    result = _get("/loki/api/v1/labels")
    if "error" in result:
        return f"Error: {result['error']}"
    labels = result.get("data", [])
    return "Available labels:\n" + "\n".join(f"  - {l}" for l in labels)


@mcp.tool()
def list_label_values(label: str) -> str:
    """List all values for a specific label (e.g. label='namespace', label='app')."""
    result = _get(f"/loki/api/v1/label/{label}/values")
    if "error" in result:
        return f"Error: {result['error']}"
    values = result.get("data", [])
    return f"Values for '{label}':\n" + "\n".join(f"  - {v}" for v in values)


@mcp.tool()
def get_pod_logs(pod_name: str, namespace: str = "devops", since: str = "30m", limit: int = 100) -> str:
    """Get logs for a specific pod from Loki."""
    return query_logs(
        query=f'{{namespace="{namespace}", pod=~"{pod_name}.*"}}',
        limit=limit,
        since=since,
    )


@mcp.tool()
def get_app_logs(app_name: str, namespace: str = "devops", since: str = "1h", limit: int = 100) -> str:
    """Get logs for a specific app label from Loki."""
    return query_logs(
        query=f'{{namespace="{namespace}", app="{app_name}"}}',
        limit=limit,
        since=since,
    )


@mcp.tool()
def search_logs(keyword: str, namespace: str = "devops", since: str = "1h", limit: int = 50) -> str:
    """Search for a keyword across all logs in a namespace."""
    return query_logs(
        query=f'{{namespace="{namespace}"}} |= "{keyword}"',
        limit=limit,
        since=since,
    )


@mcp.tool()
def get_error_logs(namespace: str = "devops", since: str = "1h", limit: int = 50) -> str:
    """Get all error/exception logs across a namespace."""
    return query_logs(
        query=f'{{namespace="{namespace}"}} |~ "(?i)(error|exception|fatal|panic|critical)"',
        limit=limit,
        since=since,
    )


@mcp.tool()
def loki_stats() -> str:
    """Get Loki ingestion and query statistics."""
    result = _get("/loki/api/v1/status/buildinfo")
    if "error" in result:
        return f"Error: {result['error']}"
    return "\n".join(f"  {k}: {v}" for k, v in result.items())


if __name__ == "__main__":
    mcp.run(transport="stdio")
