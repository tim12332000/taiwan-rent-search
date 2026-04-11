"""591房屋爬蟲"""

import re
from datetime import datetime
from typing import List
import logging
from urllib.parse import urlencode
from dataclasses import replace

from .base import BaseScraper
from ..models import HousingData, Location, Contact

logger = logging.getLogger(__name__)


class Fang591Scraper(BaseScraper):
    """591房屋爬蟲"""

    BASE_URL = "https://rent.591.com.tw"
    REGION_CODES = {
        "台北市": "1",
        "新北市": "3",
        "桃園市": "6",
        "台中市": "8",
        "台南市": "15",
        "高雄市": "17",
    }

    def __init__(self, delay: float = 2.0):
        super().__init__(name="591房屋", delay=delay)

    def scrape(
        self,
        county: str = "",
        district: str = "",
        max_pages: int = 1,
        enrich_details: bool = False,
        detail_limit: int = 10,
        **kwargs,
    ) -> List[HousingData]:
        """
        爬取591房屋數據
        
        Args:
            county: 縣市名稱（如："台北市"）
            district: 鄰近地區
            
        Returns:
            HousingData 列表
        """
        logger.info(f"開始爬取591房屋 - {county} {district}")
        
        try:
            housing_list = []
            for page in range(1, max_pages + 1):
                search_url = self._build_search_url(county, district, page=page)
                response = self._fetch_url(search_url)
                html = response.text
                soup = self._parse_html(html)

                items = soup.select("div.recommend-ware")
                if not items:
                    items = soup.find_all("div", class_="item")

                if not items:
                    if page == 1:
                        logger.warning("未找到房源卡片，可能需要Selenium")
                    break

                for item in items:
                    try:
                        data = self._parse_item(item, fallback_county=county)
                        if data:
                            housing_list.append(data)
                    except Exception as e:
                        logger.warning(f"解析房源失敗: {e}")
                        continue
            
            if enrich_details and housing_list:
                housing_list = self.enrich_listings(housing_list, limit=detail_limit)

            logger.info(f"✓ 成功爬取 {len(housing_list)} 筆房源")
            return housing_list
            
        except Exception as e:
            logger.error(f"爬蟲錯誤: {e}")
            return []

    def _build_search_url(self, county: str = "", district: str = "", page: int = 1) -> str:
        """構建搜索URL"""
        url = f"{self.BASE_URL}/list"
        params = {
            'kind': 2,  # 2 = 租屋
        }
        
        if county:
            params['region'] = self._map_county_code(county)
        if page > 1:
            params["page"] = page
        
        return f"{url}?{urlencode(params)}"

    @staticmethod
    def _map_county_code(county: str) -> str:
        """縣市代碼對應"""
        return Fang591Scraper.REGION_CODES.get(county, "")

    def _parse_item(self, item, fallback_county: str = "") -> HousingData | None:
        """解析單一房源"""
        try:
            title_link = item.select_one("a.title") or item.find("a", class_="item-link")
            title_node = item.find("h3", class_="item-title") or title_link
            if not title_node:
                return None

            title_text = title_node.get_text(" ", strip=True)

            price_elem = item.select_one("span.price") or item.find("span", class_="price")
            price = self._extract_price(price_elem.get_text() if price_elem else "")

            address_text = self._extract_address_text(item)
            location = self._parse_location(address_text, fallback_county=fallback_county)
            room_type = self._extract_room_type(item)

            info_text = item.get_text(" ", strip=True)
            bedroom, bathroom = self._extract_room_counts(info_text, room_type)
            floor_area = self._extract_floor_area(item)
            images = self._extract_images(item)
            url = self._extract_url(title_link)
            contact_name = item.select_one("span.name") or item.find("span", class_="name")
            contact_name_text = contact_name.get_text(strip=True) if contact_name else "未公開"

            now = datetime.now()
            
            data = HousingData(
                id=f"591-{url.split('/')[-1]}" if url else "591-unknown",
                platform="591",
                title=title_text,
                price=price,
                location=location,
                room_type=room_type,
                bedrooms=bedroom,
                bathrooms=bathroom,
                floor_area=floor_area,
                floor=None,
                contact=Contact(name=contact_name_text),
                images=images,
                description=info_text[:200],
                url=url,
                scraped_at=now,
                updated_at=now
            )
            
            return data
            
        except Exception as e:
            logger.debug(f"解析失敗: {e}")
            return None

    def _extract_address_text(self, item) -> str:
        """提取地址文本，優先處理現行列表卡片。"""
        address = item.select_one("span.address") or item.find("span", class_="location")
        if not address:
            return ""

        address_text = address.get_text(" ", strip=True)
        community = item.select_one("span.community")
        if community:
            community_text = community.get_text(" ", strip=True)
            if address_text.startswith(community_text):
                address_text = address_text[len(community_text):].strip()

        return " ".join(address_text.split())

    def _extract_room_type(self, item) -> str:
        """提取房型或主房間摘要。"""
        room_type = item.find("span", class_="room-type")
        if room_type:
            return room_type.get_text(" ", strip=True)

        area_spans = item.select("div.address-info span.area")
        for span in area_spans:
            text = span.get_text(" ", strip=True).rstrip("/")
            if "房" in text:
                return text

        return ""

    def _extract_floor_area(self, item) -> float | None:
        """提取坪數。"""
        area_spans = item.select("div.address-info span.area")
        for span in area_spans:
            text = span.get_text(" ", strip=True)
            if "坪" not in text:
                continue
            match = re.search(r"(\d+(?:\.\d+)?)", text)
            if match:
                return float(match.group(1))
        return None

    def _extract_images(self, item) -> List[str]:
        """提取圖片連結，過濾 placeholder。"""
        images = []
        for img in item.select("img"):
            candidate = img.get("data-src") or img.get("src")
            if not candidate or candidate.startswith("data:image/"):
                continue
            if candidate not in images:
                images.append(candidate)
        return images

    def enrich_listings(self, listings: List[HousingData], limit: int = 10) -> List[HousingData]:
        """補抓前 N 筆 591 詳頁資訊。"""
        enriched: list[HousingData] = []
        for idx, listing in enumerate(listings):
            if idx >= limit or not listing.url:
                enriched.append(listing)
                continue
            try:
                detail = self.fetch_detail(listing.url)
                enriched.append(self.merge_detail(listing, detail))
            except Exception as exc:
                logger.warning(f"補抓 591 詳頁失敗 {listing.url}: {exc}")
                enriched.append(listing)
        return enriched

    def fetch_detail(self, url: str) -> dict[str, object]:
        """抓取並解析 591 詳頁。"""
        response = self._fetch_url(url)
        return self.parse_detail_html(response.text)

    def parse_detail_html(self, html: str) -> dict[str, object]:
        """從 591 詳頁 HTML 提取補強資訊。"""
        soup = self._parse_html(html)

        info_board = soup.select_one("section.block.info-board")
        service = soup.select_one("section.block.service")
        house_detail = soup.select_one("section.block.house-detail")
        owner_note = soup.select_one("section.block.house-condition")

        result: dict[str, object] = {
            "detail_shortest_lease": None,
            "detail_rules": None,
            "detail_included_fees": None,
            "detail_deposit": None,
            "detail_management_fee": None,
            "detail_parking_fee": None,
            "detail_property_registration": None,
            "detail_direction": None,
            "detail_owner_name": None,
            "detail_contact_phone": None,
            "detail_facilities": [],
            "room_type": None,
            "bedrooms": None,
            "bathrooms": None,
            "floor_area": None,
            "floor": None,
            "description": None,
        }

        if info_board:
            pattern = info_board.select_one("div.pattern")
            if pattern:
                parts = [span.get_text(" ", strip=True) for span in pattern.select("span") if span.get_text(" ", strip=True) and span.get_text(" ", strip=True) != "|"]
                if parts:
                    result["room_type"] = parts[0]
                pattern_text = " ".join(parts)
                if pattern_text:
                    bedroom, bathroom = self._extract_room_counts(pattern_text, result["room_type"] or "")
                    if "房" in pattern_text or result["room_type"]:
                        result["bedrooms"] = bedroom
                    if "衛" in pattern_text:
                        result["bathrooms"] = bathroom
                for part in parts:
                    if "坪" in part and result["floor_area"] is None:
                        match = re.search(r"(\d+(?:\.\d+)?)", part)
                        if match:
                            result["floor_area"] = float(match.group(1))
                    floor_text = self._extract_floor_from_detail_text(part)
                    if floor_text:
                        result["floor"] = floor_text

            labels = [span.get_text(" ", strip=True) for span in info_board.select("div.house-label span.label-item") if span.get_text(" ", strip=True)]
            if labels:
                result["description"] = " ".join(labels)

        if service:
            cates = service.select("div.service-cate")
            for cate in cates:
                label = cate.select_one("p")
                value = cate.select_one("span")
                label_text = label.get_text(" ", strip=True) if label else ""
                value_text = value.get_text(" ", strip=True) if value else ""
                if label_text == "租住說明":
                    result["detail_shortest_lease"] = value_text
                elif label_text == "房屋守則":
                    result["detail_rules"] = value_text

            facilities = [dd.get_text(" ", strip=True) for dd in service.select("div.facility.service-facility dd.text")]
            result["detail_facilities"] = facilities

        if house_detail:
            for item in house_detail.select("div.item"):
                label = item.select_one("span.label")
                value = item.select_one("span.value")
                label_text = label.get_text(" ", strip=True) if label else ""
                value_text = value.get_text(" ", strip=True) if value else ""
                if label_text == "租金含":
                    result["detail_included_fees"] = value_text
                elif label_text == "押金":
                    result["detail_deposit"] = value_text
                elif label_text == "管理費":
                    result["detail_management_fee"] = value_text
                elif label_text == "車位費":
                    result["detail_parking_fee"] = value_text
                elif label_text == "產權登記":
                    result["detail_property_registration"] = value_text
                elif label_text == "朝向":
                    result["detail_direction"] = value_text

        if owner_note:
            owner_text = owner_note.get_text(" ", strip=True)
            owner_match = re.search(r"屋主[:：]\s*([^\s]+)", owner_text)
            phone_match = re.search(r"09\d{2}[- ]?\d{3}[- ]?\d{3}", owner_text)
            if owner_match:
                result["detail_owner_name"] = owner_match.group(1)
            if phone_match:
                result["detail_contact_phone"] = phone_match.group(0).replace(" ", "")
            if result["description"]:
                result["description"] = f"{result['description']} {owner_text[:300]}".strip()
            else:
                result["description"] = owner_text[:300]

        return result

    @staticmethod
    def merge_detail(listing: HousingData, detail: dict[str, object]) -> HousingData:
        """將詳頁補強資訊合併回既有物件。"""
        return replace(
            listing,
            room_type=detail.get("room_type") or listing.room_type,
            bedrooms=detail.get("bedrooms") if detail.get("bedrooms") is not None else listing.bedrooms,
            bathrooms=detail.get("bathrooms") if detail.get("bathrooms") is not None else listing.bathrooms,
            floor_area=detail.get("floor_area") if detail.get("floor_area") is not None else listing.floor_area,
            floor=detail.get("floor") or listing.floor,
            description=detail.get("description") or listing.description,
            contact=Contact(
                name=detail.get("detail_owner_name") or listing.contact.name,
                phone=detail.get("detail_contact_phone") or listing.contact.phone,
                email=listing.contact.email,
            ),
            detail_shortest_lease=detail.get("detail_shortest_lease"),
            detail_rules=detail.get("detail_rules"),
            detail_included_fees=detail.get("detail_included_fees"),
            detail_deposit=detail.get("detail_deposit"),
            detail_management_fee=detail.get("detail_management_fee"),
            detail_parking_fee=detail.get("detail_parking_fee"),
            detail_property_registration=detail.get("detail_property_registration"),
            detail_direction=detail.get("detail_direction"),
            detail_owner_name=detail.get("detail_owner_name"),
            detail_contact_phone=detail.get("detail_contact_phone"),
            detail_facilities=list(detail.get("detail_facilities") or []),
        )

    @staticmethod
    def _extract_floor_from_detail_text(text: str) -> str | None:
        """Normalize floor text from detail patterns to the shared xF/yF format."""
        cleaned = text.replace("樓層", "").replace("：", "").replace(":", "").strip()
        if "F/" in cleaned:
            return cleaned

        match = re.search(r"(\d+)\s*/\s*(\d+)", cleaned)
        if not match:
            return None
        return f"{match.group(1)}F/{match.group(2)}F"

    def _extract_url(self, title_link) -> str:
        """提取詳頁連結。"""
        if not title_link:
            return ""

        href = title_link.get("href", "")
        if not href:
            return ""
        if href.startswith("http"):
            return href
        if href.startswith("/rent/"):
            return f"https://www.591.com.tw{href}"
        return f"{self.BASE_URL}{href}"

    @staticmethod
    def _extract_room_counts(info_text: str, room_type: str) -> tuple[int, int]:
        """從文本中提取房數與衛數。"""
        bedroom = 1
        bathroom = 1

        room_text = f"{room_type} {info_text}"
        bed_match = re.search(r"(\d+)\s*房", room_text)
        bath_match = re.search(r"(\d+)\s*衛", room_text)
        if bed_match:
            bedroom = int(bed_match.group(1))
        if bath_match:
            bathroom = int(bath_match.group(1))

        return bedroom, bathroom

    @staticmethod
    def _extract_price(price_text: str) -> int:
        """提取租金數字"""
        match = re.search(r'(\d+)', price_text.replace(',', ''))
        if match:
            return int(match.group(1)) * 1000 if int(match.group(1)) < 1000 else int(match.group(1))
        return 0

    @staticmethod
    def _parse_location(location_text: str, fallback_county: str = "") -> Location:
        """解析位置"""
        cleaned = " ".join(location_text.split())
        if not cleaned:
            return Location(county=fallback_county, district="", area=None)

        if "-" in cleaned and " " not in cleaned:
            district, area = cleaned.split("-", 1)
            return Location(county=fallback_county, district=district, area=area or None)

        parts = cleaned.split(" ")
        if len(parts) >= 2 and parts[0].endswith(("市", "縣")):
            county = parts[0]
            district = parts[1]
            area = " ".join(parts[2:]) if len(parts) > 2 else None
            return Location(county=county, district=district, area=area)

        if "-" in cleaned:
            district, area = cleaned.split("-", 1)
            return Location(county=fallback_county, district=district, area=area or None)

        district = parts[0]
        area = " ".join(parts[1:]) if len(parts) > 1 else None
        return Location(county=fallback_county, district=district, area=area)


if __name__ == "__main__":
    print("✅ 591房屋爬蟲模塊定義完成")
