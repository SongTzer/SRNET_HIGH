"""對話三：動能 + 基本面（月營收年增率）。

選股邏輯
    1. 動能：過去 120 個交易日報酬，跳過最近 20 日。
    2. 基本面：月營收年增率 > 10%，讓股價的強勢有基本面撐腰。
    3. 趨勢 + 流動性濾網同對話一。
    4. 每月再平衡，等權重持有 15 檔。

月營收是月頻資料且有公布時間差（次月 10 日前），一律經由
``align_monthly`` 對齊，避免用到當下還沒公布的數字而產生前視偏誤。
"""

from __future__ import annotations

import pandas as pd

from strategies.base import (
    DataGetter,
    Strategy,
    above_ma,
    align_monthly,
    liquidity_filter,
    momentum,
    register,
    top_n,
)

LOOKBACK = 120
SKIP = 20
TREND_MA = 200
REVENUE_YOY_MIN = 0.1
HOLDINGS = 15


def build(get: DataGetter) -> pd.DataFrame:
    close = get("price:收盤價")
    volume = get("price:成交股數")
    revenue = get("monthly_revenue:當月營收")

    revenue_yoy = revenue / revenue.shift(12) - 1
    growth = align_monthly(revenue_yoy, close.index) > REVENUE_YOY_MIN
    growth = growth.reindex(columns=close.columns, fill_value=False)

    score = momentum(close, lookback=LOOKBACK, skip=SKIP)
    tradable = growth & above_ma(close, TREND_MA) & liquidity_filter(volume)

    return top_n(score.where(tradable), HOLDINGS)


STRATEGY = register(
    Strategy(
        name="momentum-revenue",
        description="動能 + 月營收年增率 > 10%，月再平衡持有 15 檔",
        build=build,
        sim_kwargs={
            "resample": "M",
            "position_limit": 1 / HOLDINGS,
            "stop_loss": 0.2,
            "name": "動能：營收成長",
        },
    )
)
