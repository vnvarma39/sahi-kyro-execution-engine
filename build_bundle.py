#!/usr/bin/env python3
"""
Builds a compact, fast-loading (<350 KB) real-data + polyglot-source bundle
(`sahi/docs/data_bundle.js`) from the harvested Sahi datasets and polyglot codebase.
"""

import csv
import json
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
        inst = row.get("instrument", row.get("symbol", "NIFTY_50"))
        counts[inst] = counts.get(inst, 0) + 1
        if counts[inst] % 150 == 1 and len(ticks_by_inst.get(inst, [])) < 80:
            ticks_by_inst.setdefault(inst, []).append({
                "ts": row.get("timestamp", ""),
                "o": float(row.get("open", 0)),
                "h": float(row.get("high", 0)),
                "l": float(row.get("low", 0)),
                "c": float(row.get("close", 0)),
                "v": int(float(row.get("volume", 0))),
                "vwap": float(row.get("vwap", row.get("close", 0))),
                "obi": float(row.get("obi", row.get("obi_5", 0))),
                "vpin": float(row.get("vpin", 0.3)),
                "gex": float(row.get("net_dealer_gex_cr", 0)),
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

# 4. Retail Behavioral Sessions (top 40 sessions from 3,000-row dataset)
sessions_sample = []
with open(os.path.join(DATA_DIR, "sahi_trader_behavioral_sessions.csv"), "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for idx, row in enumerate(reader):
        if idx < 40:
            sessions_sample.append(row)

# 5. Benchmark results (100,000 orders)
with open(os.path.join(BENCH_DIR, "benchmark_results.json"), "r", encoding="utf-8") as f:
    benchmarks = json.load(f)

# 6. Polyglot Source Code files for the live Codebase Inspector
def read_src(rel_path: str, max_chars: int = 12000) -> str:
    p = os.path.join(BASE_DIR, rel_path)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return f.read()[:max_chars]
    return ""

polyglot_sources = {
    "rust": read_src(os.path.join("rust_feedserver", "src", "lib.rs")),
    "go": read_src(os.path.join("go_ems_router", "ems_router.go")),
    "scylla": read_src(os.path.join("scylladb", "schema.cql")),
    "ts": read_src(os.path.join("ts_webmcp_sdk", "webmcp_sdk.ts")),
    "python": read_src(os.path.join("engine", "kyro_execution_engine.py"), 14000),
}

bundle = {
    "ticksByInstrument": ticks_by_inst,
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
