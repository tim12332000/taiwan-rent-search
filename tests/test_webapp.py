"""本地搜尋頁產生測試。"""

from __future__ import annotations

import csv
from pathlib import Path

from src.webapp import (
    build_default_search_app_path,
    build_review_shortlist_output_path,
    build_search_app_output_path,
    export_review_shortlist,
    export_search_app,
    listing_to_view_model,
    prepare_listing_view_models,
    render_search_app_html,
    search_speed_hint,
    search_speed_label,
    search_speed_score,
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
    assert model["cooking_convenience_score"] == 3
    assert model["cooking_convenience_label"] == "適合煮飯"
    assert model["cooking_convenience_reason"] == "文字同時提到流理臺與可煮飯設備"
    assert "台北市" in model["search_text"]
    assert "信義區" in model["search_text"]
    assert "最短租期一年" in model["search_text"]
    assert "台北市信義區松仁路" in model["search_text_compact"]


def test_listing_to_view_model_does_not_treat_cooking_allowed_as_sink_signal():
    row = {
        "id": "591-2",
        "platform": "591",
        "title": "可開伙套房",
        "price": "18000",
        "location_county": "台北市",
        "location_district": "信義區",
        "location_area": "松仁路",
        "floor_area": "12",
        "room_type": "套房",
        "description": "近捷運 可開伙",
        "url": "https://rent.591.com.tw/2",
        "images": "",
        "updated_at": "2026-01-01T00:00:00",
    }

    model = listing_to_view_model(row)

    assert model["kitchen_sink_signal"] is False
    assert model["cooking_convenience_score"] in {0, 1}


def test_prepare_listing_view_models_reads_csv(tmp_path):
    csv_path = tmp_path / "sample.csv"
    write_sample_csv(csv_path)

    models = prepare_listing_view_models(csv_path)

    assert len(models) == 2
    assert models[0]["platform"] == "591"
    assert models[1]["platform"] == "mixrent"


def test_prepare_listing_view_models_merges_adjacent_ai_reviews(tmp_path):
    csv_path = tmp_path / "sample.csv"
    write_sample_csv(csv_path)
    (tmp_path / "ai_cooking_reviews.json").write_text(
        '{"591-1":{"label":"適合煮飯","score":3,"confidence":0.91,"reason":"AI 看圖判定有完整備餐與爐具空間"}}',
        encoding="utf-8",
    )

    models = prepare_listing_view_models(csv_path)

    assert models[0]["cooking_convenience_label"] == "適合煮飯"
    assert models[0]["cooking_convenience_reason"] == "AI 看圖判定有完整備餐與爐具空間"
    assert models[0]["ai_cooking_confidence"] == 0.91


def test_prepare_listing_view_models_allows_ai_score_zero_to_override(tmp_path):
    csv_path = tmp_path / "sample.csv"
    write_sample_csv(csv_path)
    (tmp_path / "ai_cooking_reviews.json").write_text(
        '{"591-1":{"label":"不適合煮飯","score":0,"confidence":0.83,"reason":"AI 看圖判定缺少廚房與爐具"}}',
        encoding="utf-8",
    )

    models = prepare_listing_view_models(csv_path)

    assert models[0]["cooking_convenience_score"] == 0
    assert models[0]["cooking_convenience_label"] == "不適合煮飯"
    assert models[0]["cooking_convenience_reason"] == "AI 看圖判定缺少廚房與爐具"


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
    assert 'id="cooking-level"' in html_text
    assert "適合煮飯" in html_text
    assert "至少可勉強煮" in html_text
    assert "至少看圖確認" in html_text
    assert "較適合煮飯" in html_text
    assert "只看有圖片（方便手動看廚房）" in html_text
    assert "可煮飯方便程度優先" in html_text
    assert "cooking_convenience_score" in html_text
    assert "cooking_convenience_reason" in html_text
    assert "ai_cooking_confidence" in html_text
    assert "可煮飯：" in html_text
    assert "可煮飯判斷：" in html_text
    assert "AI 信心：" in html_text
    assert "立刻重跑 AI 審核" in html_text
    assert "AI 審核中..." in html_text
    assert "AI 會自動審核這筆房源" in html_text
    assert 'id="ai-status"' in html_text
    assert "updateDebugConsole" in html_text
    assert "aiUsageSummary" in html_text
    assert "window.parent.postMessage" in html_text
    assert "rent-search-debug" in html_text
    assert "setAiStatusMessage" in html_text
    assert "這筆已排入 AI 審核隊列" in html_text
    assert "這筆正在 AI 審核中" in html_text
    assert "reviewListing" in html_text
    assert "pollAiReviewJob" in html_text
    assert "applyAiReviewResult" in html_text
    assert "enqueueAutoReview" in html_text
    assert "pumpAutoReviewQueue" in html_text
    assert "scheduleVisibleAutoReviews" in html_text
    assert "AI_AUTO_REVIEW_CONCURRENCY" in html_text
    assert "/api/review-listing" in html_text
    assert "/api/ai-review-jobs/" in html_text
    assert "gallery-modal" in html_text
    assert "openGallery" in html_text
    assert "moveGallery" in html_text
    assert "preset-cooking-best" in html_text
    assert "preset-review-images" in html_text
    assert "export-shortlist" in html_text
    assert "preset-reset" in html_text
    assert "先看最能煮飯" in html_text
    assert "els.cookingLevel.value = '';" in html_text
    assert "看圖審核" in html_text
    assert "匯出 shortlist" in html_text
    assert "全部重設" in html_text
    assert "applyPreset" in html_text
    assert "REVIEW_STORAGE_KEY" in html_text
    assert "loadReviewDecisions" in html_text
    assert "setReviewDecision" in html_text
    assert "exportShortlist" in html_text
    assert "/api/export-shortlist" in html_text
    assert "count-shortlist" in html_text
    assert "sourceDatasetPath" in html_text
    assert "不錯" in html_text
    assert "先略過" in html_text
    assert "清除標記" in html_text
    assert "尚未標記" in html_text
    assert "data-gallery-id" in html_text
    assert "看圖 ${item.images.length} 張" in html_text
    assert "搜尋速度" in html_text
    assert "performance.now()" in html_text
    assert "calculateSearchSpeedScore" in html_text
    assert "requestAnimationFrame" in html_text


def test_build_search_app_output_path_uses_input_stem():
    path = build_search_app_output_path("data/sample.csv")
    assert path.parent.name == "data"
    assert path.name == "sample_search_app.html"


def test_build_default_search_app_path_is_stable():
    path = build_default_search_app_path()
    assert path.parent.name == "data"
    assert path.name == "search_app.html"


def test_build_review_shortlist_output_path_uses_dataset_directory():
    path = build_review_shortlist_output_path("data/cases/songren_100/current_dataset.csv")

    assert path.parent.as_posix().endswith("data/cases/songren_100")
    assert path.name.startswith("current_dataset_shortlist_")


def test_export_review_shortlist_writes_markdown(tmp_path):
    dataset_path = tmp_path / "current_dataset.csv"
    dataset_path.write_text("id\n1\n", encoding="utf-8")
    output_path = tmp_path / "review_shortlist.md"

    path = export_review_shortlist(
        dataset_path,
        [
            {
                "id": "591-1",
                "platform": "591",
                "title": "可開伙套房",
                "price": 18000,
                "district": "信義區",
                "area": "松仁路",
                "floor_area": 12.0,
                "cooking_convenience_label": "適合煮飯",
                "cooking_convenience_reason": "AI 與文字都顯示可正常備餐",
                "ai_cooking_confidence": 0.93,
                "url": "https://rent.591.com.tw/1",
            }
        ],
        destination="台北市信義區松仁路100號",
        output_path=output_path,
    )

    assert path == output_path
    text = output_path.read_text(encoding="utf-8")
    assert "# 租屋 shortlist" in text
    assert "匯出筆數: `1`" in text
    assert "可開伙套房" in text
    assert "AI 信心：93%" in text
    assert "https://rent.591.com.tw/1" in text


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


def test_search_speed_score_thresholds():
    assert search_speed_score(80) == 100
    assert search_speed_score(300) == 40
    assert 40 < search_speed_score(180) < 100


def test_search_speed_labels_and_hints():
    assert search_speed_label(80) == "順暢"
    assert search_speed_label(180) == "可接受"
    assert search_speed_label(300) == "偏慢"
    assert search_speed_hint(80) == "目前搜尋速度在目標內。"
    assert "縮小行政區" in search_speed_hint(180)
    assert "目的地刷新較小的資料池" in search_speed_hint(300)
