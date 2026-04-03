"""
MCP Server 4 — Jenkins Manager
Interact with Jenkins running locally on http://localhost:8080.
Default credentials: admin / admin (update via env vars JENKINS_USER / JENKINS_PASS).
"""

import httpx
import json
import os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("jenkins-manager")

JENKINS_URL = os.environ.get("JENKINS_URL", "http://localhost:30080")


def _auth() -> tuple:
    return (
        os.environ.get("JENKINS_USER", "admin"),
        os.environ.get("JENKINS_PASS", "admin"),
    )


def _get(path: str, params: dict = None) -> dict | str:
    try:
        r = httpx.get(
            f"{JENKINS_URL}/{path.lstrip('/')}",
            auth=_auth(),
            params=params or {},
            timeout=20,
            follow_redirects=True,
        )
        r.raise_for_status()
        try:
            return r.json()
        except Exception:
            return r.text
    except httpx.HTTPStatusError as e:
        return {"error": str(e), "status_code": e.response.status_code}
    except Exception as e:
        return {"error": str(e)}


def _post(path: str, data: dict = None, raw_body: str = None, headers: dict = None) -> dict | str:
    try:
        h = headers or {}
        r = httpx.post(
            f"{JENKINS_URL}/{path.lstrip('/')}",
            auth=_auth(),
            data=data,
            content=raw_body,
            headers=h,
            timeout=30,
            follow_redirects=True,
        )
        r.raise_for_status()
        try:
            return r.json()
        except Exception:
            return r.text or "OK"
    except httpx.HTTPStatusError as e:
        return {"error": str(e), "status_code": e.response.status_code, "body": e.response.text}
    except Exception as e:
        return {"error": str(e)}


def _crumb() -> dict:
    """Fetch Jenkins CSRF crumb required for POST requests."""
    try:
        r = httpx.get(
            f"{JENKINS_URL}/crumbIssuer/api/json",
            auth=_auth(),
            timeout=10,
        )
        data = r.json()
        return {data["crumbRequestField"]: data["crumb"]}
    except Exception:
        return {}


# ── Server health ──────────────────────────────────────────────────────────────

@mcp.tool()
def jenkins_health() -> str:
    """Check if Jenkins is reachable and return basic server info."""
    try:
        r = httpx.get(f"{JENKINS_URL}/api/json", auth=_auth(), timeout=10)
        data = r.json()
        return json.dumps({
            "url": JENKINS_URL,
            "mode": data.get("mode"),
            "numExecutors": data.get("numExecutors"),
            "useSecurity": data.get("useSecurity"),
            "jobs_count": len(data.get("jobs", [])),
        }, indent=2)
    except Exception as e:
        return f"Jenkins unreachable at {JENKINS_URL}: {e}"


@mcp.tool()
def jenkins_version() -> str:
    """Return the Jenkins server version."""
    try:
        r = httpx.get(f"{JENKINS_URL}/", auth=_auth(), timeout=10)
        version = r.headers.get("X-Jenkins", "unknown")
        return f"Jenkins version: {version}"
    except Exception as e:
        return f"Error: {e}"


# ── Jobs ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_jobs(folder: str = "") -> str:
    """
    List all Jenkins jobs.
    folder: optional folder/view name to filter (e.g. 'MyFolder').
    """
    path = f"job/{folder}/api/json" if folder else "api/json"
    data = _get(path, {"tree": "jobs[name,url,color,buildable]"})
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data}"
    jobs = data.get("jobs", []) if isinstance(data, dict) else []
    result = [
        {
            "name": j["name"],
            "status": j.get("color", "unknown"),
            "buildable": j.get("buildable", True),
        }
        for j in jobs
    ]
    return json.dumps(result, indent=2) if result else "No jobs found."


@mcp.tool()
def get_job_info(job_name: str) -> str:
    """Get detailed info about a specific Jenkins job."""
    data = _get(f"job/{job_name}/api/json")
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data}"
    if isinstance(data, dict):
        return json.dumps({
            "name": data.get("name"),
            "description": data.get("description"),
            "buildable": data.get("buildable"),
            "lastBuild": data.get("lastBuild"),
            "lastSuccessfulBuild": data.get("lastSuccessfulBuild"),
            "lastFailedBuild": data.get("lastFailedBuild"),
            "nextBuildNumber": data.get("nextBuildNumber"),
            "healthReport": data.get("healthReport", []),
        }, indent=2)
    return str(data)


@mcp.tool()
def create_freestyle_job(job_name: str, description: str = "", shell_command: str = "echo Hello from Jenkins") -> str:
    """
    Create a simple freestyle Jenkins job with a shell build step.
    """
    config_xml = f"""<?xml version='1.1' encoding='UTF-8'?>
<project>
  <description>{description}</description>
  <keepDependencies>false</keepDependencies>
  <properties/>
  <scm class="hudson.scm.NullSCM"/>
  <canRoam>true</canRoam>
  <disabled>false</disabled>
  <blockBuildWhenDownstreamBuilding>false</blockBuildWhenDownstreamBuilding>
  <blockBuildWhenUpstreamBuilding>false</blockBuildWhenUpstreamBuilding>
  <triggers/>
  <concurrentBuild>false</concurrentBuild>
  <builders>
    <hudson.tasks.Shell>
      <command>{shell_command}</command>
    </hudson.tasks.Shell>
  </builders>
  <publishers/>
  <buildWrappers/>
</project>"""
    crumb = _crumb()
    headers = {"Content-Type": "application/xml", **crumb}
    result = _post(f"createItem?name={job_name}", raw_body=config_xml, headers=headers)
    return str(result)


@mcp.tool()
def delete_job(job_name: str) -> str:
    """Delete a Jenkins job by name."""
    crumb = _crumb()
    result = _post(f"job/{job_name}/doDelete", headers=crumb)
    return str(result)


@mcp.tool()
def enable_job(job_name: str) -> str:
    """Enable a disabled Jenkins job."""
    crumb = _crumb()
    result = _post(f"job/{job_name}/enable", headers=crumb)
    return str(result)


@mcp.tool()
def disable_job(job_name: str) -> str:
    """Disable a Jenkins job (prevents new builds)."""
    crumb = _crumb()
    result = _post(f"job/{job_name}/disable", headers=crumb)
    return str(result)


# ── Builds ────────────────────────────────────────────────────────────────────

@mcp.tool()
def trigger_build(job_name: str, params: str = "") -> str:
    """
    Trigger a build for a Jenkins job.
    params: optional key=value pairs separated by spaces (e.g. "BRANCH=main ENV=dev").
    """
    crumb = _crumb()
    if params:
        param_dict = {}
        for p in params.split():
            k, _, v = p.partition("=")
            param_dict[k] = v
        result = _post(f"job/{job_name}/buildWithParameters", data=param_dict, headers=crumb)
    else:
        result = _post(f"job/{job_name}/build", headers=crumb)
    return f"Build triggered for '{job_name}'. {result}"


@mcp.tool()
def get_build_status(job_name: str, build_number: int = 0) -> str:
    """
    Get status of a specific build (or latest if build_number=0).
    """
    if build_number == 0:
        path = f"job/{job_name}/lastBuild/api/json"
    else:
        path = f"job/{job_name}/{build_number}/api/json"
    data = _get(path)
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data}"
    if isinstance(data, dict):
        return json.dumps({
            "number": data.get("number"),
            "result": data.get("result"),
            "building": data.get("building"),
            "duration": data.get("duration"),
            "timestamp": data.get("timestamp"),
            "url": data.get("url"),
            "causes": [c.get("shortDescription") for c in data.get("actions", [{}])[0].get("causes", [])],
        }, indent=2)
    return str(data)


@mcp.tool()
def get_build_log(job_name: str, build_number: int = 0, tail_lines: int = 100) -> str:
    """
    Fetch console log of a build.
    build_number=0 fetches last build. tail_lines limits output.
    """
    if build_number == 0:
        path = f"job/{job_name}/lastBuild/consoleText"
    else:
        path = f"job/{job_name}/{build_number}/consoleText"
    result = _get(path)
    if isinstance(result, str):
        lines = result.splitlines()
        return "\n".join(lines[-tail_lines:])
    return f"Error: {result}"


@mcp.tool()
def list_builds(job_name: str, count: int = 10) -> str:
    """List recent builds for a job with their status."""
    data = _get(f"job/{job_name}/api/json", {
        "tree": f"builds[number,result,duration,timestamp,building]{{0,{count}}}"
    })
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data}"
    builds = data.get("builds", []) if isinstance(data, dict) else []
    return json.dumps(builds, indent=2) if builds else "No builds found."


@mcp.tool()
def stop_build(job_name: str, build_number: int) -> str:
    """Abort a running build."""
    crumb = _crumb()
    result = _post(f"job/{job_name}/{build_number}/stop", headers=crumb)
    return str(result)


# ── Queue ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_queue() -> str:
    """Show all builds currently waiting in the Jenkins build queue."""
    data = _get("queue/api/json")
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data}"
    items = data.get("items", []) if isinstance(data, dict) else []
    result = [
        {
            "id": i["id"],
            "job": i.get("task", {}).get("name"),
            "why": i.get("why"),
            "inQueueSince": i.get("inQueueSince"),
        }
        for i in items
    ]
    return json.dumps(result, indent=2) if result else "Queue is empty."


# ── Plugins ───────────────────────────────────────────────────────────────────

@mcp.tool()
def list_plugins() -> str:
    """List all installed Jenkins plugins and their versions."""
    data = _get("pluginManager/api/json", {"depth": 1, "tree": "plugins[shortName,longName,version,active]"})
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data}"
    plugins = data.get("plugins", []) if isinstance(data, dict) else []
    result = [
        {"name": p["shortName"], "version": p["version"], "active": p["active"]}
        for p in plugins
    ]
    return json.dumps(sorted(result, key=lambda x: x["name"]), indent=2)


# ── Nodes / Executors ─────────────────────────────────────────────────────────

@mcp.tool()
def list_nodes() -> str:
    """List all Jenkins build nodes (master + agents)."""
    data = _get("computer/api/json", {"tree": "computer[displayName,offline,numExecutors,description]"})
    if isinstance(data, dict) and "error" in data:
        return f"Error: {data}"
    nodes = data.get("computer", []) if isinstance(data, dict) else []
    return json.dumps(nodes, indent=2) if nodes else "No nodes found."


if __name__ == "__main__":
    mcp.run(transport="stdio")
