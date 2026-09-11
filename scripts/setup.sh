#!/usr/bin/env bash
# FinLab 環境一鍵設定：建立虛擬環境、安裝套件、登入、驗證資料連線。
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-python3}"
VENV="${VENV:-.venv}"

echo "==> 建立虛擬環境 $VENV"
"$PYTHON" -m venv "$VENV"

echo "==> 安裝套件"
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install -r requirements-dev.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "==> 已建立 .env（headless 環境才需要填）"
fi

echo "==> 登入 FinLab（會開啟瀏覽器，已登入則直接跳過）"
"$VENV/bin/python" -m finlab login

echo "==> 驗證資料連線"
"$VENV/bin/python" - <<'PY'
from finlab import data

close = data.get("price:收盤價")
print(f"台股收盤價：{close.shape[1]} 檔，{close.index[0].date()} ~ {close.index[-1].date()}")
PY

echo
echo "完成。接著可以跑："
echo "  $VENV/bin/python -m finlab_lab.cli list"
echo "  $VENV/bin/python -m finlab_lab.cli run momentum --start 2013-04-01"
