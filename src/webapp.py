"""產生本地即時搜尋租屋頁面。"""

from __future__ import annotations

import argparse
import html
import json
import time
import webbrowser
from pathlib import Path

from .ai_cooking_review import load_ai_reviews
from .analysis import (
    TAIPEI_DISTRICT_CENTERS,
    cooking_convenience_profile,
    district_center,
    has_kitchen_sink_signal,
    latest_dataset_path,
    load_listings,
    parse_images,
)
from .taipei_metro import find_nearest_station


DEFAULT_SEARCH_APP_PATH = Path("data") / "search_app.html"
SEARCH_SPEED_BUDGET_MS = 120
SEARCH_SPEED_WARNING_MS = 250


def build_search_app_output_path(input_path: str | Path) -> Path:
    stem = Path(input_path).stem
    return Path("data") / f"{stem}_search_app.html"


def build_default_search_app_path() -> Path:
    return DEFAULT_SEARCH_APP_PATH


def build_review_shortlist_output_path(input_path: str | Path) -> Path:
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    source_path = Path(input_path)
    return source_path.parent / f"{source_path.stem}_shortlist_{timestamp}.md"


def search_speed_score(duration_ms: float) -> int:
    if duration_ms <= SEARCH_SPEED_BUDGET_MS:
        return 100
    if duration_ms >= SEARCH_SPEED_WARNING_MS:
        return 40

    span = SEARCH_SPEED_WARNING_MS - SEARCH_SPEED_BUDGET_MS
    penalty = (duration_ms - SEARCH_SPEED_BUDGET_MS) / span
    return round(100 - penalty * 60)


def search_speed_label(duration_ms: float) -> str:
    if duration_ms <= SEARCH_SPEED_BUDGET_MS:
        return "順暢"
    if duration_ms <= SEARCH_SPEED_WARNING_MS:
        return "可接受"
    return "偏慢"


def search_speed_hint(duration_ms: float) -> str:
    if duration_ms <= SEARCH_SPEED_BUDGET_MS:
        return "目前搜尋速度在目標內。"
    if duration_ms <= SEARCH_SPEED_WARNING_MS:
        return "若想更快，可先縮小行政區、來源或租金範圍。"
    return "建議先縮小條件，或先用目的地刷新較小的資料池。"


def normalize_search_text(text: str | None) -> str:
    return "".join((text or "").replace("臺", "台").lower().split())


def build_listing_address(row: dict[str, str]) -> str:
    return "".join(
        part for part in [
            row.get("location_county", ""),
            row.get("location_district", ""),
            row.get("location_area", ""),
        ] if part
    )


def find_ai_review_path_for_dataset(input_path: str | Path) -> Path | None:
    candidate = Path(input_path).parent / "ai_cooking_reviews.json"
    return candidate if candidate.exists() else None


def find_ai_usage_log_path_for_dataset(input_path: str | Path) -> Path | None:
    candidate = Path(input_path).parent / "ai_usage.jsonl"
    return candidate if candidate.exists() else None


def summarize_ai_usage_log(path: str | Path | None) -> dict[str, object]:
    if not path:
        return {
            "exists": False,
            "entries": 0,
            "input_tokens": 0,
            "cached_input_tokens": 0,
            "output_tokens": 0,
            "last_timestamp": "",
            "last_listing_id": "",
        }

    log_path = Path(path)
    if not log_path.exists():
        return {
            "exists": False,
            "entries": 0,
            "input_tokens": 0,
            "cached_input_tokens": 0,
            "output_tokens": 0,
            "last_timestamp": "",
            "last_listing_id": "",
        }

    summary = {
        "exists": True,
        "entries": 0,
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
        "last_timestamp": "",
        "last_listing_id": "",
    }
    with log_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            summary["entries"] += 1
            summary["input_tokens"] += int(payload.get("input_tokens") or 0)
            summary["cached_input_tokens"] += int(payload.get("cached_input_tokens") or 0)
            summary["output_tokens"] += int(payload.get("output_tokens") or 0)
            summary["last_timestamp"] = str(payload.get("timestamp") or summary["last_timestamp"])
            summary["last_listing_id"] = str(payload.get("listing_id") or summary["last_listing_id"])
    return summary


def listing_to_view_model(row: dict[str, str], ai_review: dict[str, object] | None = None) -> dict[str, object]:
    images = parse_images(row.get("images"))
    address = build_listing_address(row)
    center = district_center(row.get("location_district", ""))
    nearest_station = find_nearest_station(center.lat if center else None, center.lon if center else None)
    cooking_score, cooking_label, cooking_reason = cooking_convenience_profile(row)
    if ai_review:
        if ai_review.get("score") is not None:
            cooking_score = int(ai_review["score"])
        cooking_label = str(ai_review.get("label") or cooking_label)
        cooking_reason = str(ai_review.get("reason") or cooking_reason)
    search_text = " ".join(
        part for part in [
            row.get("platform", ""),
            row.get("title", ""),
            row.get("location_county", ""),
            row.get("location_district", ""),
            row.get("location_area", ""),
            address,
            row.get("room_type", ""),
            row.get("description", ""),
            row.get("detail_shortest_lease", ""),
            row.get("detail_rules", ""),
            row.get("detail_management_fee", ""),
            row.get("detail_deposit", ""),
            row.get("detail_facilities", ""),
        ] if part
    ).lower()
    return {
        "id": row.get("id", ""),
        "platform": row.get("platform", ""),
        "title": row.get("title", ""),
        "price": int(float(row.get("price") or 0)),
        "county": row.get("location_county", ""),
        "district": row.get("location_district", ""),
        "area": row.get("location_area", ""),
        "address": address,
        "district_center_lat": center.lat if center else None,
        "district_center_lon": center.lon if center else None,
        "nearest_metro_station": nearest_station["name"] if nearest_station else "",
        "nearest_metro_distance_km": nearest_station["distance_km"] if nearest_station else None,
        "nearest_metro_walk_minutes": nearest_station["walk_minutes"] if nearest_station else None,
        "floor_area": float(row.get("floor_area")) if row.get("floor_area") else None,
        "room_type": row.get("room_type", ""),
        "description": row.get("description", ""),
        "url": row.get("url", ""),
        "images": images,
        "cover": images[0] if images else "",
        "kitchen_sink_signal": has_kitchen_sink_signal(row),
        "cooking_convenience_score": cooking_score,
        "cooking_convenience_label": cooking_label,
        "cooking_convenience_reason": cooking_reason,
        "ai_cooking_confidence": ai_review.get("confidence") if ai_review else None,
        "updated_at": row.get("updated_at", ""),
        "detail_shortest_lease": row.get("detail_shortest_lease", ""),
        "detail_rules": row.get("detail_rules", ""),
        "detail_deposit": row.get("detail_deposit", ""),
        "detail_management_fee": row.get("detail_management_fee", ""),
        "detail_facilities": row.get("detail_facilities", ""),
        "search_text": search_text,
        "search_text_compact": normalize_search_text(search_text),
    }


def prepare_listing_view_models(input_path: str | Path) -> list[dict[str, object]]:
    rows = load_listings(input_path)
    ai_reviews = load_ai_reviews(find_ai_review_path_for_dataset(input_path) or "")
    return [listing_to_view_model(row, ai_reviews.get(row.get("id", ""))) for row in rows]


def render_review_shortlist_markdown(
    input_path: str | Path,
    items: list[dict[str, object]],
    *,
    destination: str = "",
) -> str:
    lines = [
        "# 租屋 shortlist",
        "",
        f"- 來源資料: `{Path(input_path).name}`",
        f"- 匯出筆數: `{len(items)}`",
        f"- 目的地: `{destination or '未指定'}`",
        f"- 匯出時間: `{time.strftime('%Y-%m-%d %H:%M:%S')}`",
        "",
    ]

    for index, item in enumerate(items, 1):
        title = str(item.get("title") or "未命名房源")
        district = str(item.get("district") or "未知區域")
        area = str(item.get("area") or "路段待補")
        platform = str(item.get("platform") or "unknown")
        price = item.get("price")
        floor_area = item.get("floor_area")
        cooking_label = str(item.get("cooking_convenience_label") or "未提及")
        cooking_reason = str(item.get("cooking_convenience_reason") or "待補")
        url = str(item.get("url") or "")
        confidence = item.get("ai_cooking_confidence")
        ai_confidence_text = (
            f"{round(float(confidence) * 100)}%"
            if confidence is not None and confidence != ""
            else "待補"
        )
        price_text = f"${int(price)}/月" if price not in (None, "") else "租金待補"
        area_text = f"{floor_area}坪" if floor_area not in (None, "") else "坪數待補"

        lines.extend(
            [
                f"{index}. **{title}**",
                f"   - {platform} | {district} | {area} | {price_text} | {area_text}",
                f"   - 可煮飯：{cooking_label}",
                f"   - AI 信心：{ai_confidence_text}",
                f"   - 理由：{cooking_reason}",
                f"   - 連結：{url}",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def export_review_shortlist(
    input_path: str | Path,
    items: list[dict[str, object]],
    *,
    destination: str = "",
    output_path: str | Path | None = None,
) -> Path:
    target = Path(output_path) if output_path else build_review_shortlist_output_path(input_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        render_review_shortlist_markdown(input_path, items, destination=destination),
        encoding="utf-8",
    )
    return target


def render_search_app_html(input_path: str | Path, listings: list[dict[str, object]]) -> str:
    input_path = Path(input_path)
    source_name = html.escape(input_path.name)
    source_path_json = json.dumps(str(input_path), ensure_ascii=False)
    listings_json = json.dumps(listings, ensure_ascii=False)
    district_centers_json = json.dumps(TAIPEI_DISTRICT_CENTERS, ensure_ascii=False)
    ai_usage_summary_json = json.dumps(
        summarize_ai_usage_log(find_ai_usage_log_path_for_dataset(input_path)),
        ensure_ascii=False,
    )
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>租屋即時搜尋</title>
  <style>
    :root {{
      --bg: #f5efe4;
      --paper: #fffaf3;
      --ink: #1c2826;
      --muted: #5b6763;
      --line: #d7c8b3;
      --accent: #0f766e;
      --accent-2: #b45309;
      --chip: #ece4d7;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Noto Sans TC", "Microsoft JhengHei", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top right, rgba(180,83,9,.12), transparent 24%),
        radial-gradient(circle at left center, rgba(15,118,110,.12), transparent 22%),
        var(--bg);
    }}
    .page {{
      max-width: 1320px;
      margin: 0 auto;
      padding: 24px 18px 56px;
    }}
    .hero {{
      display: grid;
      gap: 14px;
      padding: 24px;
      border-radius: 24px;
      border: 1px solid var(--line);
      background: linear-gradient(135deg, rgba(255,255,255,.78), rgba(255,248,234,.96));
      box-shadow: 0 16px 40px rgba(28,40,38,.08);
      margin-bottom: 18px;
    }}
    .hero h1 {{
      margin: 0;
      font-size: clamp(30px, 4vw, 52px);
      line-height: 1.1;
      letter-spacing: -.03em;
    }}
    .hero p {{
      margin: 0;
      color: var(--muted);
      max-width: 70ch;
      line-height: 1.7;
    }}
    .hero-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      color: var(--muted);
      font-size: 14px;
    }}
    .hero-meta span {{
      padding: 7px 11px;
      border-radius: 999px;
      background: rgba(236,228,215,.75);
    }}
    .layout {{
      display: grid;
      grid-template-columns: 300px 1fr;
      gap: 18px;
      align-items: start;
    }}
    .panel {{
      padding: 18px;
      border-radius: 22px;
      border: 1px solid var(--line);
      background: rgba(255,250,243,.92);
      box-shadow: 0 10px 30px rgba(28,40,38,.06);
    }}
    .panel h2 {{
      margin: 0 0 14px;
      font-size: 18px;
    }}
    .field {{
      display: grid;
      gap: 8px;
      margin-bottom: 14px;
    }}
    .field label {{
      font-size: 13px;
      font-weight: 700;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: .08em;
    }}
    input, select {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px 14px;
      font: inherit;
      background: #fffdf9;
      color: var(--ink);
    }}
    .check {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 12px;
      color: var(--muted);
      font-size: 14px;
    }}
    .check input {{
      width: auto;
      margin: 0;
    }}
    .summary {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 16px;
    }}
    .presets {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 16px;
    }}
    .presets button {{
      border: 1px solid var(--line);
      background: #fff7ed;
      color: var(--accent-2);
      padding: 8px 12px;
      border-radius: 999px;
      cursor: pointer;
      font: inherit;
      font-weight: 700;
    }}
    .summary .metric {{
      padding: 12px 14px;
      border-radius: 16px;
      background: rgba(236,228,215,.82);
      color: var(--muted);
      min-width: 140px;
    }}
    .summary .metric strong {{
      display: block;
      color: var(--ink);
      font-size: 22px;
      margin-top: 4px;
    }}
    .results {{
      display: grid;
      gap: 16px;
    }}
    .listing {{
      display: grid;
      grid-template-columns: 240px 1fr;
      gap: 18px;
      padding: 16px;
      border-radius: 22px;
      border: 1px solid var(--line);
      background: var(--paper);
      box-shadow: 0 8px 20px rgba(28,40,38,.05);
    }}
    .listing img, .listing .placeholder {{
      width: 100%;
      aspect-ratio: 4 / 3;
      object-fit: cover;
      border-radius: 18px;
      background: #e4d8c7;
    }}
    .listing button.image-button {{
      width: 100%;
      padding: 0;
      border: 0;
      background: transparent;
      cursor: zoom-in;
    }}
    .listing .placeholder {{
      display: grid;
      place-items: center;
      color: var(--muted);
      font-size: 14px;
      letter-spacing: .08em;
    }}
    .listing-main {{
      display: grid;
      gap: 10px;
      min-width: 0;
    }}
    .listing-top {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      color: var(--muted);
      font-size: 13px;
    }}
    .chip {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 10px;
      border-radius: 999px;
      background: var(--chip);
    }}
    .title {{
      margin: 0;
      font-size: 24px;
      line-height: 1.35;
    }}
    .meta {{
      color: var(--accent);
      font-weight: 700;
      line-height: 1.7;
    }}
    .meta-sub {{
      color: var(--muted);
      font-size: 14px;
      line-height: 1.7;
    }}
    .desc {{
      color: var(--muted);
      line-height: 1.7;
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}
    .rule, .facility {{
      color: var(--muted);
      font-size: 14px;
      line-height: 1.7;
      border-left: 3px solid rgba(15,118,110,.18);
      padding-left: 10px;
    }}
    .actions a {{
      color: var(--accent-2);
      font-weight: 700;
      text-decoration: none;
    }}
    .gallery-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }}
    .gallery-actions button {{
      border: 1px solid var(--line);
      background: #fff7ed;
      color: var(--accent-2);
      padding: 8px 12px;
      border-radius: 999px;
      cursor: pointer;
      font: inherit;
      font-weight: 700;
    }}
    .gallery-actions button[disabled] {{
      opacity: .65;
      cursor: wait;
    }}
    .review-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }}
    .review-actions button {{
      border: 1px solid var(--line);
      background: white;
      color: var(--ink);
      padding: 8px 12px;
      border-radius: 999px;
      cursor: pointer;
      font: inherit;
      font-weight: 700;
    }}
    .review-actions .shortlist {{
      border-color: rgba(20,83,45,.3);
      color: #14532d;
      background: rgba(20,83,45,.08);
    }}
    .review-actions .skip {{
      border-color: rgba(153,27,27,.24);
      color: #991b1b;
      background: rgba(153,27,27,.08);
    }}
    .review-note {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
    }}
    .gallery-modal {{
      position: fixed;
      inset: 0;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 20px;
      background: rgba(17, 24, 39, 0.82);
      z-index: 20;
    }}
    .gallery-modal.is-open {{
      display: flex;
    }}
    .gallery-dialog {{
      width: min(100%, 960px);
      display: grid;
      gap: 12px;
      padding: 18px;
      border-radius: 24px;
      background: rgba(255, 250, 243, 0.98);
      box-shadow: 0 20px 60px rgba(15, 23, 42, 0.35);
    }}
    .gallery-toolbar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      color: var(--muted);
    }}
    .gallery-toolbar button {{
      border: 1px solid var(--line);
      background: white;
      color: var(--ink);
      padding: 8px 12px;
      border-radius: 999px;
      cursor: pointer;
      font: inherit;
    }}
    .gallery-stage {{
      position: relative;
      display: grid;
      grid-template-columns: auto 1fr auto;
      align-items: center;
      gap: 10px;
    }}
    .gallery-stage img {{
      width: 100%;
      max-height: 72vh;
      object-fit: contain;
      border-radius: 18px;
      background: #e4d8c7;
    }}
    .gallery-stage button {{
      width: 44px;
      height: 44px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(255,255,255,.92);
      cursor: pointer;
      font-size: 20px;
    }}
    .gallery-caption {{
      color: var(--muted);
      line-height: 1.6;
    }}
    .empty {{
      padding: 28px;
      text-align: center;
      border: 1px dashed var(--line);
      border-radius: 18px;
      color: var(--muted);
      background: rgba(255,255,255,.52);
    }}
    @media (max-width: 1024px) {{
      .layout {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 720px) {{
      .listing {{ grid-template-columns: 1fr; }}
      .hero {{ padding: 20px; }}
      .title {{ font-size: 21px; }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <h1>租屋即時搜尋</h1>
      <p>不用再翻 CSV。這個頁面把最新資料池直接嵌進來，你可以即時輸入關鍵字、切來源、行政區、租金上限、坪數下限和可煮飯方便程度，候選會立刻更新。</p>
      <div class="hero-meta">
        <span>來源資料：{source_name}</span>
        <span>即時過濾：前端本地運算</span>
        <span>適合先篩再進 shortlist / 看圖</span>
      </div>
    </section>

    <div class="layout">
      <aside class="panel">
        <h2>篩選條件</h2>
        <div class="field">
          <label for="q">搜尋</label>
          <input id="q" type="search" placeholder="輸入完整地址、路名、捷運、物件特點…" />
        </div>
        <div class="field">
          <label for="destination">通勤目的地</label>
          <input id="destination" type="search" placeholder="輸入上班地點；留空時會自動嘗試用上面的地址搜尋" />
        </div>
        <div class="field">
          <label for="district">行政區</label>
          <select id="district">
            <option value="">全部行政區</option>
          </select>
        </div>
        <div class="field">
          <label for="platform">來源</label>
          <select id="platform">
            <option value="">全部來源</option>
          </select>
        </div>
        <div class="field">
          <label for="max-price">最高月租</label>
          <input id="max-price" type="number" min="0" step="1000" placeholder="例如 30000" />
        </div>
        <div class="field">
          <label for="min-area">最低坪數</label>
          <input id="min-area" type="number" min="0" step="1" placeholder="例如 10" />
        </div>
        <div class="field">
          <label for="cooking-level">可煮飯方便程度</label>
          <select id="cooking-level">
            <option value="">全部</option>
            <option value="3">適合煮飯</option>
            <option value="2">至少可勉強煮</option>
            <option value="1">至少看圖確認</option>
          </select>
        </div>
        <label class="check">
          <input id="has-images" type="checkbox" />
          只看有圖片（方便手動看廚房）
        </label>
        <div class="field">
          <label for="sort-by">排序</label>
          <select id="sort-by">
            <option value="cooking-desc">可煮飯方便程度優先</option>
            <option value="price-asc">租金由低到高</option>
            <option value="price-desc">租金由高到低</option>
            <option value="area-desc">坪數由大到小</option>
            <option value="updated-desc">更新時間由新到舊</option>
          </select>
        </div>
      </aside>

      <section>
        <div class="presets">
          <button id="preset-cooking-best" type="button">先看最能煮飯</button>
          <button id="preset-review-images" type="button">看圖審核</button>
          <button id="export-shortlist" type="button">匯出 shortlist</button>
          <button id="preset-reset" type="button">全部重設</button>
        </div>
        <div class="summary">
          <div class="metric">目前顯示<strong id="count-visible">0</strong></div>
          <div class="metric">資料來源<strong id="count-platforms">0</strong></div>
          <div class="metric">較適合煮飯<strong id="count-kitchen">0</strong></div>
          <div class="metric">已標記不錯<strong id="count-shortlist">0</strong></div>
          <div class="metric">平均月租<strong id="avg-price">-</strong></div>
          <div class="metric">搜尋速度<strong id="search-speed">-</strong></div>
        </div>
        <div id="ai-status" class="meta-sub">AI 會自動審核目前畫面上的候選房源。</div>
        <div id="export-status" class="meta-sub">目前還沒有標記為不錯的房源。</div>
        <div id="speed-hint" class="meta-sub">搜尋速度目標：{SEARCH_SPEED_BUDGET_MS}ms 內。</div>
        <div id="results" class="results"></div>
        <div id="empty" class="empty" hidden>目前沒有符合條件的房源。</div>
      </section>
    </div>
  </main>
  <div id="gallery-modal" class="gallery-modal" aria-hidden="true">
    <div class="gallery-dialog" role="dialog" aria-modal="true" aria-label="房源圖片檢視">
      <div class="gallery-toolbar">
        <div>
          <strong id="gallery-title">圖片檢視</strong>
          <div id="gallery-count"></div>
        </div>
        <button id="gallery-close" type="button">關閉</button>
      </div>
      <div class="gallery-stage">
        <button id="gallery-prev" type="button" aria-label="上一張">‹</button>
        <img id="gallery-image" alt="房源圖片" />
        <button id="gallery-next" type="button" aria-label="下一張">›</button>
      </div>
      <div id="gallery-caption" class="gallery-caption"></div>
    </div>
  </div>

  <script>
    const listings = {listings_json};
    const districtCenters = {district_centers_json};
    const sourceDatasetPath = {source_path_json};
    const aiUsageSummary = {ai_usage_summary_json};
    const pageParams = new URLSearchParams(window.location.search);
    const els = {{
      q: document.getElementById('q'),
      destination: document.getElementById('destination'),
      district: document.getElementById('district'),
      platform: document.getElementById('platform'),
      maxPrice: document.getElementById('max-price'),
      minArea: document.getElementById('min-area'),
      cookingLevel: document.getElementById('cooking-level'),
      hasImages: document.getElementById('has-images'),
      sortBy: document.getElementById('sort-by'),
      results: document.getElementById('results'),
      empty: document.getElementById('empty'),
      countVisible: document.getElementById('count-visible'),
      countPlatforms: document.getElementById('count-platforms'),
      countKitchen: document.getElementById('count-kitchen'),
      countShortlist: document.getElementById('count-shortlist'),
      avgPrice: document.getElementById('avg-price'),
      searchSpeed: document.getElementById('search-speed'),
      aiStatus: document.getElementById('ai-status'),
      exportStatus: document.getElementById('export-status'),
      speedHint: document.getElementById('speed-hint'),
      presetCookingBest: document.getElementById('preset-cooking-best'),
      presetReviewImages: document.getElementById('preset-review-images'),
      exportShortlist: document.getElementById('export-shortlist'),
      presetReset: document.getElementById('preset-reset'),
      galleryModal: document.getElementById('gallery-modal'),
      galleryTitle: document.getElementById('gallery-title'),
      galleryCount: document.getElementById('gallery-count'),
      galleryImage: document.getElementById('gallery-image'),
      galleryCaption: document.getElementById('gallery-caption'),
      galleryPrev: document.getElementById('gallery-prev'),
      galleryNext: document.getElementById('gallery-next'),
      galleryClose: document.getElementById('gallery-close'),
    }};
    const SEARCH_SPEED_BUDGET_MS = {SEARCH_SPEED_BUDGET_MS};
    const SEARCH_SPEED_WARNING_MS = {SEARCH_SPEED_WARNING_MS};
    const AI_AUTO_REVIEW_CONCURRENCY = 2;
    const AI_AUTO_REVIEW_VISIBLE_LIMIT = 6;
    const REVIEW_STORAGE_KEY = 'taiwan-rent-search.review-decisions';
    let filterFrame = null;
    let galleryState = null;
    let reviewDecisions = {{}};
    const aiReviewJobs = {{}};
    const aiAutoReviewQueue = [];
    const aiAutoReviewQueued = new Set();
    let aiReviewActiveCount = 0;
    let lastVisibleListingIds = [];
    let aiStatusMessage = 'AI 會自動審核目前畫面上的候選房源。';
    let shortlistedCount = 0;

    const uniqueValues = (key) => [...new Set(listings.map(item => item[key]).filter(Boolean))].sort();
    const districts = uniqueValues('district');

    function fillSelect(select, values) {{
      const baseOption = select.querySelector('option');
      select.innerHTML = '';
      select.appendChild(baseOption);
      values.forEach(value => {{
        const option = document.createElement('option');
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
      }});
    }}

    function formatNumber(value) {{
      if (value === null || value === undefined || value === '') return '-';
      return new Intl.NumberFormat('zh-TW').format(Number(value));
    }}

    function normalizeSearchText(value) {{
      return (value || '')
        .replaceAll('臺', '台')
        .toLowerCase()
        .replace(/\\s+/g, '');
    }}

    function buildAddressNeedles(query) {{
      const normalized = normalizeSearchText(query);
      if (!normalized) return [];

      const needles = new Set([normalized]);
      let trimmed = normalized;
      const tailPatterns = [
        /(?:[bB]\\d+|\\d+[fF])$/,
        /\\d+樓$/,
        /\\d+室$/,
        /(?:之\\d+)?\\d+號(?:之\\d+)?$/,
      ];

      let changed = true;
      while (changed) {{
        changed = false;
        for (const pattern of tailPatterns) {{
          if (!pattern.test(trimmed)) continue;
          trimmed = trimmed.replace(pattern, '');
          if (trimmed) needles.add(trimmed);
          changed = true;
          break;
        }}
      }}

      const district = districts.find(value => {{
        const compactDistrict = normalizeSearchText(value);
        return compactDistrict && normalized.includes(compactDistrict);
      }});
      if (district) {{
        needles.add(normalizeSearchText(district));
      }}

      return [...needles].filter(Boolean);
    }}

    function matchesQuery(item, query) {{
      const rawQuery = (query || '').trim();
      if (!rawQuery) return true;

      const loweredQuery = rawQuery.toLowerCase();
      if (item.search_text.includes(loweredQuery)) return true;

      return buildAddressNeedles(rawQuery).some(needle => item.search_text_compact.includes(needle));
    }}

    function haversineKm(origin, destination) {{
      const toRadians = degrees => degrees * Math.PI / 180;
      const radius = 6371;
      const dLat = toRadians(destination.lat - origin.lat);
      const dLon = toRadians(destination.lon - origin.lon);
      const lat1 = toRadians(origin.lat);
      const lat2 = toRadians(destination.lat);
      const a =
        Math.sin(dLat / 2) ** 2 +
        Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
      return radius * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    }}

    function estimateBikeMinutes(distanceKm) {{
      return Math.ceil(distanceKm * 4.2 + 4);
    }}

    function estimateMetroMinutes(distanceKm) {{
      return Math.ceil(distanceKm * 2.3 + 12);
    }}

    function extractDistrictFromText(value) {{
      const text = value || '';
      return Object.keys(districtCenters).find(name => text.includes(name)) || '';
    }}

    function inferDistrictFromListings(query) {{
      const needles = buildAddressNeedles(query);
      if (!needles.length) return '';

      const districtScores = new Map();
      listings.forEach(item => {{
        if (!item.district || !item.search_text_compact) return;
        let bestMatchScore = 0;
        needles.forEach(needle => {{
          if (needle && item.search_text_compact.includes(needle)) {{
            bestMatchScore = Math.max(bestMatchScore, needle.length);
          }}
        }});
        if (!bestMatchScore) return;
        districtScores.set(item.district, (districtScores.get(item.district) || 0) + bestMatchScore);
      }});

      const ranked = [...districtScores.entries()].sort((a, b) => b[1] - a[1]);
      return ranked.length ? ranked[0][0] : '';
    }}

    function getDestinationQuery() {{
      const explicitDestination = (els.destination.value || '').trim();
      if (explicitDestination) return explicitDestination;

      const searchQuery = (els.q.value || '').trim();
      return extractDistrictFromText(searchQuery) ? searchQuery : '';
    }}

    function resolveDestination(value) {{
      const latParam = pageParams.get('destination_lat');
      const lonParam = pageParams.get('destination_lon');
      const lat = latParam === null ? NaN : Number(latParam);
      const lon = lonParam === null ? NaN : Number(lonParam);
      if (!Number.isNaN(lat) && !Number.isNaN(lon)) {{
        return {{ district: extractDistrictFromText(value), lat, lon }};
      }}

      const district = extractDistrictFromText(value) || inferDistrictFromListings(value);
      if (!district || !districtCenters[district]) return null;
      const [districtLat, districtLon] = districtCenters[district];
      return {{ district, lat: districtLat, lon: districtLon }};
    }}

    function getCommuteEstimate(item, destination) {{
      if (!destination) return null;
      if (item.district_center_lat === null || item.district_center_lon === null) return null;

      const origin = {{
        lat: item.district_center_lat,
        lon: item.district_center_lon,
      }};
      const distanceKm = haversineKm(origin, destination);
      const bikeMinutes = estimateBikeMinutes(distanceKm);
      const metroMinutes = estimateMetroMinutes(distanceKm);
      return {{
        bikeMinutes,
        metroMinutes,
        bestMinutes: Math.min(bikeMinutes, metroMinutes),
        destinationDistrict: destination.district,
      }};
    }}

    function getAiReviewState(listingId) {{
      return aiReviewJobs[listingId] || null;
    }}

    function setAiStatusMessage(message) {{
      aiStatusMessage = message || 'AI 會自動審核目前畫面上的候選房源。';
      els.aiStatus.textContent = aiStatusMessage;
    }}

    function hasAiReviewResult(item) {{
      return item.ai_cooking_confidence !== null && item.ai_cooking_confidence !== undefined;
    }}

    function shouldAutoReview(item) {{
      if (!item || !item.images || !item.images.length) return false;
      if (hasAiReviewResult(item)) return false;
      const state = getAiReviewState(item.id);
      return !state;
    }}

    function card(item) {{
      const image = item.cover
        ? `<button class="image-button" type="button" data-gallery-id="${{item.id}}"><img src="${{item.cover}}" alt="${{item.title}}" loading="lazy"></button>`
        : `<div class="placeholder">無圖片</div>`;
      const kitchen = item.cooking_convenience_label || '未提及';
      const floorArea = item.floor_area ? `${{item.floor_area}}坪` : '坪數待補';
      const commute = item.commute
        ? `估通勤 ${{item.commute.bestMinutes}} 分鐘 · 單車 ${{item.commute.bikeMinutes}} / 捷運 ${{item.commute.metroMinutes}}`
        : '未設定通勤目的地';
      const metroStation = item.nearest_metro_station
        ? `最近捷運：${{item.nearest_metro_station}}站 · 步行約 ${{item.nearest_metro_walk_minutes}} 分鐘`
        : '最近捷運：待補';
      const cookingReason = item.cooking_convenience_reason
        ? `可煮飯判斷：${{item.cooking_convenience_reason}}`
        : '可煮飯判斷：待補';
      const cookingConfidence = item.ai_cooking_confidence !== null && item.ai_cooking_confidence !== undefined
        ? `AI 信心：${{Math.round(Number(item.ai_cooking_confidence) * 100)}}%`
        : 'AI 信心：待補';
      const details = [
        item.detail_shortest_lease ? `最短租期：${{item.detail_shortest_lease}}` : '',
        item.detail_deposit ? `押金：${{item.detail_deposit}}` : '',
        item.detail_management_fee ? `管理費：${{item.detail_management_fee}}` : '',
      ].filter(Boolean).join(' · ');
      const galleryButton = item.images && item.images.length
        ? `<button type="button" data-gallery-id="${{item.id}}">看圖 ${{item.images.length}} 張</button>`
        : '';
      const aiReviewState = getAiReviewState(item.id);
      const aiReviewPending = aiReviewState && ['queued', 'running'].includes(aiReviewState.status);
      const aiReviewError = aiReviewState && aiReviewState.status === 'failed';
      const aiReviewStatus = aiReviewPending
        ? `AI 審核中：${{aiReviewState.message || '準備中'}}`
        : aiReviewError
          ? `AI 審核失敗：${{aiReviewState.error || aiReviewState.message || '請稍後再試'}}`
          : aiReviewState && aiReviewState.status === 'completed'
            ? `AI 已更新：${{aiReviewState.message || '完成'}}`
            : hasAiReviewResult(item)
              ? 'AI 已完成這筆看圖判斷'
              : item.images && item.images.length
                ? 'AI 會自動審核這筆房源'
                : '這筆房源沒有可供 AI 審核的圖片';
      const aiReviewButton = item.images && item.images.length
        ? `<button type="button" data-ai-review-id="${{item.id}}"${{aiReviewPending ? ' disabled' : ''}}>${{aiReviewPending ? 'AI 審核中...' : '立刻重跑 AI 審核'}}</button>`
        : '';
      const reviewStatus = reviewDecisions[item.id] || '';
      const reviewNote = reviewStatus === 'shortlist'
        ? '已標記：不錯，之後優先回看。'
        : reviewStatus === 'skip'
          ? '已標記：先略過，避免重複查看。'
          : '尚未標記。';
      const rules = item.detail_rules ? `<div class="rule">守則：${{item.detail_rules}}</div>` : '';
      const facilities = item.detail_facilities ? `<div class="facility">設備：${{item.detail_facilities}}</div>` : '';
      return `
        <article class="listing">
          <div>${{image}}</div>
          <div class="listing-main">
            <div class="listing-top">
              <span class="chip">來源 ${{item.platform}}</span>
              <span class="chip">${{item.district || '未知區域'}}</span>
              <span class="chip">可煮飯：${{kitchen}}</span>
            </div>
            <h3 class="title">${{item.title}}</h3>
            <div class="meta">${{formatNumber(item.price)}} 元 / 月 · ${{floorArea}} · ${{item.area || '路段待補'}}</div>
            <div class="meta-sub">${{commute}}</div>
            <div class="meta-sub">${{metroStation}}</div>
            <div class="meta-sub">${{cookingReason}}</div>
            <div class="meta-sub">${{cookingConfidence}}</div>
            <div class="meta-sub">${{aiReviewStatus}}</div>
            <div class="meta-sub">${{details || '細節待補'}}</div>
            <div class="desc">${{item.description || '目前沒有額外描述。'}}</div>
            ${{rules}}
            ${{facilities}}
            <div class="gallery-actions">${{galleryButton}}${{aiReviewButton}}</div>
            <div class="review-actions">
              <button class="shortlist" type="button" data-review-id="${{item.id}}" data-review-status="shortlist">不錯</button>
              <button class="skip" type="button" data-review-id="${{item.id}}" data-review-status="skip">先略過</button>
              <button type="button" data-review-id="${{item.id}}" data-review-status="clear">清除標記</button>
            </div>
            <div class="review-note">${{reviewNote}}</div>
            <div class="actions"><a href="${{item.url}}" target="_blank" rel="noreferrer">查看原始房源</a></div>
          </div>
        </article>
      `;
    }}

    function openGallery(listingId, startIndex = 0) {{
      const item = listings.find(candidate => candidate.id === listingId);
      if (!item || !item.images || !item.images.length) return;
      galleryState = {{ item, index: Math.max(0, Math.min(startIndex, item.images.length - 1)) }};
      renderGallery();
      els.galleryModal.classList.add('is-open');
      els.galleryModal.setAttribute('aria-hidden', 'false');
    }}

    function closeGallery() {{
      galleryState = null;
      els.galleryModal.classList.remove('is-open');
      els.galleryModal.setAttribute('aria-hidden', 'true');
      els.galleryImage.removeAttribute('src');
    }}

    function renderGallery() {{
      if (!galleryState) return;
      const {{ item, index }} = galleryState;
      els.galleryTitle.textContent = item.title || '圖片檢視';
      els.galleryCount.textContent = `${{index + 1}} / ${{item.images.length}}`;
      els.galleryImage.src = item.images[index];
      els.galleryCaption.textContent = item.cooking_convenience_reason
        ? `可煮飯判斷：${{item.cooking_convenience_reason}}`
        : '可煮飯判斷：待補';
      els.galleryPrev.disabled = item.images.length <= 1;
      els.galleryNext.disabled = item.images.length <= 1;
    }}

    function moveGallery(delta) {{
      if (!galleryState) return;
      const imageCount = galleryState.item.images.length;
      galleryState.index = (galleryState.index + delta + imageCount) % imageCount;
      renderGallery();
    }}

    function loadReviewDecisions() {{
      try {{
        const raw = window.localStorage.getItem(REVIEW_STORAGE_KEY);
        reviewDecisions = raw ? JSON.parse(raw) : {{}};
      }} catch (_error) {{
        reviewDecisions = {{}};
      }}
    }}

    function applyAiReviewResult(listingId, review) {{
      const item = listings.find(candidate => candidate.id === listingId);
      if (!item || !review) return;
      item.cooking_convenience_score = Number(review.score ?? item.cooking_convenience_score);
      item.cooking_convenience_label = review.label || item.cooking_convenience_label;
      item.cooking_convenience_reason = review.reason || item.cooking_convenience_reason;
      item.ai_cooking_confidence = review.confidence ?? item.ai_cooking_confidence;
      if (galleryState && galleryState.item && galleryState.item.id === listingId) {{
        renderGallery();
      }}
    }}

    async function pollAiReviewJob(jobId, listingId) {{
      while (true) {{
        const response = await fetch(`/api/ai-review-jobs/${{jobId}}`);
        const payload = await response.json();
        if (!response.ok) {{
          throw new Error(payload.error || '查詢 AI 進度失敗');
        }}
        aiReviewJobs[listingId] = payload;
        scheduleApplyFilters();

        if (payload.status === 'completed') {{
          applyAiReviewResult(listingId, payload.review);
          aiAutoReviewQueued.delete(listingId);
          setAiStatusMessage(`AI 已完成：${{listings.find(item => item.id === listingId)?.title || listingId}}`);
          scheduleApplyFilters();
          return;
        }}
        if (payload.status === 'failed') {{
          aiAutoReviewQueued.delete(listingId);
          setAiStatusMessage(`AI 失敗：${{payload.error || payload.message || listingId}}`);
          throw new Error(payload.error || payload.message || 'AI 看圖失敗');
        }}
        await new Promise(resolve => window.setTimeout(resolve, 1000));
      }}
    }}

    async function reviewListing(listingId, options = {{}}) {{
      const item = listings.find(candidate => candidate.id === listingId);
      if (!item || !item.images || !item.images.length) return;
      const current = getAiReviewState(listingId);
      const allowQueued = options.allowQueued === true;
      const isManual = options.manual === true;
      if (current && current.status === 'running') {{
        if (isManual) {{
          setAiStatusMessage(`這筆正在 AI 審核中：${{item.title}}`);
        }}
        return;
      }}
      if (current && current.status === 'queued' && !allowQueued) {{
        if (isManual) {{
          setAiStatusMessage(`這筆已排入 AI 審核隊列：${{item.title}}`);
          pumpAutoReviewQueue();
        }}
        return;
      }}

      aiReviewJobs[listingId] = {{
        ...(aiReviewJobs[listingId] || {{}}),
        job_id: '',
        listing_id: listingId,
        status: 'queued',
        message: options.initialMessage || '準備送出 AI 審核...',
        review: null,
        cached: false,
        error: '',
      }};
      setAiStatusMessage(options.initialMessage || `已送出 AI 審核：${{item.title}}`);
      scheduleApplyFilters();

      try {{
        const response = await fetch('/api/review-listing', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            input_path: sourceDatasetPath,
            listing_id: listingId,
          }}),
        }});
        const payload = await response.json();
        if (!response.ok) {{
          throw new Error(payload.error || '無法建立 AI 審核工作');
        }}
        aiReviewJobs[listingId] = {{
          ...aiReviewJobs[listingId],
          ...payload,
          status: payload.status || 'queued',
          message: options.startedMessage || 'AI 已接手看圖...',
        }};
        setAiStatusMessage(options.startedMessage || `AI 已開始看圖：${{item.title}}`);
        scheduleApplyFilters();
        await pollAiReviewJob(payload.job_id, listingId);
      }} catch (error) {{
        aiReviewJobs[listingId] = {{
          ...(aiReviewJobs[listingId] || {{ listing_id: listingId }}),
          status: 'failed',
          message: 'AI 看圖失敗',
          error: error.message,
        }};
        aiAutoReviewQueued.delete(listingId);
        setAiStatusMessage(`AI 看圖失敗：${{item.title}}`);
        scheduleApplyFilters();
      }}
    }}

    function enqueueAutoReview(listingId) {{
      if (aiAutoReviewQueued.has(listingId)) return;
      const item = listings.find(candidate => candidate.id === listingId);
      if (!shouldAutoReview(item)) return;

      aiAutoReviewQueued.add(listingId);
      aiReviewJobs[listingId] = {{
        job_id: '',
        listing_id: listingId,
        status: 'queued',
        message: '已自動排入 AI 審核隊列...',
        review: null,
        cached: false,
        error: '',
      }};
      aiAutoReviewQueue.push(listingId);
      scheduleApplyFilters();
      pumpAutoReviewQueue();
    }}

    function pumpAutoReviewQueue() {{
      while (aiReviewActiveCount < AI_AUTO_REVIEW_CONCURRENCY && aiAutoReviewQueue.length) {{
        const listingId = aiAutoReviewQueue.shift();
        const item = listings.find(candidate => candidate.id === listingId);
        if (!item || hasAiReviewResult(item)) {{
          aiAutoReviewQueued.delete(listingId);
          continue;
        }}

        aiReviewActiveCount += 1;
        reviewListing(listingId, {{
          allowQueued: true,
          manual: false,
          initialMessage: '準備啟動自動 AI 審核...',
          startedMessage: 'AI 已自動開始看圖...',
        }}).finally(() => {{
          aiReviewActiveCount = Math.max(0, aiReviewActiveCount - 1);
          pumpAutoReviewQueue();
        }});
      }}
    }}

    function scheduleVisibleAutoReviews() {{
      lastVisibleListingIds
        .slice(0, AI_AUTO_REVIEW_VISIBLE_LIMIT)
        .forEach(enqueueAutoReview);
    }}

    function saveReviewDecisions() {{
      try {{
        window.localStorage.setItem(REVIEW_STORAGE_KEY, JSON.stringify(reviewDecisions));
      }} catch (_error) {{
        // Ignore storage failures and keep the page usable.
      }}
    }}

    function shortlistedItems() {{
      return listings.filter(item => reviewDecisions[item.id] === 'shortlist');
    }}

    function skippedCount() {{
      return Object.values(reviewDecisions).filter(status => status === 'skip').length;
    }}

    function updateReviewSummary() {{
      shortlistedCount = shortlistedItems().length;
      els.countShortlist.textContent = String(shortlistedCount);
      els.exportShortlist.disabled = shortlistedCount === 0;
      els.exportStatus.textContent = shortlistedCount
        ? `已標記不錯 ${{shortlistedCount}} 筆，先略過 ${{skippedCount()}} 筆。`
        : '目前還沒有標記為不錯的房源。';
    }}

    function updateDebugConsole(filtered) {{
      const runningCount = Object.values(aiReviewJobs).filter(job => job.status === 'running').length;
      const queuedCount = Object.values(aiReviewJobs).filter(job => job.status === 'queued').length;
      const completedCount = Object.values(aiReviewJobs).filter(job => job.status === 'completed').length;
      const failedCount = Object.values(aiReviewJobs).filter(job => job.status === 'failed').length;
      const activeFilterSummary = [
        els.q.value ? `搜尋:${{els.q.value}}` : '',
        els.destination.value ? `目的地:${{els.destination.value}}` : '',
        els.district.value ? `行政區:${{els.district.value}}` : '',
        els.platform.value ? `來源:${{els.platform.value}}` : '',
        els.cookingLevel.value ? `煮飯門檻:${{els.cookingLevel.value}}` : '',
        els.hasImages.checked ? '只看有圖' : '',
        `排序:${{els.sortBy.value}}`,
      ].filter(Boolean).join(' · ');

      if (window.top !== window.self) {{
        window.parent.postMessage(
          {{
            type: 'rent-search-debug',
            dataset_name: sourceDatasetPath.split(/[\\\\/]/).pop() || sourceDatasetPath,
            dataset_path: sourceDatasetPath,
            visible_summary: `顯示 ${{filtered.length}} / 總共 ${{listings.length}} 筆`,
            filter_summary: activeFilterSummary || '目前沒有額外篩選條件',
            ai_queue_summary: `running ${{runningCount}} · queued ${{queuedCount}} · done ${{completedCount}} · failed ${{failedCount}}`,
            ai_status: aiStatusMessage,
            ai_usage_summary: aiUsageSummary.exists
              ? `input ${{formatNumber(aiUsageSummary.input_tokens)}} · cached ${{formatNumber(aiUsageSummary.cached_input_tokens)}} · output ${{formatNumber(aiUsageSummary.output_tokens)}} · entries ${{formatNumber(aiUsageSummary.entries)}}`
              : '目前沒有 AI usage 記錄',
            ai_last_summary: aiUsageSummary.last_listing_id
              ? `最近一筆：${{aiUsageSummary.last_listing_id}} @ ${{aiUsageSummary.last_timestamp || '未知時間'}}`
              : '最近一筆：尚無',
          }},
          '*',
        );
      }}
    }}

    function setReviewDecision(listingId, status) {{
      if (status === 'clear') {{
        delete reviewDecisions[listingId];
      }} else {{
        reviewDecisions[listingId] = status;
      }}
      saveReviewDecisions();
      updateReviewSummary();
      scheduleApplyFilters();
    }}

    async function exportShortlist() {{
      const items = shortlistedItems();
      if (!items.length) {{
        updateReviewSummary();
        return;
      }}

      els.exportShortlist.disabled = true;
      els.exportStatus.textContent = `正在匯出 ${{items.length}} 筆 shortlist...`;

      try {{
        const response = await fetch('/api/export-shortlist', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            input_path: sourceDatasetPath,
            destination: getDestinationQuery(),
            items,
          }}),
        }});
        const payload = await response.json();
        if (!response.ok) {{
          throw new Error(payload.error || '匯出 shortlist 失敗');
        }}
        els.exportStatus.textContent = `已匯出 ${{payload.count}} 筆 shortlist：${{payload.path}}`;
      }} catch (error) {{
        els.exportStatus.textContent = `匯出失敗：${{error.message}}`;
      }} finally {{
        updateReviewSummary();
      }}
    }}

    function calculateSearchSpeedScore(durationMs) {{
      if (durationMs <= SEARCH_SPEED_BUDGET_MS) return 100;
      if (durationMs >= SEARCH_SPEED_WARNING_MS) return 40;
      const span = SEARCH_SPEED_WARNING_MS - SEARCH_SPEED_BUDGET_MS;
      const penalty = (durationMs - SEARCH_SPEED_BUDGET_MS) / span;
      return Math.round(100 - penalty * 60);
    }}

    function searchSpeedLabel(durationMs) {{
      if (durationMs <= SEARCH_SPEED_BUDGET_MS) return '順暢';
      if (durationMs <= SEARCH_SPEED_WARNING_MS) return '可接受';
      return '偏慢';
    }}

    function searchSpeedHint(durationMs) {{
      if (durationMs <= SEARCH_SPEED_BUDGET_MS) return '目前搜尋速度在目標內。';
      if (durationMs <= SEARCH_SPEED_WARNING_MS) return '若想更快，可先縮小行政區、來源或租金範圍。';
      return '建議先縮小條件，或先用目的地刷新較小的資料池。';
    }}

    function applyFilters() {{
      const startedAt = performance.now();
      const q = els.q.value;
      const destination = resolveDestination(getDestinationQuery());
      const district = els.district.value;
      const platform = els.platform.value;
      const maxPrice = Number(els.maxPrice.value || 0);
      const minArea = Number(els.minArea.value || 0);
      const cookingLevel = Number(els.cookingLevel.value || 0);
      const hasImages = els.hasImages.checked;
      const sortBy = els.sortBy.value;

      let filtered = listings.filter(item => {{
        if (!matchesQuery(item, q)) return false;
        if (district && item.district !== district) return false;
        if (platform && item.platform !== platform) return false;
        if (maxPrice && item.price > maxPrice) return false;
        if (minArea && (!item.floor_area || item.floor_area < minArea)) return false;
        if (cookingLevel && item.cooking_convenience_score < cookingLevel) return false;
        if (hasImages && !item.cover) return false;
        return true;
      }});

      filtered = filtered.map(item => ({{
        ...item,
        commute: destination ? getCommuteEstimate(item, destination) : null,
      }}));

      filtered.sort((a, b) => {{
        if (sortBy === 'updated-desc') return (b.updated_at || '').localeCompare(a.updated_at || '');
        if (sortBy === 'cooking-desc' && a.cooking_convenience_score !== b.cooking_convenience_score) {{
          return b.cooking_convenience_score - a.cooking_convenience_score;
        }}
        if (destination && a.commute && b.commute && a.commute.bestMinutes !== b.commute.bestMinutes) {{
          return a.commute.bestMinutes - b.commute.bestMinutes;
        }}
        if (sortBy === 'price-desc') return b.price - a.price;
        if (sortBy === 'area-desc') return (b.floor_area || 0) - (a.floor_area || 0);
        return a.price - b.price;
      }});

      lastVisibleListingIds = filtered.map(item => item.id);
      els.results.innerHTML = filtered.map(card).join('');
      els.empty.hidden = filtered.length !== 0;
      els.countVisible.textContent = String(filtered.length);
      els.countPlatforms.textContent = String(new Set(filtered.map(item => item.platform)).size);
      els.countKitchen.textContent = String(filtered.filter(item => item.cooking_convenience_score >= 2).length);
      const avg = filtered.length ? Math.round(filtered.reduce((sum, item) => sum + item.price, 0) / filtered.length) : null;
      els.avgPrice.textContent = avg ? `${{formatNumber(avg)}} 元` : '-';
      const durationMs = performance.now() - startedAt;
      const speedScore = calculateSearchSpeedScore(durationMs);
      els.searchSpeed.textContent = `${{durationMs.toFixed(1)}}ms · ${{searchSpeedLabel(durationMs)}} · ${{speedScore}}分`;
      els.speedHint.textContent = searchSpeedHint(durationMs);
      updateDebugConsole(filtered);
      scheduleVisibleAutoReviews();
    }}

    function scheduleApplyFilters() {{
      if (filterFrame !== null) cancelAnimationFrame(filterFrame);
      filterFrame = requestAnimationFrame(() => {{
        filterFrame = null;
        applyFilters();
      }});
    }}

    function applyPreset(name) {{
      if (name === 'cooking-best') {{
        els.cookingLevel.value = '';
        els.hasImages.checked = true;
        els.sortBy.value = 'cooking-desc';
      }} else if (name === 'review-images') {{
        els.cookingLevel.value = '1';
        els.hasImages.checked = true;
        els.sortBy.value = 'cooking-desc';
      }} else if (name === 'reset') {{
        els.q.value = '';
        els.destination.value = '';
        els.district.value = '';
        els.platform.value = '';
        els.maxPrice.value = '';
        els.minArea.value = '';
        els.cookingLevel.value = '';
        els.hasImages.checked = false;
        els.sortBy.value = 'cooking-desc';
      }}
      scheduleApplyFilters();
    }}

    fillSelect(els.district, uniqueValues('district'));
    fillSelect(els.platform, uniqueValues('platform'));
    const initialQuery = pageParams.get('q');
    const initialDestination = pageParams.get('destination');
    if (initialQuery) els.q.value = initialQuery;
    if (initialDestination) els.destination.value = initialDestination;
    [els.q, els.destination, els.district, els.platform, els.maxPrice, els.minArea, els.cookingLevel, els.hasImages, els.sortBy]
      .forEach(el => el.addEventListener('input', scheduleApplyFilters));
    els.results.addEventListener('click', (event) => {{
      const aiReviewTrigger = event.target.closest('[data-ai-review-id]');
      if (aiReviewTrigger) {{
        reviewListing(aiReviewTrigger.getAttribute('data-ai-review-id'), {{ manual: true }});
        return;
      }}
      const reviewTrigger = event.target.closest('[data-review-id]');
      if (reviewTrigger) {{
        setReviewDecision(
          reviewTrigger.getAttribute('data-review-id'),
          reviewTrigger.getAttribute('data-review-status'),
        );
        return;
      }}
      const trigger = event.target.closest('[data-gallery-id]');
      if (!trigger) return;
      openGallery(trigger.getAttribute('data-gallery-id'));
    }});
    els.galleryPrev.addEventListener('click', () => moveGallery(-1));
    els.galleryNext.addEventListener('click', () => moveGallery(1));
    els.galleryClose.addEventListener('click', closeGallery);
    els.galleryModal.addEventListener('click', (event) => {{
      if (event.target === els.galleryModal) closeGallery();
    }});
    els.presetCookingBest.addEventListener('click', () => applyPreset('cooking-best'));
    els.presetReviewImages.addEventListener('click', () => applyPreset('review-images'));
    els.exportShortlist.addEventListener('click', exportShortlist);
    els.presetReset.addEventListener('click', () => applyPreset('reset'));
    document.addEventListener('keydown', (event) => {{
      if (!galleryState) return;
      if (event.key === 'Escape') closeGallery();
      if (event.key === 'ArrowLeft') moveGallery(-1);
      if (event.key === 'ArrowRight') moveGallery(1);
    }});
    loadReviewDecisions();
    setAiStatusMessage(aiStatusMessage);
    updateReviewSummary();
    applyFilters();
  </script>
</body>
</html>
"""


def export_search_app(input_path: str | Path, output_path: str | Path | None = None) -> Path:
    listings = prepare_listing_view_models(input_path)
    target = Path(output_path) if output_path else build_search_app_output_path(input_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    html_text = render_search_app_html(input_path, listings)
    target.write_text(html_text, encoding="utf-8")

    stable_target = build_default_search_app_path()
    stable_target.parent.mkdir(parents=True, exist_ok=True)
    if stable_target != target:
        stable_target.write_text(html_text, encoding="utf-8")
    return target


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="產生本地即時搜尋租屋頁面")
    parser.add_argument("--input", help="來源 CSV 路徑，預設使用最新資料集")
    parser.add_argument("--output", help="輸出 HTML 路徑")
    parser.add_argument("--open", action="store_true", help="產出後直接用瀏覽器開啟固定入口")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input) if args.input else latest_dataset_path()
    output_path = export_search_app(input_path, args.output)
    stable_path = build_default_search_app_path()
    if args.open:
        webbrowser.open(stable_path.resolve().as_uri())
    print(f"Search app: {output_path}")
    print(f"Stable entry: {stable_path}")
    print(f"Source dataset: {input_path}")


if __name__ == "__main__":
    main()
