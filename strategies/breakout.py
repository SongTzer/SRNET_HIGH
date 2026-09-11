"""對話二：創新高突破 + 量能確認。

選股邏輯
    1. 突破：收盤價創 250 日新高（一年新高）。
    2. 量能確認：突破當日成交量 > 近 60 日均量的 1.5 倍，過濾無量假突破。
    3. 流動性濾網：近 60 日均量 > 500 張。
    4. 每週再平衡，等權重持有近期動能最強的 15 檔。

這是 FinLab 首頁那個 ``close >= close.rolling(300).max()`` 範例的完整版：
加上量能與流動性後才是可以真的下單的策略。
"""

from __future__ import annotations

import pandas as pd

from strategies.base import (
    DataGetter,
    Strategy,
    liquidity_filter,
    momentum,
    register,
    top_n,
)

BREAKOUT_WINDOW = 250
VOLUME_WINDOW = 60
VOLUME_RATIO = 1.5
HOLDINGS = 15


def build(get: DataGetter) -> pd.DataFrame:
    close = get("price:收盤價")
    volume = get("price:成交股數")

    high_water = close.rolling(BREAKOUT_WINDOW, min_periods=BREAKOUT_WINDOW // 2).max()
    breakout = close >= high_water

    avg_volume = volume.rolling(VOLUME_WINDOW, min_periods=VOLUME_WINDOW // 2).mean()
    volume_surge = volume > avg_volume * VOLUME_RATIO

    entry = breakout & volume_surge & liquidity_filter(volume, window=VOLUME_WINDOW)

    # 同一天可能有幾十檔一起突破，用短期動能決定誰先進場。
    score = momentum(close, lookback=60)
    return top_n(score.where(entry), HOLDINGS)


STRATEGY = register(
    Strategy(
        name="breakout",
        description="250 日新高 + 量能確認，週再平衡持有 15 檔",
        build=build,
        sim_kwargs={
            "resample": "W",
            "position_limit": 1 / HOLDINGS,
            "stop_loss": 0.15,
            "trail_stop": 0.2,
            "name": "動能：突破新高",
        },
    )
)
