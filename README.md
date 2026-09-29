# Sahi Kyro-Execution & Pulse Engine (`sahi-kyro-execution-engine`)

> **Sub-Millisecond 4-Pillar Polyglot Quantitative Infrastructure for Sahi (`sahi.com` / Aaritya Technologies Pvt. Ltd.)**  
> **Live Interactive Terminal:** [https://vnvarma39.github.io/sahi-kyro-execution-engine/](https://vnvarma39.github.io/sahi-kyro-execution-engine/)  
> **Author:** Nikhil Varma Vanapala (Computer Science & Engineering, Mahindra University)

---

## Architectural Overview

Engineered specifically for Sahi's post-Series B ($33M, Accel & Elevation Capital) active derivatives infrastructure, this repository implements the **4 Next-Horizon Pillars** atop Sahi's in-house **`Adaptors` $\rightarrow$ `Feedbroker` $\rightarrow$ Lock-Free Rust `FeedServers` (`Arc<[u8]>`) $\rightarrow$ `ScyllaDB` $\rightarrow$ `6.61 ms` EMS/OMS/RMS $\rightarrow$ `Flutter / WebMCP`** stack:

| Pillar | Subsystem | Primary Stack | Audited Benchmark / SLA |
| :--- | :--- | :--- | :--- |
| **Pillar 1** | **GEX-Flow & Regime-Gated ML Meta-Controller** | Rust (`Arc<[u8]>`) + Python Vectorized BSM | `<1.80 ms` across 200 strikes; gates *Nadaraya-Watson* (+GEX pin) vs *Lorentzian $k$-NN* (-GEX breakout) |
| **Pillar 2** | **Kyro `WebMCP` & Pulse-to-Payoff™ Compiler** | TypeScript (`web.sahi.com` Origin Trial) + ScyllaDB CQL | **`367,184 compilations/sec`** (`1.40 µs` P95); 100% **Hedged-First Invariant** ($t_{\text{long}} < t_{\text{short}}$), **75.7% upfront SPAN margin saved** |
| **Pillar 3** | **P&L Protect 2.0: `TiltGuard™` Behavioral RMS** | Rust `#[repr(C)]` Atomic Bitmask + Python RMS | **`186,381.7 orders/sec`** (**`2.01 µs` mean / `3.90 µs` P95** vs Sahi's `200 µs` budget — **99.0% headroom**) |
| **Pillar 4** | **EMS Slippage Shield & RTT Attribution Waterfall** | Go (`go_ems_router`) + Python DOM Slicer | 5-Level Exponentially Weighted $\text{OBI}_5$ ($\lambda=0.40$) + Easley-de Prado $\text{VPIN}$ Poisson Micro-Iceberg Slicing |

---

## Repository Structure

```text
sahi/
├── rust_feedserver/              # Lock-free Rust FeedServer actor, zero-copy Arc<[u8]> GEX & <15us TiltGuard RMS
│   ├── Cargo.toml
│   └── src/lib.rs
├── go_ems_router/                # AWS Mumbai EMS -> Physical DC OMS (4.28ms hop) OBI_5 & VPIN Micro-Iceberg Router
│   ├── go.mod
│   └── ems_router.go
├── scylladb/                     # Shard-aware & token-aware time-bucketed ScyllaDB CQL schemas (<20ms p999)
│   └── schema.cql
├── ts_webmcp_sdk/                # Chrome WebMCP (Origin Trial 2026-11-17) SDK & V8 Benchmark Suite
│   ├── package.json
│   ├── webmcp_sdk.ts
│   └── webmcp_benchmark.mjs
├── engine/                       # Python 4-Pillar Vectorized BSM, GEX, Lorentzian k-NN, WebMCP & TiltGuard Engine
│   └── kyro_execution_engine.py
├── api/                          # FastAPI Low-Latency REST & WebMCP Gateway
│   └── server.py
├── benchmarks/                   # 100,000-Order Stress Test Suite & Audited Telemetry Reports
│   ├── stress_test.py
│   ├── benchmark_results.json
│   └── BENCHMARK_REPORT.md
├── data/                         # 60,000 Calibrated Ticks, 400 Option Contracts, 133 Live Sahi News, 3,000 Sessions
│   ├── harvest_sahi_market_data.py
│   ├── validate_datasets.py
│   └── dataset_manifest.json
├── tests/                        # Pytest Verification Suite (10/10 Passing)
│   └── test_kyro_engine.py
├── docs/                         # Kinetic Fortress / Neo-Brutalist Dark Industrial Web Terminal (GitHub Pages)
│   ├── index.html
│   └── data_bundle.js
├── ORCHESTRATOR_AUDIT_REPORT.md  # Full Engineering & Product Lead Clearance Audit
└── problem_breakdown_and_pitch.md # Executive Architectural Blueprint for Dale Vaz & Manish Jain
```

---

## Quick Start & Verification

```bash
# 1. Run the 10-test Pytest Verification Suite
python -m pytest tests/test_kyro_engine.py -v

# 2. Run the 100,000-Order TiltGuard RMS Stress Benchmark
python benchmarks/stress_test.py

# 3. Run the 50,000-Iteration V8/Node.js WebMCP Compiler Benchmark
node ts_webmcp_sdk/webmcp_benchmark.mjs
```
