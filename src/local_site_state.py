"""Runtime state helpers for the local rental search site."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


LOCAL_SITE_STATE_PATH = Path(".omx") / "state" / "local_site.json"
VERSION_PATHS = (
    Path(__file__).with_name("local_site.py"),
    Path(__file__).with_name("webapp.py"),
    Path(__file__).with_name("analysis.py"),
)


def build_local_site_url(host: str, port: int, path: str = "") -> str:
    if not path:
        return f"http://{host}:{port}"
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"http://{host}:{port}{normalized_path}"


def get_local_site_version() -> str:
    digest = hashlib.sha1()
    for path in VERSION_PATHS:
        stat = path.stat()
        digest.update(str(path.name).encode("utf-8"))
        digest.update(str(stat.st_mtime_ns).encode("utf-8"))
        digest.update(str(stat.st_size).encode("utf-8"))
    return digest.hexdigest()[:12]


def write_local_site_state(host: str, port: int, pid: int | None = None) -> Path:
    LOCAL_SITE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "host": host,
        "port": port,
        "base_url": build_local_site_url(host, port),
        "pid": pid if pid is not None else os.getpid(),
        "version": get_local_site_version(),
    }
    LOCAL_SITE_STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return LOCAL_SITE_STATE_PATH


def read_local_site_state() -> dict[str, object] | None:
    if not LOCAL_SITE_STATE_PATH.exists():
        return None

    try:
        payload = json.loads(LOCAL_SITE_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None

    host = payload.get("host")
    port = payload.get("port")
    if not isinstance(host, str) or not isinstance(port, int):
        return None

    return payload


def clear_local_site_state(host: str, port: int) -> None:
    payload = read_local_site_state()
    if not payload:
        return
    if payload.get("host") != host or payload.get("port") != port:
        return
    LOCAL_SITE_STATE_PATH.unlink(missing_ok=True)


def resolve_running_local_site_base_url() -> str | None:
    payload = read_local_site_state()
    if not payload:
        return None

    host = payload["host"]
    port = payload["port"]
    status_url = build_local_site_url(host, port, "/api/status")
    try:
        with urlopen(status_url, timeout=1.5) as response:
            status_payload = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, HTTPError, URLError):
        LOCAL_SITE_STATE_PATH.unlink(missing_ok=True)
        return None

    if not isinstance(status_payload, dict) or status_payload.get("ok") is not True:
        return None

    return str(payload.get("base_url") or build_local_site_url(host, port))
