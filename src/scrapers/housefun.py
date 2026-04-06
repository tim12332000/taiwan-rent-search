"""好房網快租搜尋 API 探勘與後續 adapter 基礎。"""

from __future__ import annotations

import base64
import json
import logging
import re
from datetime import datetime
from typing import Any
from urllib.parse import quote, unquote

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


class HousefunScraper(BaseScraper):
    """好房網搜尋端點協議封裝。

    目前先封裝官方 `/ashx/search/search.ashx` 的 gateway 協議，讓後續
    可直接補上台北市專用 payload 與 HTML parser，不必重挖通訊格式。
    """

    BASE_URL = "https://rent.housefun.com.tw"
    SEARCH_ENDPOINT = f"{BASE_URL}/ashx/search/search.ashx"

    def __init__(self, delay: float = 1.5):
        super().__init__(name="Housefun", delay=delay)

    @staticmethod
    def _base64_encode(value: Any) -> str:
        return base64.b64encode(str(value).encode("utf-8")).decode("ascii")

    @staticmethod
    def _base64_decode(value: str) -> str:
        return base64.b64decode(unquote(value)).decode("utf-8")

    @classmethod
    def _encode_gateway_data(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return {key: cls._encode_gateway_data(val) for key, val in data.items()}
        return quote(cls._base64_encode(data), safe="")

    @classmethod
    def _decode_gateway_data(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return {key: cls._decode_gateway_data(val) for key, val in data.items()}
        return cls._base64_decode(data)

    def _build_search_payload(self, county: str = "台北市") -> dict[str, Any]:
        """建構當前已驗證可回應的 gateway payload。"""
        return {
            "Method": "Inquire",
            "Data": {
                "DataUnit": "1",
                "DataType": "",
                "DataTab": "",
                "OrderBy": "",
                "OrderType": "",
                "CityId": "0000",
                "CityId2": "",
                "CityId3": "",
                "CityName": county,
                "CityName2": "",
                "CityName3": "",
                "AreaId": "5",
                "AreaId2": "",
                "AreaId3": "",
                "AreaName": county,
                "AreaName2": "",
                "AreaName3": "",
                "PurposeID": "",
                "PriceRental": "",
                "PriceL": "",
                "PriceH": "",
                "MRTLine": "",
                "MRTLine2": "",
                "MRTLine3": "",
                "MRTLineName": "",
                "MRTLineName2": "",
                "MRTLineName3": "",
                "MRTStation": "",
                "MRTStation2": "",
                "MRTStation3": "",
                "MRTStationName": "",
                "MRTStationName2": "",
                "MRTStationName3": "",
                "SchoolType": "",
                "SchoolTypeName": "",
                "SchoolId": "",
                "SchoolName": "",
                "BuildingID": "",
                "BuildingName": "",
                "KeyWord": "",
                "KWkind": "",
                "KWID": "",
                "KWCounty": "",
                "KWDistrict": "",
                "NotRequiredOtherFeeID": "",
                "NotRequiredEquipmentID": "",
                "NotRequiredBaseMent": "",
                "Room": "",
                "LevelGroundID": "",
                "CaseTypeID": "",
                "AgentPositionID": "",
                "CaseFromFloor": "",
                "CaseToFloor": "",
                "BuildYear": "",
                "BuildYearL": "",
                "BuildYearH": "",
                "chkOTLimSex": "",
                "OTLimSex": "",
                "OTParkingSpace": "",
                "OTLimWithLandlord": "",
                "OTLimPet": "",
                "TGType": "",
                "EquipmentID": "",
                "PMPage": "1",
                "BrowseMode": "ShowModePics",
                "CenterLat": "",
                "CenterLng": "",
                "SID": "",
                "Distance": "",
                "SearchList": "",
                "MemberID": "",
                "MainShopID": "",
                "AgentName": "",
                "LandlordNo": "",
            },
        }

    def fetch_search_page(self, county: str = "台北市") -> dict[str, Any]:
        """呼叫官方 gateway 並回傳解碼後的 JSON。"""
        payload = self._build_search_payload(county=county)
        body = "RequestPackage=" + json.dumps(
            self._encode_gateway_data(payload),
            ensure_ascii=False,
        )
        response = self.session.post(
            self.SEARCH_ENDPOINT,
            data=body,
            headers={
                "User-Agent": self._get_random_ua(),
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            },
            timeout=20,
        )
        response.raise_for_status()
        decoded = self._decode_gateway_data(response.json())
        return decoded

    def scrape(self, county: str = "台北市", **kwargs):
        """抓取好房網搜尋結果並映射到統一資料模型。"""
        payload = self.fetch_search_page(county=county)
        logger.info(
            "Housefun gateway probe ok: HouseCount=%s PageCount=%s",
            payload.get("Data", {}).get("HouseCount"),
            payload.get("Data", {}).get("PageCount"),
        )

        search_content = payload.get("Data", {}).get("SearchContent", "")
        soup = self._parse_html(search_content)
        articles = soup.select("article.DataList")
        listings: list[HousingData] = []

        for article in articles:
            listing = self._parse_item(article, fallback_county=county)
            if listing:
                listings.append(listing)

        logger.info("✓ 成功解析 Housefun %s 筆台北房源", len(listings))
        return listings

    def _parse_item(self, item, fallback_county: str = "台北市") -> HousingData | None:
        title_link = item.select_one("h3.title a")
        address_node = item.select_one("address.addr")
        if not title_link or not address_node:
            return None

        title = title_link.get_text(" ", strip=True)
        url = self._absolute_url(title_link.get("href", ""))
        address_text = address_node.get_text(" ", strip=True)
        location = self._parse_location(address_text, fallback_county=fallback_county)
        if location.county != "台北市" or not location.district:
            return None

        level_text = item.select_one("span.level")
        pattern_text = item.select_one("span.pattern")
        info_text = " ".join(
            node.get_text(" ", strip=True)
            for node in item.select("div.info li.InfoList")
        )
        description = " ".join(
            part for part in [
                level_text.get_text(" ", strip=True) if level_text else "",
                pattern_text.get_text(" ", strip=True) if pattern_text else "",
                info_text,
            ] if part
        )

        room_type = self._extract_room_type(level_text.get_text(" ", strip=True) if level_text else "")
        bedrooms, bathrooms = self._extract_room_counts(level_text.get_text(" ", strip=True) if level_text else "")
        floor = self._extract_floor(pattern_text.get_text(" ", strip=True) if pattern_text else "")
        floor_area = self._extract_floor_area(info_text)
        price = self._extract_price(info_text)
        contact_name = self._extract_contact_name(info_text)
        image = item.select_one("span.photo img")
        images = [image.get("src")] if image and image.get("src") else []
        listing_id = self._extract_listing_id(url)
        now = datetime.now()

        return HousingData(
            id=listing_id,
            platform="housefun",
            title=title,
            price=price,
            location=location,
            room_type=room_type,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            floor_area=floor_area,
            floor=floor,
            contact=Contact(name=contact_name or "Housefun"),
            images=images,
            description=description,
            url=url,
            scraped_at=now,
            updated_at=now,
        )

    def _absolute_url(self, href: str) -> str:
        if not href:
            return ""
        if href.startswith("http"):
            return href
        return f"{self.BASE_URL}{href}"

    @staticmethod
    def _extract_listing_id(url: str) -> str:
        match = re.search(r"/rent/house/(\d+)/", url)
        return f"housefun-{match.group(1)}" if match else "housefun-unknown"

    @staticmethod
    def _extract_room_type(text: str) -> str:
        match = re.search(r"(\d+房(?:\(室\))?)", text)
        if match:
            return match.group(1).replace("(室)", "")
        return ""

    @staticmethod
    def _extract_room_counts(text: str) -> tuple[int, int]:
        bed_match = re.search(r"(\d+)房", text)
        bath_match = re.search(r"(\d+)衛", text)
        bedrooms = int(bed_match.group(1)) if bed_match else 1
        bathrooms = int(bath_match.group(1)) if bath_match else 1
        return bedrooms, bathrooms

    @staticmethod
    def _extract_floor(text: str) -> str | None:
        match = re.search(r"樓層：\s*(\d+)\s*/\s*(\d+)", text)
        return f"{match.group(1)}F/{match.group(2)}F" if match else None

    @staticmethod
    def _extract_floor_area(text: str) -> float | None:
        match = re.search(r"坪數：\s*([\d.]+)", text)
        return float(match.group(1)) if match else None

    @staticmethod
    def _extract_price(text: str) -> int:
        match = re.search(r"租金：\s*([\d,]+)", text)
        return int(match.group(1).replace(",", "")) if match else 0

    @staticmethod
    def _extract_contact_name(text: str) -> str:
        match = re.search(r"(仲介(?:\(收費\))?|屋主)：\s*([^\s]+)", text)
        return match.group(2) if match else ""

    @staticmethod
    def _parse_location(address: str, fallback_county: str = "台北市") -> Location:
        county = "台北市" if address.startswith("台北市") else ""
        district = ""
        area = None
        for candidate in TAIPEI_DISTRICTS:
            if candidate in address:
                district = candidate
                tail = address.split(candidate, 1)[1].lstrip("-－")
                area = tail or None
                break
        return Location(county=county or fallback_county, district=district, area=area)


if __name__ == "__main__":
    print("✅ Housefun gateway scaffold defined")
