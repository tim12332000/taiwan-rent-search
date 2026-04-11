"""本地搜尋頁產生測試。"""

from __future__ import annotations

import csv
from pathlib import Path

from src.webapp import (
    build_default_search_app_path,
    build_search_app_output_path,
    export_search_app,
    listing_to_view_model,
    prepare_listing_view_models,
    render_search_app_html,
)


def write_sample_csv(path: Path):
    rows = [
        {
            "id": "591-1",
            "platform": "591",
            "title": "可開伙套房",
            "price": "18000",
            "room_type": "套房",
            "bedrooms": "1",
            "bathrooms": "1",
            "floor_area": "12",
            "floor": "",
            "description": "近捷運 可開伙 有流理台",
            "url": "https://rent.591.com.tw/1",
            "scraped_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
            "location_county": "台北市",
            "location_district": "信義區",
            "location_area": "松仁路",
            "contact_name": "未公開",
            "contact_phone": "",
            "contact_email": "",
            "images": "https://img/1.jpg,https://img/2.jpg",
        },
        {
            "id": "mixrent-1",
            "platform": "mixrent",
            "title": "一般雅房",
            "price": "12000",
            "room_type": "",
            "bedrooms": "1",
            "bathrooms": "1",
            "floor_area": "8",
            "floor": "",
            "description": "離捷運稍遠",
            "url": "https://rent.591.com.tw/2",
            "scraped_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
            "location_county": "台北市",
            "location_district": "北投區",
            "location_area": "石牌路",
            "contact_name": "未公開",
            "contact_phone": "",
            "contact_email": "",
            "images": "",
        },
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def test_listing_to_view_model_extracts_cover_and_search_text():
    row = {
        "id": "591-1",
        "platform": "591",
        "title": "可開伙套房",
        "price": "18000",
        "location_county": "台北市",
        "location_district": "信義區",
        "location_area": "松仁路",
        "floor_area": "12",
        "room_type": "套房",
        "description": "近捷運 可開伙 有流理台",
        "url": "https://rent.591.com.tw/1",
        "images": "https://img/1.jpg,https://img/2.jpg",
        "updated_at": "2026-01-01T00:00:00",
        "detail_shortest_lease": "最短租期一年",
        "detail_rules": "不可養寵物",
        "detail_deposit": "二個月",
        "detail_management_fee": "2400元/月",
        "detail_facilities": "冰箱,天然瓦斯",
    }

    model = listing_to_view_model(row)

    assert model["cover"] == "https://img/1.jpg"
    assert model["address"] == "台北市信義區松仁路"
    assert model["district_center_lat"] == 25.0332
    assert model["district_center_lon"] == 121.566
    assert model["nearest_metro_station"] == "台北101/世貿"
    assert model["nearest_metro_walk_minutes"] == 5
    assert model["kitchen_sink_signal"] is True
    assert "台北市" in model["search_text"]
    assert "信義區" in model["search_text"]
    assert "最短租期一年" in model["search_text"]
    assert "台北市信義區松仁路" in model["search_text_compact"]


def test_prepare_listing_view_models_reads_csv(tmp_path):
    csv_path = tmp_path / "sample.csv"
    write_sample_csv(csv_path)

    models = prepare_listing_view_models(csv_path)

    assert len(models) == 2
    assert models[0]["platform"] == "591"
    assert models[1]["platform"] == "mixrent"


def test_render_search_app_html_contains_filters_and_data(tmp_path):
    csv_path = tmp_path / "sample.csv"
    write_sample_csv(csv_path)
    models = prepare_listing_view_models(csv_path)

    html_text = render_search_app_html(csv_path, models)

    assert "租屋即時搜尋" in html_text
    assert 'id="q"' in html_text
    assert "const listings =" in html_text
    assert "可開伙套房" in html_text
    assert "最短租期" in html_text
    assert "完整地址" in html_text
    assert "通勤目的地" in html_text
    assert "normalizeSearchText" in html_text
    assert "buildAddressNeedles" in html_text
    assert "search_text_compact" in html_text
    assert "getCommuteEstimate" in html_text
    assert "估通勤" in html_text
    assert "最近捷運" in html_text
    assert "URLSearchParams" in html_text
    assert "destination_lat" in html_text
    assert "inferDistrictFromListings" in html_text
    assert "latParam === null ? NaN : Number(latParam)" in html_text
    assert "const [districtLat, districtLon] = districtCenters[district]" in html_text


def test_build_search_app_output_path_uses_input_stem():
    path = build_search_app_output_path("data/sample.csv")
    assert path.parent.name == "data"
    assert path.name == "sample_search_app.html"


def test_build_default_search_app_path_is_stable():
    path = build_default_search_app_path()
    assert path.parent.name == "data"
    assert path.name == "search_app.html"


def test_export_search_app_writes_html(tmp_path):
    csv_path = tmp_path / "sample.csv"
    write_sample_csv(csv_path)
    output = tmp_path / "search.html"

    path = export_search_app(csv_path, output)

    assert path == output
    text = output.read_text(encoding="utf-8")
    assert "<!doctype html>" in text.lower()
    assert "可開伙套房" in text


def test_export_search_app_also_updates_stable_entry(tmp_path, monkeypatch):
    csv_path = tmp_path / "sample.csv"
    write_sample_csv(csv_path)
    output = tmp_path / "search.html"
    stable = tmp_path / "stable" / "search_app.html"

    monkeypatch.setattr("src.webapp.DEFAULT_SEARCH_APP_PATH", stable)

    export_search_app(csv_path, output)

    assert stable.exists()
    text = stable.read_text(encoding="utf-8")
    assert "<!doctype html>" in text.lower()
    assert "可開伙套房" in text
