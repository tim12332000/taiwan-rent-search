"""591房屋爬蟲"""

import re
from datetime import datetime
from typing import List
import logging
from urllib.parse import urlencode

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

    def scrape(self, county: str = "", district: str = "", **kwargs) -> List[HousingData]:
        """
        爬取591房屋數據
        
        Args:
            county: 縣市名稱（如："台北市"）
            district: 鄰近地區
            
        Returns:
            HousingData 列表
        """
        logger.info(f"開始爬取591房屋 - {county} {district}")
        
        # 構建搜索 URL
        search_url = self._build_search_url(county, district)
        
        try:
            response = self._fetch_url(search_url)
            html = response.text
            soup = self._parse_html(html)
            
            housing_list = []
            
            # 現行 591 列表頁使用 Nuxt-rendered `recommend-ware` 卡片。
            items = soup.select("div.recommend-ware")
            if not items:
                # 保留舊 selector，讓既有離線 fixture 仍可工作。
                items = soup.find_all("div", class_="item")
            
            if not items:
                logger.warning("未找到房源卡片，可能需要Selenium")
                return housing_list
            
            for item in items:
                try:
                    data = self._parse_item(item, fallback_county=county)
                    if data:
                        housing_list.append(data)
                except Exception as e:
                    logger.warning(f"解析房源失敗: {e}")
                    continue
            
            logger.info(f"✓ 成功爬取 {len(housing_list)} 筆房源")
            return housing_list
            
        except Exception as e:
            logger.error(f"爬蟲錯誤: {e}")
            return []

    def _build_search_url(self, county: str = "", district: str = "") -> str:
        """構建搜索URL"""
        url = f"{self.BASE_URL}/list"
        params = {
            'kind': 2,  # 2 = 租屋
        }
        
        if county:
            params['region'] = self._map_county_code(county)
        
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
