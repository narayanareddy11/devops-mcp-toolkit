"""
MCP Server 6 — Kubernetes Manager
Manage the DevOps K8s cluster on Docker Desktop.
Namespace: devops
"""

import subprocess
import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("kubernetes-manager")
NS = "devops"


def _kube(cmd: str, namespace: str = NS) -> dict:
    ns_flag = f"-n {namespace}" if namespace else ""
    full = f"kubectl {ns_flag} {cmd}"
    result = subprocess.run(full, shell=True, capture_output=True, text=True)
    return {
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "success": result.returncode == 0,
    }


def _json(cmd: str, namespace: str = NS) -> list | dict:
    out = _kube(f"{cmd} -o json", namespace)
    if not out["success"]:
        return {"error": out["stderr"]}
    try:
        return json.loads(out["stdout"])
    except Exception:
        return {"error": out["stdout"]}


# ── Cluster info ───────────────────────────────────────────────────────────────

@mcp.tool()
def cluster_info() -> str:
    """Show Kubernetes cluster info and version."""
    result = subprocess.run("kubectl cluster-info", shell=True, capture_output=True, text=True)
    version = subprocess.run("kubectl version --short 2>/dev/null || kubectl version", shell=True, capture_output=True, text=True)
    return f"{result.stdout.strip()}\n\n{version.stdout.strip()}"


@mcp.tool()
def get_nodes() -> str:
    """List all Kubernetes nodes with status and roles."""
    out = _kube("get nodes -o wide", namespace="")
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


@mcp.tool()
def get_contexts() -> str:
    """List all kubectl contexts and show the active one."""
    result = subprocess.run("kubectl config get-contexts", shell=True, capture_output=True, text=True)
    return result.stdout.strip()


# ── Namespace ─────────────────────────────────────────────────────────────────

@mcp.tool()
def list_namespaces() -> str:
    """List all Kubernetes namespaces."""
    out = _kube("get namespaces", namespace="")
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


@mcp.tool()
def create_namespace(name: str) -> str:
    """Create a Kubernetes namespace."""
    out = _kube(f"create namespace {name}", namespace="")
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


# ── Pods ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_pods(namespace: str = NS) -> str:
    """List all pods in the devops namespace with status."""
    out = _kube("get pods -o wide", namespace)
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


@mcp.tool()
def describe_pod(pod_name: str, namespace: str = NS) -> str:
    """Describe a pod — shows events, resource usage, and container state."""
    out = _kube(f"describe pod {pod_name}", namespace)
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


@mcp.tool()
def pod_logs(pod_name: str, namespace: str = NS, tail: int = 50, container: str = "") -> str:
    """Fetch logs from a pod. Optionally specify container name for multi-container pods."""
    c_flag = f"-c {container}" if container else ""
    out = _kube(f"logs {pod_name} {c_flag} --tail={tail}", namespace)
    return out["stdout"] if out["success"] else out["stderr"]


@mcp.tool()
def delete_pod(pod_name: str, namespace: str = NS) -> str:
    """Delete a pod (it will be recreated by its Deployment)."""
    out = _kube(f"delete pod {pod_name}", namespace)
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


@mcp.tool()
def exec_pod(pod_name: str, command: str, namespace: str = NS) -> str:
    """Execute a command inside a running pod."""
    out = _kube(f"exec {pod_name} -- {command}", namespace)
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


# ── Deployments ───────────────────────────────────────────────────────────────

@mcp.tool()
def list_deployments(namespace: str = NS) -> str:
    """List all deployments with replicas and age."""
    out = _kube("get deployments", namespace)
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


@mcp.tool()
def describe_deployment(name: str, namespace: str = NS) -> str:
    """Describe a deployment — shows rollout strategy, replicas, and events."""
    out = _kube(f"describe deployment {name}", namespace)
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


@mcp.tool()
def scale_deployment(name: str, replicas: int, namespace: str = NS) -> str:
    """Scale a deployment to a given number of replicas."""
    out = _kube(f"scale deployment {name} --replicas={replicas}", namespace)
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


@mcp.tool()
def rollout_status(name: str, namespace: str = NS) -> str:
    """Check the rollout status of a deployment."""
    out = _kube(f"rollout status deployment/{name}", namespace)
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


@mcp.tool()
def rollout_restart(name: str, namespace: str = NS) -> str:
    """Restart a deployment by triggering a rolling update."""
    out = _kube(f"rollout restart deployment/{name}", namespace)
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


@mcp.tool()
def apply_manifest(manifest_path: str) -> str:
    """Apply a Kubernetes manifest file (kubectl apply -f)."""
    out = _kube(f"apply -f {manifest_path}", namespace="")
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


@mcp.tool()
def delete_manifest(manifest_path: str) -> str:
    """Delete resources defined in a Kubernetes manifest file."""
    out = _kube(f"delete -f {manifest_path}", namespace="")
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


# ── Services ──────────────────────────────────────────────────────────────────

@mcp.tool()
def list_services(namespace: str = NS) -> str:
    """List all Kubernetes services with ports and type."""
    out = _kube("get services", namespace)
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


# ── PVCs & Storage ────────────────────────────────────────────────────────────

@mcp.tool()
def list_pvcs(namespace: str = NS) -> str:
    """List all PersistentVolumeClaims and their status."""
    out = _kube("get pvc", namespace)
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


# ── ConfigMaps & Secrets ──────────────────────────────────────────────────────

@mcp.tool()
def list_configmaps(namespace: str = NS) -> str:
    """List all ConfigMaps in the namespace."""
    out = _kube("get configmaps", namespace)
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


@mcp.tool()
def list_secrets(namespace: str = NS) -> str:
    """List all Secrets in the namespace (names only, no values)."""
    out = _kube("get secrets", namespace)
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


# ── Events & Troubleshooting ──────────────────────────────────────────────────

@mcp.tool()
def get_events(namespace: str = NS) -> str:
    """Show recent Kubernetes events (useful for debugging)."""
    out = _kube("get events --sort-by=.lastTimestamp", namespace)
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


@mcp.tool()
def top_pods(namespace: str = NS) -> str:
    """Show CPU and memory usage for all pods (requires metrics-server)."""
    out = _kube("top pods", namespace)
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


@mcp.tool()
def devops_stack_status() -> str:
    """Full status of the DevOps K8s stack: pods, services, PVCs, events."""
    pods = _kube("get pods -o wide", NS)
    svcs = _kube("get services", NS)
    pvcs = _kube("get pvc", NS)
    events = _kube("get events --sort-by=.lastTimestamp --field-selector=type=Warning", NS)

    return "\n".join([
        "=== PODS ===",
        pods["stdout"] or pods["stderr"],
        "",
        "=== SERVICES ===",
        svcs["stdout"] or svcs["stderr"],
        "",
        "=== PVCS ===",
        pvcs["stdout"] or pvcs["stderr"],
        "",
        "=== WARNING EVENTS ===",
        events["stdout"] or "No warning events.",
    ])


if __name__ == "__main__":
    mcp.run(transport="stdio")
