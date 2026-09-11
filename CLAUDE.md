# FinLab 台股策略研究工作區

用 AI 對話產出台股量化策略，每一段對話的結論都落成一個可回測、可測試的策略模組。

## 環境

- Python 3.9+，虛擬環境在 `.venv`（`bash scripts/setup.sh` 建立）
- 資料來源：FinLab（`finlab` 套件），需登入才能取資料
- 憑證優先序：`.env` 的三個環境變數 → 本機加密憑證 → 瀏覽器登入

## 目錄

| 路徑 | 用途 |
| --- | --- |
| `finlab_lab/session.py` | 登入與 `data.get` 載入器 |
| `finlab_lab/cli.py` | 回測 CLI（`list` / `run`） |
| `strategies/base.py` | `Strategy` 結構、`REGISTRY`、指標工具 |
| `strategies/*.py` | 一段對話 = 一個策略模組 |
| `tests/` | 用合成資料離線驗證策略邏輯 |
| `reports/` | 回測產出（已 gitignore） |

## 對話 → 策略的流程

1. **問清楚要什麼**：選股邏輯、再平衡頻率、持股檔數、停損。
2. **查資料欄位**：用 MCP 的 `get_data_catalog` 確認資料集名稱存在，不要憑印象寫。
   常用：`price:收盤價`、`price:成交股數`、`monthly_revenue:當月營收`、
   `fundamental_features:市值`、`price_earning_ratio:本益比`。
3. **寫成策略模組**：在 `strategies/` 新增檔案，實作 `build(get) -> pd.DataFrame`，
   最後用 `register(Strategy(...))` 登記，並加進 `strategies/__init__.py` 的 import。
4. **補測試**：在 `tests/` 用合成資料測邏輯（不連網）。
5. **回測**：`python -m finlab_lab.cli run <name> --start 2013-04-01`。
6. **回報**：說明指標（年化報酬、最大回檔、夏普），並說出策略的弱點。

## 寫策略的規則

- 只透過傳入的 `get` 取資料，不要在策略模組裡 `import finlab`，否則無法離線測試。
- 運算用純 pandas，讓 `tests/` 可以在沒有憑證的機器上跑。
- **不准有前視偏誤**：月頻／季頻資料一律經過 `align_monthly()`（已處理公布時間差）；
  訊號用到的價格不可晚於下單日。
- 一定要有流動性濾網，回測賺錢但買不到的策略沒有意義。
- 不要拿回測指標當保證，報告時一併說明過度配適的風險。

## 常用指令

```bash
.venv/bin/python -m finlab_lab.cli list
.venv/bin/python -m finlab_lab.cli run momentum --start 2013-04-01
.venv/bin/python -m pytest tests -q
```
