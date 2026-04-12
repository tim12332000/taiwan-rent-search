"""Headless runtime smoke test for the local rental search site."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from .local_site_state import LOCAL_SITE_STATE_PATH, get_local_site_version, read_local_site_state


def create_no_window_kwargs() -> dict[str, object]:
    kwargs: dict[str, object] = {}
    if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return kwargs


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_status(base_url: str, timeout_seconds: float = 12.0) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urlopen(f"{base_url}/api/status", timeout=2) as response:
                payload = response.read().decode("utf-8")
            if '"ok": true' in payload:
                return
        except Exception as exc:  # pragma: no cover - runtime-only path
            last_error = exc
            time.sleep(0.25)
    raise RuntimeError(f"Local site did not become healthy in time: {last_error!r}")


def can_reuse_running_site() -> str | None:
    state = read_local_site_state()
    if not state:
        return None
    if state.get("version") != get_local_site_version():
        return None
    base_url = str(state.get("base_url") or "")
    if not base_url:
        return None
    try:
        wait_for_status(base_url, timeout_seconds=2)
    except Exception:
        return None
    return base_url


@contextmanager
def local_site_base_url(*, reuse_existing: bool = False) -> str:
    reusable = can_reuse_running_site() if reuse_existing else None
    if reusable:
        yield reusable
        return

    previous_state = LOCAL_SITE_STATE_PATH.read_text(encoding="utf-8") if LOCAL_SITE_STATE_PATH.exists() else None
    repo_root = Path(__file__).resolve().parent.parent
    port = get_free_port()
    process = subprocess.Popen(
        [sys.executable, "-m", "src.local_site", "--host", "127.0.0.1", "--port", str(port), "--no-browser"],
        cwd=repo_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **create_no_window_kwargs(),
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        wait_for_status(base_url)
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive
            process.kill()
        if previous_state is None:
            LOCAL_SITE_STATE_PATH.unlink(missing_ok=True)
        else:
            LOCAL_SITE_STATE_PATH.write_text(previous_state, encoding="utf-8")


def print_console_safe(text: str) -> None:
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    safe = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
    print(safe)


def default_artifact_dir() -> Path:
    return Path(".omx") / "runtime-smoke"


def prepare_artifact_dir(path: str | Path | None) -> Path:
    artifact_dir = Path(path) if path else default_artifact_dir()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    return artifact_dir


def run_runtime_smoke(
    *,
    artifact_dir: str | Path | None = None,
    reuse_existing_site: bool = False,
) -> dict[str, object]:
    artifact_root = prepare_artifact_dir(artifact_dir)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    trace_path = artifact_root / f"runtime_smoke_{timestamp}.zip"
    screenshot_path = artifact_root / f"runtime_smoke_{timestamp}.png"

    with local_site_base_url(reuse_existing=reuse_existing_site) as base_url:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1600, "height": 1400})
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = context.new_page()

            try:
                page.goto(f"{base_url}/", wait_until="networkidle")
                page.locator("h1").wait_for(state="visible", timeout=20_000)
                root_title = page.locator("h1").text_content() or ""
                destination_value = page.locator("#destination").input_value()
                toolbar = page.locator(".toolbar")
                toolbar_before = toolbar.bounding_box()

                frame = page.frame_locator("#app-frame")
                frame.locator("#q").wait_for(state="visible", timeout=20_000)
                frame.locator(".listing").first.wait_for(state="visible", timeout=20_000)

                frame.locator("#preset-review-images").click()
                frame.locator("#cooking-level").wait_for()
                assert frame.locator("#cooking-level").input_value() == "1"
                assert frame.locator("#has-images").is_checked()

                frame.locator("#preset-cooking-best").click()
                assert frame.locator("#sort-by").input_value() == "cooking-desc"
                assert frame.locator("#has-images").is_checked()
                assert frame.locator("#cooking-level").input_value() == ""

                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(500)
                toolbar_after = toolbar.bounding_box()
                if toolbar_before and toolbar_after:
                    assert toolbar_after["y"] < 0, "Toolbar should scroll away instead of staying sticky."

                visible_count = frame.locator("#count-visible").text_content() or ""
                ai_status = frame.locator("#ai-status").text_content() or ""
                first_listing_title = frame.locator(".listing .title").first.text_content() or ""
            except Exception:
                page.screenshot(path=str(screenshot_path), full_page=True)
                context.tracing.stop(path=str(trace_path))
                browser.close()
                raise

            context.tracing.stop(path=str(trace_path))
            browser.close()

    return {
        "base_url": base_url,
        "root_title": root_title,
        "destination_value": destination_value,
        "visible_count": visible_count,
        "ai_status": ai_status,
        "first_listing_title": first_listing_title,
        "toolbar_before_y": toolbar_before["y"] if toolbar_before else None,
        "toolbar_after_y": toolbar_after["y"] if toolbar_after else None,
        "trace_path": str(trace_path),
        "screenshot_path": str(screenshot_path) if screenshot_path.exists() else "",
        "runner": "playwright",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a headless runtime smoke test against the local rental search UI.")
    parser.add_argument("--json", action="store_true", help="Print the smoke result as JSON.")
    parser.add_argument("--artifact-dir", help="Directory for trace/screenshot artifacts.")
    parser.add_argument("--reuse-existing-site", action="store_true", help="Reuse a healthy running local site instead of starting a fresh one.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        result = run_runtime_smoke(
            artifact_dir=args.artifact_dir,
            reuse_existing_site=args.reuse_existing_site,
        )
    except PlaywrightTimeoutError as exc:  # pragma: no cover - runtime-only path
        raise RuntimeError(f"Runtime smoke timed out: {exc}") from exc

    if args.json:
        print_console_safe(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print_console_safe("Runtime smoke passed")
    print_console_safe(f"Runner: {result['runner']}")
    print_console_safe(f"Base URL: {result['base_url']}")
    print_console_safe(f"Root title: {result['root_title']}")
    print_console_safe(f"Visible count: {result['visible_count']}")
    print_console_safe(f"AI status: {result['ai_status']}")
    print_console_safe(f"First listing: {result['first_listing_title']}")
    print_console_safe(f"Trace: {result['trace_path']}")
    if result["screenshot_path"]:
        print_console_safe(f"Screenshot: {result['screenshot_path']}")


if __name__ == "__main__":
    main()
