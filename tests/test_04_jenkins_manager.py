"""
Test Case 4 — Jenkins Manager
Tests for servers/04_jenkins_manager.py
Requires Jenkins running at http://localhost:30080.
"""

import pytest
import httpx
import time


@pytest.fixture(scope="module")
def jenkins(jenkins_url, jenkins_auth):
    """Return a configured session for Jenkins with CSRF crumb."""
    try:
        r = httpx.get(f"{jenkins_url}/api/json", auth=jenkins_auth, timeout=8)
        r.raise_for_status()
    except Exception:
        pytest.skip("Jenkins not reachable")

    # Fetch crumb
    crumb_r = httpx.get(f"{jenkins_url}/crumbIssuer/api/json", auth=jenkins_auth, timeout=8)
    crumb = {}
    if crumb_r.status_code == 200:
        cd = crumb_r.json()
        crumb = {cd["crumbRequestField"]: cd["crumb"]}

    return {"url": jenkins_url, "auth": jenkins_auth, "crumb": crumb}


@pytest.fixture(scope="module")
def test_job(jenkins):
    """Create a test freestyle job and delete it after tests."""
    job_name = "mcp-pytest-job"
    config_xml = b"""<?xml version="1.1" encoding="UTF-8"?>
<project>
  <description>MCP pytest test job</description>
  <keepDependencies>false</keepDependencies>
  <properties/><scm class="hudson.scm.NullSCM"/>
  <canRoam>true</canRoam><disabled>false</disabled>
  <builders>
    <hudson.tasks.Shell>
      <command>echo MCP Test OK && date</command>
    </hudson.tasks.Shell>
  </builders>
  <publishers/><buildWrappers/>
</project>"""
    headers = {"Content-Type": "application/xml;charset=UTF-8", **jenkins["crumb"]}
    httpx.post(
        f"{jenkins['url']}/createItem?name={job_name}",
        auth=jenkins["auth"], content=config_xml, headers=headers, timeout=15,
        follow_redirects=True,
    )
    yield job_name
    # Teardown: delete job
    cr = httpx.get(f"{jenkins['url']}/crumbIssuer/api/json", auth=jenkins["auth"], timeout=8)
    crumb = {}
    if cr.status_code == 200:
        cd = cr.json()
        crumb = {cd["crumbRequestField"]: cd["crumb"]}
    httpx.post(
        f"{jenkins['url']}/job/{job_name}/doDelete",
        auth=jenkins["auth"], headers=crumb, timeout=15, follow_redirects=True,
    )


class TestJenkinsManager:

    def test_jenkins_health(self, jenkins):
        """jenkins_health should return mode=NORMAL and numExecutors > 0."""
        r = httpx.get(f"{jenkins['url']}/api/json", auth=jenkins["auth"], timeout=8)
        assert r.status_code == 200
        data = r.json()
        assert data.get("mode") == "NORMAL"
        assert data.get("numExecutors", 0) > 0

    def test_jenkins_version_header(self, jenkins):
        """Jenkins response should include X-Jenkins version header."""
        r = httpx.get(f"{jenkins['url']}/", auth=jenkins["auth"], timeout=8)
        assert "X-Jenkins" in r.headers, "X-Jenkins header missing"
        version = r.headers["X-Jenkins"]
        assert version.startswith("2."), f"Unexpected Jenkins version: {version}"

    def test_create_and_list_job(self, jenkins, test_job):
        """After create_job, list_jobs should include the new job."""
        r = httpx.get(
            f"{jenkins['url']}/api/json", auth=jenkins["auth"],
            params={"tree": "jobs[name,buildable]"}, timeout=8,
        )
        assert r.status_code == 200
        names = [j["name"] for j in r.json().get("jobs", [])]
        assert test_job in names, f"Job {test_job} not found in {names}"

    def test_trigger_build_and_check_status(self, jenkins, test_job):
        """trigger_build should queue a build; last build result should be SUCCESS."""
        cr = httpx.get(f"{jenkins['url']}/crumbIssuer/api/json", auth=jenkins["auth"], timeout=8)
        crumb = {}
        if cr.status_code == 200:
            cd = cr.json()
            crumb = {cd["crumbRequestField"]: cd["crumb"]}

        r = httpx.post(
            f"{jenkins['url']}/job/{test_job}/build",
            auth=jenkins["auth"], headers=crumb, timeout=15, follow_redirects=True,
        )
        assert r.status_code in (200, 201), f"Build trigger failed: {r.status_code}"

        # Wait for build to complete (max 30s)
        for _ in range(10):
            time.sleep(3)
            status_r = httpx.get(
                f"{jenkins['url']}/job/{test_job}/lastBuild/api/json",
                auth=jenkins["auth"], timeout=8,
            )
            if status_r.status_code == 200:
                data = status_r.json()
                if not data.get("building"):
                    assert data.get("result") == "SUCCESS", f"Build result: {data.get('result')}"
                    return
        pytest.fail("Build did not complete within 30 seconds")

    def test_list_nodes(self, jenkins):
        """list_nodes should return at least the built-in node."""
        r = httpx.get(
            f"{jenkins['url']}/computer/api/json", auth=jenkins["auth"],
            params={"tree": "computer[displayName,offline,numExecutors]"}, timeout=8,
        )
        assert r.status_code == 200
        nodes = r.json().get("computer", [])
        assert len(nodes) > 0, "No nodes found"
        assert any("Built-In" in n.get("displayName", "") for n in nodes)
