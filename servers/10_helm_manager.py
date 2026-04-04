"""Helm Manager MCP Server — manage Helm charts and releases via kubectl/helm CLI."""

import subprocess
import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("helm-manager")


def _run(cmd: list[str]) -> str:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            return f"ERROR: {result.stderr.strip() or result.stdout.strip()}"
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "ERROR: Command timed out"
    except FileNotFoundError:
        return f"ERROR: '{cmd[0]}' not found. Install with: brew install helm"


def _run_json(cmd: list[str]) -> str:
    return _run(cmd + ["-o", "json"])


@mcp.tool()
def helm_version() -> str:
    """Return installed Helm version."""
    return _run(["helm", "version", "--short"])


@mcp.tool()
def list_releases(namespace: str = "default", all_namespaces: bool = False) -> str:
    """List all Helm releases. Set all_namespaces=True to see releases across all namespaces."""
    cmd = ["helm", "list"]
    if all_namespaces:
        cmd.append("--all-namespaces")
    else:
        cmd += ["-n", namespace]
    return _run(cmd)


@mcp.tool()
def list_repos() -> str:
    """List configured Helm chart repositories."""
    return _run(["helm", "repo", "list"])


@mcp.tool()
def add_repo(name: str, url: str) -> str:
    """Add a Helm chart repository. Example: name='bitnami', url='https://charts.bitnami.com/bitnami'."""
    result = _run(["helm", "repo", "add", name, url])
    _run(["helm", "repo", "update"])
    return result


@mcp.tool()
def remove_repo(name: str) -> str:
    """Remove a Helm repository."""
    return _run(["helm", "repo", "remove", name])


@mcp.tool()
def update_repos() -> str:
    """Update all Helm repository indexes."""
    return _run(["helm", "repo", "update"])


@mcp.tool()
def search_repo(keyword: str) -> str:
    """Search for charts across all added repositories."""
    return _run(["helm", "search", "repo", keyword])


@mcp.tool()
def search_hub(keyword: str) -> str:
    """Search for charts on Artifact Hub."""
    return _run(["helm", "search", "hub", keyword])


@mcp.tool()
def show_chart_values(chart: str, version: str = "") -> str:
    """Show default values for a chart. chart example: 'bitnami/nginx'."""
    cmd = ["helm", "show", "values", chart]
    if version:
        cmd += ["--version", version]
    return _run(cmd)


@mcp.tool()
def install_chart(
    release_name: str,
    chart: str,
    namespace: str = "default",
    values: str = "",
    version: str = "",
    create_namespace: bool = True,
) -> str:
    """Install a Helm chart. values is a YAML string of overrides."""
    cmd = ["helm", "install", release_name, chart, "-n", namespace]
    if create_namespace:
        cmd.append("--create-namespace")
    if version:
        cmd += ["--version", version]
    if values:
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(values)
            tmp = f.name
        cmd += ["-f", tmp]
        result = _run(cmd)
        os.unlink(tmp)
        return result
    return _run(cmd)


@mcp.tool()
def upgrade_chart(
    release_name: str,
    chart: str,
    namespace: str = "default",
    values: str = "",
    version: str = "",
    install_if_missing: bool = True,
) -> str:
    """Upgrade (or install) a Helm release."""
    cmd = ["helm", "upgrade", release_name, chart, "-n", namespace]
    if install_if_missing:
        cmd.append("--install")
    if version:
        cmd += ["--version", version]
    if values:
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(values)
            tmp = f.name
        cmd += ["-f", tmp]
        result = _run(cmd)
        os.unlink(tmp)
        return result
    return _run(cmd)


@mcp.tool()
def uninstall_release(release_name: str, namespace: str = "default") -> str:
    """Uninstall a Helm release."""
    return _run(["helm", "uninstall", release_name, "-n", namespace])


@mcp.tool()
def rollback_release(release_name: str, revision: int = 0, namespace: str = "default") -> str:
    """Rollback a release to a previous revision. revision=0 means previous revision."""
    cmd = ["helm", "rollback", release_name, str(revision), "-n", namespace]
    return _run(cmd)


@mcp.tool()
def get_release_status(release_name: str, namespace: str = "default") -> str:
    """Get the status of a Helm release."""
    return _run(["helm", "status", release_name, "-n", namespace])


@mcp.tool()
def get_release_values(release_name: str, namespace: str = "default") -> str:
    """Get the values used in a deployed release."""
    return _run(["helm", "get", "values", release_name, "-n", namespace])


@mcp.tool()
def get_release_history(release_name: str, namespace: str = "default") -> str:
    """Get the revision history of a Helm release."""
    return _run(["helm", "history", release_name, "-n", namespace])


@mcp.tool()
def template_chart(
    release_name: str,
    chart: str,
    namespace: str = "default",
    values: str = "",
) -> str:
    """Render chart templates locally without installing."""
    cmd = ["helm", "template", release_name, chart, "-n", namespace]
    if values:
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(values)
            tmp = f.name
        cmd += ["-f", tmp]
        result = _run(cmd)
        os.unlink(tmp)
        return result
    return _run(cmd)


@mcp.tool()
def lint_chart(chart_path: str) -> str:
    """Lint a local Helm chart directory for errors."""
    return _run(["helm", "lint", chart_path])


if __name__ == "__main__":
    mcp.run(transport="stdio")
