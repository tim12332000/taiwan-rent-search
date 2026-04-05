"""591房屋爬蟲"""

import re
from datetime import datetime
from typing import List
import logging

from .base import BaseScraper
from ..models import HousingData, Location, Contact

logger = logging.getLogger(__name__)


class Fang591Scraper(BaseScraper):
    """591房屋爬蟲"""

    BASE_URL = "https://www.591.com.tw"

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
        
        # 構建搜號URL
        search_url = self._build_search_url(county, district)
        
        try:
            response = self._fetch_url(search_url)
            html = response.text
            soup = self._parse_html(html)
            
            housing_list = []
            
            # 查找所有房源卡片（注意：591使用JS動態加載，需要手動解析）
            items = soup.find_all('div', class_='item')
            
            if not items:
                logger.warning("未找到房源卡片，可能需要Selenium")
                return housing_list
            
            for item in items:
                try:
                    data = self._parse_item(item)
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
        # 591的數據需要通過API獲取，暫時使用搜尋頁面
        url = f"{self.BASE_URL}/home/search/rsList"
        params = {
            'kind': 2,  # 2 = 租屋
        }
        
        # 這是簡化版本，實際需要映射縣市代碼
        if county:
            params['region'] = self._map_county_code(county)
        
        from urllib.parse import urlencode
        return f"{url}?{urlencode(params)}"

    @staticmethod
    def _map_county_code(county: str) -> str:
        """縣市代碼對應"""
        county_map = {
            '台北市': 'a1001',
            '新北市': 'a2000',
            '台中市': 'a3000',
            '高雄市': 'a4000',
            '桃園市': 'a5000',
        }
        return county_map.get(county, '')

    def _parse_item(self, item) -> HousingData | None:
        """解析單一房源"""
        try:
            # 提取基本信息
            title = item.find('h3', class_='item-title')
            if not title:
                return None
            
            title_text = title.get_text(strip=True)
            
            # 提取租金
            price_elem = item.find('span', class_='price')
            price = self._extract_price(price_elem.get_text() if price_elem else "")
            
            # 提取地點
            location_elem = item.find('span', class_='location')
            location = self._parse_location(location_elem.get_text(strip=True) if location_elem else "")
            
            # 提取房型
            room_type_elem = item.find('span', class_='room-type')
            room_type = room_type_elem.get_text(strip=True) if room_type_elem else ""
            
            # 提取床房衛
            bedroom = 1
            bathroom = 1
            info_text = item.get_text()
            bed_match = re.search(r'(\d+)\s*房', info_text)
            bath_match = re.search(r'(\d+)\s*衛', info_text)
            if bed_match:
                bedroom = int(bed_match.group(1))
            if bath_match:
                bathroom = int(bath_match.group(1))
            
            # 提取圖片
            images = []
            img_elem = item.find('img', class_='image')
            if img_elem and img_elem.get('src'):
                images.append(img_elem.get('src'))
            
            # 提取URL
            url_elem = item.find('a', class_='item-link')
            url = self.BASE_URL + url_elem.get('href') if url_elem else ""
            
            # 提取聯絡信息（可能不一定有）
            contact_name = item.find('span', class_='name')
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
                floor_area=None,  # 需要進入詳頁獲取
                floor=None,
                contact=Contact(name=contact_name_text),
                images=images,
                description=info_text[:200],  # 簡短描述
                url=url,
                scraped_at=now,
                updated_at=now
            )
            
            return data
            
        except Exception as e:
            logger.debug(f"解析失敗: {e}")
            return None

    @staticmethod
    def _extract_price(price_text: str) -> int:
        """提取租金數字"""
        match = re.search(r'(\d+)', price_text.replace(',', ''))
        if match:
            return int(match.group(1)) * 1000 if int(match.group(1)) < 1000 else int(match.group(1))
        return 0

    @staticmethod
    def _parse_location(location_text: str) -> Location:
        """解析位置"""
        parts = location_text.split(' ')
        county = parts[0] if len(parts) > 0 else ""
        district = parts[1] if len(parts) > 1 else ""
        area = ' '.join(parts[2:]) if len(parts) > 2 else None
        
        return Location(county=county, district=district, area=area)


if __name__ == "__main__":
    print("✅ 591房屋爬蟲模塊定義完成")
