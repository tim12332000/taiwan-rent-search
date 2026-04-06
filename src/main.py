"""執行租屋來源抓取並匯出 CSV。"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path

from .models import HousingData
from .scrapers.ddroom import DDRoomScraper
from .scrapers.fang591 import Fang591Scraper
from .scrapers.housefun import HousefunScraper
from .scrapers.mixrent import MixRentScraper


CSV_FIELDNAMES = [
    "id",
    "platform",
    "title",
    "price",
    "room_type",
    "bedrooms",
    "bathrooms",
    "floor_area",
    "floor",
    "description",
    "url",
    "scraped_at",
    "updated_at",
    "detail_shortest_lease",
    "detail_rules",
    "detail_included_fees",
    "detail_deposit",
    "detail_management_fee",
    "detail_parking_fee",
    "detail_property_registration",
    "detail_direction",
    "detail_owner_name",
    "detail_contact_phone",
    "detail_facilities",
    "location_county",
    "location_district",
    "location_area",
    "contact_name",
    "contact_phone",
    "contact_email",
    "images",
]


def sanitize_csv_value(value):
    """避免試算表把內容當成公式執行。"""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@"):
        return f"'{value}"
    return value


def export_to_csv(records: list[HousingData], output_path: str | Path) -> Path:
    """將房源列表寫入 CSV。空結果也會產生只有 header 的檔案。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for record in records:
            row = {
                key: sanitize_csv_value(value)
                for key, value in record.to_dict().items()
            }
            writer.writerow(row)

    return path


def build_output_path(county: str) -> Path:
    """建立本次輸出的預設 CSV 路徑。"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug_map = {
        "台北市": "taipei",
        "新北市": "newtaipei",
        "桃園市": "taoyuan",
        "台中市": "taichung",
        "台南市": "tainan",
        "高雄市": "kaohsiung",
    }
    slug = slug_map.get(county, "custom")
    return Path("data") / f"591_{slug}_{timestamp}.csv"


def build_multi_source_output_path(county: str, sources: list[str]) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug_map = {
        "台北市": "taipei",
        "新北市": "newtaipei",
        "桃園市": "taoyuan",
        "台中市": "taichung",
        "台南市": "tainan",
        "高雄市": "kaohsiung",
    }
    county_slug = slug_map.get(county, "custom")
    source_slug = "-".join(sorted(sources))
    return Path("data") / f"{source_slug}_{county_slug}_{timestamp}.csv"


def dedupe_records(records: list[HousingData]) -> list[HousingData]:
    seen_urls: set[tuple[str, str, int]] = set()
    seen_fingerprints: set[tuple[str, str, int]] = set()
    deduped: list[HousingData] = []
    for record in records:
        url_key = (record.url.strip(), record.title.strip(), record.price)
        fingerprint = (
            record.title.strip(),
            record.location.district.strip(),
            record.price,
        )
        if url_key in seen_urls or fingerprint in seen_fingerprints:
            continue
        seen_urls.add(url_key)
        seen_fingerprints.add(fingerprint)
        deduped.append(record)
    return deduped


def scrape_to_csv(county: str, output_path: str | Path | None = None, delay: float = 2.0) -> tuple[Path, list[HousingData]]:
    """抓取指定縣市並寫出 CSV。"""
    with Fang591Scraper(delay=delay) as scraper:
        records = scraper.scrape(county=county)

    target = Path(output_path) if output_path else build_output_path(county)
    path = export_to_csv(records, target)
    return path, records


def scrape_sources(
    sources: list[str],
    county: str,
    delay: float = 2.0,
    max_pages: int = 3,
    enrich_591_details: bool = False,
    enrich_591_detail_limit: int = 10,
) -> list[HousingData]:
    records: list[HousingData] = []
    for source in sources:
        if source == "591":
            with Fang591Scraper(delay=delay) as scraper:
                records.extend(
                    scraper.scrape(
                        county=county,
                        max_pages=max_pages,
                        enrich_details=enrich_591_details,
                        detail_limit=enrich_591_detail_limit,
                    )
                )
        elif source == "mixrent":
            with MixRentScraper(delay=delay) as scraper:
                records.extend(scraper.scrape(county=county, max_pages=max_pages))
        elif source == "housefun":
            with HousefunScraper(delay=delay) as scraper:
                records.extend(scraper.scrape(county=county, max_pages=max_pages))
        elif source == "ddroom":
            with DDRoomScraper(delay=delay) as scraper:
                records.extend(scraper.scrape(county=county, max_pages=max_pages))
        else:
            raise ValueError(f"Unsupported source: {source}")
    return dedupe_records(records)


def scrape_sources_to_csv(
    sources: list[str],
    county: str,
    output_path: str | Path | None = None,
    delay: float = 2.0,
    max_pages: int = 3,
    enrich_591_details: bool = False,
    enrich_591_detail_limit: int = 10,
) -> tuple[Path, list[HousingData]]:
    records = scrape_sources(
        sources=sources,
        county=county,
        delay=delay,
        max_pages=max_pages,
        enrich_591_details=enrich_591_details,
        enrich_591_detail_limit=enrich_591_detail_limit,
    )
    target = Path(output_path) if output_path else build_multi_source_output_path(county, sources)
    path = export_to_csv(records, target)
    return path, records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="抓取租屋來源並匯出 CSV")
    parser.add_argument("--county", default="台北市", help="要抓取的縣市名稱")
    parser.add_argument("--output", help="輸出 CSV 路徑")
    parser.add_argument("--delay", type=float, default=2.0, help="請求延遲秒數")
    parser.add_argument("--source", action="append", choices=["591", "mixrent", "housefun", "ddroom"], help="抓取來源，可重複傳入")
    parser.add_argument("--max-pages", type=int, default=3, help="每個支援分頁的來源最多抓幾頁")
    parser.add_argument("--enrich-591-details", action="store_true", help="補抓 591 詳頁資訊")
    parser.add_argument("--detail-limit", type=int, default=10, help="最多補抓幾筆 591 詳頁")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.source:
        path, records = scrape_sources_to_csv(
            sources=args.source,
            county=args.county,
            output_path=args.output,
            delay=args.delay,
            max_pages=args.max_pages,
            enrich_591_details=args.enrich_591_details,
            enrich_591_detail_limit=args.detail_limit,
        )
    else:
        path, records = scrape_to_csv(
            county=args.county,
            output_path=args.output,
            delay=args.delay,
        )
    print(f"CSV exported: {path}")
    print(f"Records: {len(records)}")


if __name__ == "__main__":
    main()
