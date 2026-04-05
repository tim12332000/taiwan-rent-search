# Taiwan Rent Search Web Scraper (台灣租屋爬蟲)

目前專注於台灣租屋爬蟲的基礎框架，已完成 591 房屋的核心 scraper、資料模型與基礎測試；其他平台、資料存儲與展示仍在後續規劃中。

## 項目結構

```
taiwan-rent-search/
├── src/
│   ├── __init__.py
│   ├── models.py          # 數據模型
│   └── scrapers/          # 各平台爬蟲
│       ├── __init__.py
│       ├── base.py        # 基礎爬蟲類
│       └── fang591.py     # 591房屋爬蟲
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
```

## 進度

- [x] 平台研究
- [x] 591房屋爬蟲框架
- [x] 資料模型
- [x] 測試基礎建設與離線解析驗證
- [ ] 圖片下載 & AI審核
- [ ] 永慶/信義平台
- [ ] 數據存儲 (CSV)
- [ ] 排程系統
- [ ] 後端 API
- [ ] 前端網站
