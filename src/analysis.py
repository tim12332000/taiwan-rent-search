"""租屋條件分析與候選排序。"""

from __future__ import annotations

import argparse
import csv
import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import requests


TAIPEI_DISTRICT_CENTERS = {
    "中正區": (25.0324, 121.5199),
    "大同區": (25.0631, 121.5131),
    "中山區": (25.0683, 121.5336),
    "松山區": (25.0542, 121.5639),
    "大安區": (25.0260, 121.5437),
    "萬華區": (25.0270, 121.4979),
    "信義區": (25.0332, 121.5660),
    "士林區": (25.0928, 121.5195),
    "北投區": (25.1324, 121.5017),
    "內湖區": (25.0687, 121.5889),
    "南港區": (25.0320, 121.6068),
    "文山區": (24.9896, 121.5707),
}

KITCHEN_SINK_KEYWORDS = (
    "流理台",
    "流理臺",
    "廚房",
    "可開伙",
    "可炊",
    "開伙",
    "廚具",
    "瓦斯爐",
    "電磁爐",
    "ih爐",
    "洗手槽",
)

ANALYSIS_FIELDNAMES = [
    "rank",
    "score",
    "title",
    "price",
    "location_district",
    "location_area",
    "floor_area",
    "commute_best_minutes",
    "commute_bike_minutes",
    "commute_metro_minutes",
    "kitchen_sink_signal",
    "needs_image_review",
    "matched_reasons",
    "url",
]


def score_band(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    return "C"


@dataclass
class Coordinates:
    lat: float
    lon: float


@dataclass
class SearchCriteria:
    destination_address: str | None = None
    destination_lat: float | None = None
    destination_lon: float | None = None
    max_price: int | None = None
    min_area: float | None = None
    districts: list[str] = field(default_factory=list)
    required_keywords: list[str] = field(default_factory=list)
    excluded_keywords: list[str] = field(default_factory=list)
    require_kitchen_sink: bool = False
    strict_features: bool = False
    max_commute_minutes: int | None = None
    transport_mode: str = "either"
    top_k: int = 10


@dataclass
class AnalysisResult:
    row: dict[str, str]
    score: float
    commute_bike_minutes: int | None
    commute_metro_minutes: int | None
    commute_best_minutes: int | None
    kitchen_sink_signal: bool
    needs_image_review: bool
    matched_reasons: list[str]


class NominatimGeocoder:
    """以 Nominatim geocode 地址，並使用本地 cache 減少請求。"""

    SEARCH_URL = "https://nominatim.openstreetmap.org/search"

    def __init__(self, cache_path: str | Path = ".omx/geocode-cache.json"):
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        if self.cache_path.exists():
            self.cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
        else:
            self.cache = {}
        self._last_request_at = 0.0

    def geocode(self, query: str) -> Coordinates | None:
        if not query:
            return None

        if query in self.cache:
            data = self.cache[query]
            return Coordinates(lat=data["lat"], lon=data["lon"])

        elapsed = time.monotonic() - self._last_request_at
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)

        response = requests.get(
            self.SEARCH_URL,
            params={
                "q": query,
                "format": "jsonv2",
                "limit": 1,
                "countrycodes": "tw",
            },
            headers={"User-Agent": "taiwan-rent-search/0.1"},
            timeout=20,
        )
        response.raise_for_status()
        self._last_request_at = time.monotonic()
        payload = response.json()
        if not payload:
            return None

        coords = Coordinates(lat=float(payload[0]["lat"]), lon=float(payload[0]["lon"]))
        self.cache[query] = {"lat": coords.lat, "lon": coords.lon}
        self.cache_path.write_text(
            json.dumps(self.cache, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return coords


def latest_dataset_path(data_dir: str | Path = "data") -> Path:
    datasets = sorted(
        Path(data_dir).glob("591_*.csv"),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
        reverse=True,
    )
    if not datasets:
        raise FileNotFoundError("No dataset CSV found under data/.")
    return datasets[0]


def load_listings(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def normalize_text(text: str) -> str:
    return " ".join((text or "").lower().split())


def listing_text(row: dict[str, str]) -> str:
    parts = [
        row.get("title", ""),
        row.get("description", ""),
        row.get("location_district", ""),
        row.get("location_area", ""),
        row.get("room_type", ""),
    ]
    return normalize_text(" ".join(parts))


def parse_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def parse_int(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    return int(float(value))


def parse_images(value: str | None) -> list[str]:
    if not value:
        return []
    return [part for part in value.split(",") if part]


def has_kitchen_sink_signal(row: dict[str, str]) -> bool:
    text = listing_text(row)
    return any(keyword.lower() in text for keyword in KITCHEN_SINK_KEYWORDS)


def build_listing_address(row: dict[str, str]) -> str:
    return f"{row.get('location_county', '')}{row.get('location_district', '')}{row.get('location_area', '')}".strip()


def district_center(district: str) -> Coordinates | None:
    coords = TAIPEI_DISTRICT_CENTERS.get(district)
    if not coords:
        return None
    return Coordinates(lat=coords[0], lon=coords[1])


def extract_district_from_text(text: str | None) -> str | None:
    normalized = text or ""
    for district in TAIPEI_DISTRICT_CENTERS:
        if district in normalized:
            return district
    return None


def resolve_destination(criteria: SearchCriteria, geocoder: NominatimGeocoder | None) -> Coordinates | None:
    if criteria.destination_lat is not None and criteria.destination_lon is not None:
        return Coordinates(criteria.destination_lat, criteria.destination_lon)

    if criteria.destination_address and geocoder:
        try:
            coords = geocoder.geocode(criteria.destination_address)
            if coords:
                return coords
        except requests.RequestException:
            pass

    fallback_district = extract_district_from_text(criteria.destination_address)
    if fallback_district:
        return district_center(fallback_district)

    return None


def resolve_listing_coordinates(row: dict[str, str], geocoder: NominatimGeocoder | None) -> Coordinates | None:
    district = row.get("location_district", "")
    center = district_center(district)
    if center:
        return center

    address = build_listing_address(row)
    if geocoder and address:
        try:
            return geocoder.geocode(address)
        except requests.RequestException:
            return None

    return None


def haversine_km(origin: Coordinates, destination: Coordinates) -> float:
    radius = 6371.0
    lat1 = math.radians(origin.lat)
    lon1 = math.radians(origin.lon)
    lat2 = math.radians(destination.lat)
    lon2 = math.radians(destination.lon)

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def estimate_bike_minutes(distance_km: float) -> int:
    return math.ceil(distance_km * 4.2 + 4)


def estimate_metro_minutes(distance_km: float) -> int:
    return math.ceil(distance_km * 2.3 + 12)


def keyword_match_all(text: str, keywords: Iterable[str]) -> bool:
    return all(normalize_text(keyword) in text for keyword in keywords)


def keyword_match_any(text: str, keywords: Iterable[str]) -> bool:
    return any(normalize_text(keyword) in text for keyword in keywords)


def score_listing(
    row: dict[str, str],
    criteria: SearchCriteria,
    destination: Coordinates | None,
    geocoder: NominatimGeocoder | None = None,
) -> AnalysisResult | None:
    text = listing_text(row)
    price = parse_int(row.get("price"))
    area = parse_float(row.get("floor_area"))

    if criteria.districts and row.get("location_district") not in criteria.districts:
        return None
    if criteria.max_price is not None and price is not None and price > criteria.max_price:
        return None
    if criteria.min_area is not None and area is not None and area < criteria.min_area:
        return None
    if criteria.required_keywords and not keyword_match_all(text, criteria.required_keywords):
        return None
    if criteria.excluded_keywords and keyword_match_any(text, criteria.excluded_keywords):
        return None

    kitchen_sink = has_kitchen_sink_signal(row)
    needs_image_review = False
    if criteria.require_kitchen_sink and not kitchen_sink:
        if criteria.strict_features:
            return None
        needs_image_review = True

    commute_bike = None
    commute_metro = None
    commute_best = None
    if destination:
        origin = resolve_listing_coordinates(row, geocoder)
        if origin:
            distance_km = haversine_km(origin, destination)
            commute_bike = estimate_bike_minutes(distance_km)
            commute_metro = estimate_metro_minutes(distance_km)
            if criteria.transport_mode == "bike":
                commute_best = commute_bike
            elif criteria.transport_mode == "metro":
                commute_best = commute_metro
            else:
                commute_best = min(commute_bike, commute_metro)

    if criteria.max_commute_minutes is not None and commute_best is not None and commute_best > criteria.max_commute_minutes:
        return None

    score = 50.0
    reasons = []

    if commute_best is not None:
        score += max(0, 35 - min(commute_best, 35)) * 1.2
        reasons.append(f"estimated commute {commute_best} min")
    if price is not None:
        if criteria.max_price:
            score += max(0, (criteria.max_price - min(price, criteria.max_price)) / criteria.max_price * 15)
        else:
            score += max(0, 20 - min(price / 1000, 20))
        reasons.append(f"price {price}")
    if area is not None:
        score += min(area, 20) * 0.8
        reasons.append(f"area {area} ping")

    if kitchen_sink:
        score += 8
        reasons.append("kitchen sink signal detected")
    elif criteria.require_kitchen_sink:
        score -= 8
        reasons.append("kitchen sink not confirmed")

    image_count = len(parse_images(row.get("images")))
    if image_count:
        score += min(image_count, 8) * 0.8
        reasons.append(f"{image_count} images")

    score = max(0, min(100, round(score, 1)))

    return AnalysisResult(
        row=row,
        score=score,
        commute_bike_minutes=commute_bike,
        commute_metro_minutes=commute_metro,
        commute_best_minutes=commute_best,
        kitchen_sink_signal=kitchen_sink,
        needs_image_review=needs_image_review,
        matched_reasons=reasons,
    )


def analyze_listings(
    input_path: str | Path,
    criteria: SearchCriteria,
    geocoder: NominatimGeocoder | None = None,
) -> list[AnalysisResult]:
    rows = load_listings(input_path)
    destination = resolve_destination(criteria, geocoder)

    results = []
    for row in rows:
        analyzed = score_listing(row, criteria, destination, geocoder=geocoder)
        if analyzed:
            results.append(analyzed)

    return sorted(results, key=lambda result: result.score, reverse=True)


def build_analysis_output_path(input_path: str | Path) -> Path:
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    stem = Path(input_path).stem
    return Path("data") / f"{stem}_analysis_{timestamp}.csv"


def build_report_output_path(input_path: str | Path) -> Path:
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    stem = Path(input_path).stem
    return Path("data") / f"{stem}_shortlist_{timestamp}.md"


def export_analysis_results(results: list[AnalysisResult], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=ANALYSIS_FIELDNAMES)
        writer.writeheader()
        for idx, result in enumerate(results, 1):
            writer.writerow(
                {
                    "rank": idx,
                    "score": result.score,
                    "title": result.row.get("title", ""),
                    "price": result.row.get("price", ""),
                    "location_district": result.row.get("location_district", ""),
                    "location_area": result.row.get("location_area", ""),
                    "floor_area": result.row.get("floor_area", ""),
                    "commute_best_minutes": result.commute_best_minutes or "",
                    "commute_bike_minutes": result.commute_bike_minutes or "",
                    "commute_metro_minutes": result.commute_metro_minutes or "",
                    "kitchen_sink_signal": "yes" if result.kitchen_sink_signal else "no",
                    "needs_image_review": "yes" if result.needs_image_review else "no",
                    "matched_reasons": " | ".join(result.matched_reasons),
                    "url": result.row.get("url", ""),
                }
            )

    return path


def format_listing_line(result: AnalysisResult) -> str:
    district = result.row.get("location_district", "未知區域")
    area = result.row.get("location_area", "")
    price = result.row.get("price", "?")
    floor_area = result.row.get("floor_area", "") or "?"
    commute = result.commute_best_minutes if result.commute_best_minutes is not None else "n/a"
    kitchen = "已確認" if result.kitchen_sink_signal else "待確認" if result.needs_image_review else "無訊號"
    band = score_band(result.score)
    return (
        f"**{band}級** | {district} | {area} | ${price}/月 | {floor_area}坪 | "
        f"通勤 {commute} 分 | 流理臺 {kitchen}"
    )


def render_markdown_report(
    results: list[AnalysisResult],
    criteria: SearchCriteria,
    input_path: str | Path,
) -> str:
    direct = [result for result in results if not result.needs_image_review]
    review = [result for result in results if result.needs_image_review]

    lines = [
        "# 租屋快速瀏覽報告",
        "",
        f"- 來源資料: `{Path(input_path).name}`",
        f"- 候選總數: `{len(results)}`",
        f"- 目的地: `{criteria.destination_address or '未指定'}`",
        f"- 通勤模式: `{criteria.transport_mode}`",
        f"- 最長通勤: `{criteria.max_commute_minutes if criteria.max_commute_minutes is not None else '未限制'}`",
        f"- 流理臺需求: `{'需要' if criteria.require_kitchen_sink else '未要求'}`",
        "",
        "## 直接看",
    ]

    if direct:
        for idx, result in enumerate(direct, 1):
            lines.extend(
                [
                    f"{idx}. {format_listing_line(result)}",
                    f"   - {result.row.get('title', '')}",
                    f"   - 原因: {'；'.join(result.matched_reasons)}",
                    f"   - 連結: {result.row.get('url', '')}",
                ]
            )
    else:
        lines.append("目前沒有完全符合且已確認必要條件的物件。")

    lines.extend(["", "## 待看圖確認"])
    if review:
        for idx, result in enumerate(review, 1):
            lines.extend(
                [
                    f"{idx}. {format_listing_line(result)}",
                    f"   - {result.row.get('title', '')}",
                    f"   - 原因: {'；'.join(result.matched_reasons)}",
                    f"   - 連結: {result.row.get('url', '')}",
                ]
            )
    else:
        lines.append("目前沒有需要額外看圖確認的物件。")

    return "\n".join(lines) + "\n"


def export_markdown_report(
    results: list[AnalysisResult],
    criteria: SearchCriteria,
    input_path: str | Path,
    output_path: str | Path,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    report = render_markdown_report(results, criteria, input_path)
    path.write_text(report, encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="分析租屋 CSV 並輸出候選排序")
    parser.add_argument("--input", help="來源 CSV 路徑，預設使用 data/ 最新 591 檔")
    parser.add_argument("--output", help="輸出分析 CSV 路徑")
    parser.add_argument("--destination-address", help="目的地地址，用於估算通勤")
    parser.add_argument("--destination-lat", type=float, help="目的地緯度")
    parser.add_argument("--destination-lon", type=float, help="目的地經度")
    parser.add_argument("--max-price", type=int, help="最高月租")
    parser.add_argument("--min-area", type=float, help="最低坪數")
    parser.add_argument("--district", action="append", default=[], help="限定行政區，可重複傳入")
    parser.add_argument("--require-keyword", action="append", default=[], help="必須出現在文本中的關鍵字")
    parser.add_argument("--exclude-keyword", action="append", default=[], help="排除關鍵字")
    parser.add_argument("--require-kitchen-sink", action="store_true", help="偏好有流理臺/可開伙訊號")
    parser.add_argument("--strict-features", action="store_true", help="必要設施未確認時直接排除")
    parser.add_argument("--max-commute", type=int, help="最長可接受通勤分鐘數")
    parser.add_argument("--transport-mode", choices=["either", "metro", "bike"], default="either")
    parser.add_argument("--top", type=int, default=10, help="輸出前幾筆")
    parser.add_argument("--report-output", help="輸出 Markdown 報告路徑")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input) if args.input else latest_dataset_path()
    criteria = SearchCriteria(
        destination_address=args.destination_address,
        destination_lat=args.destination_lat,
        destination_lon=args.destination_lon,
        max_price=args.max_price,
        min_area=args.min_area,
        districts=args.district,
        required_keywords=args.require_keyword,
        excluded_keywords=args.exclude_keyword,
        require_kitchen_sink=args.require_kitchen_sink,
        strict_features=args.strict_features,
        max_commute_minutes=args.max_commute,
        transport_mode=args.transport_mode,
        top_k=args.top,
    )

    geocoder = NominatimGeocoder() if criteria.destination_address else None
    results = analyze_listings(input_path, criteria, geocoder=geocoder)
    top_results = results[: criteria.top_k]
    output_path = Path(args.output) if args.output else build_analysis_output_path(input_path)
    report_path = Path(args.report_output) if args.report_output else build_report_output_path(input_path)
    export_analysis_results(top_results, output_path)
    export_markdown_report(top_results, criteria, input_path, report_path)

    print(f"Analysis CSV: {output_path}")
    print(f"Shortlist report: {report_path}")
    print(f"Matched listings: {len(results)}")
    for idx, result in enumerate(top_results, 1):
        print(
            f"{idx}. {result.row.get('title', '')} | "
            f"score={result.score} | "
            f"district={result.row.get('location_district', '')} | "
            f"price={result.row.get('price', '')} | "
            f"commute={result.commute_best_minutes if result.commute_best_minutes is not None else 'n/a'}"
        )


if __name__ == "__main__":
    main()
