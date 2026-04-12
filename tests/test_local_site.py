from src.local_site import (
    build_ai_review_job_payload,
    build_app_url,
    build_index_html,
    build_job_payload,
    build_json_response,
    create_ai_review_job,
    create_refresh_job,
    ensure_default_search_app,
    export_shortlist_payload,
    resolve_destination_payload,
    start_listing_review_payload,
    update_ai_review_job,
    update_refresh_job,
)
from src.local_site_state import (
    LOCAL_SITE_STATE_PATH,
    clear_local_site_state,
    get_local_site_version,
    read_local_site_state,
    write_local_site_state,
)


def test_build_app_url_includes_destination_query():
    url = build_app_url("台北市信義區松仁路100號")

    assert url.startswith("/app?")
    assert "destination=" in url


def test_build_app_url_includes_coordinates_when_available():
    url = build_app_url("台北市松仁路100號", lat=25.0332, lon=121.5660)

    assert "destination_lat=25.0332" in url
    assert "destination_lon=121.566" in url


def test_build_app_url_includes_revision_when_available():
    url = build_app_url("台北市信義區松仁路100號", rev="12345")

    assert "rev=12345" in url


def test_build_index_html_contains_controls_and_iframe():
    html = build_index_html("台北市信義區松仁路100號", app_revision="12345")

    assert "租屋搜尋控制台" in html
    assert "更新資料" in html
    assert "iframe" in html
    assert "/api/refresh" in html
    assert "/api/jobs/" in html
    assert "progress-bar" in html
    assert "目前累積" in html
    assert "syncDestinationToFrame" in html
    assert "withCacheBuster" in html
    assert "position: sticky" not in html
    assert "Console · 細節" in html
    assert "updateDebugConsole" in html
    assert "rent-search-debug" in html
    assert "appRevision" in html
    assert "rev=12345" in html
    assert "台北市信義區松仁路100號" in html


def test_build_ai_review_job_payload_contains_review_fields():
    job = create_ai_review_job("data/current_dataset.csv", "591-1")
    update_ai_review_job(job.id, status="completed", message="done", review={"label": "適合煮飯"}, cached=True)
    payload = build_ai_review_job_payload(job)

    assert payload["listing_id"] == "591-1"
    assert payload["status"] == "completed"
    assert payload["review"] == {"label": "適合煮飯"}
    assert payload["cached"] is True


def test_export_shortlist_payload_writes_markdown(monkeypatch, tmp_path):
    dataset_path = tmp_path / "current_dataset.csv"
    dataset_path.write_text("id\n1\n", encoding="utf-8")
    output_path = tmp_path / "current_dataset_shortlist.md"

    monkeypatch.setattr("src.local_site.export_review_shortlist", lambda input_path, items, destination="": output_path)

    payload = export_shortlist_payload(
        {
            "input_path": str(dataset_path),
            "destination": "台北市信義區松仁路100號",
            "items": [{"id": "591-1", "title": "可開伙套房"}],
        }
    )

    assert payload["ok"] is True
    assert payload["count"] == 1
    assert payload["path"] == str(output_path)


def test_start_listing_review_payload_creates_job(monkeypatch):
    calls = []
    monkeypatch.setattr("src.local_site.threading.Thread", lambda target, args, daemon: type("T", (), {"start": lambda self: calls.append((target, args, daemon))})())

    payload = start_listing_review_payload({"input_path": "data/current_dataset.csv", "listing_id": "591-1"})

    assert payload["ok"] is True
    assert payload["listing_id"] == "591-1"
    assert payload["status"] == "queued"
    assert calls


def test_build_index_html_shows_missing_data_hint():
    html = build_index_html(app_ready=False)

    assert "還沒有可用的資料頁" in html


def test_build_json_response_emits_utf8_json_bytes():
    payload = build_json_response({"ok": True, "message": "完成"})

    assert b'"ok": true' in payload
    assert "完成".encode("utf-8") in payload


def test_export_shortlist_payload_rejects_missing_items():
    try:
        export_shortlist_payload({"input_path": "data/current_dataset.csv", "items": []})
    except ValueError as exc:
        assert str(exc) == "沒有可匯出的 shortlist。"
    else:  # pragma: no cover - safety assertion
        raise AssertionError("Expected ValueError for empty shortlist")


def test_resolve_destination_payload_returns_coordinates(monkeypatch):
    class DummyCoords:
        lat = 25.0332
        lon = 121.5660

    monkeypatch.setattr("src.local_site._GEOCODER.geocode", lambda query: DummyCoords())

    payload = resolve_destination_payload("台北市信義區松仁路100號")

    assert payload["destination"] == "台北市信義區松仁路100號"
    assert payload["lat"] == 25.0332
    assert payload["lon"] == 121.566


def test_resolve_destination_payload_skips_geocode_without_district(monkeypatch):
    monkeypatch.setattr("src.local_site._GEOCODER.geocode", lambda query: (_ for _ in ()).throw(RuntimeError("should not geocode")))

    payload = resolve_destination_payload("台北市松仁路100號")

    assert payload["destination"] == "台北市松仁路100號"
    assert payload["lat"] is None
    assert payload["lon"] is None


def test_build_job_payload_contains_progress_fields():
    job = create_refresh_job("台北市信義區松仁路100號")
    update_refresh_job(job.id, status="running", message="抓取中", current=2, total=5, records_processed=12)
    payload = build_job_payload(job)

    assert payload["job_id"] == job.id
    assert payload["status"] == "running"
    assert payload["message"] == "抓取中"
    assert payload["current"] == 2
    assert payload["total"] == 5
    assert payload["records_processed"] == 12


def test_local_site_state_round_trip(monkeypatch, tmp_path):
    state_path = tmp_path / "local_site.json"
    monkeypatch.setattr("src.local_site_state.LOCAL_SITE_STATE_PATH", state_path)

    monkeypatch.setattr("src.local_site_state.get_local_site_version", lambda: "abc123")
    write_local_site_state("127.0.0.1", 9876, pid=4321)

    payload = read_local_site_state()
    assert payload == {
        "host": "127.0.0.1",
        "port": 9876,
        "base_url": "http://127.0.0.1:9876",
        "pid": 4321,
        "version": "abc123",
    }

    clear_local_site_state("127.0.0.1", 9876)
    assert not state_path.exists()


def test_ensure_default_search_app_uses_latest_dataset(monkeypatch, tmp_path):
    stable = tmp_path / "search_app.html"
    dataset = tmp_path / "latest.csv"
    dataset.write_text("id\n1\n", encoding="utf-8")
    calls = []

    monkeypatch.setattr("src.local_site.build_default_search_app_path", lambda: stable)
    monkeypatch.setattr("src.local_site.latest_dataset_path", lambda: dataset)
    monkeypatch.setattr("src.local_site.export_search_app", lambda input_path, output_path=None: calls.append((input_path, output_path)) or stable)

    app_path, source_name, generated = ensure_default_search_app()

    assert app_path == str(stable)
    assert source_name == "latest.csv"
    assert generated is True
    assert calls == [(dataset, stable)]


def test_ensure_default_search_app_returns_existing_stable_when_no_dataset(monkeypatch, tmp_path):
    stable = tmp_path / "search_app.html"
    stable.write_text("ok", encoding="utf-8")

    monkeypatch.setattr("src.local_site.build_default_search_app_path", lambda: stable)
    monkeypatch.setattr("src.local_site.latest_dataset_path", lambda: (_ for _ in ()).throw(FileNotFoundError("missing")))

    app_path, source_name, generated = ensure_default_search_app()

    assert app_path == str(stable)
    assert source_name == ""
    assert generated is False


def test_get_local_site_version_is_stable_shape():
    version = get_local_site_version()

    assert isinstance(version, str)
    assert len(version) == 12
