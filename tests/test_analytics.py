"""Unit tests for the analytics engine using hand-checkable series."""
import math
from datetime import date

import numpy as np
import pandas as pd
import pytest

from analytics import metrics as m
from analytics.dips import dip_analysis, find_dip_events
from analytics.simulators import benchmark_path, simulate_lumpsum, simulate_sip, xirr
from analytics.snapshot import compute_snapshot


def growth_series(rate=0.10, years=10, start="2010-01-01"):
    idx = pd.bdate_range(start, periods=int(252 * years))
    t = np.array([(d - idx[0]).days / 365.25 for d in idx])
    return pd.Series(100 * (1 + rate) ** t, index=idx)


def test_cagr_matches_constant_growth():
    s = growth_series(0.10)
    assert m.cagr(s) == pytest.approx(0.10, abs=1e-6)


def test_trailing_returns_have_cagr_for_multi_year():
    s = growth_series(0.12, years=6)
    tr = m.trailing_returns(s)
    assert tr["5Y"]["cagr"] == pytest.approx(0.12, abs=0.002)
    assert tr["10Y"] is None  # not enough history
    assert tr["1M"]["cagr"] is None


def test_volatility_zero_for_smooth_series_and_risk_labels():
    s = growth_series(0.08)
    assert m.annualized_volatility(s) < 0.01  # only weekend-gap effects, no real noise
    assert m.risk_label(0.05) == "Low"
    assert m.risk_label(0.15) == "Medium"
    assert m.risk_label(0.30) == "High"


def test_max_drawdown_and_recovery():
    idx = pd.bdate_range("2020-01-01", periods=7)
    s = pd.Series([100, 120, 90, 60, 80, 121, 130], index=idx, dtype=float)
    dd = m.max_drawdown(s)
    assert dd["depth"] == pytest.approx(-0.5)
    assert dd["peak_date"] == idx[1] and dd["trough_date"] == idx[3]
    assert dd["recovery_date"] == idx[5] and dd["recovered"]


def test_unrecovered_drawdown():
    s = pd.Series([100, 80, 70], index=pd.bdate_range("2020-01-01", periods=3), dtype=float)
    dd = m.max_drawdown(s)
    assert dd["recovered"] is False and dd["recovery_date"] is None


def test_drawdown_episodes():
    s = pd.Series([100, 85, 101, 70, 102, 95], index=pd.bdate_range("2020-01-01", periods=6), dtype=float)
    eps = m.drawdown_episodes(s, 0.10)
    assert len(eps) == 2
    assert eps[0]["depth"] == pytest.approx(-0.15)
    assert eps[1]["depth"] == pytest.approx(70 / 101 - 1)


def test_streaks():
    s = pd.Series([1, 2, 3, 4, 3, 2, 3], index=pd.bdate_range("2021-01-01", periods=7), dtype=float)
    st = m.streaks(s)
    assert st["up"]["days"] == 3 and st["down"]["days"] == 2


def test_real_return():
    assert m.real_return(0.10, 0.06) == pytest.approx(1.10 / 1.06 - 1)
    assert m.real_return(None, 0.05) is None


def test_unadjusted_split_is_back_adjusted():
    from pipeline.cleaning import clean_prices

    idx = pd.bdate_range("2019-01-01", periods=6)
    raw = pd.DataFrame({"close": [3000, 3030, 3060, 30.9, 31.2, 31.5]}, index=idx)  # 1:100 split on day 4
    out = clean_prices(raw)
    assert out["close"].iloc[0] == pytest.approx(30.0, rel=0.02)  # 3000 × (30.9/3060)
    assert m.max_drawdown(out["close"])["depth"] > -0.05


def test_rolling_cagr_constant():
    s = growth_series(0.09, years=8)
    r = m.rolling_cagr(s, 3)
    assert len(r) > 0
    assert r.min() == pytest.approx(0.09, abs=0.003) and r.max() == pytest.approx(0.09, abs=0.003)


def test_xirr_simple_and_degenerate():
    # 100 → 110 in exactly one year = 10%
    assert xirr([(date(2020, 1, 1), -100), (date(2021, 1, 1), 110)]) == pytest.approx(0.0997, abs=0.002)
    assert xirr([(date(2020, 1, 1), -100)]) is None


def test_sip_on_flat_price_returns_zero():
    idx = pd.bdate_range("2020-01-01", "2022-12-31")
    s = pd.Series(50.0, index=idx)
    r = simulate_sip(s, 1000, date(2020, 1, 1))
    assert r["installments"] == 36
    assert r["invested"] == pytest.approx(36000)
    assert r["final_value"] == pytest.approx(36000)
    assert abs(r["xirr"]) < 1e-4


def test_sip_step_up():
    idx = pd.bdate_range("2020-01-01", "2021-12-31")
    s = pd.Series(10.0, index=idx)
    r = simulate_sip(s, 1000, date(2020, 1, 1), step_up_pct=10)
    assert r["invested"] == pytest.approx(12 * 1000 + 12 * 1100)


def test_lumpsum_cagr():
    s = growth_series(0.10, years=6)
    r = simulate_lumpsum(s, 100000, s.index[0].date())
    assert r["cagr"] == pytest.approx(0.10, abs=0.002)
    assert r["xirr"] == pytest.approx(0.10, abs=0.003)


def test_benchmark_path_compounds():
    path = [{"date": pd.Timestamp("2020-01-01"), "invested": 100}, {"date": pd.Timestamp("2021-01-01"), "invested": 100}]
    out = benchmark_path(path, {2020: 10.0, 2021: 10.0})
    assert out[-1]["value"] == pytest.approx(110, rel=1e-3)


def test_dip_events_count_once_per_episode():
    vals = [100, 95, 89, 85, 88, 101, 90, 105]
    s = pd.Series(vals, index=pd.bdate_range("2015-01-01", periods=len(vals)), dtype=float)
    ev = find_dip_events(s, 0.10)
    assert [e["price"] for e in ev] == [89, 90]


def test_dip_analysis_forward_returns():
    idx = pd.bdate_range("2010-01-01", "2016-12-31")
    vals = np.full(len(idx), 100.0)
    vals[300:] = 80.0  # a 20% dip that never recovers until…
    vals[900:] = 120.0
    s = pd.Series(vals, index=idx)
    r = dip_analysis(s, 0.10, horizons=(1, 3))
    assert r["event_count"] == 1
    assert r["summary"]["3y"]["win_rate"] == 1.0
    assert r["summary"]["3y"]["avg_return"] == pytest.approx(0.5)
    assert r["events"][0]["days_to_recover"] is not None


def test_snapshot_is_json_safe():
    import json

    s = growth_series(0.1, years=6) * (1 + 0.01 * np.sin(np.arange(int(252 * 6)) / 7))
    macro = pd.DataFrame({"year": range(2009, 2017), "cpi_inflation": 5.0, "fd_rate": 7.0})
    snap = compute_snapshot(s, macro)
    json.dumps(snap)  # must not raise
    assert snap["risk_label"] in {"Low", "Medium", "High"}
    assert snap["benchmarks"]["avg_inflation"] == pytest.approx(0.05)
    assert not any(isinstance(v, float) and math.isnan(v) for v in snap.values())
