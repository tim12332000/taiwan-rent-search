# Taiwan Rent Search Web Scraper (台灣租屋搜尋工作台)

這個專案目前的主軸已經不是單純「爬資料」，而是把租屋搜尋做成本機工作台：

- 自動抓多來源資料
- 依目的地做第二輪加抓
- 在本地頁面直接篩選、看圖、標記
- 用「可煮飯方便程度」而不是單純關鍵字來整理候選
- 對指定案例地址做 AI 看圖快取與 token 用量記錄

## 現在最推薦的用法

### 1. 一般使用

```powershell
.\open_search_app.ps1
```

用途：
- 啟動本機搜尋工作台
- 自動重用或更新本機站
- 打開穩定入口頁

### 2. 臨時指定目的地

```powershell
.\search_by_destination.ps1
```

用途：
- 先問你目的地
- 自動啟動本機站
- 刷新較相關的資料池
- 直接打開搜尋頁

### 3. 松仁路 100 號專用案例

```powershell
.\search_songren_100.ps1
```

用途：
- 固定使用 `台北市信義區松仁路100號`
- 自動更新案例資料
- 自動跑案例專用 AI 看圖快取
- 產出案例專用搜尋頁與資料檔

## 案例工作區

目前已經有一個固定案例工作區：

- [songren_100 case.json](/c:/Git/taiwan-rent-search/data/cases/songren_100/case.json)

案例資料夾位置：

- [data/cases/songren_100](/c:/Git/taiwan-rent-search/data/cases/songren_100)

執行後會在本機留下這些檔案：

- `current_dataset.csv`
- `dataset_YYYYMMDD_HHMMSS.csv`
- `search_app.html`
- `latest_run.json`
- `ai_cooking_reviews.json`
- `ai_usage.jsonl`
- `images/`

這些案例產物都只留在本機，不進 git。

## 目前能力

### 資料來源

- `591`
- `MixRent`
- `Housefun`
- `DDRoom`

### 本地工作台

- 穩定入口頁：`data/search_app.html`
- 本機網站控制台：`python -m src.local_site`
- 頁內圖片 gallery，不用一直跳回原站
- 本地標記：`不錯 / 先略過 / 清除標記`
- 一鍵 preset：
  - `先看最能煮飯`
  - `看圖審核`
  - `全部重設`

### 可煮飯方便程度模型

目前已經不是單純看 `流理臺` 字樣，而是輸出分級：

- `適合煮飯`
- `可勉強煮`
- `看圖確認`
- `未提及`

系統會同時顯示：

- 等級
- 判斷理由
- AI 信心（如果有跑圖像判斷）

### AI 看圖

目前已接到松仁路 100 號案例流程：

- 使用 `codex exec` 看圖
- 對候選房源圖片做結構化判斷
- 寫回案例快取
- 記錄 token 用量

## 常用命令

### 抓資料

```powershell
python -m src.main --county 台北市 --source 591 --source mixrent --source housefun --source ddroom --max-pages 3
```

```powershell
python -m src.main --county 台北市 --source 591 --source mixrent --source housefun --source ddroom --max-pages 3 --enrich-591-details --detail-limit 5
```

### 分析

```powershell
python -m src.analysis --destination-address "台北市信義區松仁路100號" --max-commute 30 --transport-mode either --require-cooking-friendly --top 5
```

```powershell
python -m src.analysis --destination-address "台北市信義區松仁路100號" --max-commute 30 --transport-mode either --min-cooking-level 3 --top 5
```

### 建搜尋頁

```powershell
python -m src.webapp
```

### 松仁路 100 號案例

```powershell
python -m src.songren_100_case --open
```

限制 AI 看圖筆數／圖片數：

```powershell
python -m src.songren_100_case --ai-review-max-listings 3 --ai-review-max-images 2 --open
```

## 專案結構

```text
taiwan-rent-search/
├── src/
│   ├── analysis.py
│   ├── ai_cooking_review.py
│   ├── case_workspace.py
│   ├── local_site.py
│   ├── local_site_state.py
│   ├── main.py
│   ├── models.py
│   ├── smart_search.py
│   ├── songren_100_case.py
│   ├── taipei_metro.py
│   ├── webapp.py
│   └── scrapers/
├── tests/
├── docs/
├── data/
│   └── cases/
├── open_search_app.*
├── search_by_destination.*
├── search_songren_100.*
├── README.md
└── PROGRESS.md
```

## 驗證狀態

目前最新驗證基線：

- `pytest tests -q`
- `119 passed`

## 現況總結

已完成：

- 多來源抓取
- 來源級平行化
- 591 詳頁補強
- 本機工作台
- 目的地導向刷新
- 搜尋速度量測與分數
- 可煮飯方便程度分級
- 圖片 gallery
- 本地標記記憶
- 松仁路 100 號專用案例工作區
- AI 看圖快取與 token 用量記錄

還沒完成：

- 通用地址案例模板化（不只松仁路 100 號）
- 更完整的 AI 看圖批次策略與優先級
- 更多平台
- 排程
- 長期資料品質報表

## 你現在最該記住的事

如果只是要用：

- 平常打開：`open_search_app`
- 臨時輸入地址：`search_by_destination`
- 松仁路 100 號反覆使用：`search_songren_100`

你不需要再自己分辨哪個 `*_search_app.html` 才是新的，這件事應該由工具處理。
