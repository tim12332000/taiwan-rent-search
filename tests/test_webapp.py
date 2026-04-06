"""本地搜尋頁產生測試。"""

from __future__ import annotations

import csv
from pathlib import Path

from src.webapp import (
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
        "location_district": "信義區",
        "location_area": "松仁路",
        "floor_area": "12",
        "room_type": "套房",
        "description": "近捷運 可開伙 有流理台",
        "url": "https://rent.591.com.tw/1",
        "images": "https://img/1.jpg,https://img/2.jpg",
        "updated_at": "2026-01-01T00:00:00",
    }

    model = listing_to_view_model(row)

    assert model["cover"] == "https://img/1.jpg"
    assert model["kitchen_sink_signal"] is True
    assert "信義區" in model["search_text"]


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


def test_build_search_app_output_path_uses_input_stem():
    path = build_search_app_output_path("data/sample.csv")
    assert path.parent.name == "data"
    assert path.name == "sample_search_app.html"


def test_export_search_app_writes_html(tmp_path):
    csv_path = tmp_path / "sample.csv"
    write_sample_csv(csv_path)
    output = tmp_path / "search.html"

    path = export_search_app(csv_path, output)

    assert path == output
    text = output.read_text(encoding="utf-8")
    assert "<!doctype html>" in text.lower()
    assert "可開伙套房" in text
