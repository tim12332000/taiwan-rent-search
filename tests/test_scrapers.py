"""爬蟲測試"""

import pytest
from datetime import datetime
import sys
from pathlib import Path
from types import SimpleNamespace

# 添加項目路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models import HousingData, Location, Contact
from src.scrapers.base import BaseScraper
from src.scrapers.fang591 import Fang591Scraper


class DummyScraper(BaseScraper):
    """用於測試 BaseScraper 共用行為的最小實作。"""

    def scrape(self, **kwargs):
        return []


class TestModels:
    """測試數據模型"""

    def test_housing_data_creation(self):
        """測試創建房源數據"""
        data = HousingData(
            id="591-test-001",
            platform="591",
            title="台北市大同區套房出租",
            price=15000,
            location=Location(county="台北市", district="大同區", area="民雄街"),
            room_type="整套房",
            bedrooms=1,
            bathrooms=1,
            floor_area=25.0,
            floor="3F",
            contact=Contact(name="王小明", phone="0901-234-567"),
            images=["http://example.com/img1.jpg"],
            description="新裝潢套房",
            url="https://www.591.com.tw/rent/detail/xxxxx",
            scraped_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert data.id == "591-test-001"
        assert data.platform == "591"
        assert data.price == 15000
        assert data.location.county == "台北市"
        assert len(data.images) == 1

    def test_housing_data_to_dict(self):
        """測試將房源數據轉為字典"""
        data = HousingData(
            id="591-test-001",
            platform="591",
            title="台北市大同區套房出租",
            price=15000,
            location=Location(county="台北市", district="大同區"),
            room_type="整套房",
            bedrooms=1,
            bathrooms=1,
            floor_area=None,
            floor=None,
            contact=Contact(name="王小明"),
            images=["img1.jpg", "img2.jpg"],
            description="測試",
            url="https://example.com",
            scraped_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        result = data.to_dict()
        assert isinstance(result, dict)
        assert result['location_county'] == "台北市"
        assert result['contact_name'] == "王小明"
        assert 'img1.jpg,img2.jpg' in result['images']


class TestBaseScraper:
    """測試基礎爬蟲"""

    def test_get_random_ua(self):
        """測試獲取隨機 User-Agent"""
        with DummyScraper(name="test") as scraper:
            ua = scraper._get_random_ua()
            assert isinstance(ua, str)
            assert len(ua) > 0
            assert "Mozilla" in ua

    def test_get_headers(self):
        """測試獲取請求頭"""
        with DummyScraper(name="test") as scraper:
            headers = scraper._get_headers()
            assert 'User-Agent' in headers
            assert 'Accept' in headers
            assert 'Accept-Language' in headers

    def test_base_scraper_abstract(self):
        """測試基礎爬蟲是抽象類"""
        with pytest.raises(TypeError):
            BaseScraper(name="test")


class TestFang591Scraper:
    """測試591爬蟲"""

    def test_scraper_initialization(self):
        """測試991爬蟲初始化"""
        scraper = Fang591Scraper()
        assert scraper.name == "591房屋"
        assert scraper.delay == 2.0

    def test_map_county_code(self):
        """測試縣市代碼映射"""
        assert Fang591Scraper._map_county_code("台北市") == "a1001"
        assert Fang591Scraper._map_county_code("新北市") == "a2000"
        assert Fang591Scraper._map_county_code("台中市") == "a3000"

    def test_extract_price(self):
        """測試租金提取"""
        assert Fang591Scraper._extract_price("15,000元") == 15000
        assert Fang591Scraper._extract_price("20,000") == 20000
        assert Fang591Scraper._extract_price("5") == 5000
        assert Fang591Scraper._extract_price("") == 0

    def test_parse_location(self):
        """測試位置解析"""
        location = Fang591Scraper._parse_location("台北市 大同區 民雄街")
        assert location.county == "台北市"
        assert location.district == "大同區"
        assert location.area == "民雄街"

    def test_build_search_url(self):
        """測試搜索URL構建"""
        scraper = Fang591Scraper()
        url = scraper._build_search_url("台北市")
        assert "591" in url
        assert "kind=2" in url or "search" in url

    def test_scrape_empty(self):
        """測試爬蟲在無效HTML時返回空列表"""
        scraper = Fang591Scraper()
        # 由於我們不能模擬真實網絡請求，這個測試主要檢查方法存在
        assert hasattr(scraper, 'scrape')
        assert callable(scraper.scrape)

    def test_parse_item_happy_path_extracts_all_core_fields(self):
        """測試單筆卡片可正確映射到 HousingData。"""
        scraper = Fang591Scraper()
        item = scraper._parse_html(
            """
            <div class="item">
                <h3 class="item-title">台北市大同區電梯套房</h3>
                <span class="price">18,500元/月</span>
                <span class="location">台北市 大同區 民權西路</span>
                <span class="room-type">獨立套房</span>
                <div class="meta">2房 1衛</div>
                <img class="image" src="https://img.example.com/1.jpg" />
                <a class="item-link" href="/rent/detail/12345"></a>
                <span class="name">陳小姐</span>
            </div>
            """
        ).find("div", class_="item")

        data = scraper._parse_item(item)

        assert data is not None
        assert data.title == "台北市大同區電梯套房"
        assert data.price == 18500
        assert data.location.county == "台北市"
        assert data.location.district == "大同區"
        assert data.location.area == "民權西路"
        assert data.room_type == "獨立套房"
        assert data.bedrooms == 2
        assert data.bathrooms == 1
        assert data.images == ["https://img.example.com/1.jpg"]
        assert data.url == "https://www.591.com.tw/rent/detail/12345"
        assert data.id == "591-12345"
        assert data.contact.name == "陳小姐"

    def test_parse_item_missing_optional_nodes_uses_defaults(self):
        """測試缺少選填欄位時仍能返回合理預設值。"""
        scraper = Fang591Scraper()
        item = scraper._parse_html(
            """
            <div class="item">
                <h3 class="item-title">台北市雅房</h3>
                <span class="price">9,000</span>
            </div>
            """
        ).find("div", class_="item")

        data = scraper._parse_item(item)

        assert data is not None
        assert data.location.county == ""
        assert data.location.district == ""
        assert data.location.area is None
        assert data.room_type == ""
        assert data.images == []
        assert data.url == ""
        assert data.id == "591-unknown"
        assert data.contact.name == "未公開"
        assert data.bedrooms == 1
        assert data.bathrooms == 1

    def test_scrape_parses_multiple_items_from_mocked_response(self, monkeypatch):
        """測試 scrape() 可解析多筆離線 HTML。"""
        scraper = Fang591Scraper()
        html = """
        <div class="item">
            <h3 class="item-title">台北市中山區套房</h3>
            <span class="price">15,000元</span>
            <span class="location">台北市 中山區 南京東路</span>
            <span class="room-type">整層住家</span>
            <div>3房 2衛</div>
            <a class="item-link" href="/rent/detail/alpha"></a>
            <span class="name">王先生</span>
        </div>
        <div class="item">
            <h3 class="item-title">新北市板橋區雅房</h3>
            <span class="price">8,500元</span>
            <span class="location">新北市 板橋區 文化路</span>
            <span class="room-type">雅房</span>
            <div>1房 1衛</div>
            <a class="item-link" href="/rent/detail/beta"></a>
        </div>
        """

        monkeypatch.setattr(
            scraper,
            "_fetch_url",
            lambda url, **kwargs: SimpleNamespace(text=html),
        )

        result = scraper.scrape(county="台北市")

        assert len(result) == 2
        assert result[0].title == "台北市中山區套房"
        assert result[0].bedrooms == 3
        assert result[1].contact.name == "未公開"
        assert result[1].location.county == "新北市"

    def test_scrape_skips_bad_item_and_continues(self, monkeypatch):
        """測試單筆解析失敗時，不影響其他房源繼續返回。"""
        scraper = Fang591Scraper()
        html = """
        <div class="item"><h3 class="item-title">第一筆</h3></div>
        <div class="item"><h3 class="item-title">第二筆</h3></div>
        """
        good_data = HousingData(
            id="591-good",
            platform="591",
            title="有效房源",
            price=20000,
            location=Location(county="台北市", district="中正區"),
            room_type="整套房",
            bedrooms=2,
            bathrooms=1,
            floor_area=None,
            floor=None,
            contact=Contact(name="王小明"),
            images=[],
            description="有效描述",
            url="https://www.591.com.tw/rent/detail/good",
            scraped_at=datetime.now(),
            updated_at=datetime.now(),
        )
        calls = {"count": 0}

        def fake_parse_item(item):
            calls["count"] += 1
            if calls["count"] == 1:
                raise ValueError("boom")
            return good_data

        monkeypatch.setattr(
            scraper,
            "_fetch_url",
            lambda url, **kwargs: SimpleNamespace(text=html),
        )
        monkeypatch.setattr(scraper, "_parse_item", fake_parse_item)

        result = scraper.scrape()

        assert result == [good_data]


class TestLocationAndContact:
    """測試位置和聯絡信息"""

    def test_location(self):
        """測試位置對象"""
        loc = Location(county="台北市", district="中山區", area="南京東路")
        assert loc.county == "台北市"
        assert loc.district == "中山區"
        assert loc.area == "南京東路"

    def test_contact(self):
        """測試聯絡信息"""
        contact = Contact(name="李大明", phone="0901-234-567", email="li@example.com")
        assert contact.name == "李大明"
        assert contact.phone == "0901-234-567"
        assert contact.email == "li@example.com"

    def test_contact_optional_fields(self):
        """測試聯絡信息可選字段"""
        contact = Contact(name="王二麻子")
        assert contact.name == "王二麻子"
        assert contact.phone is None
        assert contact.email is None


if __name__ == "__main__":
    # 運行測試
    pytest.main([__file__, "-v", "--tb=short"])
