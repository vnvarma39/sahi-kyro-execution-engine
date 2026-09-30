# Sahi Kyro Execution & Quantitative Risk Engine

Low-latency polyglot derivatives execution, 2nd-order option Greek surface evaluation, pre-trade behavioral risk management, and `WebMCP` strategy compilation engine for Indian equity and commodity derivatives (`NSE F&O`, `BSE SENSEX`, `MCX`).

**Live Terminal:** [https://vnvarma39.github.io/sahi-kyro-execution-engine/](https://vnvarma39.github.io/sahi-kyro-execution-engine/)

---

## System Architecture

```text
+---------------------------------------------------------------------------------------------------+
|                                   EXCHANGE MULTICAST / L2 FEEDS                                   |
|                        (NSE NIFTY 50, BANKNIFTY, BSE SENSEX, MCX CRUDE/GOLD)                      |
+-------------------------------------------------+-------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| 1. MARKET DATA & GREEK ENGINE (Rust 1.82 + C++20 AVX-512 SIMD)                                    |
|    - Lock-free actor fan-out via zero-copy Arc<[u8; 64]> cache-line-aligned wire frames           |
|    - 16-wide __m512 vectorized BSM kernel: Delta, Gamma, Vanna, Charm & Strike-Wise Net GEX       |
+-----------------------+---------------------------------------------------+-----------------------+
                        |                                                   |
                        v                                                   v
+-----------------------------------------------+   +-----------------------------------------------+
| 2. PERSISTENCE & ANALYTICS (ScyllaDB + SQL)   |   | 3. CLIENT RUNTIME (WASM WAT + Chrome WebMCP)  |
|    - Shard-aware time-bucketed 5s candles     |   |    - Zero-copy ArrayBuffer WASM frame decoder |
|    - 32D historical catalyst vector analogs   |   |    - navigator.modelContext tool registry     |
|    - DuckDB / ClickHouse OLAP telemetry       |   |    - Multi-pane HTML5 Canvas orderbook & GEX  |
+-----------------------+-----------------------+   +-----------------------+-----------------------+
                        |                                                   |
                        +-------------------------+-------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
| 4. EXECUTION & PRE-TRADE RISK PIPELINE (Go 1.23 EMS Router + Rust/Python Atomic RMS)              |
|    - Hedged-First Multi-Leg Sequencer: enforces t_exec(L_long) < t_exec(L_short)                  |
|    - Pre-Trade TiltGuard RMS: #[repr(C)] atomic bitmask gate (< 15 us p99 SLA)                    |
|    - Smart Order Router: 5-Level OBI_5 + VPIN toxicity gate + Poisson micro-iceberg slicing       |
+---------------------------------------------------------------------------------------------------+
```

---

## Core Subsystems & Technical Specifications

### 1. Strike-Wise Dealer Gamma Exposure (`GEX`) & Regime-Gated ML
Evaluates first- and second-order Black-Scholes-Merton sensitivities across full 200-strike option chains using 16-wide AVX-512 SIMD intrinsics (`_mm512_fmadd_ps`):

$$\text{GEX}_K = \Gamma_K \cdot \left(\text{OI}^{\text{Call}}_K - \text{OI}^{\text{Put}}_K\right) \cdot M \cdot S^2 \times 10^{-2}$$

$$\text{Vanna}_K = \frac{\partial \Delta_K}{\partial \sigma} = -e^{-qT}\phi(d_1)\frac{d_2}{\sigma}, \qquad \text{Charm}_K = -\frac{\partial \Delta_K}{\partial T}$$

- **Zero-Gamma Flip Boundary ($S^*$):** Interpolated across strikes where cumulative dealer $\sum_K \text{GEX}_K = 0$.
- **Regime-Gated Indicator Selection:** Suppresses mean-reversion oscillators in negative-gamma acceleration regimes ($\text{GEX} < 0, \text{VPIN} > 0.65$) and suppresses breakout chases inside positive-gamma dealer pinning zones ($\text{GEX} > 0$).

### 2. `WebMCP` Strategy Compiler & Hedged-First Sequencer
Implements a browser-native `navigator.modelContext` tool registry (`sahi.kyro.compile_strategy`, `sahi.gex.get_regime_gate`, `sahi.rms.evaluate_tiltguard`, `sahi.ems.slice_iceberg_order`) that compiles natural-language or voice-transcribed option views into multi-leg execution plans:
- **Hedged-First Execution Invariant:** Strictly sequences protective long-option legs (`BUY CE` / `BUY PE`) prior to short-margin legs (`SELL CE` / `SELL PE`), ensuring $t_{\text{exec}}(L_{\text{long}}) < t_{\text{exec}}(L_{\text{short}})$ so exchange SPAN/Exposure margin benefits apply on initial entry.
- **Transaction Cost Accounting:** Computes break-even boundaries and expected values net of brokerage, Securities Transaction Tax (STT), exchange turnover charges, SEBI fees, stamp duty, and GST.

### 3. Pre-Trade Behavioral Risk Engine (`TiltGuard™ RMS`)
Evaluates trader behavioral telemetry inline within the pre-trade risk check budget (`1.93 µs` mean, `3.80 µs` P95 across 100,000 orders):

$$\text{TiltScore}_t = w_1 Z(\Delta \text{SL}_{\text{widen}}) + w_2 Z\left(\frac{\text{Lots}_t}{\overline{\text{Lots}}_{10}}\;\middle|\;\text{Loss}_{t-1}\right) + w_3 Z(\nu_{\text{cancel/replace}}) + w_4 \mathbb{I}(\text{DrawdownTamper})$$

- **Normal State ($\text{TiltScore} < 60$):** Standard order routing.
- **Governance State ($60 \le \text{TiltScore} < 82$):** Caps maximum order size to 1 lot and restricts entries to defined-risk hedged structures.
- **Lockout State ($\text{TiltScore} \ge 82$):** Generates an HMAC-SHA256 time-locked state token rejecting risk-increasing orders for 900 seconds while permitting risk-reducing closes.

### 4. Smart Order Router (`EMS`) & Micro-Iceberg Slicer
Minimizes market impact and exchange freeze-limit rejections across a 3-hop execution topology (`Client -> Regional EMS -> Core OMS -> Pre-Trade RMS -> Exchange Colocation`):
- **Order Book Imbalance ($\text{OBI}_5$):** Exponentially depth-weighted across the top 5 DOM levels ($\lambda = 0.40$).
- **Flow Toxicity ($\text{VPIN}$):** Volume-Synchronized Probability of Informed Trading over rolling 50-bucket volume bars.
- **Execution Policy:** Automatically partitions large orders exceeding exchange freeze quantities (`1,800` for `NIFTY`, `900` for `BANKNIFTY`, `1,000` for `SENSEX`) into Poisson-jittered (`250–650 µs`) limit-pegged child slices priced at the L1 microprice.

### 5. 64-Byte Cache-Line-Aligned Wire Protocol (`SahiWireFrame64`)
Replaces verbose text-based WebSocket payloads (`~482 bytes` JSON) with a fixed 64-byte `#[repr(C, align(64))]` binary struct (`86.7%` payload reduction) decoded directly from shared `WebAssembly.Memory`:

| Byte Offset | Type | Field | Description |
| :--- | :--- | :--- | :--- |
| `0x00..0x07` | `u64` | `magic_header` | ASCII magic constant `"SAHIKYRO"` (`0x4F52594B49484153`) |
| `0x08..0x0F` | `u64` | `timestamp_ns` | Monotonic exchange matching-engine timestamp (ns) |
| `0x10..0x13` | `u32` | `instrument_id` | Numeric token (`101=NIFTY50`, `102=BANKNIFTY`, `103=SENSEX`) |
| `0x14..0x17` | `f32` | `spot_price` | Underlying index / futures last traded price |
| `0x18..0x1B` | `f32` | `microprice` | L1 liquidity-weighted microprice ($P_{\text{micro}}$) |
| `0x1C..0x1F` | `f32` | `obi_5` | 5-level exponentially weighted Order Book Imbalance ($\in [-1, 1]$) |
| `0x20..0x23` | `f32` | `vpin_toxicity` | Easley-de Prado VPIN flow toxicity metric ($\in [0, 1]$) |
| `0x24..0x27` | `f32` | `net_gex_cr` | Aggregate dealer Gamma Exposure (INR Crores / 1% move) |
| `0x28..0x2B` | `f32` | `zero_gamma_flip` | Interpolated Zero-Gamma Flip strike ($S^*$) |
| `0x2C..0x2F` | `f32` | `atm_iv` | At-the-money implied volatility ($\sigma_{\text{ATM}}$) |
| `0x30..0x33` | `f32` | `atm_vanna` | Second-order cross-derivative $\partial \Delta / \partial \sigma$ |
| `0x34..0x37` | `f32` | `atm_charm` | Second-order time-decay of delta $-\partial \Delta / \partial T$ |
| `0x38..0x3B` | `u32` | `rms_bitmask` | Pre-trade `TiltGuard™` atomic status bitmask & flags |
| `0x3C..0x3F` | `u32` | `fnv1a_checksum` | 32-bit FNV-1a frame integrity checksum |

---

## Polyglot Implementation Matrix

| Language / Runtime | Source Path | Subsystem Responsibility | Measured Performance |
| :--- | :--- | :--- | :--- |
| **C++20 (`AVX-512 SIMD`)** | `cpp_simd_greeks/simd_bsm_vanna.hpp` | 16-wide `__m512` BSM $\Delta, \Gamma, \text{Vanna}, \text{Charm}$ & Net GEX evaluation | `190 µs` / 200-strike chain |
| **Rust 1.82 (`Tokio`)** | `rust_feedserver/src/lib.rs`, `wire_frame_codec.rs` | Lock-free `FeedServer`, `Arc<[u8; 64]>` wire codec & `#[repr(C)]` `TiltGuardRMS` | `1.93 µs` mean / `3.80 µs` P95 |
| **WebAssembly (`WAT`)** | `wasm_wire_decoder/sahi_zero_copy_frame.wat` | Zero-copy shared `ArrayBuffer` 64-byte frame decoder | `0.04 µs` / frame in V8 |
| **Go 1.23** | `go_ems_router/ems_router.go`, `broker_race_simulator.go` | 5-level $\text{OBI}_5$, $\text{VPIN}$ gate, freeze-limit splitter & Poisson micro-iceberg router | `6.61 ms` e2e 3-hop RTT |
| **ScyllaDB (`CQL 3.4`)** | `scylladb/schema.cql` | Shard-aware time-bucketed 5s candles, GEX snapshots & RMS audit tables | `< 20 ms` P999 (0 coordinator hops) |
| **SQL (`ClickHouse / DuckDB`)** | `analytics_sql/cfo_arr_ltv_model.sql` | Cohort survival curves, post-drawdown governance telemetry & execution attribution | Columnar OLAP queries |
| **TypeScript 5.6 (`WebMCP`)** | `ts_webmcp_sdk/webmcp_sdk.ts`, `webmcp_benchmark.mjs` | `navigator.modelContext` tool registration & deterministic strategy compiler | `367,184 ops/sec` (`1.40 µs` P95) |
| **React 19 (`TSX`)** | `ts_webmcp_sdk/KyroVoiceCommandHook.tsx` | Push-to-talk `Web Speech API` F&O phonetic normalizer & `WebMCP` dispatcher | `< 8 ms` client dispatch |
| **Python 3.12 (`FastAPI`)** | `engine/kyro_execution_engine.py`, `api/server.py` | Vectorized 4-pillar reference engine, REST/WebMCP API server & `pytest` suite | `186,381.7 orders/sec` |

---

## Dataset Specification (`data/` — 203.71 MB, 936,033 Rows)

All datasets are partitioned below `25 MB` per file in `CSV`, `Parquet`, and `JSON` formats for standard Git compatibility without Git LFS:

| Dataset Category | File Pattern | Rows | Format | Description |
| :--- | :--- | :--- | :--- | :--- |
| **L2 5-Level DOM Ticks** | `sahi_l2_ticks_{SYMBOL}_part*.{csv,parquet}` | `600,000` | CSV + Parquet | 5-level bid/ask prices & sizes, microprice, $\text{OBI}_5$, $\text{VPIN}$, and Net GEX across `NIFTY50`, `BANKNIFTY`, `SENSEX`, `CRUDEOIL_MCX`, `GOLD_MCX` |
| **Multi-Expiry Greek Surface** | `sahi_option_greeks_surface_120k_part*.csv` | `120,000` | CSV | Strike-wise IV, $\Delta, \Gamma, \Theta, \mathcal{V}, \text{Vanna}, \text{Charm}$, Open Interest, and Dealer GEX across 300 intraday snapshots |
| **EMS/OMS/RMS Audit Log** | `sahi_ems_order_audit_log_100k_part*.csv` | `100,000` | CSV | Hop-by-hop nanosecond latency telemetry, $\text{OBI}_5$, $\text{VPIN}$, child slice counts, and slippage attribution |
| **Behavioral Risk Sessions** | `sahi_trader_behavioral_sessions_50k.csv` | `50,000` | CSV | Intraday drawdown trajectories, stop-loss modification logs, lot-size spikes, and RMS state transitions |
| **Historical Event Analogs** | `sahi_scylladb_news_vectors_2500.json` | `2,500` | JSON | 32-dimensional embeddings and post-event realized volatility distributions for macro/corporate catalysts |

---

## Repository Structure

```text
.
├── .github/workflows/
│   └── polyglot_ci_audit.yml          # Automated multi-language CI & benchmark verification workflow
├── analytics_sql/
│   └── cfo_arr_ltv_model.sql          # ClickHouse / DuckDB SQL OLAP cohort & execution telemetry queries
├── api/
│   └── server.py                      # FastAPI REST & WebMCP gateway serving live telemetry and static UI
├── benchmarks/
│   ├── stress_test.py                 # 100,000-order pre-trade RMS & multi-leg compiler benchmark harness
│   ├── benchmark_results.json         # Recorded latency percentiles (p50, p95, p99, p999) and throughput
│   └── BENCHMARK_REPORT.md            # Detailed benchmark methodology and hardware telemetry report
├── cpp_simd_greeks/
│   ├── CMakeLists.txt                 # CMake C++20 AVX-512/FMA build configuration
│   └── simd_bsm_vanna.hpp             # 16-wide AVX-512 Black-Scholes-Merton 1st & 2nd-order Greek kernel
├── data/
│   ├── harvest_sahi_market_data.py    # Initial market data & option chain generator
│   ├── scale_institutional_datasets.py# Partitioned 203.71 MB (936,033-row) dataset generator
│   ├── validate_datasets.py           # Schema, null-check, and arbitrage-free surface validator
│   └── dataset_manifest.json          # Checksums, row counts, and byte sizes for all 31 data files
├── docs/
│   ├── index.html                     # 4-quadrant HTML5 Canvas quantitative execution & risk terminal
│   └── data_bundle.js                 # Pre-compiled browser telemetry and source inspection bundle
├── engine/
│   └── kyro_execution_engine.py       # Vectorized Python implementation of all 4 quantitative subsystems
├── go_ems_router/
│   ├── go.mod                         # Go 1.23 module definition
│   ├── ems_router.go                  # OBI_5, VPIN toxicity gate & Poisson micro-iceberg order router
│   └── broker_race_simulator.go       # High-throughput 0DTE expiry flash-crash execution simulator
├── rust_feedserver/
│   ├── Cargo.toml                     # Rust crate manifest (tokio, serde, wasm-bindgen)
│   └── src/
│       ├── lib.rs                     # Lock-free FeedServer actor & #[repr(C)] atomic TiltGuardRMS
│       └── wire_frame_codec.rs        # 64-byte #[repr(C, align(64))] SahiWireFrame64 zero-copy codec
├── scylladb/
│   └── schema.cql                     # Shard-aware time-bucketed CQL tables for candles, GEX & RMS logs
├── tests/
│   └── test_kyro_engine.py            # Pytest unit and invariant test suite (10 test cases)
├── ts_webmcp_sdk/
│   ├── package.json                   # TypeScript / Node.js package manifest
│   ├── webmcp_sdk.ts                  # Chrome WebMCP (navigator.modelContext) schema & tool registry
│   ├── webmcp_benchmark.mjs           # 50,000-iteration V8 execution benchmark
│   └── KyroVoiceCommandHook.tsx       # React 19 Web Speech API + WebMCP integration hook
└── wasm_wire_decoder/
    └── sahi_zero_copy_frame.wat       # WebAssembly Text (WAT) zero-copy 64-byte wire frame decoder
```

---

## Build, Test & Benchmark Instructions

### 1. Run Unit & Invariant Tests (`pytest`)
```bash
python -m pytest tests/test_kyro_engine.py -v
```

### 2. Run Pre-Trade RMS & Strategy Compiler Stress Benchmarks (`100,000` Orders)
```bash
python benchmarks/stress_test.py
```

### 3. Run V8 `WebMCP` Tool Registry Benchmark (`50,000` Iterations)
```bash
node ts_webmcp_sdk/webmcp_benchmark.mjs
```

### 4. Validate Partitioned Datasets (`203.71 MB` / `936,033` Rows)
```bash
python data/validate_datasets.py
```

### 5. Build Native C++20 AVX-512 Shared Library & Run Rust/Go Modules
```bash
# C++20 AVX-512 Greek Kernel
cmake -S cpp_simd_greeks -B cpp_simd_greeks/build -DCMAKE_BUILD_TYPE=Release
cmake --build cpp_simd_greeks/build --config Release

# Rust FeedServer & 64-Byte Wire Codec
cd rust_feedserver && cargo test --release && cd ..

# Go Smart Order Router & Expiry Flash-Crash Simulator
cd go_ems_router && go test -v ./... && cd ..
```

### 6. Start the FastAPI Telemetry Server & Web Terminal
```bash
python -m uvicorn api.server:app --host 127.0.0.1 --port 8088
```
Then open [`http://127.0.0.1:8088/`](http://127.0.0.1:8088/) in any modern Chromium/WebGL2 browser.
