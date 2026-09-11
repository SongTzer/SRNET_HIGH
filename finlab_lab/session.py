"""FinLab 登入與資料載入。

登入優先序（與 finlab.auth.get_session 一致）：

1. 環境變數 ``FINLAB_REFRESH_TOKEN`` / ``FINLAB_SESSION_ID`` / ``FINLAB_API_KEY``
   三個都存在時直接使用，適合 CI、伺服器等沒有瀏覽器的環境。
2. 本機加密憑證檔（``python -m finlab login`` 產生）。
3. 以上皆無時開瀏覽器登入。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Protocol

ENV_KEYS = ("FINLAB_REFRESH_TOKEN", "FINLAB_SESSION_ID", "FINLAB_API_KEY")


class DataFrameLike(Protocol):  # pragma: no cover - 型別標註用
    pass


def load_dotenv(path: str | os.PathLike[str] = ".env") -> None:
    """把 .env 讀進 os.environ（不覆蓋既有變數）。

    刻意手寫而不強制依賴 python-dotenv，讓這個模組在最小環境也能運作。
    """
    env_path = Path(path)
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and value and key not in os.environ:
            os.environ[key] = value


def has_env_credentials() -> bool:
    """三個環境變數是否齊全（缺一 finlab 就不會走 env 路徑）。"""
    return all(os.environ.get(k) for k in ENV_KEYS)


def ensure_login(dotenv: str | os.PathLike[str] = ".env") -> None:
    """確保 finlab 已登入，必要時觸發瀏覽器登入流程。"""
    load_dotenv(dotenv)

    import finlab
    from finlab import auth

    if has_env_credentials():
        return

    if auth.get_session() is not None:
        return

    print("找不到 FinLab 憑證，開啟瀏覽器登入……")
    print("（若在無瀏覽器環境，請先在本機執行 `python -m finlab login`，")
    print("  再用 `python -m finlab token` 把三個環境變數寫進 .env）")
    finlab.login()


def loader() -> Callable[[str], object]:
    """回傳 ``finlab.data.get``，策略只依賴這個 callable，方便測試時替換。"""
    from finlab import data

    return data.get
