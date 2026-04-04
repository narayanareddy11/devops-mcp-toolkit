"""
MCP Server 7 — Prometheus & Grafana Manager
Query metrics, alerts, and manage Grafana dashboards.
Prometheus → http://localhost:30090
Grafana    → http://localhost:30030
"""

import httpx
import json
import os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("prometheus-grafana")

PROM_URL    = os.environ.get("PROMETHEUS_URL", "http://localhost:30090")
GRAFANA_URL = os.environ.get("GRAFANA_URL",    "http://localhost:30030")
GRAFANA_AUTH = (
    os.environ.get("GRAFANA_USER", "admin"),
    os.environ.get("GRAFANA_PASS", "admin"),
)


def _prom(path: str, params: dict = None) -> dict | None:
    try:
        r = httpx.get(f"{PROM_URL}/{path}", params=params or {}, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def _grafana_get(path: str) -> dict | None:
    try:
        r = httpx.get(f"{GRAFANA_URL}/{path}", auth=GRAFANA_AUTH, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def _grafana_post(path: str, data: dict) -> dict:
    try:
        r = httpx.post(f"{GRAFANA_URL}/{path}", auth=GRAFANA_AUTH, json=data, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# ── Prometheus ─────────────────────────────────────────────────────────────────

@mcp.tool()
def prometheus_health() -> str:
    """Check if Prometheus is up and ready."""
    try:
        r = httpx.get(f"{PROM_URL}/-/ready", timeout=5)
        return f"Prometheus: {'ready' if r.status_code == 200 else 'not ready'} at {PROM_URL}"
    except Exception as e:
        return f"Prometheus unreachable: {e}"


@mcp.tool()
def query_metric(promql: str) -> str:
    """
    Run an instant PromQL query and return results.
    Examples:
      - up
      - container_memory_usage_bytes{namespace='devops'}
      - rate(container_cpu_usage_seconds_total[5m])
    """
    data = _prom("api/v1/query", {"query": promql})
    if "error" in data:
        return f"Error: {data}"
    results = data.get("data", {}).get("result", [])
    return json.dumps(results, indent=2) if results else "No data returned for query."


@mcp.tool()
def query_range(promql: str, start: str, end: str, step: str = "60s") -> str:
    """
    Run a range PromQL query over a time window.
    start/end: Unix timestamps or relative (e.g. 'now-1h')
    step: resolution (e.g. '60s', '5m')
    """
    data = _prom("api/v1/query_range", {"query": promql, "start": start, "end": end, "step": step})
    if "error" in data:
        return f"Error: {data}"
    return json.dumps(data.get("data", {}), indent=2)


@mcp.tool()
def list_targets() -> str:
    """List all Prometheus scrape targets and their status (up/down)."""
    data = _prom("api/v1/targets")
    if "error" in data:
        return f"Error: {data}"
    active = data.get("data", {}).get("activeTargets", [])
    return json.dumps([
        {
            "job":      t.get("labels", {}).get("job"),
            "instance": t.get("labels", {}).get("instance"),
            "health":   t.get("health"),
            "lastError": t.get("lastError", ""),
        }
        for t in active
    ], indent=2)


@mcp.tool()
def list_alerts() -> str:
    """List all active Prometheus alerts."""
    data = _prom("api/v1/alerts")
    if "error" in data:
        return f"Error: {data}"
    alerts = data.get("data", {}).get("alerts", [])
    if not alerts:
        return "No active alerts."
    return json.dumps([
        {
            "name":     a.get("labels", {}).get("alertname"),
            "state":    a.get("state"),
            "severity": a.get("labels", {}).get("severity"),
            "summary":  a.get("annotations", {}).get("summary", ""),
        }
        for a in alerts
    ], indent=2)


@mcp.tool()
def list_metrics() -> str:
    """List all available metric names in Prometheus."""
    data = _prom("api/v1/label/__name__/values")
    if "error" in data:
        return f"Error: {data}"
    metrics = data.get("data", [])
    return "\n".join(metrics) if metrics else "No metrics found."


@mcp.tool()
def pod_cpu_usage(namespace: str = "devops") -> str:
    """Get current CPU usage for all pods in a namespace."""
    query = f"sum(rate(container_cpu_usage_seconds_total{{namespace='{namespace}',container!=''}}[5m])) by (pod)"
    return query_metric(query)


@mcp.tool()
def pod_memory_usage(namespace: str = "devops") -> str:
    """Get current memory usage (bytes) for all pods in a namespace."""
    query = f"sum(container_memory_usage_bytes{{namespace='{namespace}',container!=''}}) by (pod)"
    return query_metric(query)


@mcp.tool()
def reload_prometheus_config() -> str:
    """Hot-reload Prometheus configuration without restarting."""
    try:
        r = httpx.post(f"{PROM_URL}/-/reload", timeout=10)
        return "Config reloaded successfully." if r.status_code == 200 else f"Failed: {r.status_code}"
    except Exception as e:
        return f"Error: {e}"


# ── Grafana ────────────────────────────────────────────────────────────────────

@mcp.tool()
def grafana_health() -> str:
    """Check Grafana health and version."""
    data = _grafana_get("api/health")
    if "error" in data:
        return f"Grafana unreachable: {data}"
    return json.dumps({"url": GRAFANA_URL, **data}, indent=2)


@mcp.tool()
def list_dashboards() -> str:
    """List all Grafana dashboards."""
    data = _grafana_get("api/search?type=dash-db")
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data}"
    return json.dumps([
        {"uid": d.get("uid"), "title": d.get("title"), "url": d.get("url")}
        for d in (data or [])
    ], indent=2) if data else "No dashboards found."


@mcp.tool()
def get_dashboard(uid: str) -> str:
    """Get a Grafana dashboard by UID."""
    data = _grafana_get(f"api/dashboards/uid/{uid}")
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data}"
    meta = data.get("meta", {})
    dashboard = data.get("dashboard", {})
    return json.dumps({
        "title":   dashboard.get("title"),
        "uid":     dashboard.get("uid"),
        "panels":  len(dashboard.get("panels", [])),
        "created": meta.get("created"),
        "updated": meta.get("updated"),
    }, indent=2)


@mcp.tool()
def list_datasources() -> str:
    """List all configured Grafana datasources."""
    data = _grafana_get("api/datasources")
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data}"
    return json.dumps([
        {"id": d.get("id"), "name": d.get("name"), "type": d.get("type"),
         "url": d.get("url"), "isDefault": d.get("isDefault")}
        for d in (data or [])
    ], indent=2)


@mcp.tool()
def create_dashboard(title: str, prometheus_query: str, panel_title: str = "Metric") -> str:
    """
    Create a simple Grafana dashboard with one time-series panel.
    title: dashboard name
    prometheus_query: PromQL expression for the panel
    """
    dashboard = {
        "dashboard": {
            "title": title,
            "panels": [{
                "id": 1,
                "title": panel_title,
                "type": "timeseries",
                "gridPos": {"x": 0, "y": 0, "w": 24, "h": 8},
                "targets": [{
                    "datasource": {"type": "prometheus", "uid": "prometheus"},
                    "expr": prometheus_query,
                    "legendFormat": "{{pod}}",
                }],
            }],
            "time": {"from": "now-1h", "to": "now"},
            "refresh": "30s",
        },
        "overwrite": True,
        "folderId": 0,
    }
    data = _grafana_post("api/dashboards/db", dashboard)
    return json.dumps(data, indent=2)


@mcp.tool()
def list_grafana_users() -> str:
    """List all Grafana users."""
    data = _grafana_get("api/users")
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data}"
    return json.dumps([
        {"id": u.get("id"), "login": u.get("login"), "email": u.get("email"), "role": u.get("role")}
        for u in (data or [])
    ], indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
