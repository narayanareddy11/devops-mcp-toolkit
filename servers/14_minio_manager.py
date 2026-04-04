"""MinIO Manager MCP Server — manage MinIO S3-compatible object storage."""

import os
import httpx
import json
import hashlib
import hmac
import datetime
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("minio-manager")

MINIO_URL = os.environ.get("MINIO_URL", "http://localhost:30920")
MINIO_CONSOLE_URL = os.environ.get("MINIO_CONSOLE_URL", "http://localhost:30921")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "Admin@123456789@")

# Use MinIO Admin API via mc or httpx with credentials
MINIO_ENDPOINT = MINIO_URL.replace("http://", "").replace("https://", "")


def _run_mc(args: list[str]) -> str:
    """Run mc (MinIO client) command."""
    import subprocess
    mc_path = "mc"
    cmd = [mc_path, "--json"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = result.stdout.strip()
        if result.returncode != 0:
            stderr = result.stderr.strip()
            if stderr:
                return f"ERROR: {stderr}"
        return output
    except FileNotFoundError:
        return "ERROR: 'mc' not found. Install: brew install minio-mc"
    except subprocess.TimeoutExpired:
        return "ERROR: Command timed out"


def _setup_alias() -> str:
    """Ensure myminio alias is configured."""
    return _run_mc(["alias", "set", "myminio", MINIO_URL, MINIO_ACCESS_KEY, MINIO_SECRET_KEY])


def _api_get(path: str) -> dict:
    """Call MinIO health/info endpoints."""
    try:
        r = httpx.get(f"{MINIO_URL}{path}", timeout=10)
        return r.json() if r.text else {"status": r.status_code}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def minio_health() -> str:
    """Check MinIO server health."""
    try:
        r = httpx.get(f"{MINIO_URL}/minio/health/ready", timeout=10)
        if r.status_code == 200:
            return f"MinIO Status: Healthy\nAPI: {MINIO_URL}\nConsole: {MINIO_CONSOLE_URL}\nAccess Key: {MINIO_ACCESS_KEY}"
        return f"MinIO not ready: HTTP {r.status_code}"
    except Exception as e:
        return f"MinIO unreachable at {MINIO_URL}: {e}"


@mcp.tool()
def list_buckets() -> str:
    """List all MinIO buckets."""
    _setup_alias()
    output = _run_mc(["ls", "myminio"])
    if "ERROR" in output:
        return output
    lines = []
    for line in output.strip().split("\n"):
        if line.strip():
            try:
                data = json.loads(line)
                lines.append(f"  {data.get('key', '')} — {data.get('type', '')}")
            except Exception:
                lines.append(f"  {line}")
    return "Buckets:\n" + "\n".join(lines) if lines else "No buckets found"


@mcp.tool()
def create_bucket(bucket_name: str) -> str:
    """Create a new MinIO bucket."""
    _setup_alias()
    output = _run_mc(["mb", f"myminio/{bucket_name}"])
    if "ERROR" in output:
        return output
    return f"Bucket '{bucket_name}' created successfully"


@mcp.tool()
def delete_bucket(bucket_name: str, force: bool = False) -> str:
    """Delete a MinIO bucket. Set force=True to delete non-empty bucket."""
    _setup_alias()
    cmd = ["rb", f"myminio/{bucket_name}"]
    if force:
        cmd.append("--force")
    output = _run_mc(cmd)
    if "ERROR" in output:
        return output
    return f"Bucket '{bucket_name}' deleted"


@mcp.tool()
def list_objects(bucket_name: str, prefix: str = "", recursive: bool = False) -> str:
    """List objects in a bucket."""
    _setup_alias()
    path = f"myminio/{bucket_name}"
    if prefix:
        path += f"/{prefix}"
    cmd = ["ls", path]
    if recursive:
        cmd.append("--recursive")
    output = _run_mc(cmd)
    if "ERROR" in output:
        return output
    lines = []
    for line in output.strip().split("\n"):
        if line.strip():
            try:
                data = json.loads(line)
                size = data.get("size", 0)
                size_str = f"{size // 1024}KB" if size > 1024 else f"{size}B"
                lines.append(f"  {data.get('key', '')} ({size_str}) — {data.get('lastModified', '')[:19]}")
            except Exception:
                lines.append(f"  {line}")
    return f"Objects in '{bucket_name}':\n" + "\n".join(lines) if lines else "No objects found"


@mcp.tool()
def upload_object(bucket_name: str, local_path: str, object_name: str = "") -> str:
    """Upload a local file to a MinIO bucket."""
    _setup_alias()
    dest = f"myminio/{bucket_name}/{object_name}" if object_name else f"myminio/{bucket_name}/"
    output = _run_mc(["cp", local_path, dest])
    if "ERROR" in output:
        return output
    return f"Uploaded '{local_path}' to '{bucket_name}/{object_name or local_path.split('/')[-1]}'"


@mcp.tool()
def download_object(bucket_name: str, object_name: str, local_path: str) -> str:
    """Download an object from MinIO to local filesystem."""
    _setup_alias()
    output = _run_mc(["cp", f"myminio/{bucket_name}/{object_name}", local_path])
    if "ERROR" in output:
        return output
    return f"Downloaded '{object_name}' to '{local_path}'"


@mcp.tool()
def delete_object(bucket_name: str, object_name: str) -> str:
    """Delete an object from a MinIO bucket."""
    _setup_alias()
    output = _run_mc(["rm", f"myminio/{bucket_name}/{object_name}"])
    if "ERROR" in output:
        return output
    return f"Deleted '{object_name}' from '{bucket_name}'"


@mcp.tool()
def get_bucket_policy(bucket_name: str) -> str:
    """Get the access policy for a bucket."""
    _setup_alias()
    output = _run_mc(["anonymous", "get", f"myminio/{bucket_name}"])
    return output if output else "No policy set (private)"


@mcp.tool()
def set_bucket_policy(bucket_name: str, policy: str = "none") -> str:
    """Set bucket access policy. policy: none (private), download (read-only), upload (write-only), public (read-write)."""
    _setup_alias()
    output = _run_mc(["anonymous", "set", policy, f"myminio/{bucket_name}"])
    if "ERROR" in output:
        return output
    return f"Policy '{policy}' set on bucket '{bucket_name}'"


@mcp.tool()
def get_bucket_info(bucket_name: str) -> str:
    """Get detailed info about a bucket including size and object count."""
    _setup_alias()
    output = _run_mc(["du", f"myminio/{bucket_name}"])
    return output if output else f"Could not get info for '{bucket_name}'"


@mcp.tool()
def mirror_bucket(source: str, destination_bucket: str) -> str:
    """Mirror a local directory to a MinIO bucket (sync)."""
    _setup_alias()
    output = _run_mc(["mirror", source, f"myminio/{destination_bucket}"])
    if "ERROR" in output:
        return output
    return f"Mirrored '{source}' to '{destination_bucket}'"


@mcp.tool()
def list_users() -> str:
    """List MinIO users."""
    _setup_alias()
    output = _run_mc(["admin", "user", "ls", "myminio"])
    lines = []
    for line in output.strip().split("\n"):
        if line.strip():
            try:
                data = json.loads(line)
                lines.append(f"  {data.get('accessKey', '')} — {data.get('userStatus', '')}")
            except Exception:
                lines.append(f"  {line}")
    return "MinIO Users:\n" + "\n".join(lines) if lines else "No users found"


@mcp.tool()
def create_user(access_key: str, secret_key: str) -> str:
    """Create a new MinIO user."""
    _setup_alias()
    output = _run_mc(["admin", "user", "add", "myminio", access_key, secret_key])
    if "ERROR" in output:
        return output
    return f"User '{access_key}' created"


@mcp.tool()
def minio_info() -> str:
    """Get MinIO server info and statistics."""
    _setup_alias()
    output = _run_mc(["admin", "info", "myminio"])
    return output if output else "Could not retrieve MinIO info"


if __name__ == "__main__":
    mcp.run(transport="stdio")
