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
│   └── scrapers/          # 各平台爬蟲
│       ├── __init__.py
│       ├── base.py        # 基礎爬蟲類
│       └── fang591.py     # 591房屋爬蟲
│       └── mixrent.py     # MixRent 聚合搜尋爬蟲
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

# 依條件分析 CSV 並輸出候選清單
python -m src.analysis --destination-address "台北市信義區松仁路100號" --max-commute 30 --transport-mode either --require-kitchen-sink --top 5

# 產出給人快速瀏覽的 shortlist 報告
# 會同時輸出 analysis.csv + shortlist.md
python -m src.analysis --destination-address "台北市信義區松仁路100號 29樓" --transport-mode either --require-kitchen-sink --top 10

# 產出圖文穿插的 HTML 報告
# 會同時輸出 analysis.csv + shortlist.md + shortlist.html
python -m src.analysis --destination-address "台北市信義區松仁路100號 29樓" --transport-mode either --require-kitchen-sink --top 10
```

## 進度

- [x] 平台研究
- [x] 591房屋爬蟲框架
- [x] MixRent 聚合爬蟲
- [x] 資料模型
- [x] 測試基礎建設與離線解析驗證
- [x] 第一份 591 CSV 匯出
- [x] 可重複使用的條件分析核心
- [x] 人看得懂的 shortlist 報告
- [x] 圖文卡片式 HTML 報告
- [x] 多來源整合輸出
- [ ] 圖片下載 & AI審核
- [ ] 永慶/信義平台
- [x] 數據存儲 (CSV)
- [ ] 排程系統
- [ ] 後端 API
- [ ] 前端網站
