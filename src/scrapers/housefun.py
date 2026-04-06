"""好房網快租搜尋 API 探勘與後續 adapter 基礎。"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any
from urllib.parse import quote, unquote

from .base import BaseScraper

logger = logging.getLogger(__name__)


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
                "DataUnit": "",
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
        """後續會補正式 parser；目前先保留已驗證的 gateway 探勘能力。"""
        payload = self.fetch_search_page(county=county)
        logger.info(
            "Housefun gateway probe ok: HouseCount=%s PageCount=%s",
            payload.get("Data", {}).get("HouseCount"),
            payload.get("Data", {}).get("PageCount"),
        )
        return []


if __name__ == "__main__":
    print("✅ Housefun gateway scaffold defined")
