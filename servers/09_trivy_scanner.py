"""
MCP Server 9 — Trivy Security Scanner
Scan container images, filesystems, and K8s workloads for vulnerabilities.
Requires: trivy CLI installed (brew install trivy)
"""

import json
import subprocess
import shutil
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("trivy-scanner")


def _trivy(*args) -> dict:
    """Run trivy with JSON output and return parsed result."""
    if not shutil.which("trivy"):
        return {"error": "trivy not installed — run: brew install trivy"}
    cmd = ["trivy", "--quiet", "--format", "json"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode not in (0, 1):  # 1 = vulns found (normal)
        return {"error": result.stderr[:500] or "trivy failed"}
    try:
        return json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        return {"error": "Failed to parse trivy output", "raw": result.stdout[:300]}


def _summarise(trivy_json: dict) -> dict:
    """Extract a compact summary from trivy JSON output."""
    results = trivy_json.get("Results", [])
    summary = {"target": trivy_json.get("ArtifactName", ""), "results": []}
    total = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNKNOWN": 0}
    for r in results:
        vulns = r.get("Vulnerabilities") or []
        counts = {}
        for v in vulns:
            sev = v.get("Severity", "UNKNOWN")
            counts[sev] = counts.get(sev, 0) + 1
            total[sev] = total.get(sev, 0) + 1
        summary["results"].append({
            "target": r.get("Target"),
            "type":   r.get("Type"),
            "vulns":  counts,
        })
    summary["total"] = total
    return summary


# ── Image scanning ─────────────────────────────────────────────────────────────

@mcp.tool()
def scan_image(image: str, severity: str = "CRITICAL,HIGH") -> str:
    """
    Scan a container image for vulnerabilities.
    image: Docker image name (e.g. nginx:latest, python:3.11)
    severity: comma-separated severities to filter (CRITICAL,HIGH,MEDIUM,LOW)
    Returns a summary with counts by severity.
    """
    data = _trivy("image", "--severity", severity, image)
    if "error" in data:
        return f"Error: {data['error']}"
    summary = _summarise(data)
    return json.dumps(summary, indent=2)


@mcp.tool()
def scan_image_full(image: str) -> str:
    """
    Scan a container image and return ALL vulnerability details.
    image: Docker image name
    Returns full CVE list with IDs, titles, fixed versions.
    """
    data = _trivy("image", image)
    if "error" in data:
        return f"Error: {data['error']}"
    results = data.get("Results", [])
    output = []
    for r in results:
        vulns = r.get("Vulnerabilities") or []
        for v in vulns:
            output.append({
                "id":           v.get("VulnerabilityID"),
                "package":      v.get("PkgName"),
                "version":      v.get("InstalledVersion"),
                "fixedVersion": v.get("FixedVersion", "no fix"),
                "severity":     v.get("Severity"),
                "title":        v.get("Title", "")[:80],
            })
    return json.dumps(output, indent=2) if output else f"No vulnerabilities found in {image}"


@mcp.tool()
def scan_critical_only(image: str) -> str:
    """
    Scan a container image and return only CRITICAL vulnerabilities.
    image: Docker image name
    """
    data = _trivy("image", "--severity", "CRITICAL", image)
    if "error" in data:
        return f"Error: {data['error']}"
    results = data.get("Results", [])
    crits = []
    for r in results:
        for v in (r.get("Vulnerabilities") or []):
            crits.append({
                "id":      v.get("VulnerabilityID"),
                "package": v.get("PkgName"),
                "fixed":   v.get("FixedVersion", "no fix"),
                "title":   v.get("Title", "")[:80],
            })
    return json.dumps(crits, indent=2) if crits else f"No CRITICAL vulnerabilities in {image}"


# ── Filesystem scanning ────────────────────────────────────────────────────────

@mcp.tool()
def scan_filesystem(path: str = ".", severity: str = "CRITICAL,HIGH") -> str:
    """
    Scan a local directory for vulnerabilities (dependencies, IaC misconfigs).
    path: local filesystem path to scan (default: current directory)
    severity: filter by severity
    """
    data = _trivy("fs", "--severity", severity, path)
    if "error" in data:
        return f"Error: {data['error']}"
    summary = _summarise(data)
    return json.dumps(summary, indent=2)


@mcp.tool()
def scan_config(path: str = ".") -> str:
    """
    Scan IaC configuration files (Kubernetes YAML, Terraform, Dockerfile) for misconfigurations.
    path: local path containing IaC files
    """
    data = _trivy("config", path)
    if "error" in data:
        return f"Error: {data['error']}"
    results = data.get("Results", [])
    findings = []
    for r in results:
        misconfigs = r.get("Misconfigurations") or []
        for m in misconfigs:
            findings.append({
                "file":     r.get("Target"),
                "id":       m.get("ID"),
                "title":    m.get("Title"),
                "severity": m.get("Severity"),
                "message":  m.get("Message", "")[:120],
            })
    return json.dumps(findings, indent=2) if findings else "No misconfigurations found."


# ── Kubernetes scanning ────────────────────────────────────────────────────────

@mcp.tool()
def scan_k8s_cluster(namespace: str = "devops") -> str:
    """
    Scan all images running in a Kubernetes namespace for vulnerabilities.
    namespace: K8s namespace to scan
    """
    # Get all unique images from pods in the namespace
    get_images = subprocess.run(
        ["kubectl", "get", "pods", "-n", namespace,
         "-o", "jsonpath={.items[*].spec.containers[*].image}"],
        capture_output=True, text=True,
    )
    if get_images.returncode != 0:
        return f"Error getting pods: {get_images.stderr[:200]}"
    images = list(set(get_images.stdout.split()))
    if not images:
        return f"No pods found in namespace '{namespace}'"
    results = {}
    for img in images:
        data = _trivy("image", "--severity", "CRITICAL,HIGH", img)
        if "error" in data:
            results[img] = {"error": data["error"]}
        else:
            results[img] = _summarise(data).get("total", {})
    return json.dumps(results, indent=2)


@mcp.tool()
def scan_k8s_manifest(manifest_path: str) -> str:
    """
    Scan a Kubernetes manifest file for security misconfigurations.
    manifest_path: path to YAML manifest file
    """
    data = _trivy("config", manifest_path)
    if "error" in data:
        return f"Error: {data['error']}"
    results = data.get("Results", [])
    findings = []
    for r in results:
        for m in (r.get("Misconfigurations") or []):
            findings.append({
                "id":       m.get("ID"),
                "title":    m.get("Title"),
                "severity": m.get("Severity"),
                "message":  m.get("Message", "")[:120],
                "resolution": m.get("Resolution", "")[:120],
            })
    return json.dumps(findings, indent=2) if findings else "No misconfigurations found."


# ── Utility ────────────────────────────────────────────────────────────────────

@mcp.tool()
def trivy_version() -> str:
    """Check if trivy is installed and return its version."""
    if not shutil.which("trivy"):
        return "trivy not installed. Install with: brew install trivy"
    result = subprocess.run(["trivy", "--version"], capture_output=True, text=True)
    return result.stdout.strip() or result.stderr.strip()


@mcp.tool()
def update_trivy_db() -> str:
    """Update the Trivy vulnerability database to the latest version."""
    if not shutil.which("trivy"):
        return "trivy not installed. Install with: brew install trivy"
    result = subprocess.run(
        ["trivy", "image", "--download-db-only"],
        capture_output=True, text=True, timeout=120,
    )
    return "Database updated successfully." if result.returncode == 0 else f"Error: {result.stderr[:300]}"


@mcp.tool()
def scan_sbom(image: str) -> str:
    """
    Generate a Software Bill of Materials (SBOM) for a container image.
    Returns a list of all packages and their versions.
    """
    data = _trivy("image", "--format", "json", "--list-all-pkgs", image)
    # Re-run without --format json since we already pass it in _trivy
    result = subprocess.run(
        ["trivy", "--quiet", "--format", "json", "image", "--list-all-pkgs", image],
        capture_output=True, text=True, timeout=120,
    )
    try:
        data = json.loads(result.stdout)
    except Exception:
        return f"Error parsing SBOM output: {result.stderr[:200]}"
    packages = []
    for r in data.get("Results", []):
        for pkg in (r.get("Packages") or []):
            packages.append({
                "name":    pkg.get("Name"),
                "version": pkg.get("Version"),
                "type":    r.get("Type"),
            })
    return json.dumps(packages, indent=2) if packages else "No packages found."


if __name__ == "__main__":
    mcp.run(transport="stdio")
