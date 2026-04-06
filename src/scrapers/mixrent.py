"""MixRent 聚合租屋搜尋爬蟲。"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import List
from urllib.parse import quote_plus

from .base import BaseScraper
from ..models import Contact, HousingData, Location

logger = logging.getLogger(__name__)


TAIPEI_DISTRICTS = (
    "中正區",
    "大同區",
    "中山區",
    "松山區",
    "大安區",
    "萬華區",
    "信義區",
    "士林區",
    "北投區",
    "內湖區",
    "南港區",
    "文山區",
)


class MixRentScraper(BaseScraper):
    """抓取 MixRent 聚合搜尋結果。"""

    BASE_URL = "https://tw.mixrent.com"

    def __init__(self, delay: float = 1.5):
        super().__init__(name="MixRent", delay=delay)

    def scrape(self, county: str = "台北市", district: str = "", query: str = "", **kwargs) -> List[HousingData]:
        search_term = query or f"{county}{district}".strip() or "台北市"
        search_url = self._build_search_url(search_term)
        logger.info(f"開始爬取 MixRent - {search_term}")

        try:
            response = self._fetch_url(search_url)
            soup = self._parse_html(response.text)
            items = soup.select("div.rental_result")
            listings = []

            for item in items:
                data = self._parse_item(item, fallback_county=county)
                if data:
                    listings.append(data)

            logger.info(f"✓ 成功爬取 MixRent {len(listings)} 筆房源")
            return listings
        except Exception as exc:
            logger.error(f"MixRent 爬蟲錯誤: {exc}")
            return []

    def _build_search_url(self, search_term: str) -> str:
        return f"{self.BASE_URL}/search.php?q={quote_plus(search_term)}"

    def _parse_item(self, item, fallback_county: str = "台北市") -> HousingData | None:
        title_node = item.select_one("a.house_title")
        if not title_node:
            return None

        title = title_node.get_text(" ", strip=True)
        url = title_node.get("href", "")
        address = item.select_one("div.house_address")
        description = item.select_one("div.house_description")
        labels = [label.get_text(" ", strip=True) for label in item.select("ul.feature_list li")]
        source_name = title_node.get("name", "").strip() or self._extract_source_name(item)

        description_text = description.get_text(" ", strip=True) if description else ""
        address_text = address.get_text(" ", strip=True) if address else ""
        location = self._parse_location_text(address_text, description_text, fallback_county=fallback_county)
        if location.county != "台北市" or not location.district:
            return None

        area = self._extract_floor_area(labels, description_text)
        price = self._extract_price(" ".join(labels))
        room_type = self._extract_room_type(description_text)
        bedrooms, bathrooms = self._extract_room_counts(description_text, room_type)
        now = datetime.now()

        listing_id = self._build_listing_id(url, title, price)
        return HousingData(
            id=listing_id,
            platform="mixrent",
            title=title,
            price=price,
            location=location,
            room_type=room_type,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            floor_area=area,
            floor=self._extract_floor(description_text),
            contact=Contact(name=source_name or "MixRent"),
            images=[],
            description=description_text,
            url=url,
            scraped_at=now,
            updated_at=now,
        )

    @staticmethod
    def _build_listing_id(url: str, title: str, price: int) -> str:
        token = url.rstrip("/").split("/")[-1] if url else ""
        if token:
            return f"mixrent-{token}"
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        return f"mixrent-{slug or 'unknown'}-{price}"

    @staticmethod
    def _extract_source_name(item) -> str:
        house_url = item.select_one("div.house_url")
        if not house_url:
            return ""
        text = house_url.get_text(" ", strip=True)
        if "-" in text:
            return text.split("-", 1)[0].strip()
        return text

    @staticmethod
    def _extract_floor_area(labels: list[str], description: str) -> float | None:
        for text in labels + [description]:
            if "坪" not in text:
                continue
            match = re.search(r"(\d+(?:\.\d+)?)\s*坪", text)
            if match:
                return float(match.group(1))
        return None

    @staticmethod
    def _extract_room_type(description: str) -> str:
        for pattern in (r"(\d+\s*房)", r"(套房|雅房|整層住家|分租套房|獨立套房)"):
            match = re.search(pattern, description)
            if match:
                return match.group(1).replace(" ", "")
        return ""

    @staticmethod
    def _extract_room_counts(description: str, room_type: str) -> tuple[int, int]:
        bedroom = 1
        bathroom = 1
        text = f"{room_type} {description}"
        bed_match = re.search(r"(\d+)\s*房", text)
        bath_match = re.search(r"(\d+)\s*衛", text)
        if bed_match:
            bedroom = int(bed_match.group(1))
        if bath_match:
            bathroom = int(bath_match.group(1))
        return bedroom, bathroom

    @staticmethod
    def _extract_floor(description: str) -> str | None:
        match = re.search(r"(\d+F/\d+F)", description)
        return match.group(1) if match else None

    @staticmethod
    def _extract_price(text: str) -> int:
        match = re.search(r"\$\s*(\d+)", text.replace(",", ""))
        return int(match.group(1)) if match else 0

    @staticmethod
    def _parse_location_text(address: str, description: str, fallback_county: str = "台北市") -> Location:
        combined = f"{address} {description}"
        if not combined.strip():
            return Location(county="", district="", area=None)

        county = "台北市" if "台北市" in combined else ""
        district = ""
        area = None

        for candidate in TAIPEI_DISTRICTS:
            if candidate not in combined:
                continue
            district = candidate
            tail_match = re.search(rf"{re.escape(candidate)}[-－]?(?P<area>[^\s，,]+)", combined)
            if tail_match:
                area = tail_match.group("area")
            break

        if not district:
            return Location(county=county, district="", area=None)

        return Location(county=county, district=district, area=area)


if __name__ == "__main__":
    print("✅ MixRent 爬蟲模塊定義完成")
