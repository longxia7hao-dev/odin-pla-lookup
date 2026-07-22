# 解放軍武器 · 裝備 · 載具速查（ODIN 風格）

單機網頁工具，用於快速查找**解放軍武器、裝備、載具**。介面為**繁體中文**，資料欄位對齊美軍 **ODIN Worldwide Equipment Guide (WEG)** 常見結構。

## 快速開始

### 方法一：直接開啟（完全單機）

雙擊 `index.html` 即可（資料以 JS 載入，無需伺服器）。

### 方法二：本機伺服器

```bash
cd ~/odin-pla-lookup
./start.sh
```

瀏覽器會開啟 `http://127.0.0.1:8877/`。

### 手機區網瀏覽

1. 電腦執行 `./start.sh`（預設會監聽區網）。
2. 手機與電腦連**同一個 Wi‑Fi**。
3. 手機瀏覽器開啟終端機顯示的區網網址，例如：`http://192.168.x.x:8877/`。

若連不上：檢查 macOS「系統設定 → 網路 → 防火牆」是否阻擋 Python；或確認手機不是用行動數據。

## 功能

| 功能 | 說明 |
|------|------|
| 即時搜尋 | 型號、中英文名、別名、標籤、口徑 |
| 分類篩選 | 武器 / 裝備 / 載具 |
| 規格詳情 | 口徑、乘員、重量、射程、防護、機動、感測等 |
| 繁中＋英文 | 主介面與條目以繁中為主，英文並列 |
| JSON 匯入 | 合併你從 ODIN 整理的資料 |
| JSON 匯出 | 匯出目前完整資料庫 |
| 照片 | **本機縮圖**（`assets/images/`）優先，列表＋詳情大圖；缺圖有占位 |
| 離線 | 文字＋已下載照片可離線；未下載者占位；匯入存於瀏覽器 |

## ODIN 資料整合方式

1. 在瀏覽器開啟 [ODIN WEG](https://odin.t2com.army.mil/WEG)（或 `odin.tradoc.army.mil`）。
2. 依中國／PLA 裝備條目整理為 JSON（見 `data/schema.example.json`）。
3. 在本工具點 **「匯入 ODIN／JSON」** 貼上或選檔。
4. 建議每筆填 `odin_url` 連回官方條目。

> 注意：ODIN 站台可能需特定網路環境。本機工具**不是**官方鏡像，內建資料為公開來源整理，供訓練參考。

## 資料欄位

| 欄位 | 說明 |
|------|------|
| `id` | 唯一識別 |
| `name_zh` / `name_en` | 繁中／英文名稱 |
| `designation` | 型號 |
| `category` | `weapon` \| `equipment` \| `vehicle` |
| `subcategory` | 如 `mbt`、`sam`、`uav` |
| `caliber`, `crew`, `weight_kg`, `range_m`… | 規格 |
| `notes_zh` / `notes_en` | 說明 |
| `tags` | 搜尋標籤 |
| `odin_hint` / `odin_url` | WEG 分類提示／官方連結 |

## 目錄

```
odin-pla-lookup/
├── index.html
├── start.sh
├── css/styles.css
├── js/equipment-data.js   # 內建資料
├── js/app.js
├── data/schema.example.json
└── README.md
```

## 免責

僅供教育與訓練參考。正式引用請以 [ODIN](https://odin.t2com.army.mil/) 官方 WEG 為準。
