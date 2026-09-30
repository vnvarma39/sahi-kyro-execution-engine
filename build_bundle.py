#!/usr/bin/env python3
"""
Builds a compact, fast-loading real-data + polyglot-source bundle
(`sahi/docs/data_bundle.js`) from the harvested Sahi datasets and polyglot codebase.

Includes:
1. Normalized `behavioralSessions` from `sahi_trader_behavioral_sessions_50k.csv`
   (populating both 50k and legacy schema fields so `archetype`, `sl_drag_count`,
   `post_loss_lot_multiplier`, `composite_tilt_score`, and `tiltguard_intervention`
   are always defined and never `undefined`).
2. Pre-computed `sahiScalperTriad` for the 3-chart Sahi Scalper layout matching the
   exact calibrated NIFTY50 screenshot (`NIFTY50 Spot` @ 25043.05, swing high 25261.60,
   swing low 25004.90 + glowing bands at 50.0% orange 25285, 20.0% blue 25178,
   20.0% yellow 25048; `NIFTY 30 Sep 25100 Call` @ 84.55 `-25.85 (23.62%)`,
   swing high 122.80, swing low 73.90 + EMA + volume; `NIFTY 30 Sep 24950 Put` @ 48.60
   `+0.65 (1.36%)`, swing high 60.75) plus 2nd-order Greek candle projections for
   `BANKNIFTY`, `SENSEX`, `CRUDEOIL_MCX`, and `GOLD_MCX`.
"""

import csv
import json
import math
import os

BASE_DIR = r"e:\NIKHIL\MAHINDRA UNIVERSITY\internship\sahi"
DATA_DIR = os.path.join(BASE_DIR, "data")
BENCH_DIR = os.path.join(BASE_DIR, "benchmarks")
DOCS_DIR = os.path.join(BASE_DIR, "docs")
os.makedirs(DOCS_DIR, exist_ok=True)

# 1. Sample 80 real intraday 5s bars per instrument from sahi_intraday_ticks_50k.csv
ticks_by_inst = {}
with open(os.path.join(DATA_DIR, "sahi_intraday_ticks_50k.csv"), "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    counts = {}
    for idx, row in enumerate(reader):
        inst = row.get("instrument", row.get("symbol", "NIFTY50"))
        counts[inst] = counts.get(inst, 0) + 1
        if counts[inst] % 150 == 1 and len(ticks_by_inst.get(inst, [])) < 80:
            ticks_by_inst.setdefault(inst, []).append({
                "ts": row.get("timestamp", ""),
                "o": round(float(row.get("open", 0)), 2),
                "h": round(float(row.get("high", 0)), 2),
                "l": round(float(row.get("low", 0)), 2),
                "c": round(float(row.get("close", 0)), 2),
                "v": int(float(row.get("volume", 0))),
                "vwap": round(float(row.get("vwap", row.get("close", 0))), 2),
                "obi": round(float(row.get("obi", row.get("obi_5", 0))), 3),
                "vpin": round(float(row.get("vpin", 0.3)), 3),
                "gex": round(float(row.get("net_dealer_gex_cr", 0)), 2),
                "regime": row.get("regime", "PINNED_EXPIRY"),
            })

# 2. Option chains & 1st/2nd order Greeks
with open(os.path.join(DATA_DIR, "sahi_option_chains_greeks.json"), "r", encoding="utf-8") as f:
    raw_options = json.load(f)

# 3. Real Sahi Live News Catalysts (top 28 real headlines from sahi.com/news)
with open(os.path.join(DATA_DIR, "sahi_live_news_catalysts.json"), "r", encoding="utf-8") as f:
    raw_news = json.load(f)
news_list = raw_news.get("catalysts", raw_news) if isinstance(raw_news, dict) else raw_news
news_sample = news_list[:28] if isinstance(news_list, list) else []


# 4. Retail Behavioral Sessions — read from sahi_trader_behavioral_sessions_50k.csv
#    and normalize both 50k and legacy schemas so no field is ever undefined.
def normalize_session_row(row: dict) -> dict:
    sl_drags = int(float(row.get("sl_drag_count", row.get("sl_dragback_count", 0)) or 0))
    lot_mult = round(float(row.get("post_loss_lot_multiplier", row.get("post_loss_martingale_multiplier", 1.0)) or 1.0), 2)
    tamper = int(float(row.get("pnl_protect_tamper_attempts", row.get("pnl_protect_tamper_count", 0)) or 0))
    tilt = round(float(row.get("composite_tilt_score", row.get("tilt_score", 15)) or 15), 1)
    orders_cnt = int(float(row.get("orders_executed", row.get("trades_count", 10)) or 10))
    gross_pnl = round(float(row.get("gross_pnl_inr", 0.0) or 0.0), 2)
    brok = round(float(row.get("brokerage_and_taxes_inr", row.get("brokerage_and_stt_inr", 200.0)) or 200.0), 2)
    net_pnl = round(float(row.get("net_pnl_inr", gross_pnl - brok) or 0.0), 2)

    archetype = row.get("archetype") or row.get("experience_tier")
    if not archetype:
        if sl_drags >= 3:
            archetype = "SL_DRAGGER"
        elif lot_mult >= 2.0:
            archetype = "REVENGE_MARTINGALE"
        elif tilt >= 60:
            archetype = "EXPIRY_0DTE_GAMBLER"
        else:
            archetype = "DISCIPLINED_SCALPER"

    intervention = row.get("tiltguard_intervention") or row.get("sahi_nudge_triggered")
    if not intervention or intervention == "NONE":
        if tilt >= 80:
            intervention = "RED_CARD_15MIN_HMAC_LOCK"
        elif tilt >= 50:
            intervention = "YELLOW_CARD_1LOT_GOVERNOR"
        else:
            intervention = "GREEN_ACTIVE_NORMAL"

    return {
        "session_id": row.get("session_id", "SAHI-SESS-000001"),
        "trader_id": row.get("trader_id", "TRD-BLR-1000"),
        "archetype": archetype,
        "experience_tier": row.get("experience_tier", archetype),
        "orders_executed": orders_cnt,
        "trades_count": orders_cnt,
        "sl_drag_count": sl_drags,
        "sl_dragback_count": sl_drags,
        "post_loss_lot_multiplier": lot_mult,
        "post_loss_martingale_multiplier": lot_mult,
        "pnl_protect_tamper_attempts": tamper,
        "pnl_protect_tamper_count": tamper,
        "gross_pnl_inr": gross_pnl,
        "brokerage_and_taxes_inr": brok,
        "brokerage_and_stt_inr": brok,
        "net_pnl_inr": net_pnl,
        "composite_tilt_score": int(round(tilt)) if tilt == int(tilt) else tilt,
        "tilt_score": tilt,
        "tiltguard_intervention": intervention,
        "sahi_nudge_triggered": intervention,
        "estimated_capital_saved_inr": round(float(row.get("estimated_capital_saved_inr", 0.0) or 0.0), 2),
        "rms_eval_latency_us": round(float(row.get("rms_eval_latency_us", 1.93) or 1.93), 2),
    }


sessions_sample = []
sessions_50k_path = os.path.join(DATA_DIR, "sahi_trader_behavioral_sessions_50k.csv")
sessions_legacy_path = os.path.join(DATA_DIR, "sahi_trader_behavioral_sessions.csv")
source_sessions_path = sessions_50k_path if os.path.exists(sessions_50k_path) else sessions_legacy_path

with open(source_sessions_path, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for idx, row in enumerate(reader):
        if idx < 45:
            sessions_sample.append(normalize_session_row(row))


# 5. Pre-computed `sahiScalperTriad` — Calibrated 3-Chart Sahi Scalper Series
#    - Exact NIFTY50 screenshot calibration:
#      * NIFTY50 Spot: LTP 25,043.05, Swing High 25,261.60, Swing Low 25,004.90,
#        glowing bands at 50.0% orange 25,285, 20.0% blue 25,178, 20.0% yellow 25,048.
#      * NIFTY 30 Sep 25100 Call: LTP 84.55, -25.85 (23.62%), Swing High 122.80,
#        Swing Low 73.90 + 9-EMA curve + volume bars.
#      * NIFTY 30 Sep 24950 Put: LTP 48.60, +0.65 (1.36%), Swing High 60.75 + 9-EMA + volume.
#    - Plus 2nd-Order BSM Greek Taylor-Projected Option Candles for BANKNIFTY, SENSEX,
#      CRUDEOIL_MCX, and GOLD_MCX.
def compute_ema_series(closes: list[float], span: int = 9) -> list[float]:
    if not closes:
        return []
    alpha = 2.0 / (span + 1.0)
    ema = []
    curr = closes[0]
    for c in closes:
        curr = alpha * c + (1.0 - alpha) * curr
        ema.append(round(curr, 2))
    return ema


def build_nifty50_calibrated_triad() -> dict:
    """
    Constructs the 48-candle (5m bars, 09:15 to 13:10 IST) synchronized triad
    matching the exact Sahi Scalper screenshot telemetry for NIFTY50.
    """
    # 48 timestamps at 5-minute intervals from 09:15 to 13:10
    timestamps = []
    h_clock, m_clock = 9, 15
    for _ in range(48):
        timestamps.append(f"{h_clock:02d}:{m_clock:02d}")
        m_clock += 5
        if m_clock >= 60:
            h_clock += 1
            m_clock -= 60

    # Key waypoints on NIFTY50 Spot trajectory:
    # Bar 0 (09:15): Open 25188.40 -> rallies toward 25261.60
    # Bar 10 (10:05): Swing High 25261.60 (rejection below 50.0% orange band 25285)
    # Bar 21 (11:00): Consolidates around 20.0% blue band 25178.00
    # Bar 36 (12:15): Breakdown to exact Swing Low 25004.90
    # Bar 47 (13:10): Stabilizes along 20.0% yellow band 25048 at exact LTP 25043.05
    waypoints = [
        (0, 25192.50),
        (5, 25224.80),
        (10, 25254.20),   # Peak bar (high hits 25261.60)
        (15, 25208.40),
        (21, 25178.00),   # Blue 20.0% band pivot (25178)
        (27, 25122.60),
        (32, 25064.30),
        (36, 25012.40),   # Trough bar (low hits 25004.90)
        (41, 25051.80),   # Yellow 20.0% band test (25048)
        (45, 25038.90),
        (47, 25043.05),   # Exact terminal LTP 25043.05
    ]

    # Interpolate baseline spot closes with deterministic micro-structure wave
    spot_closes = []
    for idx in range(48):
        # Find surrounding waypoints
        for w_i in range(len(waypoints) - 1):
            i0, v0 = waypoints[w_i]
            i1, v1 = waypoints[w_i + 1]
            if i0 <= idx <= i1:
                t = (idx - i0) / max(1, (i1 - i0))
                base = v0 + t * (v1 - v0)
                wave = math.sin(idx * 1.35) * 6.4 if idx not in (10, 36, 47) else 0.0
                spot_closes.append(round(base + wave, 2))
                break

    spot_candles = []
    cum_pv = 0.0
    cum_v = 0
    for idx, c_val in enumerate(spot_closes):
        o_val = 25188.40 if idx == 0 else spot_closes[idx - 1]
        body_hi = max(o_val, c_val)
        body_lo = min(o_val, c_val)
        wick_up = 4.2 + (idx % 5) * 1.8
        wick_dn = 4.0 + ((idx + 2) % 5) * 1.7
        h_val = round(min(25259.40, body_hi + wick_up), 2)
        l_val = round(max(25008.20, body_lo - wick_dn), 2)

        if idx == 10:
            h_val = 25261.60  # Exact screenshot swing high
        elif idx == 36:
            l_val = 25004.90  # Exact screenshot swing low
        elif idx == 47:
            c_val = 25043.05  # Exact screenshot spot LTP
            h_val = max(o_val, c_val) + 3.45
            l_val = min(o_val, c_val) - 4.10

        vol = int(18500 + 14200 * abs(c_val - o_val) / 10.0 + (idx % 7) * 2100)
        if idx in (10, 22, 35, 36):
            vol = int(vol * 1.75)
        cum_pv += c_val * vol
        cum_v += vol
        obi = round(max(-0.92, min(0.92, (c_val - o_val) / 14.5)), 3)

        spot_candles.append({
            "ts": timestamps[idx],
            "o": round(o_val, 2),
            "h": round(h_val, 2),
            "l": round(l_val, 2),
            "c": round(c_val, 2),
            "v": vol,
            "vwap": round(cum_pv / max(1, cum_v), 2),
            "obi": obi,
            "vpin": round(min(0.92, 0.34 + abs(obi) * 0.48), 3),
        })

    spot_emas = compute_ema_series([b["c"] for b in spot_candles], span=9)
    for idx, b in enumerate(spot_candles):
        b["ema"] = spot_emas[idx]

    # Project NIFTY 30 Sep 25100 Call via 2nd-Order Greek expansion calibrated to [73.90, 122.80] & close 84.55
    # And NIFTY 30 Sep 24950 Put calibrated to swing high 60.75 & close 48.60
    s_min, s_max = 25004.90, 25261.60
    call_candles = []
    put_candles = []

    for idx, sb in enumerate(spot_candles):
        # Normalized spot position u in [0, 1] plus intraday theta decay & vanna skew
        u_close = (sb["c"] - s_min) / (s_max - s_min)
        u_open = (sb["o"] - s_min) / (s_max - s_min)
        u_high = (sb["h"] - s_min) / (s_max - s_min)
        u_low = (sb["l"] - s_min) / (s_max - s_min)
        theta_drift = (idx / 47.0) * 3.80

        # 2nd-order convexity term (0.5 * Gamma * dS^2)
        def map_call(u: float, bar_i: int) -> float:
            val = 75.40 + 44.20 * u + 4.80 * (u ** 2) - (bar_i / 47.0) * 2.90
            return round(max(73.95, min(122.40, val)), 2)

        def map_put(u: float, bar_i: int) -> float:
            inv = 1.0 - u
            val = 31.80 + 24.50 * inv + 4.90 * (inv ** 2) - (bar_i / 47.0) * 1.45
            return round(max(31.40, min(60.35, val)), 2)

        co = 110.40 if idx == 0 else call_candles[idx - 1]["c"]
        cc = map_call(u_close, idx)
        ch = round(max(co, cc, map_call(u_high, idx)) + 1.15, 2)
        cl = round(min(co, cc, map_call(u_low, idx)) - 1.05, 2)
        ch = min(122.45, ch)
        cl = max(74.15, cl)

        if idx == 10:
            ch = 122.80  # Exact screenshot Call Swing High
        elif idx == 36:
            cl = 73.90   # Exact screenshot Call Swing Low
            cc = 75.85
        elif idx == 47:
            cc = 84.55   # Exact screenshot Call LTP
            ch = max(co, cc) + 1.20
            cl = min(co, cc) - 0.95

        po = 47.95 if idx == 0 else put_candles[idx - 1]["c"]
        pc = map_put(u_close, idx)
        ph = round(max(po, pc, map_put(u_low, idx)) + 0.85, 2)
        pl = round(min(po, pc, map_put(u_high, idx)) - 0.75, 2)
        ph = min(60.20, ph)
        pl = max(31.40, pl)

        if idx == 10:
            pl = 31.40   # Put Swing Low when Spot hits 25261.60
        elif idx == 36:
            ph = 60.75   # Exact screenshot Put Swing High when Spot hits 25004.90
            pc = 58.40
        elif idx == 47:
            pc = 48.60   # Exact screenshot Put LTP
            ph = max(po, pc) + 0.80
            pl = min(po, pc) - 0.65

        c_vol = int(sb["v"] * (1.85 if cc >= co else 1.45))
        p_vol = int(sb["v"] * (1.95 if pc >= po else 1.35))

        call_candles.append({
            "ts": sb["ts"],
            "o": round(co, 2),
            "h": round(ch, 2),
            "l": round(cl, 2),
            "c": round(cc, 2),
            "v": c_vol,
            "obi": round(sb["obi"] * 0.92, 3),
        })
        put_candles.append({
            "ts": sb["ts"],
            "o": round(po, 2),
            "h": round(ph, 2),
            "l": round(pl, 2),
            "c": round(pc, 2),
            "v": p_vol,
            "obi": round(-sb["obi"] * 0.88, 3),
        })

    call_emas = compute_ema_series([b["c"] for b in call_candles], span=9)
    put_emas = compute_ema_series([b["c"] for b in put_candles], span=9)
    for idx in range(48):
        call_candles[idx]["ema"] = call_emas[idx]
        put_candles[idx]["ema"] = put_emas[idx]

    bands = [
        {
            "label": "50.0%",
            "pct": 50.0,
            "level": 25285.0,
            "price": 25285.0,
            "upper": 25302.0,
            "lower": 25268.0,
            "color": "#FF6D00",
            "glow": "rgba(255, 109, 0, 0.28)",
            "tier": "orange",
            "description": "50.0% Upper Call-Wall Gamma Resistance Zone",
        },
        {
            "label": "20.0%",
            "pct": 20.0,
            "level": 25178.0,
            "price": 25178.0,
            "upper": 25192.0,
            "lower": 25164.0,
            "color": "#00B0FF",
            "glow": "rgba(0, 176, 255, 0.26)",
            "tier": "blue",
            "description": "20.0% Intraday Zero-Gamma Flip Pivot Band",
        },
        {
            "label": "20.0%",
            "pct": 20.0,
            "level": 25048.0,
            "price": 25048.0,
            "upper": 25062.0,
            "lower": 25034.0,
            "color": "#FFD600",
            "glow": "rgba(255, 214, 0, 0.26)",
            "tier": "yellow",
            "description": "20.0% Nadaraya-Watson Support Absorption Zone",
        },
    ]

    return {
        "instrument": "NIFTY50",
        "timeframe": "5m",
        "expiry": "30 Sep",
        "lot_size": 75,
        "projection_mode": "CALIBRATED_SCREENSHOT_AND_2ND_ORDER_GREEKS",
        "spot": {
            "symbol": "NIFTY50",
            "title": "NIFTY 50",
            "label": "NIFTY 50 Spot",
            "ltp": 25043.05,
            "price": 25043.05,
            "change": -145.35,
            "change_pct": -0.58,
            "change_text": "-145.35 (0.58%)",
            "swing_high": 25261.60,
            "swing_low": 25004.90,
            "zero_gamma_flip": 25178.00,
            "bands": bands,
            "candles": spot_candles,
        },
        "call": {
            "symbol": "NIFTY30SEP25100CE",
            "title": "NIFTY 30 Sep 25100 Call",
            "label": "NIFTY 30 Sep 25100 Call",
            "strike": 25100,
            "expiry": "30 Sep",
            "option_type": "CE",
            "ltp": 84.55,
            "price": 84.55,
            "change": -25.85,
            "change_pct": -23.62,
            "change_text": "-25.85 (23.62%)",
            "swing_high": 122.80,
            "swing_low": 73.90,
            "greeks": {
                "delta": 0.412,
                "gamma": 0.00215,
                "theta": -14.80,
                "vega": 8.45,
                "vanna": 0.0184,
                "charm": -0.062,
                "iv_pct": 13.8,
            },
            "candles": call_candles,
        },
        "put": {
            "symbol": "NIFTY30SEP24950PE",
            "title": "NIFTY 30 Sep 24950 Put",
            "label": "NIFTY 30 Sep 24950 Put",
            "strike": 24950,
            "expiry": "30 Sep",
            "option_type": "PE",
            "ltp": 48.60,
            "price": 48.60,
            "change": 0.65,
            "change_pct": 1.36,
            "change_text": "+0.65 (1.36%)",
            "swing_high": 60.75,
            "swing_low": 31.40,
            "greeks": {
                "delta": -0.348,
                "gamma": 0.00198,
                "theta": -13.20,
                "vega": 7.90,
                "vanna": -0.0162,
                "charm": 0.054,
                "iv_pct": 14.2,
            },
            "candles": put_candles,
        },
        "bands": bands,
    }


def build_greek_projected_triad(
    inst_key: str,
    display_name: str,
    spot_bars_raw: list[dict],
    call_strike: int,
    put_strike: int,
    lot_size: int,
    base_call_ltp: float,
    base_put_ltp: float,
    call_greeks: dict,
    put_greeks: dict,
) -> dict:
    """
    Projects 48 synchronized Call & Put OHLCV + 9-EMA + Volume candles from underlying
    Spot bars using 2nd-order BSM Greek Taylor expansion:
      dV = Delta * dS + 0.5 * Gamma * dS^2 + Vanna * dS * dIV + Charm * dS * dt + Theta * dt
    """
    bars = (spot_bars_raw or [])[:48]
    spot_candles = []
    for idx, b in enumerate(bars):
        spot_candles.append({
            "ts": b.get("ts", "")[-14:-9] if len(b.get("ts", "")) >= 14 else f"10:{idx:02d}",
            "o": round(float(b["o"]), 2),
            "h": round(float(b["h"]), 2),
            "l": round(float(b["l"]), 2),
            "c": round(float(b["c"]), 2),
            "v": int(b.get("v", 12000)),
            "vwap": round(float(b.get("vwap", b["c"])), 2),
            "obi": round(float(b.get("obi", 0.0)), 3),
            "vpin": round(float(b.get("vpin", 0.35)), 3),
        })

    spot_emas = compute_ema_series([b["c"] for b in spot_candles], span=9)
    for idx, b in enumerate(spot_candles):
        b["ema"] = spot_emas[idx]

    swing_high = round(max(b["h"] for b in spot_candles), 2)
    swing_low = round(min(b["l"] for b in spot_candles), 2)
    span_range = max(1.0, swing_high - swing_low)
    ref_spot = spot_candles[0]["o"]
    last_spot = spot_candles[-1]["c"]
    spot_chg = round(last_spot - ref_spot, 2)
    spot_chg_pct = round((spot_chg / max(1.0, ref_spot)) * 100.0, 2)

    band_50 = round(swing_high + span_range * 0.09, 2)
    band_20_blue = round(swing_low + span_range * 0.62, 2)
    band_20_yellow = round(swing_low + span_range * 0.18, 2)
    band_half_w = round(span_range * 0.035, 2)

    bands = [
        {
            "label": "50.0%",
            "pct": 50.0,
            "level": band_50,
            "price": band_50,
            "upper": round(band_50 + band_half_w, 2),
            "lower": round(band_50 - band_half_w, 2),
            "color": "#FF6D00",
            "glow": "rgba(255, 109, 0, 0.28)",
            "tier": "orange",
            "description": "50.0% Upper Call-Wall Gamma Resistance Zone",
        },
        {
            "label": "20.0%",
            "pct": 20.0,
            "level": band_20_blue,
            "price": band_20_blue,
            "upper": round(band_20_blue + band_half_w, 2),
            "lower": round(band_20_blue - band_half_w, 2),
            "color": "#00B0FF",
            "glow": "rgba(0, 176, 255, 0.26)",
            "tier": "blue",
            "description": "20.0% Intraday Zero-Gamma Flip Pivot Band",
        },
        {
            "label": "20.0%",
            "pct": 20.0,
            "level": band_20_yellow,
            "price": band_20_yellow,
            "upper": round(band_20_yellow + band_half_w, 2),
            "lower": round(band_20_yellow - band_half_w, 2),
            "color": "#FFD600",
            "glow": "rgba(255, 214, 0, 0.26)",
            "tier": "yellow",
            "description": "20.0% Nadaraya-Watson Support Absorption Zone",
        },
    ]

    call_candles = []
    put_candles = []
    dt_bar = 1.0 / (48.0 * 6.25)

    for idx, sb in enumerate(spot_candles):
        ds_c = sb["c"] - ref_spot
        ds_h = sb["h"] - ref_spot
        ds_l = sb["l"] - ref_spot
        div = -0.015 * (ds_c / max(10.0, span_range))  # Spot-vol skew for Vanna

        def project_opt(base_v: float, g: dict, ds: float, bar_idx: int) -> float:
            d_v = (
                g["delta"] * ds
                + 0.5 * g["gamma"] * (ds ** 2)
                + g["vanna"] * ds * div
                + g["charm"] * ds * (bar_idx * dt_bar)
                + g["theta"] * (bar_idx * dt_bar)
            )
            return round(max(4.50, base_v + d_v), 2)

        co = round(base_call_ltp, 2) if idx == 0 else call_candles[idx - 1]["c"]
        cc = project_opt(base_call_ltp, call_greeks, ds_c, idx)
        ch = round(max(co, cc, project_opt(base_call_ltp, call_greeks, ds_h, idx)) + 0.85, 2)
        cl = round(max(3.50, min(co, cc, project_opt(base_call_ltp, call_greeks, ds_l, idx)) - 0.75), 2)

        po = round(base_put_ltp, 2) if idx == 0 else put_candles[idx - 1]["c"]
        pc = project_opt(base_put_ltp, put_greeks, ds_c, idx)
        ph = round(max(po, pc, project_opt(base_put_ltp, put_greeks, ds_l, idx)) + 0.80, 2)
        pl = round(max(3.20, min(po, pc, project_opt(base_put_ltp, put_greeks, ds_h, idx)) - 0.70), 2)

        call_candles.append({
            "ts": sb["ts"],
            "o": co,
            "h": ch,
            "l": cl,
            "c": cc,
            "v": int(sb["v"] * 1.65),
            "obi": round(sb["obi"] * 0.9, 3),
        })
        put_candles.append({
            "ts": sb["ts"],
            "o": po,
            "h": ph,
            "l": pl,
            "c": pc,
            "v": int(sb["v"] * 1.58),
            "obi": round(-sb["obi"] * 0.9, 3),
        })

    call_emas = compute_ema_series([b["c"] for b in call_candles], span=9)
    put_emas = compute_ema_series([b["c"] for b in put_candles], span=9)
    for idx in range(len(call_candles)):
        call_candles[idx]["ema"] = call_emas[idx]
        put_candles[idx]["ema"] = put_emas[idx]

    c_open = call_candles[0]["o"]
    c_last = call_candles[-1]["c"]
    c_chg = round(c_last - c_open, 2)
    c_chg_pct = round((c_chg / max(1.0, c_open)) * 100.0, 2)

    p_open = put_candles[0]["o"]
    p_last = put_candles[-1]["c"]
    p_chg = round(p_last - p_open, 2)
    p_chg_pct = round((p_chg / max(1.0, p_open)) * 100.0, 2)

    short_sym = inst_key.replace("_MCX", "")
    return {
        "instrument": inst_key,
        "timeframe": "5m",
        "expiry": "30 Sep",
        "lot_size": lot_size,
        "projection_mode": "2ND_ORDER_BSM_GREEK_TAYLOR_PROJECTION",
        "spot": {
            "symbol": inst_key,
            "title": display_name,
            "label": f"{display_name} Spot",
            "ltp": last_spot,
            "price": last_spot,
            "change": spot_chg,
            "change_pct": spot_chg_pct,
            "change_text": f"{'+' if spot_chg >= 0 else ''}{spot_chg} ({abs(spot_chg_pct):.2f}%)",
            "swing_high": swing_high,
            "swing_low": swing_low,
            "zero_gamma_flip": band_20_blue,
            "bands": bands,
            "candles": spot_candles,
        },
        "call": {
            "symbol": f"{short_sym}30SEP{call_strike}CE",
            "title": f"{short_sym} 30 Sep {call_strike} Call",
            "label": f"{short_sym} 30 Sep {call_strike} Call",
            "strike": call_strike,
            "expiry": "30 Sep",
            "option_type": "CE",
            "ltp": c_last,
            "price": c_last,
            "change": c_chg,
            "change_pct": c_chg_pct,
            "change_text": f"{'+' if c_chg >= 0 else ''}{c_chg:.2f} ({abs(c_chg_pct):.2f}%)",
            "swing_high": round(max(b["h"] for b in call_candles), 2),
            "swing_low": round(min(b["l"] for b in call_candles), 2),
            "greeks": call_greeks,
            "candles": call_candles,
        },
        "put": {
            "symbol": f"{short_sym}30SEP{put_strike}PE",
            "title": f"{short_sym} 30 Sep {put_strike} Put",
            "label": f"{short_sym} 30 Sep {put_strike} Put",
            "strike": put_strike,
            "expiry": "30 Sep",
            "option_type": "PE",
            "ltp": p_last,
            "price": p_last,
            "change": p_chg,
            "change_pct": p_chg_pct,
            "change_text": f"{'+' if p_chg >= 0 else ''}{p_chg:.2f} ({abs(p_chg_pct):.2f}%)",
            "swing_high": round(max(b["h"] for b in put_candles), 2),
            "swing_low": round(min(b["l"] for b in put_candles), 2),
            "greeks": put_greeks,
            "candles": put_candles,
        },
        "bands": bands,
    }


nifty_triad = build_nifty50_calibrated_triad()
banknifty_triad = build_greek_projected_triad(
    inst_key="BANKNIFTY",
    display_name="BANKNIFTY",
    spot_bars_raw=ticks_by_inst.get("BANKNIFTY", []),
    call_strike=51700,
    put_strike=51500,
    lot_size=15,
    base_call_ltp=248.50,
    base_put_ltp=192.40,
    call_greeks={"delta": 0.445, "gamma": 0.00092, "theta": -28.4, "vega": 18.2, "vanna": 0.024, "charm": -0.085, "iv_pct": 15.6},
    put_greeks={"delta": -0.382, "gamma": 0.00088, "theta": -25.1, "vega": 17.4, "vanna": -0.021, "charm": 0.074, "iv_pct": 16.1},
)
sensex_triad = build_greek_projected_triad(
    inst_key="SENSEX",
    display_name="BSE SENSEX",
    spot_bars_raw=ticks_by_inst.get("SENSEX", []),
    call_strike=74200,
    put_strike=73900,
    lot_size=10,
    base_call_ltp=312.00,
    base_put_ltp=246.80,
    call_greeks={"delta": 0.438, "gamma": 0.00074, "theta": -32.0, "vega": 22.5, "vanna": 0.019, "charm": -0.072, "iv_pct": 13.9},
    put_greeks={"delta": -0.376, "gamma": 0.00071, "theta": -29.4, "vega": 21.1, "vanna": -0.017, "charm": 0.068, "iv_pct": 14.4},
)
crude_triad = build_greek_projected_triad(
    inst_key="CRUDEOIL_MCX",
    display_name="MCX CRUDE OIL",
    spot_bars_raw=ticks_by_inst.get("CRUDEOIL_MCX", []),
    call_strike=8200,
    put_strike=8100,
    lot_size=100,
    base_call_ltp=118.40,
    base_put_ltp=94.20,
    call_greeks={"delta": 0.425, "gamma": 0.00310, "theta": -9.8, "vega": 6.4, "vanna": 0.031, "charm": -0.048, "iv_pct": 31.5},
    put_greeks={"delta": -0.390, "gamma": 0.00295, "theta": -8.9, "vega": 6.1, "vanna": -0.028, "charm": 0.044, "iv_pct": 32.1},
)
gold_triad = build_greek_projected_triad(
    inst_key="GOLD_MCX",
    display_name="MCX GOLD",
    spot_bars_raw=ticks_by_inst.get("GOLD_MCX", []),
    call_strike=136000,
    put_strike=135000,
    lot_size=100,
    base_call_ltp=685.00,
    base_put_ltp=540.00,
    call_greeks={"delta": 0.452, "gamma": 0.00042, "theta": -41.5, "vega": 34.0, "vanna": 0.015, "charm": -0.052, "iv_pct": 15.5},
    put_greeks={"delta": -0.388, "gamma": 0.00039, "theta": -38.2, "vega": 31.8, "vanna": -0.014, "charm": 0.049, "iv_pct": 15.9},
)

sahi_scalper_triad = {
    "defaultInstrument": "NIFTY50",
    "spot": nifty_triad["spot"],
    "call": nifty_triad["call"],
    "put": nifty_triad["put"],
    "bands": nifty_triad["bands"],
    "NIFTY50": nifty_triad,
    "BANKNIFTY": banknifty_triad,
    "SENSEX": sensex_triad,
    "CRUDEOIL_MCX": crude_triad,
    "GOLD_MCX": gold_triad,
    "instruments": {
        "NIFTY50": nifty_triad,
        "BANKNIFTY": banknifty_triad,
        "SENSEX": sensex_triad,
        "CRUDEOIL_MCX": crude_triad,
        "GOLD_MCX": gold_triad,
    },
}

# 6. Benchmark results (100,000 orders)
with open(os.path.join(BENCH_DIR, "benchmark_results.json"), "r", encoding="utf-8") as f:
    benchmarks = json.load(f)


# 7. Polyglot Source Code files for the live Codebase Inspector
def read_src(rel_path: str, max_chars: int = 12000) -> str:
    p = os.path.join(BASE_DIR, rel_path)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return f.read()[:max_chars]
    return ""


polyglot_sources = {
    "rust": read_src(os.path.join("rust_feedserver", "src", "lib.rs")) + "\n\n// --- 64-BYTE WIRE CODEC ---\n" + read_src(os.path.join("rust_feedserver", "src", "wire_frame_codec.rs")),
    "go": read_src(os.path.join("go_ems_router", "ems_router.go")) + "\n\n// --- 0DTE EXPIRY BROKER RACE ---\n" + read_src(os.path.join("go_ems_router", "broker_race_simulator.go")),
    "cpp": read_src(os.path.join("cpp_simd_greeks", "simd_bsm_vanna.hpp")),
    "wasm": read_src(os.path.join("wasm_wire_decoder", "sahi_zero_copy_frame.wat")),
    "scylla": read_src(os.path.join("scylladb", "schema.cql")),
    "sql": read_src(os.path.join("analytics_sql", "cfo_arr_ltv_model.sql")),
    "ts": read_src(os.path.join("ts_webmcp_sdk", "webmcp_sdk.ts")),
    "tsx": read_src(os.path.join("ts_webmcp_sdk", "KyroVoiceCommandHook.tsx")),
    "python": read_src(os.path.join("engine", "kyro_execution_engine.py"), 14000),
}

bundle = {
    "ticksByInstrument": ticks_by_inst,
    "sahiScalperTriad": sahi_scalper_triad,
    "optionChains": raw_options,
    "newsCatalysts": news_sample,
    "behavioralSessions": sessions_sample,
    "benchmarks": benchmarks,
    "polyglotSources": polyglot_sources,
}

out_path = os.path.join(DOCS_DIR, "data_bundle.js")
with open(out_path, "w", encoding="utf-8") as f:
    f.write("window.SAHI_DATA = " + json.dumps(bundle, separators=(",", ":")) + ";\n")

print(f"Generated {out_path} ({os.path.getsize(out_path):,} bytes)")
print("Instruments in ticksByInstrument:", list(ticks_by_inst.keys()))
print("Instruments in sahiScalperTriad:", list(sahi_scalper_triad["instruments"].keys()))
print("Behavioral sessions count:", len(sessions_sample), "Sample keys:", list(sessions_sample[0].keys()))
