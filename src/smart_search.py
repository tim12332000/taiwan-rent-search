"""Destination-first refresh flow for the local rental search app."""

from __future__ import annotations

import argparse
import webbrowser
from pathlib import Path
from typing import Callable
from urllib.parse import urlencode

from .ai_cooking_review import review_dataset_images_in_place
from .analysis import extract_county_from_text, extract_district_from_text
from .local_site_state import resolve_running_local_site_base_url
from .main import scrape_sources_with_focus
from .webapp import build_default_search_app_path, export_search_app


DEFAULT_SOURCES = ["591", "mixrent", "housefun", "ddroom"]
ProgressCallback = Callable[[str, int | None, int | None, int | None], None]


def build_open_url(destination_address: str) -> str:
    running_site = resolve_running_local_site_base_url()
    if running_site:
        if not destination_address:
            return f"{running_site}/app"
        return f"{running_site}/app?{urlencode({'destination': destination_address})}"

    stable_path = build_default_search_app_path().resolve().as_uri()
    if not destination_address:
        return stable_path
    return f"{stable_path}?{urlencode({'destination': destination_address})}"


def refresh_search_for_destination(
    destination_address: str,
    county: str | None = None,
    sources: list[str] | None = None,
    output_path: str | Path | None = None,
    search_output_path: str | Path | None = None,
    delay: float = 1.5,
    base_max_pages: int = 3,
    focus_max_pages: int = 5,
    enrich_591_details: bool = True,
    enrich_591_detail_limit: int = 20,
    ai_review_max_listings: int = 8,
    ai_review_max_images: int = 3,
    progress_callback: ProgressCallback | None = None,
) -> tuple[Path, Path, int, str, str]:
    resolved_county = county or extract_county_from_text(destination_address, default="台北市") or "台北市"
    district = extract_district_from_text(destination_address) or ""
    selected_sources = sources or DEFAULT_SOURCES

    dataset_path, records = scrape_sources_with_focus(
        sources=selected_sources,
        county=resolved_county,
        destination_address=destination_address,
        output_path=output_path,
        delay=delay,
        base_max_pages=base_max_pages,
        focus_max_pages=focus_max_pages,
        enrich_591_details=enrich_591_details,
        enrich_591_detail_limit=enrich_591_detail_limit,
        progress_callback=progress_callback,
    )
    if ai_review_max_listings > 0 and ai_review_max_images > 0:
        try:
            if progress_callback:
                progress_callback("AI 看圖判斷中...", None, None, len(records))
            ai_summary = review_dataset_images_in_place(
                dataset_path=dataset_path,
                max_listings=ai_review_max_listings,
                max_images_per_listing=ai_review_max_images,
            )
            if progress_callback:
                progress_callback(
                    f"AI 看圖完成，本輪新判斷 {ai_summary['reviewed_count']} 筆，快取命中 {ai_summary['cached_count']} 筆",
                    None,
                    None,
                    len(records),
                )
        except Exception as exc:
            if progress_callback:
                progress_callback(f"AI 看圖略過：{exc}", None, None, len(records))
    if progress_callback:
        progress_callback("正在產生搜尋頁...", None, None, len(records))
    target_search_path = Path(search_output_path) if search_output_path else build_default_search_app_path()
    search_path = export_search_app(dataset_path, target_search_path)
    if progress_callback:
        progress_callback("搜尋頁已更新", None, None, len(records))
    return dataset_path, search_path, len(records), resolved_county, district


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="先輸入目的地，再更新資料池並開啟本地搜尋頁")
    parser.add_argument("--destination-address", required=True, help="目的地地址")
    parser.add_argument("--county", help="抓取縣市，預設由目的地推斷")
    parser.add_argument("--source", action="append", choices=DEFAULT_SOURCES, help="抓取來源，可重複傳入")
    parser.add_argument("--output", help="輸出 CSV 路徑")
    parser.add_argument("--delay", type=float, default=1.5, help="請求延遲秒數")
    parser.add_argument("--base-max-pages", type=int, default=3, help="全市資料池每個來源抓幾頁")
    parser.add_argument("--focus-max-pages", type=int, default=5, help="目的地加抓每個來源抓幾頁")
    parser.add_argument("--detail-limit", type=int, default=20, help="最多補抓幾筆 591 詳頁")
    parser.add_argument("--ai-review-max-listings", type=int, default=8, help="最多用 AI 看圖幾筆候選")
    parser.add_argument("--ai-review-max-images", type=int, default=3, help="每筆最多送幾張圖給 AI")
    parser.add_argument("--open", action="store_true", help="完成後直接開啟搜尋頁")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_path, search_path, record_count, county, district = refresh_search_for_destination(
        destination_address=args.destination_address,
        county=args.county,
        sources=args.source,
        output_path=args.output,
        delay=args.delay,
        base_max_pages=args.base_max_pages,
        focus_max_pages=args.focus_max_pages,
        enrich_591_detail_limit=args.detail_limit,
        ai_review_max_listings=args.ai_review_max_listings,
        ai_review_max_images=args.ai_review_max_images,
    )
    if args.open:
        webbrowser.open(build_open_url(args.destination_address))

    print(f"Destination: {args.destination_address}")
    print(f"County: {county}")
    print(f"District: {district or '未識別'}")
    print(f"Dataset: {dataset_path}")
    print(f"Search app: {search_path}")
    print(f"Records: {record_count}")


if __name__ == "__main__":
    main()
