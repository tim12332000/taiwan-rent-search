"""租屋分析核心測試。"""

from __future__ import annotations

import csv
from pathlib import Path

from src.analysis import (
    ANALYSIS_FIELDNAMES,
    AnalysisResult,
    Coordinates,
    SearchCriteria,
    analyze_listings,
    build_analysis_output_path,
    build_report_output_path,
    extract_district_from_text,
    export_analysis_results,
    export_markdown_report,
    format_listing_line,
    has_kitchen_sink_signal,
    latest_dataset_path,
    render_markdown_report,
    resolve_destination,
    score_band,
)


class DummyGeocoder:
    def __init__(self, mapping):
        self.mapping = mapping

    def geocode(self, query: str):
        return self.mapping.get(query)


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
            "id": "591-2",
            "platform": "591",
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
            "images": "https://img/3.jpg",
        },
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def test_has_kitchen_sink_signal_detects_keywords():
    row = {
        "title": "可開伙套房",
        "description": "附流理台與簡易廚房",
        "location_district": "信義區",
        "location_area": "松仁路",
        "room_type": "套房",
    }

    assert has_kitchen_sink_signal(row) is True


def test_analyze_listings_filters_and_scores_with_geocoder(tmp_path):
    csv_path = tmp_path / "sample.csv"
    write_sample_csv(csv_path)

    geocoder = DummyGeocoder(
        {
            "台北市信義區松仁路100號": Coordinates(25.0341, 121.5685),
        }
    )
    criteria = SearchCriteria(
        destination_address="台北市信義區松仁路100號",
        max_price=20000,
        max_commute_minutes=30,
        require_kitchen_sink=True,
        transport_mode="either",
    )

    results = analyze_listings(csv_path, criteria, geocoder=geocoder)

    assert len(results) == 1
    assert results[0].row["title"] == "可開伙套房"
    assert results[0].kitchen_sink_signal is True
    assert results[0].commute_best_minutes is not None


def test_analyze_listings_marks_unknown_feature_for_image_review(tmp_path):
    csv_path = tmp_path / "sample.csv"
    write_sample_csv(csv_path)

    criteria = SearchCriteria(
        require_kitchen_sink=True,
        strict_features=False,
    )
    results = analyze_listings(csv_path, criteria, geocoder=None)

    assert len(results) == 2
    second = next(result for result in results if result.row["id"] == "591-2")
    assert second.kitchen_sink_signal is False
    assert second.needs_image_review is True


def test_export_analysis_results_writes_expected_columns(tmp_path):
    result = AnalysisResult(
        row={
            "title": "可開伙套房",
            "price": "18000",
            "location_district": "信義區",
            "location_area": "松仁路",
            "floor_area": "12",
            "url": "https://rent.591.com.tw/1",
        },
        score=91.2,
        commute_bike_minutes=8,
        commute_metro_minutes=12,
        commute_best_minutes=8,
        kitchen_sink_signal=True,
        needs_image_review=False,
        matched_reasons=["estimated commute 8 min", "kitchen sink signal detected"],
    )

    output = tmp_path / "analysis.csv"
    export_analysis_results([result], output)

    with output.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert reader.fieldnames == ANALYSIS_FIELDNAMES
    assert rows[0]["rank"] == "1"
    assert rows[0]["kitchen_sink_signal"] == "yes"


def test_score_band_maps_scores_to_bands():
    assert score_band(95) == "A"
    assert score_band(80) == "B"
    assert score_band(60) == "C"


def test_format_listing_line_contains_human_readable_summary():
    result = AnalysisResult(
        row={
            "location_district": "信義區",
            "location_area": "松仁路",
            "price": "18000",
            "floor_area": "12",
        },
        score=91.2,
        commute_bike_minutes=8,
        commute_metro_minutes=12,
        commute_best_minutes=8,
        kitchen_sink_signal=True,
        needs_image_review=False,
        matched_reasons=[],
    )

    line = format_listing_line(result)
    assert "A級" in line
    assert "信義區" in line
    assert "通勤 8 分" in line
    assert "流理臺 已確認" in line


def test_render_markdown_report_groups_direct_and_review_items():
    criteria = SearchCriteria(
        destination_address="台北市信義區松仁路100號",
        require_kitchen_sink=True,
    )
    direct = AnalysisResult(
        row={
            "title": "可開伙套房",
            "url": "https://rent.591.com.tw/1",
            "location_district": "信義區",
            "location_area": "松仁路",
            "price": "18000",
            "floor_area": "12",
        },
        score=95,
        commute_bike_minutes=8,
        commute_metro_minutes=12,
        commute_best_minutes=8,
        kitchen_sink_signal=True,
        needs_image_review=False,
        matched_reasons=["estimated commute 8 min", "kitchen sink signal detected"],
    )
    review = AnalysisResult(
        row={
            "title": "待確認套房",
            "url": "https://rent.591.com.tw/2",
            "location_district": "大安區",
            "location_area": "和平東路",
            "price": "22000",
            "floor_area": "10",
        },
        score=82,
        commute_bike_minutes=15,
        commute_metro_minutes=18,
        commute_best_minutes=15,
        kitchen_sink_signal=False,
        needs_image_review=True,
        matched_reasons=["estimated commute 15 min", "kitchen sink not confirmed"],
    )

    report = render_markdown_report([direct, review], criteria, "data/sample.csv")

    assert "# 租屋快速瀏覽報告" in report
    assert "## 直接看" in report
    assert "## 待看圖確認" in report
    assert "可開伙套房" in report
    assert "待確認套房" in report


def test_export_markdown_report_writes_file(tmp_path):
    criteria = SearchCriteria(destination_address="台北市信義區松仁路100號")
    result = AnalysisResult(
        row={
            "title": "可開伙套房",
            "url": "https://rent.591.com.tw/1",
            "location_district": "信義區",
            "location_area": "松仁路",
            "price": "18000",
            "floor_area": "12",
        },
        score=95,
        commute_bike_minutes=8,
        commute_metro_minutes=12,
        commute_best_minutes=8,
        kitchen_sink_signal=True,
        needs_image_review=False,
        matched_reasons=["estimated commute 8 min"],
    )
    output = tmp_path / "shortlist.md"

    export_markdown_report([result], criteria, "data/sample.csv", output)

    text = output.read_text(encoding="utf-8")
    assert "租屋快速瀏覽報告" in text
    assert "可開伙套房" in text


def test_resolve_destination_falls_back_to_district_center_when_geocode_missing():
    criteria = SearchCriteria(destination_address="台北市信義區松仁路100號")

    coords = resolve_destination(criteria, DummyGeocoder({}))

    assert coords is not None
    assert round(coords.lat, 4) == 25.0332
    assert round(coords.lon, 4) == 121.5660


def test_extract_district_from_text_returns_matched_district():
    assert extract_district_from_text("台北市信義區松仁路100號") == "信義區"


def test_build_analysis_output_path_uses_input_stem():
    path = build_analysis_output_path("data/591_taipei_20260406_022332.csv")
    assert path.parent.name == "data"
    assert path.name.startswith("591_taipei_20260406_022332_analysis_")


def test_build_report_output_path_uses_input_stem():
    path = build_report_output_path("data/591_taipei_20260406_022332.csv")
    assert path.parent.name == "data"
    assert path.name.startswith("591_taipei_20260406_022332_shortlist_")


def test_latest_dataset_path_picks_newest_file(tmp_path):
    older = tmp_path / "591_a.csv"
    newer = tmp_path / "591_b.csv"
    older.write_text("x", encoding="utf-8")
    newer.write_text("x", encoding="utf-8")
    older.touch()
    newer.touch()

    assert latest_dataset_path(tmp_path) == newer
