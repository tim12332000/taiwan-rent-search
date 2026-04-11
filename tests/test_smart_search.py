from pathlib import Path

from src.smart_search import build_open_url, refresh_search_for_destination


def test_build_open_url_includes_destination_query(monkeypatch):
    monkeypatch.setattr("src.smart_search.resolve_running_local_site_base_url", lambda: None)
    url = build_open_url("台北市信義區松仁路100號")

    assert "search_app.html" in url
    assert "destination=" in url


def test_build_open_url_prefers_running_local_site(monkeypatch):
    monkeypatch.setattr("src.smart_search.resolve_running_local_site_base_url", lambda: "http://127.0.0.1:9876")

    url = build_open_url("台北市信義區松仁路100號")

    assert url == "http://127.0.0.1:9876/app?destination=%E5%8F%B0%E5%8C%97%E5%B8%82%E4%BF%A1%E7%BE%A9%E5%8D%80%E6%9D%BE%E4%BB%81%E8%B7%AF100%E8%99%9F"


def test_refresh_search_for_destination_runs_focus_pipeline(monkeypatch, tmp_path):
    dataset = tmp_path / "focused.csv"
    stable = tmp_path / "search_app.html"
    calls = {}

    def fake_scrape_sources_with_focus(**kwargs):
        calls["scrape"] = kwargs
        return dataset, [object(), object()]

    def fake_export_search_app(input_path, output_path=None):
        calls["webapp"] = (input_path, output_path)
        return stable

    monkeypatch.setattr("src.smart_search.scrape_sources_with_focus", fake_scrape_sources_with_focus)
    monkeypatch.setattr("src.smart_search.export_search_app", fake_export_search_app)
    monkeypatch.setattr("src.smart_search.build_default_search_app_path", lambda: stable)

    dataset_path, search_path, record_count, county, district = refresh_search_for_destination(
        destination_address="台北市信義區松仁路100號",
        base_max_pages=2,
        focus_max_pages=4,
        search_output_path=stable,
    )

    assert dataset_path == dataset
    assert search_path == stable
    assert record_count == 2
    assert county == "台北市"
    assert district == "信義區"
    assert calls["scrape"]["county"] == "台北市"
    assert calls["scrape"]["destination_address"] == "台北市信義區松仁路100號"
    assert calls["scrape"]["base_max_pages"] == 2
    assert calls["scrape"]["focus_max_pages"] == 4
    assert calls["webapp"] == (dataset, stable)


def test_refresh_search_for_destination_forwards_progress_callback(monkeypatch, tmp_path):
    dataset = tmp_path / "focused.csv"
    stable = tmp_path / "search_app.html"
    messages = []

    def fake_scrape_sources_with_focus(**kwargs):
        kwargs["progress_callback"]("抓取中", 1, 4, 12)
        return dataset, [object()]

    monkeypatch.setattr("src.smart_search.scrape_sources_with_focus", fake_scrape_sources_with_focus)
    monkeypatch.setattr("src.smart_search.export_search_app", lambda input_path, output_path=None: stable)
    monkeypatch.setattr("src.smart_search.build_default_search_app_path", lambda: stable)

    refresh_search_for_destination(
        destination_address="台北市信義區松仁路100號",
        progress_callback=lambda message, current, total, records: messages.append((message, current, total, records)),
    )

    assert messages[0] == ("抓取中", 1, 4, 12)
    assert messages[-1] == ("搜尋頁已更新", None, None, 1)
