"""產生本地即時搜尋租屋頁面。"""

from __future__ import annotations

import argparse
import html
import json
import webbrowser
from pathlib import Path

from .analysis import (
    TAIPEI_DISTRICT_CENTERS,
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


def listing_to_view_model(row: dict[str, str]) -> dict[str, object]:
    images = parse_images(row.get("images"))
    address = build_listing_address(row)
    center = district_center(row.get("location_district", ""))
    nearest_station = find_nearest_station(center.lat if center else None, center.lon if center else None)
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
    return [listing_to_view_model(row) for row in rows]


def render_search_app_html(input_path: str | Path, listings: list[dict[str, object]]) -> str:
    source_name = html.escape(Path(input_path).name)
    listings_json = json.dumps(listings, ensure_ascii=False)
    district_centers_json = json.dumps(TAIPEI_DISTRICT_CENTERS, ensure_ascii=False)
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
      <p>不用再翻 CSV。這個頁面把最新資料池直接嵌進來，你可以即時輸入關鍵字、切來源、行政區、租金上限、坪數下限和圖片條件，候選會立刻更新。</p>
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
        <label class="check">
          <input id="kitchen-only" type="checkbox" />
          只看文字明確提到流理臺
        </label>
        <label class="check">
          <input id="has-images" type="checkbox" />
          只看有圖片（方便手動看廚房）
        </label>
        <div class="field">
          <label for="sort-by">排序</label>
          <select id="sort-by">
            <option value="price-asc">租金由低到高</option>
            <option value="price-desc">租金由高到低</option>
            <option value="area-desc">坪數由大到小</option>
            <option value="updated-desc">更新時間由新到舊</option>
          </select>
        </div>
      </aside>

      <section>
        <div class="summary">
          <div class="metric">目前顯示<strong id="count-visible">0</strong></div>
          <div class="metric">資料來源<strong id="count-platforms">0</strong></div>
          <div class="metric">文字提及流理臺<strong id="count-kitchen">0</strong></div>
          <div class="metric">平均月租<strong id="avg-price">-</strong></div>
          <div class="metric">搜尋速度<strong id="search-speed">-</strong></div>
        </div>
        <div id="speed-hint" class="meta-sub">搜尋速度目標：{SEARCH_SPEED_BUDGET_MS}ms 內。</div>
        <div id="results" class="results"></div>
        <div id="empty" class="empty" hidden>目前沒有符合條件的房源。</div>
      </section>
    </div>
  </main>

  <script>
    const listings = {listings_json};
    const districtCenters = {district_centers_json};
    const pageParams = new URLSearchParams(window.location.search);
    const els = {{
      q: document.getElementById('q'),
      destination: document.getElementById('destination'),
      district: document.getElementById('district'),
      platform: document.getElementById('platform'),
      maxPrice: document.getElementById('max-price'),
      minArea: document.getElementById('min-area'),
      kitchenOnly: document.getElementById('kitchen-only'),
      hasImages: document.getElementById('has-images'),
      sortBy: document.getElementById('sort-by'),
      results: document.getElementById('results'),
      empty: document.getElementById('empty'),
      countVisible: document.getElementById('count-visible'),
      countPlatforms: document.getElementById('count-platforms'),
      countKitchen: document.getElementById('count-kitchen'),
      avgPrice: document.getElementById('avg-price'),
      searchSpeed: document.getElementById('search-speed'),
      speedHint: document.getElementById('speed-hint'),
    }};
    const SEARCH_SPEED_BUDGET_MS = {SEARCH_SPEED_BUDGET_MS};
    const SEARCH_SPEED_WARNING_MS = {SEARCH_SPEED_WARNING_MS};
    let filterFrame = null;

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

    function card(item) {{
      const image = item.cover
        ? `<img src="${{item.cover}}" alt="${{item.title}}" loading="lazy">`
        : `<div class="placeholder">無圖片</div>`;
      const kitchen = item.kitchen_sink_signal ? '文字提及流理臺' : '看圖確認';
      const floorArea = item.floor_area ? `${{item.floor_area}}坪` : '坪數待補';
      const commute = item.commute
        ? `估通勤 ${{item.commute.bestMinutes}} 分鐘 · 單車 ${{item.commute.bikeMinutes}} / 捷運 ${{item.commute.metroMinutes}}`
        : '未設定通勤目的地';
      const metroStation = item.nearest_metro_station
        ? `最近捷運：${{item.nearest_metro_station}}站 · 步行約 ${{item.nearest_metro_walk_minutes}} 分鐘`
        : '最近捷運：待補';
      const details = [
        item.detail_shortest_lease ? `最短租期：${{item.detail_shortest_lease}}` : '',
        item.detail_deposit ? `押金：${{item.detail_deposit}}` : '',
        item.detail_management_fee ? `管理費：${{item.detail_management_fee}}` : '',
      ].filter(Boolean).join(' · ');
      const rules = item.detail_rules ? `<div class="rule">守則：${{item.detail_rules}}</div>` : '';
      const facilities = item.detail_facilities ? `<div class="facility">設備：${{item.detail_facilities}}</div>` : '';
      return `
        <article class="listing">
          <div>${{image}}</div>
          <div class="listing-main">
            <div class="listing-top">
              <span class="chip">來源 ${{item.platform}}</span>
              <span class="chip">${{item.district || '未知區域'}}</span>
              <span class="chip">${{kitchen}}</span>
            </div>
            <h3 class="title">${{item.title}}</h3>
            <div class="meta">${{formatNumber(item.price)}} 元 / 月 · ${{floorArea}} · ${{item.area || '路段待補'}}</div>
            <div class="meta-sub">${{commute}}</div>
            <div class="meta-sub">${{metroStation}}</div>
            <div class="meta-sub">${{details || '細節待補'}}</div>
            <div class="desc">${{item.description || '目前沒有額外描述。'}}</div>
            ${{rules}}
            ${{facilities}}
            <div class="actions"><a href="${{item.url}}" target="_blank" rel="noreferrer">查看原始房源</a></div>
          </div>
        </article>
      `;
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
      const kitchenOnly = els.kitchenOnly.checked;
      const hasImages = els.hasImages.checked;
      const sortBy = els.sortBy.value;

      let filtered = listings.filter(item => {{
        if (!matchesQuery(item, q)) return false;
        if (district && item.district !== district) return false;
        if (platform && item.platform !== platform) return false;
        if (maxPrice && item.price > maxPrice) return false;
        if (minArea && (!item.floor_area || item.floor_area < minArea)) return false;
        if (kitchenOnly && !item.kitchen_sink_signal) return false;
        if (hasImages && !item.cover) return false;
        return true;
      }});

      filtered = filtered.map(item => ({{
        ...item,
        commute: destination ? getCommuteEstimate(item, destination) : null,
      }}));

      filtered.sort((a, b) => {{
        if (sortBy === 'updated-desc') return (b.updated_at || '').localeCompare(a.updated_at || '');
        if (destination && a.commute && b.commute && a.commute.bestMinutes !== b.commute.bestMinutes) {{
          return a.commute.bestMinutes - b.commute.bestMinutes;
        }}
        if (sortBy === 'price-desc') return b.price - a.price;
        if (sortBy === 'area-desc') return (b.floor_area || 0) - (a.floor_area || 0);
        return a.price - b.price;
      }});

      els.results.innerHTML = filtered.map(card).join('');
      els.empty.hidden = filtered.length !== 0;
      els.countVisible.textContent = String(filtered.length);
      els.countPlatforms.textContent = String(new Set(filtered.map(item => item.platform)).size);
      els.countKitchen.textContent = String(filtered.filter(item => item.kitchen_sink_signal).length);
      const avg = filtered.length ? Math.round(filtered.reduce((sum, item) => sum + item.price, 0) / filtered.length) : null;
      els.avgPrice.textContent = avg ? `${{formatNumber(avg)}} 元` : '-';
      const durationMs = performance.now() - startedAt;
      const speedScore = calculateSearchSpeedScore(durationMs);
      els.searchSpeed.textContent = `${{durationMs.toFixed(1)}}ms · ${{searchSpeedLabel(durationMs)}} · ${{speedScore}}分`;
      els.speedHint.textContent = searchSpeedHint(durationMs);
    }}

    function scheduleApplyFilters() {{
      if (filterFrame !== null) cancelAnimationFrame(filterFrame);
      filterFrame = requestAnimationFrame(() => {{
        filterFrame = null;
        applyFilters();
      }});
    }}

    fillSelect(els.district, uniqueValues('district'));
    fillSelect(els.platform, uniqueValues('platform'));
    const initialQuery = pageParams.get('q');
    const initialDestination = pageParams.get('destination');
    if (initialQuery) els.q.value = initialQuery;
    if (initialDestination) els.destination.value = initialDestination;
    [els.q, els.destination, els.district, els.platform, els.maxPrice, els.minArea, els.kitchenOnly, els.hasImages, els.sortBy]
      .forEach(el => el.addEventListener('input', scheduleApplyFilters));
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
