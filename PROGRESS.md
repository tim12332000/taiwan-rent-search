# 台灣租屋爬蟲 - 進度追蹤

**最後更新**: 2026-04-06

## ✅ 已完成事項

### 環境設置
- [x] Node.js v25.9.0 已安裝
- [x] Codex CLI v0.118.0 已安裝
- [x] oh-my-codex v0.11.13 已安裝
- [x] OMX 設定完成（20 個提示、25 個技能）
- [x] Python 依賴已安裝（requests, beautifulsoup4, selenium, pytest 等）

### 項目結構
- [x] Git 倉庫初始化（僅 `LICENSE` 已提交）
- [x] 專案代碼已建立基線提交
- [x] 目錄結構創建
  - `src/` - 源代碼
  - `tests/` - 測試模塊
  - `data/` - 數據存儲
  - `docs/` - 文檔

### 代碼開發
- [x] **數據模型** (`src/models.py`)
  - HousingData - 房源數據類
  - Location - 位置信息
  - Contact - 聯絡信息
  
- [x] **基礎爬蟲類** (`src/scrapers/base.py`)
  - BaseScraper - 抽象基類
  - 反爬蟲機制：UA 輪換、延遲控制
  - HTTP 請求封裝

- [x] **591房屋爬蟲** (`src/scrapers/fang591.py`)
  - Fang591Scraper 類
  - URL 構建
  - HTML 解析邏輯
  - 數據提取方法
  - 已支援分頁抓取（由 `max_pages` 控制）

- [x] **MixRent 聚合爬蟲** (`src/scrapers/mixrent.py`)
  - MixRentScraper 類
  - 聚合搜尋結果解析
  - 原始來源連結保留
  - 台北市結果過濾
  - 已支援分頁抓取（由 `max_pages` 控制）

- [x] **好房網搜尋爬蟲** (`src/scrapers/housefun.py`)
  - 已打通 `/ashx/search/search.ashx`
  - 已重建 Base64 gateway 封包格式
  - 已可取得並解析官方 `SearchContent`
  - 已可過濾出台北市結果
  - 已支援分頁抓取（由 `max_pages` 控制）

- [x] **租租通 API 爬蟲** (`src/scrapers/ddroom.py`)
  - 已打通 `https://api.dd-room.com/api/v1/search`
  - 已可解析 `search.items`
  - 已可過濾出台北市結果
  - 已保留主圖與主題標籤
  - 已支援多頁抓取（目前預設 3 頁）

- [x] **研究文檔** (`docs/research.md`)
  - 5個主流平台結構分析
  - 爬蟲難度評分
  - 數據字段標準化

- [x] **執行入口與 CSV 匯出** (`src/main.py`)
  - 抓取 591 台北市列表頁
  - 扁平化輸出為 CSV
  - 自動建立 `data/` 輸出路徑
  - 支援多來源抓取與合併去重
  - 支援 `max_pages` 控制可分頁來源抓取深度

- [x] **條件分析核心** (`src/analysis.py`)
  - 從既有 CSV 讀取房源
  - 支援可重複使用的條件篩選與排序
  - 支援目的地地址、通勤時間、行政區、關鍵字、流理臺需求
  - 產出分析後的候選 CSV
  - 產出給人快速瀏覽的 Markdown shortlist 報告
  - 產出圖文卡片式 HTML 報告

- [x] **本地即時搜尋網站** (`src/webapp.py`)
  - 將最新資料池嵌入單檔 HTML
  - 支援文字、來源、行政區、租金、坪數、流理臺、圖片條件即時篩選
  - 不需後端即可在本地快速查

### 測試代碼
- [x] 創建 `tests/test_scrapers.py`
- [x] 68個測試用例
  - 數據模型測試
  - 爬蟲類初始化
  - User-Agent 輪換
  - URL 構建
  - 價格/位置解析
  - 離線 HTML 卡片解析
  - mock scrape 流程驗證
  - MixRent 結構解析
  - 多來源去重與整合輸出
  - Housefun gateway 編解碼驗證
  - Housefun 結果解析與台北過濾驗證
  - DDRoom API 結構解析
  - CSV 匯出與 CLI 入口驗證
  - 條件分析與通勤估算驗證
  - Markdown shortlist 報告驗證
  - HTML shortlist 報告驗證
  - 本地搜尋網站產生驗證

## 🔧 當前狀態

### 已完成的修正
1. ✅ **導入路徑修復完成** - `from ..models import` 已修正
2. ✅ **BaseScraper 測試修正** - 改為使用測試 stub，並驗證抽象類不可直接實例化
3. ✅ **覆蓋率命令驗證完成** - `pytest tests/test_scrapers.py -v --cov=src` 已可執行
4. ✅ **離線解析測試補強** - 591 卡片解析、缺欄位 fallback、mock scrape 流程已納入測試
5. ✅ **現行 591 列表頁相容** - 已支援 `div.recommend-ware` 結構
6. ✅ **第一份真實資料檔已產出** - `data/591_taipei_*.csv`，目前實跑為 20 筆
7. ✅ **條件分析核心已完成** - 已可根據條件輸出候選清單與分析 CSV
8. ✅ **快速瀏覽報告已完成** - 已可直接產出給人看的 shortlist Markdown
9. ✅ **圖文穿插報告已完成** - 已可直接產出 `shortlist.html`
10. ✅ **多來源整合已完成** - 已可合併 `591 + MixRent` 並輸出整合資料池
11. ✅ **Housefun 已正式接入** - 已可納入三來源整合資料池
12. ✅ **DDRoom 已正式接入** - 已可納入四來源整合資料池
13. ✅ **資料池已開始擴量** - `591`、`MixRent`、`Housefun`、`DDRoom` 已支援分頁抓取
14. ✅ **本地搜尋網站已完成** - 已可直接產出 `search_app.html`

### 目前缺口
1. ⏳ **來源數仍偏少** - `樂屋網` 等來源還沒接
3. ⏳ **欄位仍以列表頁為主** - `bathrooms`、`contact`、`floor` 等資訊仍多半缺失或推估
4. ⏳ **缺少資料品質統計** - 尚未輸出 skipped rows、重複筆數、欄位完整率
5. ⏳ **缺少 detail-page enrichment** - 需要第二階段補詳頁資料
6. ⏳ **缺少長期抗 drift 測試** - 還沒保存真實 fixture 做回歸保護
7. ⏳ **district 參數尚未接線** - 目前 API 簽名保留，但還沒映射到查詢條件
8. ⏳ **圖片評分尚未接線** - 目前只能先做文字訊號與待看圖標記
9. ⏳ **圖片品質仍未打分** - HTML 目前只做首圖展示，還沒有視覺評級
10. ⏳ **Housefun 查詢條件仍可再優化** - 目前已能取出台北結果，但 payload 仍可再校準以提升純度與覆蓋

## 📋 下一步工作

### 立即執行
1. **重新產出一份資料檔**
   ```bash
   python -m src.main --county 台北市 --source 591 --source mixrent --source housefun --source ddroom --max-pages 3
   ```

2. **依條件輸出候選清單**
   ```bash
   python -m src.analysis --destination-address "台北市信義區松仁路100號" --max-commute 30 --transport-mode either --require-kitchen-sink --top 5
   ```

3. **產出本地即時搜尋網站**
   ```bash
   python -m src.webapp --input data\591-ddroom-housefun-mixrent_taipei_20260406_233623.csv
   ```

4. **輸出給人快速瀏覽的 shortlist 報告**
   ```bash
   python -m src.analysis --destination-address "台北市信義區松仁路100號 29樓" --transport-mode either --require-kitchen-sink --top 10
   ```

5. **輸出圖文卡片式 HTML 報告**
   ```bash
   python -m src.analysis --destination-address "台北市信義區松仁路100號 29樓" --transport-mode either --require-kitchen-sink --top 10
   ```

6. **運行單元測試**
   ```bash
   pytest tests/test_scrapers.py tests/test_analysis.py tests/test_webapp.py -v
   ```

7. **運行含覆蓋率的驗證**
   ```bash
   pytest tests/test_scrapers.py tests/test_analysis.py tests/test_webapp.py -v --cov=src
   ```

8. **提交本地搜尋網站功能**
   ```bash
   git add .
   git commit -m "加入本地即時搜尋網站"
   ```

### 在 Codex 中執行（推薦）
```
omx --madmax --high
$ralph "運行單元測試 pytest tests/test_scrapers.py -v"
$ralph "第一次 Git 提交：初始化爬蟲框架"
```

或分步：
```
$deep-interview "確認測試內容"
$ralplan "批准測試和提交方案"
$ralph "執行測試"
$ralph "執行 git 提交"
```

### 後續計劃
3. **擴展真實數據抓取**
   - 多頁爬取
   - 詳頁補強
   - 資料品質指標
   
4. **其他平台爬蟲**
   - 東森房屋（簡單）
   - 永慶房屋（困難）

5. **圖片處理**
   - 批量下載
   - AI 品質檢測

6. **數據存儲**
   - CSV 導出
   - SQLite 數據庫

7. **排程系統**
   - 1小時自動更新

## 📁 文件結構
```
taiwan-rent-search/
├── src/
│   ├── __init__.py
│   ├── analysis.py            ✅ 完成
│   ├── main.py                ✅ 完成
│   ├── models.py              ✅ 完成
│   ├── webapp.py              ✅ 完成
│   └── scrapers/
│       ├── __init__.py
│       ├── base.py            ✅ 完成
│       ├── fang591.py         ✅ 完成
│       ├── mixrent.py         ✅ 完成
│       ├── housefun.py        ✅ 完成
│       └── ddroom.py          ✅ 完成
├── tests/
│   ├── __init__.py
│   └── test_scrapers.py       ✅ 完成（已驗證）
├── docs/
│   └── research.md            ✅ 完成
├── requirements.txt           ✅ 完成
├── .gitignore                 ✅ 完成
├── README.md                  ✅ 完成
└── PROGRESS.md                ✅ 本文件

```

## 🎯 快速命令

### 本地執行
```bash
# 安裝依賴
pip install -r requirements.txt

# 運行測試
pytest tests/ -v --cov=src

# 檢查代碼
python src/models.py

# git 操作
git status
git add .
git commit -m "message"
git log --oneline
```

### Codex 執行
```
omx --madmax --high
> $ralph "pytest tests/test_scrapers.py -v"
> $ralph "git status && git add . && git commit -m 'Initial scraper framework'"
```

## 💡 提示

- 所有代碼已設置，邏輯就緒
- 目前測試集共 40 個案例，已全數通過
- 目前測試集共 68 個案例，已全數通過
- 已產出第一份真實 CSV：`data/591_taipei_*.csv`
- 已產出第一份多來源整合 CSV：`data/591-mixrent_taipei_*.csv`
- 已產出第一份三來源整合 CSV：`data/591-housefun-mixrent_taipei_*.csv`
- 已產出第一份四來源整合 CSV：`data/591-ddroom-housefun-mixrent_taipei_*.csv`
- 最新四來源整合資料池約 `78` 筆
- 已可產出條件分析 CSV：`data/*analysis*.csv`
- 已可產出人看報告：`data/*shortlist*.md`
- 已可產出圖文報告：`data/*shortlist*.html`
- 已可產出本地搜尋網站：`data/*search_app.html`
- 列表頁抓取已可工作，但仍是單頁版與列表欄位版
- 覆蓋率驗證已通過，總覆蓋率為 85%
- 下一步最有價值的是第 5 個來源 + pagination + 詳頁補強

---

**下一步**: 提交本輪真實抓取能力，然後做 pagination 與詳頁補強
