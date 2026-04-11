# Taiwan Rent Search Web Scraper (台灣租屋爬蟲)

目前專注於台灣租屋爬蟲的基礎框架，已完成 591 房屋的核心 scraper、資料模型與基礎測試；其他平台、資料存儲與展示仍在後續規劃中。

## 項目結構

```
taiwan-rent-search/
├── src/
│   ├── __init__.py
│   ├── analysis.py        # 條件分析、通勤估算、候選排序
│   ├── main.py            # 執行抓取並匯出 CSV
│   ├── models.py          # 數據模型
│   ├── webapp.py          # 產生本地即時搜尋網站
│   └── scrapers/          # 各平台爬蟲
│       ├── __init__.py
│       ├── base.py        # 基礎爬蟲類
│       ├── fang591.py     # 591房屋爬蟲
│       ├── mixrent.py     # MixRent 聚合搜尋爬蟲
│       ├── housefun.py    # 好房網搜尋結果爬蟲
│       └── ddroom.py      # 租租通 API 爬蟲
├── tests/
│   ├── __init__.py
│   └── test_scrapers.py   # 爬蟲測試
├── docs/
│   └── research.md        # 平台研究文檔
├── data/                  # 預留給匯出資料
├── PROGRESS.md            # 進度追蹤
└── requirements.txt
```

## 安裝

```bash
pip install -r requirements.txt
```

## 最簡單用法

```bash
# Windows：直接打開本機搜尋站
.\open_search_app.ps1

# Windows：輸入目的地，會自動啟動本機搜尋站並刷新較相關的資料
.\search_by_destination.ps1
```

現在優先推薦把這個專案當成「本機租屋控制台」來用，不需要先手動產生 `search_app.html`。
只要資料夾裡已經有最新的 CSV，打開本機網站時會自動把它轉成固定入口頁；如果還沒有，你也可以直接在控制台裡輸入目的地並按「更新資料」。

## 使用

```bash
# 安裝依賴
pip install -r requirements.txt

# 執行目前的 scraper 測試
pytest tests/test_scrapers.py -v

# 執行含覆蓋率的驗證
pytest tests/test_scrapers.py -v --cov=src

# 抓取台北市 591 列表並輸出 CSV
python -m src.main --county 台北市

# 抓取多來源並整合輸出 CSV
python -m src.main --county 台北市 --source 591 --source mixrent

# 抓取三來源並整合輸出 CSV
python -m src.main --county 台北市 --source 591 --source mixrent --source housefun

# 抓取四來源並整合輸出 CSV
python -m src.main --county 台北市 --source 591 --source mixrent --source housefun --source ddroom

# 擴量抓取（對支援分頁的來源抓多頁）
python -m src.main --county 台北市 --source 591 --source mixrent --source housefun --source ddroom --max-pages 3

# 補抓 591 詳頁資訊（最短租期、房屋守則、管理費、設備等）
python -m src.main --county 台北市 --source 591 --source mixrent --source housefun --source ddroom --max-pages 3 --enrich-591-details --detail-limit 5

# 依條件分析 CSV 並輸出候選清單
python -m src.analysis --destination-address "台北市信義區松仁路100號" --max-commute 30 --transport-mode either --require-cooking-friendly --top 5

# 產出給人快速瀏覽的 shortlist 報告
# 會同時輸出 analysis.csv + shortlist.md
python -m src.analysis --destination-address "台北市信義區松仁路100號 29樓" --transport-mode either --require-cooking-friendly --top 10

# 產出圖文穿插的 HTML 報告
# 會同時輸出 analysis.csv + shortlist.md + shortlist.html
python -m src.analysis --destination-address "台北市信義區松仁路100號 29樓" --transport-mode either --require-cooking-friendly --top 10

# 產出本地即時搜尋網站
python -m src.webapp --input data\\591-ddroom-housefun-mixrent_taipei_20260406_233623.csv

# 啟動本機網站（建議）
python -m src.local_site

# 先輸入目的地，再更新較相關的資料池並打開搜尋頁
python -m src.smart_search --destination-address "台北市信義區松仁路100號" --open

# Windows 一鍵開啟本機網站
.\open_search_app.ps1

# Windows 目的地導向更新
.\search_by_destination.ps1
```

固定入口檔案是 `data/search_app.html`。現在更推薦直接啟動本機網站，因為可以在網頁裡按「更新資料」而不是回到命令列。
`open_search_app` 會優先重用既有的本機搜尋站；如果預設的 `8765` 埠已被別的程式佔用，會改用其他可用埠，而不會先把對方殺掉。
如果本機搜尋站正在執行，`search_by_destination` / `python -m src.smart_search --open` 也會自動重用那個站點並直接打開對應搜尋頁。
如果本機搜尋站還沒啟動，`search_by_destination.ps1` / `.bat` 也會先幫你把它啟起來，再做目的地更新。
`python -m src.main ...` 在匯出後也會直接印出資料品質摘要，例如來源分布、圖片覆蓋率、樓層資訊覆蓋率與詳頁補強覆蓋率，方便快速判斷這份資料池是否值得繼續分析。

## 進度

- [x] 平台研究
- [x] 591房屋爬蟲框架
- [x] MixRent 聚合爬蟲
- [x] 好房網搜尋爬蟲
- [x] 租租通 API 爬蟲
- [x] 資料模型
- [x] 測試基礎建設與離線解析驗證
- [x] 第一份 591 CSV 匯出
- [x] 可重複使用的條件分析核心
- [x] 人看得懂的 shortlist 報告
- [x] 圖文卡片式 HTML 報告
- [x] 多來源整合輸出
- [x] 三來源資料池
- [x] 四來源資料池
- [x] 現有來源開始擴量
- [x] 四來源多頁資料池
- [x] 本地即時搜尋網站
- [x] 591 詳頁補強
- [ ] 圖片下載 & AI審核
- [ ] 永慶/信義平台
- [x] 數據存儲 (CSV)
- [ ] 排程系統
- [ ] 後端 API
- [ ] 前端網站
