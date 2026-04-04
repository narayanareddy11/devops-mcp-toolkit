"""Container Registry Manager MCP Server — manage Docker Registry v2 (OCI-compatible)."""

import os
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("harbor-manager")

REGISTRY_URL = os.environ.get("HARBOR_URL", "http://127.0.0.1:30880")
REGISTRY_UI_URL = os.environ.get("HARBOR_UI_URL", "http://127.0.0.1:30881")
REGISTRY_USER = os.environ.get("HARBOR_USER", "admin")
REGISTRY_PASS = os.environ.get("HARBOR_PASS", "Admin@123456789@")


def _auth() -> tuple:
    return (REGISTRY_USER, REGISTRY_PASS)


def _get(path: str) -> dict | list:
    try:
        r = httpx.get(f"{REGISTRY_URL}{path}", auth=_auth(), timeout=15)
        if r.status_code == 401:
            return {"error": "Unauthorized - check credentials"}
        if r.status_code == 404:
            return {"error": "Not found"}
        return r.json() if r.text else {}
    except Exception as e:
        return {"error": str(e)}


def _delete_req(path: str, headers: dict = {}) -> dict:
    try:
        r = httpx.delete(f"{REGISTRY_URL}{path}", auth=_auth(), headers=headers, timeout=15)
        return {"status": r.status_code}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def registry_health() -> str:
    """Check if the container registry is healthy and reachable."""
    try:
        r = httpx.get(f"{REGISTRY_URL}/v2/", auth=_auth(), timeout=10)
        if r.status_code in [200, 401]:
            return (
                f"Registry Status: Healthy\n"
                f"API Endpoint: {REGISTRY_URL}\n"
                f"UI: {REGISTRY_UI_URL}\n"
                f"Docker pull: docker pull localhost:30880/<image>:<tag>\n"
                f"Docker push: docker tag <image> localhost:30880/<image>:<tag> && docker push localhost:30880/<image>:<tag>"
            )
        return f"Registry returned: HTTP {r.status_code}"
    except Exception as e:
        return f"Registry unreachable at {REGISTRY_URL}: {e}"


@mcp.tool()
def list_repositories() -> str:
    """List all image repositories in the container registry."""
    result = _get("/v2/_catalog")
    if "error" in result:
        return f"Error: {result['error']}"
    repos = result.get("repositories", [])
    return "Repositories:\n" + "\n".join(f"  - {r}" for r in repos) if repos else "No repositories found"


@mcp.tool()
def list_tags(repository: str) -> str:
    """List all tags for a repository. repository example: 'myapp' or 'myorg/myapp'."""
    result = _get(f"/v2/{repository}/tags/list")
    if "error" in result:
        return f"Error: {result['error']}"
    tags = result.get("tags", [])
    return f"Tags for '{repository}':\n" + "\n".join(f"  - {t}" for t in tags) if tags else f"No tags found for '{repository}'"


@mcp.tool()
def get_manifest(repository: str, tag: str = "latest") -> str:
    """Get the manifest for an image (shows layers, config digest, size)."""
    try:
        r = httpx.get(
            f"{REGISTRY_URL}/v2/{repository}/manifests/{tag}",
            auth=_auth(),
            headers={"Accept": "application/vnd.docker.distribution.manifest.v2+json"},
            timeout=15
        )
        if r.status_code == 404:
            return f"Image '{repository}:{tag}' not found"
        data = r.json()
        config = data.get("config", {})
        layers = data.get("layers", [])
        total_size = sum(l.get("size", 0) for l in layers) // (1024 * 1024)
        digest = r.headers.get("Docker-Content-Digest", "N/A")
        return (
            f"Image: {repository}:{tag}\n"
            f"Digest: {digest}\n"
            f"Schema: {data.get('schemaVersion', 'N/A')}\n"
            f"Config digest: {config.get('digest', 'N/A')[:30]}...\n"
            f"Layers: {len(layers)}\n"
            f"Total size: ~{total_size}MB"
        )
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def delete_image(repository: str, tag: str) -> str:
    """Delete an image tag from the registry. First gets the digest, then deletes by digest."""
    try:
        r = httpx.get(
            f"{REGISTRY_URL}/v2/{repository}/manifests/{tag}",
            auth=_auth(),
            headers={"Accept": "application/vnd.docker.distribution.manifest.v2+json"},
            timeout=15
        )
        if r.status_code == 404:
            return f"Image '{repository}:{tag}' not found"
        digest = r.headers.get("Docker-Content-Digest")
        if not digest:
            return "Could not get image digest"
        del_r = _delete_req(f"/v2/{repository}/manifests/{digest}")
        if del_r.get("status") == 202:
            return f"Image '{repository}:{tag}' (digest: {digest[:20]}...) deleted"
        return f"Delete result: {del_r}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def get_blob(repository: str, digest: str) -> str:
    """Get info about a specific layer blob."""
    try:
        r = httpx.head(f"{REGISTRY_URL}/v2/{repository}/blobs/{digest}", auth=_auth(), timeout=15)
        size = int(r.headers.get("Content-Length", 0))
        return f"Blob: {digest}\nSize: {size // 1024}KB\nContent-Type: {r.headers.get('Content-Type', 'N/A')}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def docker_push_instructions(image_name: str, tag: str = "latest") -> str:
    """Get instructions for pushing a Docker image to this registry."""
    host = REGISTRY_URL.replace("http://", "").replace("https://", "")
    return (
        f"Push '{image_name}:{tag}' to local registry:\n\n"
        f"1. Configure Docker to allow insecure registry:\n"
        f"   Add to /etc/docker/daemon.json:\n"
        f'   {{"insecure-registries": ["{host}"]}}\n\n'
        f"2. Login:\n"
        f"   docker login {host} -u {REGISTRY_USER}\n\n"
        f"3. Tag image:\n"
        f"   docker tag {image_name}:{tag} {host}/{image_name}:{tag}\n\n"
        f"4. Push:\n"
        f"   docker push {host}/{image_name}:{tag}\n\n"
        f"5. Pull from K8s:\n"
        f"   image: {host}/{image_name}:{tag}"
    )


@mcp.tool()
def registry_stats() -> str:
    """Get registry statistics — total repositories and tags."""
    result = _get("/v2/_catalog")
    if "error" in result:
        return f"Error: {result['error']}"
    repos = result.get("repositories", [])
    total_tags = 0
    details = []
    for repo in repos:
        tags_result = _get(f"/v2/{repo}/tags/list")
        tags = tags_result.get("tags", []) if "error" not in tags_result else []
        total_tags += len(tags)
        details.append(f"  {repo}: {len(tags)} tags")
    return (
        f"Registry Statistics:\n"
        f"  Total repositories: {len(repos)}\n"
        f"  Total tags: {total_tags}\n\n"
        "Details:\n" + ("\n".join(details) if details else "  No repositories")
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
