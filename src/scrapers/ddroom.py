"""租租通 API 爬蟲。"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, List

from .base import BaseScraper
from ..models import Contact, HousingData, Location

logger = logging.getLogger(__name__)


class DDRoomScraper(BaseScraper):
    """從租租通公開搜尋 API 取得租屋物件。"""

    API_URL = "https://api.dd-room.com/api/v1/search"

    def __init__(self, delay: float = 1.5):
        super().__init__(name="DDRoom", delay=delay)

    def scrape(
        self,
        county: str = "台北市",
        district: str = "",
        keyword: str = "",
        max_pages: int = 1,
        **kwargs,
    ) -> List[HousingData]:
        search_keyword = keyword or f"{county}{district}".strip() or county
        logger.info("開始爬取 DDRoom - %s", search_keyword)

        try:
            listings = []
            page = 1
            last_page = 1
            while page <= min(last_page, max_pages):
                params = {
                    "category": "house",
                    "keyword": search_keyword,
                    "page": page,
                }
                response = self._fetch_url(self.API_URL, params=params)
                payload = response.json()
                search = payload.get("data", {}).get("search", {})
                last_page = int(search.get("last_page") or 1)
                items = search.get("items", [])
                for item in items:
                    listing = self._parse_item(item)
                    if listing:
                        listings.append(listing)
                page += 1
            logger.info("✓ 成功爬取 DDRoom %s 筆台北房源", len(listings))
            return listings
        except Exception as exc:
            logger.error("DDRoom 爬蟲錯誤: %s", exc)
            return []

    def _parse_item(self, item: dict[str, Any]) -> HousingData | None:
        address = item.get("address", {})
        city = address.get("city", "")
        if city not in {"台北市", "臺北市"}:
            return None

        object_id = item.get("object_id", "")
        if not object_id:
            return None

        pattern = item.get("pattern", {})
        images = [
            cover.get("image", {}).get("md")
            for cover in item.get("covers", [])
            if cover.get("image", {}).get("md")
        ]
        now = datetime.now()

        return HousingData(
            id=f"ddroom-{object_id}",
            platform="ddroom",
            title=item.get("title", ""),
            price=int(item.get("rent") or 0),
            location=Location(
                county="台北市",
                district=address.get("area", ""),
                area=address.get("road") or address.get("complete"),
            ),
            room_type=item.get("type_space_name", ""),
            bedrooms=int(pattern.get("bedroom") or 1),
            bathrooms=int(pattern.get("bathroom") or 1),
            floor_area=float(item.get("ping")) if item.get("ping") is not None else None,
            floor=f"{item.get('floor')}F" if item.get("floor") else None,
            contact=Contact(name=item.get("role") or "DDRoom"),
            images=images,
            description=" ".join(item.get("themes", [])),
            url=f"https://www.dd-room.com/object/{object_id}",
            scraped_at=now,
            updated_at=now,
        )


if __name__ == "__main__":
    print("✅ DDRoom 爬蟲模塊定義完成")
