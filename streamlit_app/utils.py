"""
Shared helpers for Streamlit MCP Dashboard.
All underlying calls mirror what the MCP servers do.
"""

import subprocess
import json
import os
import shlex
import httpx
from pathlib import Path

# ── Service config ─────────────────────────────────────────────────────────────
JENKINS_URL  = os.environ.get("JENKINS_URL",  "http://localhost:30080")
SONAR_URL    = os.environ.get("SONAR_URL",    "http://localhost:30900")
JENKINS_AUTH = (os.environ.get("JENKINS_USER", "admin"), os.environ.get("JENKINS_PASS", "admin@123456789@"))
SONAR_AUTH   = (os.environ.get("SONAR_USER",  "admin"), os.environ.get("SONAR_PASS",   "Aa75696462461@"))
TF_WORKDIR   = str(Path(__file__).parent.parent / "terraform" / "local")


# ── Shell helpers ──────────────────────────────────────────────────────────────
def shell(cmd: str, cwd: str = None, extra_env: dict = None) -> dict:
    env = {**os.environ, **(extra_env or {})}
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd, env=env)
    return {"out": result.stdout.strip(), "err": result.stderr.strip(), "ok": result.returncode == 0}


def docker(args: str) -> dict:
    return shell(f"docker {args}")


def kube(args: str, ns: str = "devops") -> dict:
    ns_flag = f"-n {ns}" if ns else ""
    return shell(f"kubectl {ns_flag} {args}")


def tf(cmd: str) -> dict:
    return shell(cmd, cwd=TF_WORKDIR, extra_env={"TF_IN_AUTOMATION": "1"})


# ── HTTP helpers ───────────────────────────────────────────────────────────────
def http_get(url: str, auth: tuple = None, timeout: int = 8, params: dict = None) -> dict | None:
    try:
        kwargs = {"params": params or {}, "timeout": timeout, "follow_redirects": True}
        if auth:
            kwargs["auth"] = auth
        r = httpx.get(url, **kwargs)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def http_post(url: str, auth: tuple = None, data: dict = None, content: bytes = None,
              headers: dict = None, json_data: dict = None) -> tuple[int, any]:
    try:
        kwargs = {"auth": auth, "headers": headers or {}, "timeout": 20, "follow_redirects": True}
        if json_data is not None:
            kwargs["json"] = json_data
        elif content is not None:
            kwargs["content"] = content
        else:
            kwargs["data"] = data
        r = httpx.post(url, **kwargs)
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, r.text
    except Exception as e:
        return 0, str(e)


def jenkins_crumb() -> dict:
    try:
        r = httpx.get(f"{JENKINS_URL}/crumbIssuer/api/json", auth=JENKINS_AUTH, timeout=8)
        if r.status_code == 200:
            cd = r.json()
            return {cd["crumbRequestField"]: cd["crumb"]}
    except Exception:
        pass
    return {}


# ── Service health ─────────────────────────────────────────────────────────────
def service_health() -> dict:
    import socket, shutil

    def port_open(port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        r = s.connect_ex(("localhost", port))
        s.close()
        return r == 0

    docker_ver = docker("info --format '{{.ServerVersion}}'")
    jenkins_data = http_get(f"{JENKINS_URL}/api/json", JENKINS_AUTH, timeout=5)
    sonar_data   = http_get(f"{SONAR_URL}/api/system/health", SONAR_AUTH, timeout=5)
    kube_nodes   = kube("get nodes --no-headers", ns="")
    tf_ver       = tf("terraform version -json")

    try:
        tf_version = json.loads(tf_ver["out"]).get("terraform_version", "?") if tf_ver["ok"] else "not installed"
    except Exception:
        tf_version = "not installed"

    return {
        "docker":     {"up": docker_ver["ok"], "version": docker_ver["out"] or "unavailable"},
        "jenkins":    {"up": jenkins_data is not None, "jobs": len(jenkins_data.get("jobs", [])) if jenkins_data else 0},
        "sonarqube":  {"up": sonar_data is not None, "health": sonar_data.get("health", "?") if sonar_data else "down"},
        "kubernetes": {"up": kube_nodes["ok"], "node": "docker-desktop" if kube_nodes["ok"] else "unavailable"},
        "terraform":  {"up": shutil.which("terraform") is not None, "version": tf_version},
        "ports": {
            "Jenkins:30080":   port_open(30080),
            "SonarQube:30900": port_open(30900),
            "Agent:30500":     port_open(30500),
        },
    }
