"""離線測試：用合成資料驗證策略邏輯，不需要 FinLab 憑證或網路。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from strategies import REGISTRY
from strategies.base import align_monthly, liquidity_filter, momentum, top_n

STOCKS = [f"{1000 + i}" for i in range(12)]
DAYS = 900


@pytest.fixture(scope="module")
def fake_data() -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(20260911)
    index = pd.bdate_range("2020-01-01", periods=DAYS)

    drift = np.linspace(-0.0004, 0.0008, len(STOCKS))
    steps = rng.normal(drift, 0.02, size=(DAYS, len(STOCKS)))
    close = pd.DataFrame(100 * np.exp(np.cumsum(steps, axis=0)), index=index, columns=STOCKS)

    volume = pd.DataFrame(
        rng.lognormal(mean=14.5, sigma=0.5, size=(DAYS, len(STOCKS))),
        index=index,
        columns=STOCKS,
    )

    months = pd.PeriodIndex(pd.date_range("2019-01-01", periods=60, freq="MS"), freq="M")
    revenue = pd.DataFrame(
        rng.lognormal(mean=12, sigma=0.3, size=(60, len(STOCKS))),
        index=[f"{p.year}-M{p.month}" for p in months],
        columns=STOCKS,
    )

    return {
        "price:收盤價": close,
        "price:成交股數": volume,
        "monthly_revenue:當月營收": revenue,
    }


@pytest.fixture
def get(fake_data):
    def _get(dataset: str) -> pd.DataFrame:
        return fake_data[dataset].copy()

    return _get


def test_top_n_selects_exactly_n_per_row():
    score = pd.DataFrame(
        [[3.0, 1.0, 2.0, 4.0], [1.0, 4.0, 3.0, 2.0]], columns=list("abcd")
    )
    selected = top_n(score, 2)
    assert selected.sum(axis=1).tolist() == [2, 2]
    assert selected.loc[0].tolist() == [True, False, False, True]
    assert selected.loc[1].tolist() == [False, True, True, False]


def test_top_n_ignores_nan():
    score = pd.DataFrame([[np.nan, 1.0, 2.0]], columns=list("abc"))
    selected = top_n(score, 2)
    assert selected.loc[0].tolist() == [False, True, True]


def test_momentum_skips_recent_window():
    close = pd.DataFrame({"a": [1.0] * 10 + [2.0] * 5})
    # skip=5 時，最近 5 天的漲幅還沒進入動能計算。
    assert momentum(close, lookback=5, skip=5).iloc[-1]["a"] == pytest.approx(0.0)
    assert momentum(close, lookback=5, skip=0).iloc[-1]["a"] == pytest.approx(1.0)


def test_liquidity_filter_threshold():
    volume = pd.DataFrame({"a": [1_000_000.0] * 60, "b": [100_000.0] * 60})
    result = liquidity_filter(volume, window=60, min_lots=500)
    assert bool(result.iloc[-1]["a"])
    assert not bool(result.iloc[-1]["b"])


def test_align_monthly_has_no_lookahead():
    monthly = pd.DataFrame({"a": [1.0, 2.0]}, index=["2024-M1", "2024-M2"])
    daily = pd.bdate_range("2024-02-01", "2024-03-31")
    aligned = align_monthly(monthly, daily)

    # 1 月營收要到 2/10 之後才看得到，2/1 當天必須是 NaN。
    assert pd.isna(aligned.loc[pd.Timestamp("2024-02-01"), "a"])
    assert aligned.loc[pd.Timestamp("2024-02-15"), "a"] == 1.0
    # 2 月營收在 3/10 之後才生效。
    assert aligned.loc[pd.Timestamp("2024-03-05"), "a"] == 1.0
    assert aligned.loc[pd.Timestamp("2024-03-15"), "a"] == 2.0


@pytest.mark.parametrize("name", sorted(REGISTRY))
def test_strategy_builds_valid_position(name, get):
    strategy = REGISTRY[name]
    position = strategy.build(get)

    assert isinstance(position, pd.DataFrame)
    assert position.dtypes.unique().tolist() == [np.dtype("bool")]

    holdings = int(1 / strategy.sim_kwargs["position_limit"])
    assert position.sum(axis=1).max() <= holdings
    # 合成資料上至少要選得出東西，否則代表濾網把所有標的都擋掉了。
    assert position.sum(axis=1).max() > 0


@pytest.mark.parametrize("name", sorted(REGISTRY))
def test_strategy_has_sim_config(name):
    strategy = REGISTRY[name]
    assert strategy.sim_kwargs["resample"] in {"M", "W", "Q"}
    assert strategy.description
