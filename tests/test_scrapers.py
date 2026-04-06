"""爬蟲測試"""

import pytest
from datetime import datetime
import sys
from pathlib import Path
from types import SimpleNamespace
import csv

# 添加項目路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models import HousingData, Location, Contact
from src.main import (
    CSV_FIELDNAMES,
    build_output_path,
    build_multi_source_output_path,
    dedupe_records,
    export_to_csv,
    main as main_entry,
    sanitize_csv_value,
    scrape_sources_to_csv,
    scrape_to_csv,
)
from src.scrapers.base import BaseScraper
from src.scrapers.fang591 import Fang591Scraper
from src.scrapers.housefun import HousefunScraper
from src.scrapers.mixrent import MixRentScraper


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
        assert Fang591Scraper._map_county_code("台北市") == "1"
        assert Fang591Scraper._map_county_code("新北市") == "3"
        assert Fang591Scraper._map_county_code("台中市") == "8"

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
        assert "kind=2" in url
        assert "region=1" in url

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

        def fake_parse_item(item, **kwargs):
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

    def test_parse_live_card_structure(self):
        """測試現行 591 recommend-ware 卡片結構。"""
        scraper = Fang591Scraper()
        item = scraper._parse_html(
            """
            <div class="recommend-ware">
                <a class="img-container" href="https://rent.591.com.tw/20949608">
                    <img data-src="https://img.example.com/cover.jpg" />
                </a>
                <div class="content">
                    <a class="title" href="https://rent.591.com.tw/20949608">清新美景電梯兩房雙車位</a>
                    <div class="address-info">
                        <span class="address"><span class="community">清新美景</span><span>文山區-富山路</span></span>
                        <span class="area">2房/</span>
                        <span class="area">31.6坪</span>
                    </div>
                    <div class="distance-info">
                        <span class="desc">距中港抽水站</span>
                        <span class="distance">404公尺</span>
                    </div>
                    <div class="price-info"><span class="price">45,000</span></div>
                </div>
            </div>
            """
        ).find("div", class_="recommend-ware")

        data = scraper._parse_item(item, fallback_county="台北市")

        assert data is not None
        assert data.title == "清新美景電梯兩房雙車位"
        assert data.url == "https://rent.591.com.tw/20949608"
        assert data.price == 45000
        assert data.location.county == "台北市"
        assert data.location.district == "文山區"
        assert data.location.area == "富山路"
        assert data.room_type == "2房"
        assert data.bedrooms == 2
        assert data.floor_area == 31.6
        assert data.images == ["https://img.example.com/cover.jpg"]

    def test_parse_live_card_missing_optional_fields_uses_defaults(self):
        """測試現行卡片缺欄位時仍能安全解析。"""
        scraper = Fang591Scraper()
        item = scraper._parse_html(
            """
            <div class="recommend-ware">
                <div class="content">
                    <a class="title" href="https://rent.591.com.tw/20151975">臺北市中山區相鄰花博公園近捷運雅房</a>
                    <div class="address-info">
                        <span class="address"><span>中山區-農安街</span></span>
                        <span class="area">9坪</span>
                    </div>
                    <div class="price-info"><span class="price">14,500</span></div>
                </div>
            </div>
            """
        ).find("div", class_="recommend-ware")

        data = scraper._parse_item(item, fallback_county="台北市")

        assert data is not None
        assert data.location.county == "台北市"
        assert data.location.district == "中山區"
        assert data.location.area == "農安街"
        assert data.room_type == ""
        assert data.images == []
        assert data.contact.name == "未公開"
        assert data.floor_area == 9.0

    def test_scrape_parses_live_cards_from_mocked_response(self, monkeypatch):
        """測試 scrape() 可解析現行 recommend-ware 列表。"""
        scraper = Fang591Scraper()
        html = """
        <div class="recommend-ware">
            <div class="content">
                <a class="title" href="https://rent.591.com.tw/10001">第一筆</a>
                <div class="address-info">
                    <span class="address"><span>文山區-久康街</span></span>
                    <span class="area">2房/</span>
                    <span class="area">20坪</span>
                </div>
                <div class="price-info"><span class="price">15,500</span></div>
            </div>
        </div>
        <div class="recommend-ware">
            <div class="content">
                <a class="title" href="https://rent.591.com.tw/10002">第二筆</a>
                <div class="address-info">
                    <span class="address"><span>大同區-重慶北路三段</span></span>
                    <span class="area">35坪</span>
                </div>
                <div class="price-info"><span class="price">35,500</span></div>
            </div>
        </div>
        """

        monkeypatch.setattr(
            scraper,
            "_fetch_url",
            lambda url, **kwargs: SimpleNamespace(text=html),
        )

        result = scraper.scrape(county="台北市")

        assert len(result) == 2
        assert result[0].location.district == "文山區"
        assert result[0].bedrooms == 2
        assert result[1].location.district == "大同區"
        assert result[1].floor_area == 35.0


class TestMixRentScraper:
    """測試 MixRent 聚合爬蟲。"""

    def test_scraper_initialization(self):
        scraper = MixRentScraper()
        assert scraper.name == "MixRent"
        assert scraper.delay == 1.5

    def test_build_search_url(self):
        scraper = MixRentScraper()
        url = scraper._build_search_url("台北市信義區")
        assert "mixrent" in url
        assert "q=" in url

    def test_parse_item_extracts_core_fields(self):
        scraper = MixRentScraper()
        item = scraper._parse_html(
            """
            <div class="rental_result">
              <div class="row">
                <div class="col-xs-12 col-sm-10">
                  <a class="house_title" href="https://www.dd-room.com/object/abc" name="租租通">台北市士林區共生住宅</a>
                </div>
              </div>
              <div class="row">
                <div class="col-sm-2 col-sm-push-10">
                  <ul class="list-inline feature_list">
                    <li><span class="label label-success"><strong>50</strong> 坪</span></li>
                    <li><span class="label label-primary">$ <strong>13000</strong></span></li>
                  </ul>
                </div>
                <div class="col-sm-10 col-sm-pull-2">
                  <div class="house_address">台北市士林區大南路</div>
                  <div class="house_description">有廚房 2房 1衛 5F/12F</div>
                </div>
              </div>
              <div class="row">
                <div class="col-xs-12 col-sm-10">
                  <div class="house_url"><small>租租通 - https://www.dd-room.com/object/abc</small></div>
                </div>
              </div>
            </div>
            """
        ).find("div", class_="rental_result")

        data = scraper._parse_item(item)

        assert data is not None
        assert data.title == "台北市士林區共生住宅"
        assert data.price == 13000
        assert data.location.county == "台北市"
        assert data.location.district == "士林區"
        assert data.location.area == "大南路"
        assert data.floor_area == 50.0
        assert data.room_type == "2房"
        assert data.bedrooms == 2
        assert data.bathrooms == 1
        assert data.floor == "5F/12F"
        assert data.contact.name == "租租通"

    def test_scrape_parses_mocked_response(self, monkeypatch):
        scraper = MixRentScraper()
        html = """
        <div class="rental_result">
          <div class="row"><div class="col-xs-12 col-sm-10"><a class="house_title" href="https://example.com/1" name="來源A">士林區好房</a></div></div>
          <div class="row">
            <div class="col-sm-2 col-sm-push-10"><ul class="list-inline feature_list"><li><span class="label label-success"><strong>10</strong> 坪</span></li><li><span class="label label-primary">$ <strong>10000</strong></span></li></ul></div>
            <div class="col-sm-10 col-sm-pull-2"><div class="house_address">台北市士林區文林路</div><div class="house_description">可開伙 1房 1衛</div></div>
          </div>
        </div>
        <div class="rental_result">
          <div class="row"><div class="col-xs-12 col-sm-10"><a class="house_title" href="https://example.com/2" name="來源B">大安區好房</a></div></div>
          <div class="row">
            <div class="col-sm-2 col-sm-push-10"><ul class="list-inline feature_list"><li><span class="label label-success"><strong>20</strong> 坪</span></li><li><span class="label label-primary">$ <strong>20000</strong></span></li></ul></div>
            <div class="col-sm-10 col-sm-pull-2"><div class="house_address">台北市大安區和平東路</div><div class="house_description">2房 1衛</div></div>
          </div>
        </div>
        """

        monkeypatch.setattr(scraper, "_fetch_url", lambda url, **kwargs: SimpleNamespace(text=html))
        result = scraper.scrape(county="台北市")

        assert len(result) == 2
        assert result[0].location.district == "士林區"
        assert result[1].location.district == "大安區"

    def test_parse_item_rejects_non_taipei_listing(self):
        scraper = MixRentScraper()
        item = scraper._parse_html(
            """
            <div class="rental_result">
              <div class="row"><div class="col-xs-12 col-sm-10"><a class="house_title" href="https://example.com/1" name="來源A">竹北租屋透天電梯住店鄰近生醫園區高鐵站</a></div></div>
              <div class="row">
                <div class="col-sm-2 col-sm-push-10"><ul class="list-inline feature_list"><li><span class="label label-success"><strong>40</strong> 坪</span></li><li><span class="label label-primary">$ <strong>26000</strong></span></li></ul></div>
                <div class="col-sm-10 col-sm-pull-2"><div class="house_address">新竹縣竹北市嘉豐十路</div><div class="house_description">高鐵站旁 2房 1衛</div></div>
              </div>
            </div>
            """
        ).find("div", class_="rental_result")

        assert scraper._parse_item(item) is None


class TestHousefunScraper:
    """測試好房網 gateway scaffold。"""

    def test_scraper_initialization(self):
        scraper = HousefunScraper()
        assert scraper.name == "Housefun"
        assert scraper.delay == 1.5

    def test_gateway_encode_decode_round_trip(self):
        payload = {"Method": "Inquire", "Data": {"CityName": "台北市", "PMPage": "1"}}

        encoded = HousefunScraper._encode_gateway_data(payload)
        decoded = HousefunScraper._decode_gateway_data(encoded)

        assert decoded == payload

    def test_build_search_payload_contains_taipei_defaults(self):
        scraper = HousefunScraper()
        payload = scraper._build_search_payload("台北市")

        assert payload["Method"] == "Inquire"
        assert payload["Data"]["CityName"] == "台北市"
        assert payload["Data"]["AreaName"] == "台北市"
        assert payload["Data"]["PMPage"] == "1"

    def test_fetch_search_page_decodes_gateway_response(self, monkeypatch):
        scraper = HousefunScraper()
        fake_payload = {
            "Method": "Inquire",
            "Status": "1",
            "StatusMessage": "Success",
            "StatusCode": "1",
            "Data": {
                "SearchContent": "<div>ok</div>",
                "PageCount": "1/10",
                "HouseCount": "100",
                "AddDataSourceCache": "0",
            },
        }
        encoded_response = HousefunScraper._encode_gateway_data(fake_payload)

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return encoded_response

        monkeypatch.setattr(scraper.session, "post", lambda *args, **kwargs: FakeResponse())

        result = scraper.fetch_search_page("台北市")

        assert result["Status"] == "1"
        assert result["Data"]["HouseCount"] == "100"

    def test_parse_item_extracts_core_fields(self):
        scraper = HousefunScraper()
        item = scraper._parse_html(
            """
            <article class="DataList both">
              <div class="Data">
                <h3 class="title"><a href="/rent/house/1986175/" title="復興路繁華店面">復興路繁華店面</a></h3>
                <address class="addr">台北市信義區松仁路</address>
                <span class="sectionList">
                  <span class="level">1房(室)1廳1衛</span>
                  <span class="pattern">樓層：1 / 4</span>
                </span>
              </div>
              <div class="info">
                <ul>
                  <li class="InfoList"><span class="title">租金：</span><span class="infos num">30,000 元/月</span></li>
                  <li class="InfoList"><span class="title">坪數：</span><span class="infos">22.69 坪</span></li>
                  <li class="InfoList"><span class="infos">仲介(收費)：永慶房屋(股)公司中平榮富直營店</span></li>
                </ul>
              </div>
              <span class="photoWrap"><span class="photo middleSet"><img src="https://img.housefun/1.jpg" /></span></span>
            </article>
            """
        ).find("article", class_="DataList")

        data = scraper._parse_item(item)

        assert data is not None
        assert data.id == "housefun-1986175"
        assert data.platform == "housefun"
        assert data.title == "復興路繁華店面"
        assert data.price == 30000
        assert data.location.county == "台北市"
        assert data.location.district == "信義區"
        assert data.location.area == "松仁路"
        assert data.room_type == "1房"
        assert data.bedrooms == 1
        assert data.bathrooms == 1
        assert data.floor_area == 22.69
        assert data.floor == "1F/4F"
        assert data.contact.name == "永慶房屋(股)公司中平榮富直營店"
        assert data.images == ["https://img.housefun/1.jpg"]

    def test_parse_item_rejects_non_taipei_listing(self):
        scraper = HousefunScraper()
        item = scraper._parse_html(
            """
            <article class="DataList both">
              <div class="Data">
                <h3 class="title"><a href="/rent/house/1986175/" title="新莊店面">新莊店面</a></h3>
                <address class="addr">新北市新莊區復興路一段</address>
              </div>
            </article>
            """
        ).find("article", class_="DataList")

        assert scraper._parse_item(item) is None

    def test_scrape_parses_mocked_response(self, monkeypatch):
        scraper = HousefunScraper()
        fake_payload = {
            "Status": "1",
            "Data": {
                "HouseCount": "2",
                "PageCount": "1/1",
                "SearchContent": """
                    <article class=\"DataList both\">
                      <div class=\"Data\">
                        <h3 class=\"title\"><a href=\"/rent/house/1/\">信義區套房</a></h3>
                        <address class=\"addr\">台北市信義區光復南路</address>
                        <span class=\"sectionList\"><span class=\"level\">1房(室)1廳1衛</span><span class=\"pattern\">樓層：3 / 12</span></span>
                      </div>
                      <div class=\"info\"><ul><li class=\"InfoList\"><span class=\"title\">租金：</span><span class=\"infos num\">20,000 元/月</span></li><li class=\"InfoList\"><span class=\"title\">坪數：</span><span class=\"infos\">12 坪</span></li></ul></div>
                    </article>
                    <article class=\"DataList both\">
                      <div class=\"Data\">
                        <h3 class=\"title\"><a href=\"/rent/house/2/\">新莊套房</a></h3>
                        <address class=\"addr\">新北市新莊區中正路</address>
                      </div>
                    </article>
                """,
            },
        }

        monkeypatch.setattr(scraper, "fetch_search_page", lambda county="台北市": fake_payload)
        result = scraper.scrape("台北市")

        assert len(result) == 1
        assert result[0].location.district == "信義區"


class TestCsvExport:
    """測試 CSV 匯出流程。"""

    @staticmethod
    def _sample_records():
        return [
            HousingData(
                id="591-1",
                platform="591",
                title="第一筆",
                price=10000,
                location=Location(county="台北市", district="文山區", area="久康街"),
                room_type="套房",
                bedrooms=1,
                bathrooms=1,
                floor_area=10.0,
                floor=None,
                contact=Contact(name="王小明"),
                images=["https://img.example.com/1.jpg"],
                description="desc",
                url="https://rent.591.com.tw/1",
                scraped_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            HousingData(
                id="591-2",
                platform="591",
                title="第二筆",
                price=20000,
                location=Location(county="台北市", district="中山區", area="農安街"),
                room_type="2房",
                bedrooms=2,
                bathrooms=1,
                floor_area=20.0,
                floor=None,
                contact=Contact(name="陳小姐"),
                images=[],
                description="desc2",
                url="https://rent.591.com.tw/2",
                scraped_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ]

    def test_export_to_csv_writes_flattened_rows(self, tmp_path):
        records = self._sample_records()

        output = tmp_path / "sample.csv"
        export_to_csv(records, output)

        with output.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)

        assert reader.fieldnames == CSV_FIELDNAMES
        assert len(rows) == 2
        assert rows[0]["location_county"] == "台北市"
        assert rows[0]["contact_name"] == "王小明"
        assert rows[1]["title"] == "第二筆"

    def test_export_to_csv_empty_results_writes_header_only(self, tmp_path):
        output = tmp_path / "empty.csv"
        export_to_csv([], output)

        with output.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))

        assert len(rows) == 1
        assert rows[0] == CSV_FIELDNAMES

    def test_sanitize_csv_value_prefixes_formula_like_strings(self):
        assert sanitize_csv_value("=SUM(A1:A2)") == "'=SUM(A1:A2)"
        assert sanitize_csv_value("+cmd") == "'+cmd"
        assert sanitize_csv_value("@foo") == "'@foo"
        assert sanitize_csv_value("正常文字") == "正常文字"

    def test_build_output_path_uses_county_slug(self):
        path = build_output_path("台北市")
        assert path.parent.name == "data"
        assert path.name.startswith("591_taipei_")
        assert path.suffix == ".csv"

    def test_build_multi_source_output_path_uses_source_slug(self):
        path = build_multi_source_output_path("台北市", ["mixrent", "591"])
        assert path.parent.name == "data"
        assert "591-mixrent_taipei_" in path.name
        assert path.suffix == ".csv"

    def test_scrape_to_csv_writes_records_with_mocked_scraper(self, monkeypatch, tmp_path):
        records = self._sample_records()

        monkeypatch.setattr(Fang591Scraper, "scrape", lambda self, county="": records)

        output = tmp_path / "from-scrape.csv"
        path, written_records = scrape_to_csv("台北市", output_path=output, delay=0)

        assert path == output
        assert written_records == records
        assert output.exists()

    def test_main_prints_export_summary(self, monkeypatch, capsys, tmp_path):
        output = tmp_path / "cli.csv"

        monkeypatch.setattr(
            "src.main.scrape_to_csv",
            lambda county, output_path=None, delay=2.0: (output, self._sample_records()),
        )
        monkeypatch.setattr(sys, "argv", ["src.main", "--county", "台北市", "--output", str(output)])

        main_entry()
        out = capsys.readouterr().out

        assert "CSV exported:" in out
        assert "Records: 2" in out

    def test_dedupe_records_keeps_unique_url_title_price(self):
        records = self._sample_records()
        duplicate = self._sample_records()[0]
        deduped = dedupe_records(records + [duplicate])

        assert len(deduped) == 2

    def test_scrape_sources_to_csv_writes_combined_records(self, monkeypatch, tmp_path):
        mixrent_records = [self._sample_records()[0]]
        rent591_records = [self._sample_records()[1]]

        monkeypatch.setattr(Fang591Scraper, "scrape", lambda self, county="": rent591_records)
        monkeypatch.setattr(MixRentScraper, "scrape", lambda self, county="台北市", district="", query="": mixrent_records)

        output = tmp_path / "combined.csv"
        path, written_records = scrape_sources_to_csv(["591", "mixrent"], "台北市", output_path=output, delay=0)

        assert path == output
        assert len(written_records) == 2
        assert output.exists()


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
