# 台灣租屋平台研究

## 主流平台分析

### 1. 591房屋 (https://www.591.com.tw)
**爬蟲難度**：⭐⭐⭐ (中度)
- **特點**：台灣最大租屋平台，房源最多
- **反爬蟲**：使用JavaScript動態加載，有基本速率限制
- **技術**：需使用 Selenium 或 Playwright
- **數據結構**：房源卡片包含租金、地點、房型、圖片
- **主要URL**：`https://www.591.com.tw/home/search/`
- **參數**：
  - `kind`: 2 (租屋)
  - `region`: 所在縣市代碼
  - `section`: 鄰近地區代碼
- **注意事項**：
  - 大量並行請求會觸發反爬
  - 建議設置 User-Agent 和延遲
  - 圖片需單獨下載

### 2. 永慶房屋 (https://www.sinyi.com.tw)
**爬蟲難度**：⭐⭐⭐⭐ (困難)
- **特點**：老牌房屋仲介，數據結構複雜
- **反爬蟲**：強反爬蟲機制，CloudFlare 防護
- **技術**：可能需要 Selenium + 代理
- **數據結構**：信息分散在多個部分
- **主要URL**：`https://www.sinyi.com.tw/buy/` 或 `/rent/`

### 3. 信義房屋 (https://www.est-living.com.tw)
**爬蟲難度**：⭐⭐⭐⭐ (困難)
- **特點**：信義房屋主網站
- **反爬蟲**：API 基礎架構，需逆向工程
- **技術**：需要分析 API 端點
- **主要URL**：https://www.est-living.com.tw/

### 4. 東森房屋 (https://www.easyhouse.com.tw)
**爬蟲難度**：⭐⭐ (簡單)
- **特點**：東森房屋平台
- **反爬蟲**：相對較弱
- **技術**：可使用 BeautifulSoup + requests
- **主要URL**：https://www.easyhouse.com.tw/

### 5. Google 地圖房源
**爬蟲難度**：⭐⭐⭐⭐⭐ (極困難)
- **特點**：Google Maps 內嵌房源信息
- **反爬蟲**：Google 官方嚴格限制
- **建議**：不爬取，使用 Google Maps API

## 推薦策略

### 第一階段（立即開始）
1. **591房屋** ← 優先攻略，房源最多，爬蟲難度適中
2. 建立基礎框架和測試

### 第二階段（可選）
3. **東森房屋** ← 簡單平台，可快速集成
4. **永慶房屋** ← 困難但值得，需代理和UA輪換

### 技術方案

**基礎爬蟲框架**：
```python
- BaseScraperclass (基類)
- Fang591Scraper (591)
- EastHouseScraper (東森)
- YongqingScraper (永慶)
```

**核心技術棧**：
- `requests` + `BeautifulSoup` ← 簡單頁面
- `Selenium` ← 動態頁面 (591主要)
- `aiohttp` + `asyncio` ← 異步並發
- 代理池 + UA 輪換 ← 反爬蟲

## 數據字段標準化

```json
{
  "id": "591-xxxxx",
  "platform": "591",
  "title": "房源標題",
  "price": 15000,
  "location": {
    "county": "台北市",
    "district": "大同區",
    "area": "房間名稱或街道"
  },
  "room_type": "整套房/分租",
  "bedrooms": 1,
  "bathrooms": 1,
  "floor_area": 25,
  "floor": "1F",
  "contact": {
    "name": "房東名字",
    "phone": "09xx-xxx-xxx",
    "email": "email@example.com"
  },
  "images": ["url1", "url2"],
  "description": "房源描述",
  "url": "原始頁面URL",
  "scraped_at": "2024-01-01T12:00:00",
  "updated_at": "2024-01-01T12:00:00"
}
```

## 反爬蟲應對方案

| 防護方式 | 應對策略 |
|---------|---------|
| User-Agent 檢查 | 輪換 UA 列表 |
| 速率限制 | 添加隨機延遲、使用代理 |
| CloudFlare | Selenium + 瀏覽器渲染 |
| 驗證碼 | 手動審查或 API 服務 |
| IP 封禁 | 使用代理池、分散爬蟲 |

