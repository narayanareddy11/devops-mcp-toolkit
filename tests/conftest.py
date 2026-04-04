"""
Shared pytest fixtures for DevOps MCP Toolkit tests.
Services must be running in K8s devops namespace:
  - Jenkins  → http://localhost:30080
  - SonarQube → http://localhost:30900
"""

import subprocess
import pytest
import httpx
import os


JENKINS_URL  = os.environ.get("JENKINS_URL",  "http://localhost:30080")
SONAR_URL    = os.environ.get("SONAR_URL",    "http://localhost:30900")
JENKINS_AUTH = (os.environ.get("JENKINS_USER", "admin"), os.environ.get("JENKINS_PASS", "admin"))
SONAR_AUTH   = (os.environ.get("SONAR_USER",  "admin"), os.environ.get("SONAR_PASS",   "Aa75696462461@"))


@pytest.fixture(scope="session")
def jenkins_url():
    return JENKINS_URL


@pytest.fixture(scope="session")
def sonar_url():
    return SONAR_URL


@pytest.fixture(scope="session")
def jenkins_auth():
    return JENKINS_AUTH


@pytest.fixture(scope="session")
def sonar_auth():
    return SONAR_AUTH


@pytest.fixture(scope="session")
def docker_available():
    result = subprocess.run("docker info", shell=True, capture_output=True)
    return result.returncode == 0


@pytest.fixture(scope="session")
def kubectl_available():
    result = subprocess.run("kubectl version --client", shell=True, capture_output=True)
    return result.returncode == 0


@pytest.fixture(scope="session")
def terraform_available():
    result = subprocess.run("terraform version", shell=True, capture_output=True)
    return result.returncode == 0
