@echo off
REM FinLab 環境一鍵設定（Windows / CMD）：建立虛擬環境、安裝套件、登入、驗證資料連線。
setlocal

cd /d "%~dp0.."

REM 讓中文輸出不會亂碼
chcp 65001 >nul
set PYTHONUTF8=1

if not defined PYTHON set PYTHON=python

echo ==^> 建立虛擬環境 .venv
%PYTHON% -m venv .venv
if errorlevel 1 (
    echo 建立虛擬環境失敗，請確認已安裝 Python 3.9+ 並勾選 "Add python.exe to PATH"
    exit /b 1
)

echo ==^> 安裝套件
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if errorlevel 1 exit /b 1

if not exist .env (
    copy .env.example .env >nul
    echo ==^> 已建立 .env（headless 環境才需要填）
)

echo ==^> 登入 FinLab（會開啟瀏覽器，已登入則直接跳過）
.venv\Scripts\python.exe -m finlab login
if errorlevel 1 exit /b 1

echo ==^> 驗證資料連線
.venv\Scripts\python.exe -c "from finlab import data; c = data.get('price:收盤價'); print(f'台股收盤價：{c.shape[1]} 檔，{c.index[0].date()} ~ {c.index[-1].date()}')"
if errorlevel 1 exit /b 1

echo.
echo 完成。接著可以跑：
echo   .venv\Scripts\python.exe -m finlab_lab.cli list
echo   .venv\Scripts\python.exe -m finlab_lab.cli run momentum --start 2013-04-01
