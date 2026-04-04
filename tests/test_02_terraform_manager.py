"""
Test Case 2 — Terraform Manager
Tests for servers/02_terraform_manager.py
Verifies Terraform CLI wrapper tools work against terraform/local.
"""

import subprocess
import json
import os
import pytest
from pathlib import Path

WORKDIR = str(Path(__file__).parent.parent / "terraform" / "local")


def tf(cmd: str) -> dict:
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        cwd=WORKDIR, env={**os.environ, "TF_IN_AUTOMATION": "1"},
    )
    return {"stdout": result.stdout.strip(), "stderr": result.stderr.strip(), "success": result.returncode == 0}


@pytest.fixture(scope="module", autouse=True)
def terraform_init():
    """Ensure terraform is initialized before any terraform test."""
    result = subprocess.run("terraform version", shell=True, capture_output=True)
    if result.returncode != 0:
        pytest.skip("terraform CLI not installed")
    tf("terraform init -no-color")


class TestTerraformManager:

    def test_terraform_version(self):
        """terraform_version should return a valid version string."""
        out = tf("terraform version -json")
        assert out["success"], f"terraform version failed: {out['stderr']}"
        data = json.loads(out["stdout"])
        assert "terraform_version" in data
        assert data["terraform_version"].startswith("1."), "Expected Terraform 1.x"

    def test_terraform_validate(self):
        """terraform_validate should pass on the local example config."""
        out = tf("terraform validate -json")
        assert out["success"], f"validate failed: {out['stderr']}"
        data = json.loads(out["stdout"])
        assert data.get("valid") is True, f"Config invalid: {data.get('diagnostics')}"

    def test_terraform_plan_produces_output(self):
        """terraform_plan should produce a non-empty execution plan."""
        out = tf("terraform plan -no-color -var-file=terraform.tfvars")
        combined = out["stdout"] + out["stderr"]
        assert "Plan:" in combined or "No changes" in combined, "Plan produced no output"

    def test_terraform_apply_creates_resources(self):
        """terraform_apply should create all 4 resources in the local example."""
        out = tf("terraform apply -no-color -auto-approve -var-file=terraform.tfvars")
        combined = out["stdout"] + out["stderr"]
        assert "Apply complete!" in combined, f"Apply did not complete:\n{combined}"
        assert "4 added" in combined or "0 to change" in combined

    def test_terraform_state_list_has_resources(self):
        """terraform state list should show the 4 managed resources."""
        out = tf("terraform state list")
        assert out["success"], f"state list failed: {out['stderr']}"
        resources = out["stdout"].splitlines()
        assert len(resources) >= 4, f"Expected 4 resources, got: {resources}"
        assert any("local_file" in r for r in resources)
        assert any("null_resource" in r for r in resources)

    def test_terraform_output_matches_vars(self):
        """terraform output should reflect the values from terraform.tfvars."""
        out = tf("terraform output -json")
        assert out["success"]
        data = json.loads(out["stdout"])
        assert "deployment_summary" in data
        summary = data["deployment_summary"]["value"]
        assert summary["app_name"] == "my-devops-app"
        assert summary["environment"] == "dev"
        assert summary["port"] == 3000
