"""Dedicated workspace flow for 台北市信義區松仁路100號."""

from __future__ import annotations

import argparse
import json
import webbrowser

from .analysis import extract_county_from_text, extract_district_from_text
from .case_workspace import (
    build_case_current_dataset_path,
    build_case_dir,
    build_case_search_app_path,
    build_case_snapshot_dataset_path,
    ensure_case_workspace,
    sync_case_current_dataset,
)
from .smart_search import build_open_url, refresh_search_for_destination


CASE_SLUG = "songren_100"
DESTINATION_ADDRESS = "台北市信義區松仁路100號"


def refresh_songren_100_case(
    *,
    base_dir: str = "data/cases",
    open_browser: bool = False,
    base_max_pages: int = 3,
    focus_max_pages: int = 5,
    detail_limit: int = 20,
) -> dict[str, str | int]:
    county = extract_county_from_text(DESTINATION_ADDRESS, default="台北市") or "台北市"
    district = extract_district_from_text(DESTINATION_ADDRESS) or ""
    case_dir = ensure_case_workspace(
        CASE_SLUG,
        destination_address=DESTINATION_ADDRESS,
        county=county,
        district=district,
        base_dir=base_dir,
    )
    snapshot_dataset = build_case_snapshot_dataset_path(CASE_SLUG, base_dir)
    case_search_app = build_case_search_app_path(CASE_SLUG, base_dir)

    dataset_path, search_path, record_count, _, _ = refresh_search_for_destination(
        destination_address=DESTINATION_ADDRESS,
        output_path=snapshot_dataset,
        search_output_path=case_search_app,
        base_max_pages=base_max_pages,
        focus_max_pages=focus_max_pages,
        enrich_591_detail_limit=detail_limit,
    )
    current_dataset = sync_case_current_dataset(dataset_path, case_slug=CASE_SLUG, base_dir=base_dir)
    summary = {
        "case_dir": str(case_dir),
        "destination_address": DESTINATION_ADDRESS,
        "dataset_snapshot": str(dataset_path),
        "dataset_current": str(current_dataset),
        "search_app": str(search_path),
        "records": record_count,
    }
    (case_dir / "latest_run.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if open_browser:
        webbrowser.open(build_open_url(DESTINATION_ADDRESS))

    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="更新松仁路 100 號案例工作區")
    parser.add_argument("--base-dir", default="data/cases", help="案例資料夾根目錄")
    parser.add_argument("--base-max-pages", type=int, default=3, help="全市基礎資料池每來源頁數")
    parser.add_argument("--focus-max-pages", type=int, default=5, help="目的地加抓每來源頁數")
    parser.add_argument("--detail-limit", type=int, default=20, help="591 詳頁補抓數量")
    parser.add_argument("--open", action="store_true", help="完成後直接開啟本機搜尋頁")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = refresh_songren_100_case(
        base_dir=args.base_dir,
        open_browser=args.open,
        base_max_pages=args.base_max_pages,
        focus_max_pages=args.focus_max_pages,
        detail_limit=args.detail_limit,
    )
    print(f"Case dir: {summary['case_dir']}")
    print(f"Destination: {summary['destination_address']}")
    print(f"Snapshot: {summary['dataset_snapshot']}")
    print(f"Current dataset: {summary['dataset_current']}")
    print(f"Search app: {summary['search_app']}")
    print(f"Records: {summary['records']}")


if __name__ == "__main__":
    main()
