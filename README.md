# FinLab 台股策略工作區

用 AI 對話產策略、用 FinLab 回測台股。三個現成的動能策略，加上一套可以持續長出新策略的流程。

## 1. 安裝

先裝好 [Python 3.9+](https://www.python.org/downloads/)（Windows 安裝時務必勾選 **Add python.exe to PATH**）與 Git。

**Windows（CMD）**

```bat
git clone https://github.com/SongTzer/SRNET_HIGH.git
cd SRNET_HIGH
scripts\setup.bat
```

**macOS / Linux**

```bash
git clone https://github.com/SongTzer/SRNET_HIGH.git
cd SRNET_HIGH
bash scripts/setup.sh
```

安裝腳本會建立 `.venv`、安裝套件、開瀏覽器登入 FinLab，最後抓一次收盤價確認連線正常。

想手動做也可以：

```bat
REM Windows CMD
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m finlab login
```

```bash
# macOS / Linux
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m finlab login
```

> 之後所有指令，Windows 用 `.venv\Scripts\python.exe`，macOS / Linux 用 `.venv/bin/python`，其餘參數完全一樣。
> 本文以下範例寫 macOS / Linux 的路徑，Windows 請自行替換。

## 2. 登入與憑證

FinLab 2.x 已改成瀏覽器登入，憑證加密存在本機，**不需要**在程式碼裡寫 api_token。

| 情境 | 做法 |
| --- | --- |
| 本機 / Notebook | `python -m finlab login` |
| 伺服器、CI、Colab 等無瀏覽器環境 | 先在本機登入，再 `python -m finlab token` 把三個環境變數寫進 `.env` |
| 確認狀態 | `python -m finlab status` |
| 登出 | `python -m finlab logout` |

`.env` 的三個變數（`FINLAB_REFRESH_TOKEN`、`FINLAB_SESSION_ID`、`FINLAB_API_KEY`）要嘛全填、要嘛全空，
缺一個 finlab 就會忽略環境變數退回瀏覽器登入。`.env` 已在 `.gitignore`，不要提交。

## 3. 接上 AI Agent

專案內附 `.mcp.json`，在專案目錄開 Claude Code 就會載入 FinLab 官方 MCP server：

```json
{ "mcpServers": { "finlab": { "type": "http", "url": "https://mcp.finlab.finance/mcp" } } }
```

也可以用指令加：

```bash
claude mcp add --transport http finlab https://mcp.finlab.finance/mcp
```

或安裝官方 CLI skill（會自動偵測環境並裝好 `uv`）：

```bash
curl -sSf https://ai.finlab.finance/install.sh | sh
```

MCP 提供的工具：`how_to_start`、`get_data_catalog`（900+ 欄位、80+ 資料表）、
`list_strategies`、`get_strategy`、`get_stock_evidence`、`get_finlab_docs`。

對話時 AI 該遵守的流程寫在 [`CLAUDE.md`](CLAUDE.md)：查資料目錄 → 寫策略模組 → 補測試 → 回測 → 說明弱點。

## 4. 跑回測

```bash
.venv/bin/python -m finlab_lab.cli list
.venv/bin/python -m finlab_lab.cli run momentum --start 2013-04-01
.venv/bin/python -m finlab_lab.cli run breakout --start 2013-04-01 --end 2026-08-31
.venv/bin/python -m finlab_lab.cli run momentum-revenue --start 2013-04-01
```

指標會印在畫面上並存成 `reports/<策略>.json`，互動式報表存成 `reports/<策略>.html`。
預設**不會**上傳到 FinLab 雲端，要上傳請加 `--upload`。

## 5. 內建策略

| 名稱 | 邏輯 | 再平衡 | 持股 |
| --- | --- | --- | --- |
| `momentum` | 12-1 相對強弱動能 + 200 日均線 + 流動性濾網 | 月 | 20 |
| `breakout` | 250 日新高 + 量能放大 1.5 倍 + 流動性濾網 | 週 | 15 |
| `momentum-revenue` | 動能 + 月營收年增率 > 10% | 月 | 15 |

三支都套了停損（`breakout` 另有移動停利），細節看各策略模組開頭的 docstring。

## 6. 新增策略

在 `strategies/` 開一個檔案：

```python
from strategies.base import DataGetter, Strategy, register, top_n, momentum

def build(get: DataGetter):
    close = get("price:收盤價")
    return top_n(momentum(close, lookback=120, skip=20), 20)

STRATEGY = register(Strategy(
    name="my-strategy",
    description="一句話說明",
    build=build,
    sim_kwargs={"resample": "M", "position_limit": 0.05},
))
```

再把模組加進 `strategies/__init__.py` 的 import，就會出現在 `cli list`。

策略只透過傳進來的 `get` 取資料、運算全用純 pandas，所以 `tests/` 可以用合成資料離線驗證：

```bash
.venv/bin/python -m pytest tests -q
```

## 7. 注意事項

- 月頻／季頻資料一律用 `strategies.base.align_monthly()` 對齊，它已處理台股月營收「次月 10 日前公布」的
  時間差；直接拿月營收跟當月股價對齊會產生前視偏誤，回測數字會假得很漂亮。
- 回測有交易成本假設（`sim` 的 `fee_ratio` / `tax_ratio`），但沒有滑價與流動性衝擊，小型股實際成交會更差。
- 參數是挑過的，任何回測指標都不是未來報酬的保證。換一段期間再測一次，看策略還站不站得住。

## 8. Windows 常見問題

| 症狀 | 處理 |
| --- | --- |
| `'python' 不是內部或外部命令` | 重裝 Python 並勾選 Add python.exe to PATH，或改用 `py -3` 取代 `python` |
| 中文顯示成亂碼 | 在 CMD 先跑 `chcp 65001` 與 `set PYTHONUTF8=1`（`setup.bat` 已內建） |
| 把輸出導到檔案時出現 `UnicodeEncodeError` | 同上，設定 `set PYTHONUTF8=1` 再執行 |
| `.venv\Scripts\Activate.ps1 因為在此系統上禁止執行指令碼` | 不用 activate，直接呼叫 `.venv\Scripts\python.exe` 即可 |
| 登入視窗沒跳出來 | 手動複製終端機印出的網址到瀏覽器；或改用 `.env` 的三個環境變數 |
