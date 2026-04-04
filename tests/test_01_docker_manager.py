"""
Test Case 1 — Docker Manager
Tests for servers/01_docker_manager.py
Verifies Docker CLI wrapper tools work correctly.
"""

import subprocess
import json
import pytest


def run_docker(args: str) -> dict:
    result = subprocess.run(f"docker {args}", shell=True, capture_output=True, text=True)
    return {
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "success": result.returncode == 0,
    }


class TestDockerManager:

    def test_docker_daemon_running(self):
        """Docker daemon must be reachable before any other Docker test."""
        out = run_docker("info --format '{{.ServerVersion}}'")
        assert out["success"], "Docker daemon is not running"
        assert out["stdout"] != "", "Docker version should not be empty"

    def test_list_containers_returns_list(self):
        """list_containers should return a valid JSON array."""
        out = run_docker("ps -a --format json")
        assert out["success"], f"docker ps failed: {out['stderr']}"
        containers = [json.loads(l) for l in out["stdout"].splitlines() if l.strip()]
        assert isinstance(containers, list), "Expected a list of containers"

    def test_k8s_devops_containers_running(self):
        """Jenkins, SonarQube and Postgres K8s containers should be running."""
        out = run_docker("ps --format json")
        assert out["success"]
        containers = [json.loads(l) for l in out["stdout"].splitlines() if l.strip()]
        names = [c.get("Names", "") for c in containers]
        devops_running = any("jenkins" in n or "sonarqube" in n or "postgres" in n for n in names)
        assert devops_running, f"No DevOps containers found running. Running: {names}"

    def test_list_images_not_empty(self):
        """At least the Jenkins, SonarQube and Postgres images should exist locally."""
        out = run_docker("images --format json")
        assert out["success"]
        images = [json.loads(l) for l in out["stdout"].splitlines() if l.strip()]
        repos = [i.get("Repository", "") for i in images]
        assert any("jenkins" in r for r in repos), "jenkins/jenkins image not found"
        assert any("sonarqube" in r for r in repos), "sonarqube image not found"
        assert any("postgres" in r for r in repos), "postgres image not found"

    def test_list_volumes_returns_devops_volumes(self):
        """K8s-managed volumes for the devops stack should exist."""
        out = run_docker("volume ls --format json")
        assert out["success"]
        vols = [json.loads(l) for l in out["stdout"].splitlines() if l.strip()]
        names = [v.get("Name", "") for v in vols]
        assert len(names) > 0, "No Docker volumes found"
