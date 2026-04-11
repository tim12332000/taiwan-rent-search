# 台灣租屋搜尋工作台 - 進度追蹤

**最後更新**: 2026-04-12

## 目前定位

這個專案目前已經從「爬蟲原型」演進成「本機租屋審核工作台」。

核心目標：

- 抓到足夠多的候選房源
- 用目的地與通勤快速縮小範圍
- 以「可煮飯方便程度」作為重要決策軸
- 在本地完成大部分篩選、看圖、標記與複查

## 已完成

### 1. 資料抓取

- [x] `591` 列表抓取
- [x] `MixRent` 聚合抓取
- [x] `Housefun` 搜尋結果抓取
- [x] `DDRoom` API 抓取
- [x] 多來源合併與去重
- [x] 來源級平行抓取
- [x] 591 詳頁補強

### 2. 本地工作台

- [x] 穩定入口 `data/search_app.html`
- [x] 本機網站控制台 `src.local_site`
- [x] 目的地導向刷新 `src.smart_search`
- [x] 舊版背景本機站自動重啟，避免 `.bat` 點開還看到舊 UI
- [x] 搜尋速度量測、分數、優化提示

### 3. 可煮飯方便程度

- [x] 從「流理臺字樣」改成更接近實際需求的分級
- [x] 分級：
  - `適合煮飯`
  - `可勉強煮`
  - `看圖確認`
  - `未提及`
- [x] 排除浴室洗手台 / 洗面盆 / 衛浴語境誤判
- [x] 搜尋頁可按可煮飯等級篩選
- [x] CLI 可用 `--min-cooking-level`
- [x] 分析 CSV 會輸出：
  - `cooking_convenience_score`
  - `cooking_convenience_label`
  - `cooking_convenience_reason`

### 4. 圖片審核流程

- [x] 頁內圖片 gallery
- [x] 可煮飯判斷理由直接顯示在卡片與圖庫裡
- [x] 一鍵 preset：
  - `先看最能煮飯`
  - `看圖審核`
  - `全部重設`
- [x] 本地標記記憶：
  - `不錯`
  - `先略過`
  - `清除標記`

### 5. 松仁路 100 號專用案例

- [x] 固定案例工作區：
  - `data/cases/songren_100/`
- [x] 專用啟動腳本：
  - `search_songren_100.bat`
  - `search_songren_100.ps1`
- [x] 自動產出：
  - `current_dataset.csv`
  - `dataset_*.csv`
  - `search_app.html`
  - `latest_run.json`

### 6. AI 看圖

- [x] 松仁路 100 號案例已接入 AI 圖片判斷
- [x] 只對有限候選做圖像判定
- [x] 本地快取：
  - `ai_cooking_reviews.json`
- [x] token / usage 記錄：
  - `ai_usage.jsonl`
- [x] 搜尋頁可吃到案例 AI verdict、理由、信心

## 最新驗證

- [x] `pytest tests -q`
- [x] 最新基線：`119 passed`
- [x] `python -m src.songren_100_case --base-max-pages 1 --focus-max-pages 1 --detail-limit 5 --ai-review-max-listings 3 --ai-review-max-images 2`
- [x] 已成功產出松仁路 100 號案例資料、AI 快取與 usage log

## 目前主要工作流

### 一般工作流

1. `open_search_app`
2. 直接在本機網站搜尋 / 篩選 / 看圖 / 標記

### 臨時地址工作流

1. `search_by_destination`
2. 輸入地址
3. 自動刷新較相關資料池

### 松仁路 100 號重複工作流

1. `search_songren_100`
2. 自動更新案例資料
3. 自動跑 AI 看圖（受快取與上限控制）
4. 在案例搜尋頁複查與標記

## 當前缺口

### 高優先

- [ ] 把 AI 看圖結果更明顯地排序到搜尋頁前面
- [ ] 把 AI cache 命中 / 未命中 / 本輪花費量顯示到前台
- [ ] 讓本地標記（不錯/先略過）可輸出成正式 shortlist 檔案
- [ ] 把「案例工作區」從松仁路 100 號推廣成通用模板

### 中優先

- [ ] AI 圖片挑選策略更聰明
  - 優先挑可能是廚房的圖
  - 避免把純外觀圖也送進去浪費 token
- [ ] AI confidence 與文字規則衝突時的顯示策略
- [ ] 資料品質統計頁
  - 缺欄位率
  - 來源分布
  - 詳頁補強覆蓋率

### 低優先

- [ ] 新平台
- [ ] 排程
- [ ] SQLite / 長期存儲
- [ ] API / 正式網站化

## 下一步建議

最有價值的下一步不是再加一個入口，而是把目前已有流程再收斂成更少決策成本：

1. 前台顯示 AI 看圖快取命中與 token 使用摘要
2. 本地標記可一鍵匯出成 shortlist
3. 通用案例模板化，讓新的地址也能複製松仁路 100 號模式

## 備註

這份文件現在只記：

- 真正已完成的能力
- 目前穩定可用的工作流
- 還沒完成但值得做的缺口

不再保留早期原型期的過時待辦與舊命令。
