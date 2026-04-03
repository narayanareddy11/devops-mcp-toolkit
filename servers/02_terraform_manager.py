"""
MCP Server 2 — Terraform Manager
Run Terraform commands locally: init, plan, apply, destroy, and inspect state.
Includes a local example under terraform/local/.
"""

import subprocess
import json
import os
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("terraform-manager")

DEFAULT_WORKDIR = str(Path(__file__).parent.parent / "terraform" / "local")


def _tf(cmd: str, workdir: str = DEFAULT_WORKDIR) -> dict:
    """Run a terraform command in the given working directory."""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        cwd=workdir,
        env={**os.environ, "TF_IN_AUTOMATION": "1"},
    )
    return {
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "returncode": result.returncode,
        "success": result.returncode == 0,
    }


# ── Core lifecycle ─────────────────────────────────────────────────────────────

@mcp.tool()
def terraform_init(workdir: str = DEFAULT_WORKDIR) -> str:
    """
    Initialize a Terraform working directory.
    Downloads providers and sets up the backend.
    Default workdir points to the local example at terraform/local/.
    """
    out = _tf("terraform init -no-color", workdir)
    combined = f"{out['stdout']}\n{out['stderr']}".strip()
    return combined if out["success"] else f"Error (rc={out['returncode']}):\n{combined}"


@mcp.tool()
def terraform_validate(workdir: str = DEFAULT_WORKDIR) -> str:
    """Validate the Terraform configuration files in a directory."""
    out = _tf("terraform validate -json", workdir)
    combined = f"{out['stdout']}\n{out['stderr']}".strip()
    try:
        return json.dumps(json.loads(out["stdout"]), indent=2)
    except Exception:
        return combined


@mcp.tool()
def terraform_plan(
    workdir: str = DEFAULT_WORKDIR,
    var_file: str = "terraform.tfvars",
    extra_vars: str = "",
) -> str:
    """
    Show execution plan without making changes.
    extra_vars format: "key=value key2=value2"
    """
    var_flags = f"-var-file={var_file}" if var_file and Path(f"{workdir}/{var_file}").exists() else ""
    extra = " ".join(f"-var '{v}'" for v in extra_vars.split()) if extra_vars else ""
    cmd = f"terraform plan -no-color {var_flags} {extra}"
    out = _tf(cmd, workdir)
    combined = f"{out['stdout']}\n{out['stderr']}".strip()
    return combined


@mcp.tool()
def terraform_apply(
    workdir: str = DEFAULT_WORKDIR,
    var_file: str = "terraform.tfvars",
    extra_vars: str = "",
    auto_approve: bool = True,
) -> str:
    """
    Apply the Terraform plan and provision resources.
    auto_approve=True skips the interactive confirmation prompt.
    """
    var_flags = f"-var-file={var_file}" if var_file and Path(f"{workdir}/{var_file}").exists() else ""
    extra = " ".join(f"-var '{v}'" for v in extra_vars.split()) if extra_vars else ""
    approve = "-auto-approve" if auto_approve else ""
    cmd = f"terraform apply -no-color {approve} {var_flags} {extra}"
    out = _tf(cmd, workdir)
    combined = f"{out['stdout']}\n{out['stderr']}".strip()
    return combined


@mcp.tool()
def terraform_destroy(
    workdir: str = DEFAULT_WORKDIR,
    var_file: str = "terraform.tfvars",
    auto_approve: bool = True,
) -> str:
    """
    Destroy all resources managed by Terraform in the given directory.
    WARNING: This is destructive and irreversible.
    """
    var_flags = f"-var-file={var_file}" if var_file and Path(f"{workdir}/{var_file}").exists() else ""
    approve = "-auto-approve" if auto_approve else ""
    cmd = f"terraform destroy -no-color {approve} {var_flags}"
    out = _tf(cmd, workdir)
    combined = f"{out['stdout']}\n{out['stderr']}".strip()
    return combined


# ── State inspection ──────────────────────────────────────────────────────────

@mcp.tool()
def terraform_show(workdir: str = DEFAULT_WORKDIR) -> str:
    """Show the current Terraform state in human-readable format."""
    out = _tf("terraform show -no-color", workdir)
    combined = f"{out['stdout']}\n{out['stderr']}".strip()
    return combined if combined else "No state found — run terraform_apply first."


@mcp.tool()
def terraform_state_list(workdir: str = DEFAULT_WORKDIR) -> str:
    """List all resources tracked in the Terraform state."""
    out = _tf("terraform state list", workdir)
    if not out["success"]:
        return f"Error: {out['stderr']}"
    resources = out["stdout"].splitlines()
    return "\n".join(resources) if resources else "State is empty."


@mcp.tool()
def terraform_output(workdir: str = DEFAULT_WORKDIR) -> str:
    """Show all Terraform output values as JSON."""
    out = _tf("terraform output -json", workdir)
    if not out["success"]:
        return f"Error: {out['stderr']}"
    try:
        return json.dumps(json.loads(out["stdout"]), indent=2)
    except Exception:
        return out["stdout"] or "No outputs defined."


@mcp.tool()
def terraform_refresh(workdir: str = DEFAULT_WORKDIR) -> str:
    """Refresh the Terraform state against real infrastructure."""
    out = _tf("terraform refresh -no-color", workdir)
    combined = f"{out['stdout']}\n{out['stderr']}".strip()
    return combined


# ── Workspace management ──────────────────────────────────────────────────────

@mcp.tool()
def terraform_workspace_list(workdir: str = DEFAULT_WORKDIR) -> str:
    """List all Terraform workspaces."""
    out = _tf("terraform workspace list", workdir)
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


@mcp.tool()
def terraform_workspace_new(name: str, workdir: str = DEFAULT_WORKDIR) -> str:
    """Create a new Terraform workspace."""
    out = _tf(f"terraform workspace new {name}", workdir)
    combined = f"{out['stdout']}\n{out['stderr']}".strip()
    return combined


@mcp.tool()
def terraform_workspace_select(name: str, workdir: str = DEFAULT_WORKDIR) -> str:
    """Switch to an existing Terraform workspace."""
    out = _tf(f"terraform workspace select {name}", workdir)
    combined = f"{out['stdout']}\n{out['stderr']}".strip()
    return combined


# ── Utility ───────────────────────────────────────────────────────────────────

@mcp.tool()
def terraform_version() -> str:
    """Show the installed Terraform version."""
    out = _tf("terraform version -json", os.getcwd())
    try:
        return json.dumps(json.loads(out["stdout"]), indent=2)
    except Exception:
        return out["stdout"] or f"Error: {out['stderr']}"


@mcp.tool()
def list_workdirs(base_path: str = str(Path(__file__).parent.parent / "terraform")) -> str:
    """
    List available Terraform working directories under the terraform/ folder.
    """
    base = Path(base_path)
    if not base.exists():
        return f"Directory not found: {base_path}"
    dirs = [str(d) for d in base.rglob("*.tf")]
    return "\n".join(sorted(set(str(Path(d).parent) for d in dirs))) or "No .tf files found."


if __name__ == "__main__":
    mcp.run(transport="stdio")
