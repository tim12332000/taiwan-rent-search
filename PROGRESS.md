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

- [x] **研究文檔** (`docs/research.md`)
  - 5個主流平台結構分析
  - 爬蟲難度評分
  - 數據字段標準化

- [x] **執行入口與 CSV 匯出** (`src/main.py`)
  - 抓取 591 台北市列表頁
  - 扁平化輸出為 CSV
  - 自動建立 `data/` 輸出路徑

### 測試代碼
- [x] 創建 `tests/test_scrapers.py`
- [x] 27個測試用例
  - 數據模型測試
  - 爬蟲類初始化
  - User-Agent 輪換
  - URL 構建
  - 價格/位置解析
  - 離線 HTML 卡片解析
  - mock scrape 流程驗證
  - CSV 匯出與 CLI 入口驗證

## 🔧 當前狀態

### 已完成的修正
1. ✅ **導入路徑修復完成** - `from ..models import` 已修正
2. ✅ **BaseScraper 測試修正** - 改為使用測試 stub，並驗證抽象類不可直接實例化
3. ✅ **覆蓋率命令驗證完成** - `pytest tests/test_scrapers.py -v --cov=src` 已可執行
4. ✅ **離線解析測試補強** - 591 卡片解析、缺欄位 fallback、mock scrape 流程已納入測試
5. ✅ **現行 591 列表頁相容** - 已支援 `div.recommend-ware` 結構
6. ✅ **第一份真實資料檔已產出** - `data/591_taipei_*.csv`，目前實跑為 20 筆

### 目前缺口
1. ⏳ **只有單頁資料** - 尚未做 pagination 與跨頁去重
2. ⏳ **欄位仍以列表頁為主** - `bathrooms`、`contact`、`floor` 等資訊仍多半缺失或推估
3. ⏳ **缺少資料品質統計** - 尚未輸出 skipped rows、重複筆數、欄位完整率
4. ⏳ **缺少 detail-page enrichment** - 需要第二階段補詳頁資料
5. ⏳ **缺少長期抗 drift 測試** - 還沒保存真實 591 fixture 做回歸保護
6. ⏳ **district 參數尚未接線** - 目前 API 簽名保留，但還沒映射到查詢條件

## 📋 下一步工作

### 立即執行
1. **重新產出一份資料檔**
   ```bash
   python -m src.main --county 台北市
   ```

2. **運行單元測試**
   ```bash
   pytest tests/test_scrapers.py -v
   ```

3. **運行含覆蓋率的驗證**
   ```bash
   pytest tests/test_scrapers.py -v --cov=src
   ```

4. **提交本輪真實抓取能力**
   ```bash
   git add .
   git commit -m "加入真實 591 列表抓取與 CSV 匯出"
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
│   ├── main.py                ✅ 完成
│   ├── models.py              ✅ 完成
│   └── scrapers/
│       ├── __init__.py
│       ├── base.py            ✅ 完成
│       └── fang591.py         ✅ 完成
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
- 目前測試集共 27 個案例，已全數通過
- 已產出第一份真實 CSV：`data/591_taipei_*.csv`
- 列表頁抓取已可工作，但仍是單頁版與列表欄位版
- 覆蓋率驗證已通過，總覆蓋率為 89%
- 下一步最有價值的是 pagination + 詳頁補強

---

**下一步**: 提交本輪真實抓取能力，然後做 pagination 與詳頁補強
