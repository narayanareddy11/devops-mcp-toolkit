"""
MCP Server 1 — Docker Manager
Manage Docker containers, images, volumes, and networks on your local Mac.
"""

import subprocess
import json
import shlex
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("docker-manager")


def _run(cmd: str) -> dict:
    """Run a shell command and return stdout/stderr/returncode."""
    result = subprocess.run(
        shlex.split(cmd),
        capture_output=True,
        text=True,
    )
    return {
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "returncode": result.returncode,
        "success": result.returncode == 0,
    }


def _docker(args: str) -> dict:
    return _run(f"docker {args}")


# ── Containers ────────────────────────────────────────────────────────────────

@mcp.tool()
def list_containers(all: bool = True) -> str:
    """List Docker containers. Set all=False to show only running containers."""
    flag = "-a" if all else ""
    out = _docker(f"ps {flag} --format json")
    if not out["success"]:
        return f"Error: {out['stderr']}"
    containers = []
    for line in out["stdout"].splitlines():
        if line.strip():
            containers.append(json.loads(line))
    return json.dumps(containers, indent=2) if containers else "No containers found."


@mcp.tool()
def start_container(container_id: str) -> str:
    """Start a stopped container by ID or name."""
    out = _docker(f"start {container_id}")
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


@mcp.tool()
def stop_container(container_id: str) -> str:
    """Stop a running container by ID or name."""
    out = _docker(f"stop {container_id}")
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


@mcp.tool()
def restart_container(container_id: str) -> str:
    """Restart a container by ID or name."""
    out = _docker(f"restart {container_id}")
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


@mcp.tool()
def remove_container(container_id: str, force: bool = False) -> str:
    """Remove a container. Use force=True to remove running containers."""
    flag = "-f" if force else ""
    out = _docker(f"rm {flag} {container_id}")
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


@mcp.tool()
def container_logs(container_id: str, tail: int = 50) -> str:
    """Fetch the last N lines of logs from a container."""
    out = _docker(f"logs --tail {tail} {container_id}")
    if not out["success"]:
        return f"Error: {out['stderr']}"
    return out["stdout"] or out["stderr"]  # docker logs goes to stderr


@mcp.tool()
def container_stats(container_id: str) -> str:
    """Get live resource usage stats for a container (one snapshot)."""
    out = _docker(f"stats --no-stream --format json {container_id}")
    if not out["success"]:
        return f"Error: {out['stderr']}"
    return out["stdout"]


@mcp.tool()
def inspect_container(container_id: str) -> str:
    """Return full JSON inspection of a container."""
    out = _docker(f"inspect {container_id}")
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


@mcp.tool()
def exec_in_container(container_id: str, command: str) -> str:
    """Run a command inside a running container and return the output."""
    out = _docker(f"exec {container_id} {command}")
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


@mcp.tool()
def run_container(
    image: str,
    name: str = "",
    ports: str = "",
    env_vars: str = "",
    detach: bool = True,
    remove_on_exit: bool = False,
) -> str:
    """
    Run a new container from an image.
    ports format: "host_port:container_port" (e.g. "8080:80")
    env_vars format: "KEY=VALUE KEY2=VALUE2"
    """
    parts = ["run"]
    if detach:
        parts.append("-d")
    if remove_on_exit:
        parts.append("--rm")
    if name:
        parts.extend(["--name", name])
    if ports:
        for p in ports.split():
            parts.extend(["-p", p])
    if env_vars:
        for e in env_vars.split():
            parts.extend(["-e", e])
    parts.append(image)
    out = _docker(" ".join(parts))
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


# ── Images ────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_images() -> str:
    """List all local Docker images."""
    out = _docker("images --format json")
    if not out["success"]:
        return f"Error: {out['stderr']}"
    images = [json.loads(l) for l in out["stdout"].splitlines() if l.strip()]
    return json.dumps(images, indent=2) if images else "No images found."


@mcp.tool()
def pull_image(image: str) -> str:
    """Pull a Docker image from Docker Hub (e.g. 'nginx:latest')."""
    out = _docker(f"pull {image}")
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


@mcp.tool()
def remove_image(image: str, force: bool = False) -> str:
    """Remove a local Docker image."""
    flag = "-f" if force else ""
    out = _docker(f"rmi {flag} {image}")
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


@mcp.tool()
def build_image(context_path: str, tag: str, dockerfile: str = "Dockerfile") -> str:
    """Build a Docker image from a Dockerfile."""
    out = _docker(f"build -t {tag} -f {dockerfile} {context_path}")
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


# ── Volumes & Networks ────────────────────────────────────────────────────────

@mcp.tool()
def list_volumes() -> str:
    """List all Docker volumes."""
    out = _docker("volume ls --format json")
    if not out["success"]:
        return f"Error: {out['stderr']}"
    volumes = [json.loads(l) for l in out["stdout"].splitlines() if l.strip()]
    return json.dumps(volumes, indent=2) if volumes else "No volumes found."


@mcp.tool()
def list_networks() -> str:
    """List all Docker networks."""
    out = _docker("network ls --format json")
    if not out["success"]:
        return f"Error: {out['stderr']}"
    networks = [json.loads(l) for l in out["stdout"].splitlines() if l.strip()]
    return json.dumps(networks, indent=2) if networks else "No networks found."


@mcp.tool()
def prune_system(volumes: bool = False) -> str:
    """
    Remove all stopped containers, unused images, and build cache.
    Set volumes=True to also remove unused volumes (destructive!).
    """
    flag = "--volumes" if volumes else ""
    out = _docker(f"system prune -f {flag}")
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


# ── Docker Compose ────────────────────────────────────────────────────────────

@mcp.tool()
def compose_up(compose_file: str, detach: bool = True) -> str:
    """Start services defined in a docker-compose.yml file."""
    flag = "-d" if detach else ""
    out = _run(f"docker compose -f {compose_file} up {flag}")
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


@mcp.tool()
def compose_down(compose_file: str) -> str:
    """Stop and remove services defined in a docker-compose.yml file."""
    out = _run(f"docker compose -f {compose_file} down")
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


@mcp.tool()
def compose_ps(compose_file: str) -> str:
    """List services and their status in a docker-compose project."""
    out = _run(f"docker compose -f {compose_file} ps")
    return out["stdout"] if out["success"] else f"Error: {out['stderr']}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
