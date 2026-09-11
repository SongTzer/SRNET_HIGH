"""對話一：相對強弱動能（12-1 momentum）。

選股邏輯
    1. 動能：過去 240 個交易日報酬，跳過最近 20 日（避開短期反轉）。
    2. 趨勢濾網：股價需站上 200 日均線，空頭時不硬做多。
    3. 流動性濾網：近 60 日均量 > 500 張，確保買得到也賣得掉。
    4. 每月最後一個交易日再平衡，等權重持有動能最強的 20 檔。
"""

from __future__ import annotations

import pandas as pd

from strategies.base import (
    DataGetter,
    Strategy,
    above_ma,
    liquidity_filter,
    momentum,
    register,
    top_n,
)

LOOKBACK = 240
SKIP = 20
TREND_MA = 200
HOLDINGS = 20


def build(get: DataGetter) -> pd.DataFrame:
    close = get("price:收盤價")
    volume = get("price:成交股數")

    score = momentum(close, lookback=LOOKBACK, skip=SKIP)
    tradable = above_ma(close, TREND_MA) & liquidity_filter(volume)

    # 先濾掉不可交易的標的再排名，否則名次會被買不到的股票占走。
    return top_n(score.where(tradable), HOLDINGS)


STRATEGY = register(
    Strategy(
        name="momentum",
        description="12-1 相對強弱動能，月再平衡持有 20 檔",
        build=build,
        sim_kwargs={
            "resample": "M",
            "position_limit": 1 / HOLDINGS,
            "stop_loss": 0.2,
            "name": "動能：相對強弱",
        },
    )
)
