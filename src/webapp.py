"""產生本地即時搜尋租屋頁面。"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from .analysis import (
    has_kitchen_sink_signal,
    latest_dataset_path,
    load_listings,
    parse_images,
)


def build_search_app_output_path(input_path: str | Path) -> Path:
    stem = Path(input_path).stem
    return Path("data") / f"{stem}_search_app.html"


def listing_to_view_model(row: dict[str, str]) -> dict[str, object]:
    images = parse_images(row.get("images"))
    return {
        "id": row.get("id", ""),
        "platform": row.get("platform", ""),
        "title": row.get("title", ""),
        "price": int(float(row.get("price") or 0)),
        "district": row.get("location_district", ""),
        "area": row.get("location_area", ""),
        "floor_area": float(row.get("floor_area")) if row.get("floor_area") else None,
        "room_type": row.get("room_type", ""),
        "description": row.get("description", ""),
        "url": row.get("url", ""),
        "images": images,
        "cover": images[0] if images else "",
        "kitchen_sink_signal": has_kitchen_sink_signal(row),
        "updated_at": row.get("updated_at", ""),
        "search_text": " ".join(
            part for part in [
                row.get("platform", ""),
                row.get("title", ""),
                row.get("location_district", ""),
                row.get("location_area", ""),
                row.get("room_type", ""),
                row.get("description", ""),
            ] if part
        ).lower(),
    }


def prepare_listing_view_models(input_path: str | Path) -> list[dict[str, object]]:
    rows = load_listings(input_path)
    return [listing_to_view_model(row) for row in rows]


def render_search_app_html(input_path: str | Path, listings: list[dict[str, object]]) -> str:
    source_name = html.escape(Path(input_path).name)
    listings_json = json.dumps(listings, ensure_ascii=False)
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
    .desc {{
      color: var(--muted);
      line-height: 1.7;
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      overflow: hidden;
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
      <p>不用再翻 CSV。這個頁面把最新資料池直接嵌進來，你可以即時輸入關鍵字、切來源、行政區、租金上限、坪數下限和流理臺需求，候選會立刻更新。</p>
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
          <input id="q" type="search" placeholder="輸入關鍵字、路名、捷運、物件特點…" />
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
          只看有流理臺 / 可開伙訊號
        </label>
        <label class="check">
          <input id="has-images" type="checkbox" />
          只看有圖片
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
          <div class="metric">有流理臺訊號<strong id="count-kitchen">0</strong></div>
          <div class="metric">平均月租<strong id="avg-price">-</strong></div>
        </div>
        <div id="results" class="results"></div>
        <div id="empty" class="empty" hidden>目前沒有符合條件的房源。</div>
      </section>
    </div>
  </main>

  <script>
    const listings = {listings_json};
    const els = {{
      q: document.getElementById('q'),
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
    }};

    const uniqueValues = (key) => [...new Set(listings.map(item => item[key]).filter(Boolean))].sort();

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

    function card(item) {{
      const image = item.cover
        ? `<img src="${{item.cover}}" alt="${{item.title}}" loading="lazy">`
        : `<div class="placeholder">無圖片</div>`;
      const kitchen = item.kitchen_sink_signal ? '有流理臺訊號' : '待確認';
      const floorArea = item.floor_area ? `${{item.floor_area}}坪` : '坪數待補';
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
            <div class="desc">${{item.description || '目前沒有額外描述。'}}</div>
            <div class="actions"><a href="${{item.url}}" target="_blank" rel="noreferrer">查看原始房源</a></div>
          </div>
        </article>
      `;
    }}

    function applyFilters() {{
      const q = els.q.value.trim().toLowerCase();
      const district = els.district.value;
      const platform = els.platform.value;
      const maxPrice = Number(els.maxPrice.value || 0);
      const minArea = Number(els.minArea.value || 0);
      const kitchenOnly = els.kitchenOnly.checked;
      const hasImages = els.hasImages.checked;
      const sortBy = els.sortBy.value;

      let filtered = listings.filter(item => {{
        if (q && !item.search_text.includes(q)) return false;
        if (district && item.district !== district) return false;
        if (platform && item.platform !== platform) return false;
        if (maxPrice && item.price > maxPrice) return false;
        if (minArea && (!item.floor_area || item.floor_area < minArea)) return false;
        if (kitchenOnly && !item.kitchen_sink_signal) return false;
        if (hasImages && !item.cover) return false;
        return true;
      }});

      filtered.sort((a, b) => {{
        if (sortBy === 'price-desc') return b.price - a.price;
        if (sortBy === 'area-desc') return (b.floor_area || 0) - (a.floor_area || 0);
        if (sortBy === 'updated-desc') return (b.updated_at || '').localeCompare(a.updated_at || '');
        return a.price - b.price;
      }});

      els.results.innerHTML = filtered.map(card).join('');
      els.empty.hidden = filtered.length !== 0;
      els.countVisible.textContent = String(filtered.length);
      els.countPlatforms.textContent = String(new Set(filtered.map(item => item.platform)).size);
      els.countKitchen.textContent = String(filtered.filter(item => item.kitchen_sink_signal).length);
      const avg = filtered.length ? Math.round(filtered.reduce((sum, item) => sum + item.price, 0) / filtered.length) : null;
      els.avgPrice.textContent = avg ? `${{formatNumber(avg)}} 元` : '-';
    }}

    fillSelect(els.district, uniqueValues('district'));
    fillSelect(els.platform, uniqueValues('platform'));
    [els.q, els.district, els.platform, els.maxPrice, els.minArea, els.kitchenOnly, els.hasImages, els.sortBy]
      .forEach(el => el.addEventListener('input', applyFilters));
    applyFilters();
  </script>
</body>
</html>
"""


def export_search_app(input_path: str | Path, output_path: str | Path | None = None) -> Path:
    listings = prepare_listing_view_models(input_path)
    target = Path(output_path) if output_path else build_search_app_output_path(input_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_search_app_html(input_path, listings), encoding="utf-8")
    return target


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="產生本地即時搜尋租屋頁面")
    parser.add_argument("--input", help="來源 CSV 路徑，預設使用最新資料集")
    parser.add_argument("--output", help="輸出 HTML 路徑")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input) if args.input else latest_dataset_path()
    output_path = export_search_app(input_path, args.output)
    print(f"Search app: {output_path}")
    print(f"Source dataset: {input_path}")


if __name__ == "__main__":
    main()

