# Taiwan Address Normalizer

[English](README.en.md) | 繁體中文

一個為台灣資料匯入、物流、CRM 與電商流程設計的 Python 地址清洗套件。**零執行期相依套件、不連網、不含座標資料**。

它處理的是「把地址文字整理成一致格式」，不是地理編碼服務，也不會宣稱一個地址真實存在。

## 能處理什麼

- `臺` / `台`、全形半形、空白與常見異體字
- 舊縣市與舊鄉鎮市名稱，例如 `桃園縣八德市` → `桃園市八德區`
- 三碼/五碼郵遞區號
- 中文段號、樓層、地下室、門牌 `38-11號` / `38－11號`
- 舊路名別名，例如 `台中港路` → `台灣大道`
- 缺縣市、缺行政區、缺路名、缺門牌等格式警告
- CSV 批次清洗，保留原始欄位並新增清洗結果與警告

## 安裝

PyPI 發布前請從 repository 安裝：

```bash
pip install git+https://github.com/ted622622/taiwan-address-normalizer.git
```

正式發布 PyPI 後可使用：

```bash
pip install taiwan-address-normalizer
```

## Python API

```python
from taiwan_address_normalizer import normalize, normalize_with_report

normalize(" 臺北市 大同區 延平北路二段57號 3樓 ")
# '台北市大同區延平北路2段57號3F'

result = normalize_with_report("忠孝東路四段")
print(result.normalized)  # 忠孝東路4段
print(result.format_score)  # 25
print(result.warnings)
# ('missing_city_or_county', 'missing_district', 'missing_house_number')
```

`format_score` 只表示地址欄位完整度，不代表地址存在，也不代表地理編碼一定成功。

## Safe 與 Aggressive 模式

預設 `safe` 模式不猜缺少的縣市，也不會擅自捨棄多個門牌：

```python
normalize("桃園縣八德市介壽路一段991、993號")
# '桃園市八德區介壽路1段991、993號'
```

物流匯入情境若已確認「複合門牌只取第一筆」且接受行政區推測，可明確開啟：

```python
normalize("桃園縣八德市介壽路一段991、993號", mode="aggressive")
# '桃園市八德區介壽路1段991號'
```

`aggressive` 另會把 `38-11號` 解讀成 `38之11號`、為路名後的尾數補上 `號`，並在特定歷史資料格式中移除地下室門牌標記。這些規則可能改變原始語意，請先用自己的樣本驗證再啟用。

## CLI

單筆：

```bash
tw-address normalize "臺北市 大安區 忠孝東路四段285號2樓"
```

JSON 報告：

```bash
tw-address normalize "忠孝東路四段" --json
```

CSV 批次：

```bash
tw-address batch orders.csv --column 地址 --output orders.normalized.csv
```

輸入與輸出使用 UTF-8 with BOM，可直接用台灣常見的 Excel 開啟。
為避免 CSV 公式注入，批次輸出預設會在 `=`, `+`, `-`, `@` 開頭的儲存格前加上單引號；只有在完全信任輸入時才使用 `--allow-formulas` 關閉保護。

## 設計邊界

本專案刻意不包含：

- 經緯度、門牌資料庫或 TGOS 資料
- Google Maps、Mapbox 或其他付費 API
- 模糊門牌配對與路線排程
- 任何真實客戶名單或配送資料

地址清洗之後，仍應使用你有權使用的地理編碼服務或門牌資料庫確認位置。

## 警告代碼

| 代碼 | 意義 |
| --- | --- |
| `empty_address` | 沒有地址內容 |
| `not_traditional_chinese_address` | 看起來不是中文台灣地址 |
| `missing_city_or_county` | 缺縣市 |
| `missing_district` | 缺行政區 |
| `missing_road_or_street` | 缺路/街/大道 |
| `missing_house_number` | 缺門牌號 |
| `multiple_house_numbers` | 同一列可能含多個門牌，安全模式不會自行捨棄 |
| `aggressive_rules_applied` | 使用了可能推測或刪減內容的積極模式規則 |

## 貢獻

歡迎提交不含個資的最小重現案例。請使用虛構姓名，並只保留重現格式問題所需的地址文字。詳見 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 授權

MIT License。行政區別名表為台灣行政區名稱與歷史沿革的整理，不包含門牌座標資料；來源與邊界見 [DATA_SOURCES.md](DATA_SOURCES.md)。

本套件源自 [順路王](https://route.runly-ai.com/) 在台灣配送資料匯入流程累積的地址格式處理經驗。
