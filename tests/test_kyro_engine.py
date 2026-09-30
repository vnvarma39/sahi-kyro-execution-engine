#!/usr/bin/env python3
"""
Comprehensive Pytest Verification Suite — Sahi Kyro-Execution & Pulse Engine
============================================================================
Verifies mathematical invariants, sub-millisecond latency SLAs, Hedged-First
leg ordering, and harvested dataset integrity across all 4 quantitative pillars.
"""

import os
import sys
import json
import time
import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from engine.kyro_execution_engine import (
        VectorizedBSMEngine,
        GEXFlowEngine,
        RegimeGatedMLMetaController,
        PulseToPayoffCompiler,
        TiltGuardRMS,
        SlippageShieldEngine,
        SahiKyroExecutionEngine,
        OrderRequest,
        OrderSide,
        OrderType,
        OptionType,
        MarketRegime,
        RMSVerdict,
        TraderAccountState,
        Level2Depth,
    )
except ImportError:
    from sahi.engine.kyro_execution_engine import (
        VectorizedBSMEngine,
        GEXFlowEngine,
        RegimeGatedMLMetaController,
        PulseToPayoffCompiler,
        TiltGuardRMS,
        SlippageShieldEngine,
        SahiKyroExecutionEngine,
        OrderRequest,
        OrderSide,
        OrderType,
        OptionType,
        MarketRegime,
        RMSVerdict,
        TraderAccountState,
        Level2Depth,
    )

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def test_pillar1_vectorized_bsm_1st_and_2nd_order_greeks():
    bsm = VectorizedBSMEngine()
    strikes = np.linspace(22000, 23500, 31)
    t0 = time.perf_counter()
    ce = bsm.compute_greeks(22716.20, strikes, 4.0 / 365.0, 0.135, "CE")
    pe = bsm.compute_greeks(22716.20, strikes, 4.0 / 365.0, 0.135, "PE")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert elapsed_ms < 15.0
    assert np.all(ce["delta"] > 0.0) and np.all(ce["delta"] <= 1.0)
    assert np.all(pe["delta"] < 0.0) and np.all(pe["delta"] >= -1.0)
    assert np.all(ce["gamma"] > 0.0)
    assert np.allclose(ce["gamma"], pe["gamma"], atol=1e-6)
    assert "vanna" in ce and "charm" in ce


def test_pillar1_gex_surface_and_zero_gamma_flip():
    gex_engine = GEXFlowEngine()
    strikes = np.array([22500, 22600, 22700, 22800, 22900], dtype=np.float64)
    call_oi = np.array([100000, 200000, 450000, 900000, 1200000], dtype=np.float64)
    put_oi = np.array([1100000, 850000, 500000, 200000, 90000], dtype=np.float64)
    ivs = np.full_like(strikes, 0.14)

    res = gex_engine.calculate_gex_surface(22716.20, strikes, call_oi, put_oi, 4.0 / 365.0, ivs, ivs, 75)
    assert 22500.0 <= res["zero_gamma_flip"] <= 22900.0
    assert res["regime"] in [
        MarketRegime.POSITIVE_GAMMA_MEAN_REVERTING.value,
        MarketRegime.NEGATIVE_GAMMA_DIRECTIONAL.value,
    ]


def test_pillar1_regime_gated_nadaraya_watson_and_lorentzian_knn():
    ml = RegimeGatedMLMetaController()
    X = np.arange(100, dtype=np.float64)
    Y = 22700.0 + 40.0 * np.sin(X / 8.0)
    fv, std = ml.nadaraya_watson_fair_value(99.0, X, Y, 0.14, 0.14)
    assert 22600.0 <= fv <= 22800.0 and std > 0.0

    rng = np.random.default_rng(42)
    db = rng.normal(0, 1, size=(250, 6))
    labels = (db[:, 0] + db[:, 1] > 0).astype(int)
    query = np.array([1.5, 1.2, 0.4, 0.8, 1.1, -0.3])
    out = ml.lorentzian_distance_knn(query, db, labels, k=7)
    assert 0.0 <= out["probability_bullish_breakout"] <= 1.0
    assert out["signal"] in ["BULL_BREAKOUT", "BEAR_BREAKDOWN", "NEUTRAL"]


@pytest.mark.parametrize(
    "prompt,expected_name",
    [
        ("Hedge downside crash below 22500", "Bear Put Debit Spread"),
        ("Order win rally bullish breakout", "Bull Call Debit Spread"),
        ("Analyst meet earnings IV crush calendar", "ATM Long Calendar Spread"),
        ("Delta neutral iron condor pin", "Delta-Neutral Iron Condor"),
    ],
)
def test_pillar2_hedged_first_invariant_compiler(prompt, expected_name):
    compiler = PulseToPayoffCompiler()
    strat = compiler.compile_strategy(prompt, "NIFTY", 22716.20, 50.0, 75, 15000.0)
    assert strat.strategy_name == expected_name
    assert strat.hedged_first_verified is True

    actions = [leg.action for leg in strat.legs_in_execution_order]
    first_sell_idx = actions.index(OrderSide.SELL)
    for idx in range(first_sell_idx):
        assert actions[idx] == OrderSide.BUY, "Hedged-First Invariant violated: BUY leg must precede SELL leg!"


def test_pillar3_tiltguard_rms_sub_200us_and_behavioral_interventions():
    rms = TiltGuardRMS()
    # 1. Test 1-Lot Recovery Governor at >= 75% drawdown (-19,500 on 25,000 limit)
    rms.register_account(
        TraderAccountState(
            trader_id="TRD_GOV",
            allocated_margin_inr=500000.0,
            current_mtm_inr=-19500.0,
            max_daily_loss_limit_inr=25000.0,
            consecutive_losses=1,
            last_order_quantity_lots=4,
        )
    )
    order_gov = OrderRequest(
        order_id="O1",
        trader_id="TRD_GOV",
        symbol="NIFTY",
        strike=22750.0,
        option_type=OptionType.CALL,
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity_lots=5,
        lot_size=75,
        limit_price=140.0,
        client_timestamp_ns=time.perf_counter_ns(),
    )
    dec_gov = rms.evaluate_order_fast(order_gov)
    assert dec_gov.verdict == RMSVerdict.MODIFIED_ONE_LOT_GOVERNOR
    assert dec_gov.approved_quantity_lots == 1
    assert dec_gov.latency_microseconds < 200.0

    # 2. Test Anti-Martingale Rejection after 2+ consecutive losses
    rms.register_account(
        TraderAccountState(
            trader_id="TRD_MART",
            allocated_margin_inr=500000.0,
            current_mtm_inr=-8000.0,
            max_daily_loss_limit_inr=25000.0,
            consecutive_losses=3,
            last_order_quantity_lots=2,
        )
    )
    order_mart = OrderRequest(
        order_id="O2",
        trader_id="TRD_MART",
        symbol="NIFTY",
        strike=22750.0,
        option_type=OptionType.CALL,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity_lots=6,
        lot_size=75,
        limit_price=140.0,
        client_timestamp_ns=time.perf_counter_ns(),
    )
    dec_mart = rms.evaluate_order_fast(order_mart)
    assert dec_mart.verdict == RMSVerdict.REJECTED_TILT_MARTINGALE
    assert dec_mart.approved_quantity_lots == 0


def test_pillar4_slippage_shield_obi5_vpin_and_iceberg():
    shield = SlippageShieldEngine()
    depth = Level2Depth(
        bid_prices=[142.5, 142.25, 142.0, 141.75, 141.5],
        bid_volumes=[800, 1200, 1600, 2000, 2500],
        ask_prices=[142.75, 143.0, 143.25, 143.5, 143.75],
        ask_volumes=[200, 350, 500, 700, 900],
    )
    obi5 = shield.compute_weighted_obi_5(depth)
    assert 0.0 < obi5 <= 1.0

    vpin = shield.compute_vpin(buy_vol=4200, sell_vol=1100, total_bucket_vol=5300)
    assert 0.0 <= vpin <= 1.0

    slices = shield.slice_order_micro_iceberg(total_lots=25, depth_l1_vol=30)
    assert sum(s["quantity_lots"] for s in slices) == 25
    assert all(12 <= s["jitter_delay_ms"] <= 38 for s in slices)


def test_harvested_sahi_datasets_exist_and_non_empty():
    for fname in [
        "sahi_intraday_ticks_50k.csv",
        "sahi_option_chains_greeks.json",
        "sahi_live_news_catalysts.json",
        "sahi_trader_behavioral_sessions.csv",
        "dataset_manifest.json",
    ]:
        fpath = os.path.join(DATA_DIR, fname)
        assert os.path.exists(fpath), f"Missing dataset file: {fpath}"
        assert os.path.getsize(fpath) > 1000, f"Dataset file unexpectedly small: {fpath}"
