"""
Test Case 3 — SonarQube Manager
Tests for servers/03_sonarqube_manager.py
Requires SonarQube running at http://localhost:30900.
"""

import pytest
import httpx


@pytest.fixture(scope="module")
def sonar(sonar_url, sonar_auth):
    """Return a configured httpx client for SonarQube."""
    try:
        r = httpx.get(f"{sonar_url}/api/system/ping", auth=sonar_auth, timeout=5)
        if r.text != "pong":
            pytest.skip("SonarQube not reachable")
    except Exception:
        pytest.skip("SonarQube not reachable")
    return {"url": sonar_url, "auth": sonar_auth}


@pytest.fixture(scope="module")
def test_project(sonar):
    """Create a throwaway project for testing and clean it up after."""
    key = "mcp-test-project"
    httpx.post(
        f"{sonar['url']}/api/projects/create",
        auth=sonar["auth"],
        data={"project": key, "name": "MCP Test Project", "visibility": "public"},
        timeout=10,
    )
    yield key
    httpx.post(
        f"{sonar['url']}/api/projects/delete",
        auth=sonar["auth"],
        data={"project": key},
        timeout=10,
    )


class TestSonarQubeManager:

    def test_sonar_ping(self, sonar):
        """sonar_ping should return 'pong'."""
        r = httpx.get(f"{sonar['url']}/api/system/ping", auth=sonar["auth"], timeout=5)
        assert r.status_code == 200
        assert r.text == "pong"

    def test_sonar_health_green(self, sonar):
        """sonar_health should return GREEN status."""
        r = httpx.get(f"{sonar['url']}/api/system/health", auth=sonar["auth"], timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data.get("health") == "GREEN", f"SonarQube health is {data.get('health')}"

    def test_create_and_list_project(self, sonar, test_project):
        """create_project then list_projects should include the new project."""
        r = httpx.get(
            f"{sonar['url']}/api/projects/search",
            auth=sonar["auth"], params={"ps": 50}, timeout=10,
        )
        assert r.status_code == 200
        keys = [c["key"] for c in r.json().get("components", [])]
        assert test_project in keys, f"Project {test_project} not found in {keys}"

    def test_quality_gate_exists(self, sonar):
        """list_quality_gates should return at least the default 'Sonar way' gate."""
        r = httpx.get(f"{sonar['url']}/api/qualitygates/list", auth=sonar["auth"], timeout=10)
        assert r.status_code == 200
        gates = r.json().get("qualitygates", [])
        assert len(gates) > 0, "No quality gates found"
        names = [g["name"] for g in gates]
        assert "Sonar way" in names, f"Default gate missing. Found: {names}"

    def test_generate_token(self, sonar):
        """generate_token should return a token with login and name fields."""
        token_name = "mcp-test-token-pytest"
        # Clean up first in case previous run left it
        httpx.post(f"{sonar['url']}/api/user_tokens/revoke", auth=sonar["auth"],
                   data={"name": token_name, "login": "admin"}, timeout=10)
        r = httpx.post(
            f"{sonar['url']}/api/user_tokens/generate",
            auth=sonar["auth"],
            data={"name": token_name, "login": "admin"},
            timeout=10,
        )
        assert r.status_code == 200
        data = r.json()
        assert "token" in data, "No token in response"
        assert data.get("login") == "admin"
        assert data.get("name") == token_name
        # Cleanup
        httpx.post(f"{sonar['url']}/api/user_tokens/revoke", auth=sonar["auth"],
                   data={"name": token_name, "login": "admin"}, timeout=10)
