"""Local web UI for destination-first rental search."""

from __future__ import annotations

import argparse
import json
import threading
import uuid
import webbrowser
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

from .analysis import NominatimGeocoder, extract_district_from_text
from .local_site_state import clear_local_site_state, write_local_site_state
from .smart_search import refresh_search_for_destination
from .webapp import build_default_search_app_path


@dataclass
class RefreshJob:
    id: str
    destination: str
    status: str = "queued"
    message: str = "等待開始..."
    current: int | None = None
    total: int | None = None
    records_processed: int = 0
    dataset: str = ""
    search_app: str = ""
    records: int = 0
    county: str = ""
    district: str = ""
    error: str = ""


_JOBS: dict[str, RefreshJob] = {}
_JOBS_LOCK = threading.Lock()
_GEOCODER = NominatimGeocoder()


def build_app_url(destination: str = "", lat: float | None = None, lon: float | None = None) -> str:
    params: dict[str, str | float] = {}
    if destination:
        params["destination"] = destination
    if lat is not None and lon is not None:
        params["destination_lat"] = lat
        params["destination_lon"] = lon
    query = urlencode(params) if params else ""
    return f"/app{f'?{query}' if query else ''}"


def resolve_destination_payload(destination: str) -> dict[str, object]:
    destination = destination.strip()
    if not destination:
        return {"destination": "", "lat": None, "lon": None}

    # If the user did not provide a district, geocoding often snaps to the wrong
    # part of Taipei. Let the in-page listing matcher infer the district instead.
    if not extract_district_from_text(destination):
        return {"destination": destination, "lat": None, "lon": None}

    coords = _GEOCODER.geocode(destination)
    if not coords:
        return {"destination": destination, "lat": None, "lon": None}

    return {
        "destination": destination,
        "lat": coords.lat,
        "lon": coords.lon,
    }


def build_job_payload(job: RefreshJob) -> dict[str, object]:
    return {
        "job_id": job.id,
        "status": job.status,
        "message": job.message,
        "current": job.current,
        "total": job.total,
        "records_processed": job.records_processed,
        "dataset": job.dataset,
        "search_app": job.search_app,
        "records": job.records,
        "county": job.county,
        "district": job.district,
        "destination": job.destination,
        "error": job.error,
    }


def create_refresh_job(destination: str) -> RefreshJob:
    job = RefreshJob(id=uuid.uuid4().hex, destination=destination)
    with _JOBS_LOCK:
        _JOBS[job.id] = job
    return job


def get_refresh_job(job_id: str) -> RefreshJob | None:
    with _JOBS_LOCK:
        return _JOBS.get(job_id)


def update_refresh_job(
    job_id: str,
    *,
    status: str | None = None,
    message: str | None = None,
    current: int | None = None,
    total: int | None = None,
    records_processed: int | None = None,
    dataset: str | None = None,
    search_app: str | None = None,
    records: int | None = None,
    county: str | None = None,
    district: str | None = None,
    error: str | None = None,
) -> RefreshJob | None:
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if not job:
            return None
        if status is not None:
            job.status = status
        if message is not None:
            job.message = message
        if current is not None:
            job.current = current
        if total is not None:
            job.total = total
        if records_processed is not None:
            job.records_processed = records_processed
        if dataset is not None:
            job.dataset = dataset
        if search_app is not None:
            job.search_app = search_app
        if records is not None:
            job.records = records
        if county is not None:
            job.county = county
        if district is not None:
            job.district = district
        if error is not None:
            job.error = error
        return job


def run_refresh_job(job_id: str) -> None:
    job = get_refresh_job(job_id)
    if not job:
        return

    def progress_callback(message: str, current: int | None, total: int | None, records: int | None) -> None:
        update_refresh_job(
            job_id,
            status="running",
            message=message,
            current=current,
            total=total,
            records_processed=records,
        )

    try:
        update_refresh_job(job_id, status="running", message="準備更新資料池...")
        dataset_path, search_path, record_count, county, district = refresh_search_for_destination(
            destination_address=job.destination,
            progress_callback=progress_callback,
        )
        update_refresh_job(
            job_id,
            status="completed",
            message=f"已更新 {record_count} 筆資料",
            current=get_refresh_job(job_id).total if get_refresh_job(job_id) else None,
            records_processed=record_count,
            dataset=str(dataset_path),
            search_app=str(search_path),
            records=record_count,
            county=county,
            district=district,
        )
    except Exception as exc:  # pragma: no cover - defensive; UI gets surfaced errors.
        update_refresh_job(
            job_id,
            status="failed",
            message="更新失敗",
            error=str(exc),
        )


def build_index_html(destination: str = "") -> str:
    escaped_destination = json.dumps(destination, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>租屋搜尋控制台</title>
  <style>
    :root {{
      --bg: #f3efe7;
      --panel: rgba(255, 250, 242, 0.95);
      --ink: #1f2937;
      --muted: #5b6470;
      --line: #d7c7af;
      --accent: #0f766e;
      --accent-2: #b45309;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Noto Sans TC", "Microsoft JhengHei", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(15,118,110,.08), transparent 28%),
        radial-gradient(circle at bottom right, rgba(180,83,9,.10), transparent 30%),
        var(--bg);
    }}
    .page {{
      display: grid;
      grid-template-rows: auto 1fr;
      min-height: 100vh;
    }}
    .toolbar {{
      position: sticky;
      top: 0;
      z-index: 2;
      padding: 18px;
      border-bottom: 1px solid var(--line);
      background: rgba(243,239,231,.94);
      backdrop-filter: blur(10px);
    }}
    .panel {{
      max-width: 1200px;
      margin: 0 auto;
      display: grid;
      gap: 12px;
      padding: 18px;
      border-radius: 22px;
      border: 1px solid var(--line);
      background: var(--panel);
      box-shadow: 0 16px 36px rgba(31,41,55,.08);
    }}
    .panel h1 {{
      margin: 0;
      font-size: clamp(24px, 4vw, 36px);
    }}
    .panel p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.7;
    }}
    .controls {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto auto;
      gap: 10px;
      align-items: center;
    }}
    input, button {{
      border-radius: 14px;
      border: 1px solid var(--line);
      padding: 12px 14px;
      font: inherit;
    }}
    input {{
      width: 100%;
      background: #fffdf9;
      color: var(--ink);
    }}
    button {{
      cursor: pointer;
      font-weight: 700;
      background: white;
    }}
    button.primary {{
      color: white;
      border-color: var(--accent);
      background: linear-gradient(135deg, var(--accent), #115e59);
    }}
    button.secondary {{
      color: var(--accent-2);
      border-color: rgba(180,83,9,.35);
      background: #fff7ed;
    }}
    .status {{
      min-height: 24px;
      color: var(--muted);
      font-size: 14px;
    }}
    .progress {{
      height: 10px;
      overflow: hidden;
      border-radius: 999px;
      background: rgba(215,199,175,.55);
    }}
    .progress-bar {{
      width: 0%;
      height: 100%;
      background: linear-gradient(90deg, var(--accent), #14b8a6);
      transition: width .25s ease;
    }}
    .progress-meta {{
      min-height: 20px;
      color: var(--muted);
      font-size: 13px;
    }}
    .frame-wrap {{
      padding: 18px;
      height: 100%;
    }}
    iframe {{
      width: 100%;
      height: calc(100vh - 220px);
      border: 0;
      border-radius: 18px;
      background: white;
      box-shadow: 0 14px 34px rgba(31,41,55,.08);
    }}
    @media (max-width: 900px) {{
      .controls {{
        grid-template-columns: 1fr;
      }}
      iframe {{
        height: calc(100vh - 320px);
      }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <div class="toolbar">
      <section class="panel">
        <h1>租屋搜尋控制台</h1>
        <p>在這裡輸入目的地，按一次就會更新較相關的資料池，然後直接刷新下面的搜尋頁。</p>
        <div class="controls">
          <input id="destination" type="search" placeholder="例如：台北市信義區松仁路100號" />
          <button id="refresh" class="primary" type="button">更新資料</button>
          <button id="open-app" class="secondary" type="button">另開搜尋頁</button>
        </div>
        <div id="status" class="status"></div>
        <div class="progress"><div id="progress-bar" class="progress-bar"></div></div>
        <div id="progress-meta" class="progress-meta"></div>
      </section>
    </div>
    <div class="frame-wrap">
      <iframe id="app-frame" title="租屋搜尋頁" src="{build_app_url(destination)}"></iframe>
    </div>
  </main>
  <script>
    const destinationInput = document.getElementById('destination');
    const refreshButton = document.getElementById('refresh');
    const openButton = document.getElementById('open-app');
    const status = document.getElementById('status');
    const progressBar = document.getElementById('progress-bar');
    const progressMeta = document.getElementById('progress-meta');
    const frame = document.getElementById('app-frame');
    const initialDestination = {escaped_destination};
    if (initialDestination) {{
      destinationInput.value = initialDestination;
    }}
    let syncTimer = null;

    let resolvedDestination = null;

    function appUrl(destination, resolved = null) {{
      const params = new URLSearchParams();
      if (destination) params.set('destination', destination);
      if (resolved && resolved.lat !== null && resolved.lat !== undefined && resolved.lon !== null && resolved.lon !== undefined) {{
        params.set('destination_lat', resolved.lat);
        params.set('destination_lon', resolved.lon);
      }}
      const query = params.toString();
      return `/app${{query ? `?${{query}}` : ''}}`;
    }}

    function withCacheBuster(url) {{
      const separator = url.includes('?') ? '&' : '?';
      return `${{url}}${{separator}}t=${{Date.now()}}`;
    }}

    async function resolveDestination(destination) {{
      if (!destination) return null;
      try {{
        const response = await fetch(`/api/resolve-destination?${{new URLSearchParams({{ destination }}).toString()}}`);
        const payload = await response.json();
        if (!response.ok) return null;
        return payload;
      }} catch (_error) {{
        return null;
      }}
    }}

    async function syncDestinationToFrame() {{
      const destination = destinationInput.value.trim();
      resolvedDestination = await resolveDestination(destination);
      frame.src = appUrl(destination, resolvedDestination);
    }}

    function formatProgress(payload) {{
      if (!payload) return '';
      if (payload.current === null || payload.current === undefined || !payload.total) return payload.message || '';
      const percent = Math.max(0, Math.min(100, Math.round((payload.current / payload.total) * 100)));
      return `${{payload.message || ''}} (${{percent}}% · ${{payload.current}}/${{payload.total}})`;
    }}

    function updateProgressUi(payload) {{
      if (!payload) return;
      const percent = payload.current === null || payload.current === undefined || !payload.total
        ? 0
        : Math.max(0, Math.min(100, Math.round((payload.current / payload.total) * 100)));
      progressBar.style.width = `${{percent}}%`;
      const recordsText = payload.records_processed ? ` · 目前累積 ${{payload.records_processed}} 筆` : '';
      progressMeta.textContent = payload.status === 'completed'
        ? `完成 · 共 ${{payload.records}} 筆`
        : payload.status === 'failed'
          ? '更新失敗'
          : `進度 ${{percent}}%${{recordsText}}`;
    }}

    async function waitForJob(jobId, destination) {{
      while (true) {{
        const response = await fetch(`/api/jobs/${{jobId}}`);
        const payload = await response.json();
        if (!response.ok) {{
          throw new Error(payload.error || '查詢進度失敗');
        }}

        status.textContent = formatProgress(payload);
        updateProgressUi(payload);

        if (payload.status === 'completed') {{
          status.textContent = `已更新 ${{payload.records}} 筆資料，現在顯示 ${{payload.county}}${{payload.district ? ' / ' + payload.district : ''}}。`;
          progressBar.style.width = '100%';
          progressMeta.textContent = `完成 · 共 ${{payload.records}} 筆`;
          frame.src = withCacheBuster(appUrl(destination, resolvedDestination));
          return;
        }}
        if (payload.status === 'failed') {{
          throw new Error(payload.error || payload.message || '更新失敗');
        }}

        await new Promise(resolve => window.setTimeout(resolve, 1000));
      }}
    }}

    async function refreshData() {{
      const destination = destinationInput.value.trim();
      if (!destination) {{
        status.textContent = '請先輸入目的地地址。';
        destinationInput.focus();
        return;
      }}

      refreshButton.disabled = true;
      status.textContent = '更新資料池中，正在建立工作...';
      progressBar.style.width = '0%';
      progressMeta.textContent = '準備開始...';

      try {{
        const response = await fetch('/api/refresh', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ destination }}),
        }});
        const payload = await response.json();
        if (!response.ok) {{
          throw new Error(payload.error || '更新失敗');
        }}
        await waitForJob(payload.job_id, destination);
      }} catch (error) {{
        status.textContent = `更新失敗：${{error.message}}`;
        progressMeta.textContent = '請稍後再試';
      }} finally {{
        refreshButton.disabled = false;
      }}
    }}

    if (initialDestination) {{
      syncDestinationToFrame();
    }}

    refreshButton.addEventListener('click', refreshData);
    destinationInput.addEventListener('input', () => {{
      window.clearTimeout(syncTimer);
      syncTimer = window.setTimeout(syncDestinationToFrame, 250);
    }});
    destinationInput.addEventListener('keydown', (event) => {{
      if (event.key === 'Enter') {{
        event.preventDefault();
        window.clearTimeout(syncTimer);
        syncDestinationToFrame();
        refreshData();
      }}
    }});
    openButton.addEventListener('click', () => {{
      window.open(appUrl(destinationInput.value.trim(), resolvedDestination), '_blank', 'noopener');
    }});
  </script>
</body>
</html>
"""


def build_json_response(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


class LocalSiteHandler(BaseHTTPRequestHandler):
    server_version = "TaiwanRentLocalSite/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        destination = params.get("destination", [""])[0]

        if parsed.path == "/":
            self._send_html(build_index_html(destination))
            return

        if parsed.path == "/app":
            app_path = build_default_search_app_path()
            if not app_path.exists():
                self._send_html("<h1>尚未產生搜尋頁</h1><p>請先按上方的更新資料。</p>", status=HTTPStatus.NOT_FOUND)
                return
            self._send_file(app_path)
            return

        if parsed.path == "/api/status":
            self._send_json({"ok": True})
            return

        if parsed.path == "/api/resolve-destination":
            destination_query = params.get("destination", [""])[0]
            self._send_json(resolve_destination_payload(destination_query))
            return

        if parsed.path.startswith("/api/jobs/"):
            job_id = parsed.path.rsplit("/", 1)[-1]
            job = get_refresh_job(job_id)
            if not job:
                self._send_json({"error": "找不到工作"}, status=HTTPStatus.NOT_FOUND)
                return
            self._send_json(build_job_payload(job))
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/refresh":
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            destination = str(payload.get("destination", "")).strip()
            if not destination:
                self._send_json({"error": "請輸入目的地地址。"}, status=HTTPStatus.BAD_REQUEST)
                return

            job = create_refresh_job(destination)
            threading.Thread(target=run_refresh_job, args=(job.id,), daemon=True).start()
            self._send_json(
                {
                    "ok": True,
                    "job_id": job.id,
                    "destination": destination,
                },
                status=HTTPStatus.ACCEPTED,
            )
        except Exception as exc:  # pragma: no cover - exercised via tests on helper seams
            self._send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _send_html(self, html_text: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = html_text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = build_json_response(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_file(self, path: Path) -> None:
        encoded = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def run_local_site(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    server = ThreadingHTTPServer((host, port), LocalSiteHandler)
    url = f"http://{host}:{port}/"
    write_local_site_state(host, port)
    if open_browser:
        threading.Timer(0.3, lambda: webbrowser.open(url)).start()

    print(f"Local site: {url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        clear_local_site_state(host, port)
        server.server_close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="啟動本機租屋搜尋網站")
    parser.add_argument("--host", default="127.0.0.1", help="綁定主機")
    parser.add_argument("--port", type=int, default=8765, help="綁定埠號")
    parser.add_argument("--no-browser", action="store_true", help="不要自動打開瀏覽器")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_local_site(host=args.host, port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
