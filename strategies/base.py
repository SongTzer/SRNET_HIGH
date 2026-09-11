"""策略共用結構與指標工具。

設計原則：策略只透過 ``get`` (即 ``finlab.data.get``) 取資料，並且所有運算都是
純 pandas，因此不需要連線 FinLab 也能對策略邏輯做單元測試。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict

import pandas as pd

#: 取資料的函式型別，實務上是 ``finlab.data.get``
DataGetter = Callable[[str], pd.DataFrame]


@dataclass(frozen=True)
class Strategy:
    """一個可回測的策略。

    Attributes:
        name: 策略代號，CLI 用這個名字呼叫。
        description: 一句話說明選股邏輯。
        build: 吃 ``DataGetter``，回傳持股訊號（True = 持有）。
        sim_kwargs: 傳給 ``finlab.backtest.sim`` 的參數。
    """

    name: str
    description: str
    build: Callable[[DataGetter], pd.DataFrame]
    sim_kwargs: Dict[str, object] = field(default_factory=dict)


REGISTRY: Dict[str, Strategy] = {}


def register(strategy: Strategy) -> Strategy:
    """把策略登記到 REGISTRY，重複命名直接報錯以免被靜默覆蓋。"""
    if strategy.name in REGISTRY:
        raise ValueError(f"策略名稱重複：{strategy.name}")
    REGISTRY[strategy.name] = strategy
    return strategy


# ---------------------------------------------------------------------------
# 指標工具
# ---------------------------------------------------------------------------


def top_n(score: pd.DataFrame, n: int) -> pd.DataFrame:
    """每一列（每個交易日）取分數最高的 n 檔，回傳布林 DataFrame。

    等價於 FinLab 的 ``score.is_largest(n)``，這裡用純 pandas 實作，
    讓策略可以離線測試。NaN 不會被選入。
    """
    if n <= 0:
        raise ValueError("n 必須為正整數")
    ranked = score.rank(axis=1, ascending=False, method="first")
    return (ranked <= n) & score.notna()


def momentum(close: pd.DataFrame, lookback: int, skip: int = 0) -> pd.DataFrame:
    """動能 = 過去 ``lookback`` 個交易日報酬，並跳過最近 ``skip`` 日。

    跳過最近一個月是學術上的標準做法：短期有反轉效應，直接用會稀釋動能。
    """
    if lookback <= 0:
        raise ValueError("lookback 必須為正整數")
    base = close.shift(skip)
    return base / base.shift(lookback) - 1


def liquidity_filter(
    volume: pd.DataFrame, window: int = 60, min_lots: float = 500
) -> pd.DataFrame:
    """成交量濾網：近 ``window`` 日平均成交量需大於 ``min_lots`` 張。

    ``price:成交股數`` 單位是股，1 張 = 1000 股。流動性濾網是動能策略能不能
    真的下單的關鍵，回測看起來很好卻買不到的股票多半死在這裡。
    """
    avg_lots = volume.rolling(window, min_periods=window // 2).mean() / 1000
    return avg_lots > min_lots


def above_ma(close: pd.DataFrame, window: int) -> pd.DataFrame:
    """股價站上 ``window`` 日均線（長線多頭濾網）。"""
    return close > close.rolling(window, min_periods=window // 2).mean()


_MONTH_INDEX = re.compile(r"^(\d{4})-M(\d{1,2})$")


def month_index_to_date(index: pd.Index) -> pd.DatetimeIndex:
    """把 FinLab 月營收的 ``'2024-M3'`` 索引轉成該月月底日期。"""
    parsed = []
    for value in index:
        match = _MONTH_INDEX.match(str(value))
        if match is None:
            raise ValueError(f"無法解析的月份索引：{value!r}")
        year, month = int(match.group(1)), int(match.group(2))
        parsed.append(pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0))
    return pd.DatetimeIndex(parsed)


def align_monthly(
    monthly: pd.DataFrame, daily_index: pd.Index, publish_lag_days: int = 10
) -> pd.DataFrame:
    """把月頻資料對齊到日頻索引，並考慮公布時間差以避免前視偏誤。

    台股月營收依規定在次月 10 日前公布，所以 3 月的營收最快 4/10 才能用。
    FinLab 的 ``FinlabDataFrame.deadline()`` 做的是同一件事；這裡在拿得到
    ``deadline`` 時直接沿用官方實作，否則退回手動平移。
    """
    df = monthly
    deadline = getattr(df, "deadline", None)
    if callable(deadline):
        shifted = deadline()
    else:
        shifted = df.copy()
        shifted.index = month_index_to_date(df.index) + pd.Timedelta(days=publish_lag_days)

    shifted = shifted.sort_index()
    target = pd.DatetimeIndex(daily_index)
    return shifted.reindex(shifted.index.union(target)).ffill().reindex(target)
