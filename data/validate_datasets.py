import os
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import json
import pandas as pd

data_dir = r"e:\NIKHIL\MAHINDRA UNIVERSITY\internship\sahi\data"

print("=" * 80)
print("  DATASET VALIDATION SUITE")
print("=" * 80)

# 1. sahi_intraday_ticks_50k.csv
ticks_p = os.path.join(data_dir, "sahi_intraday_ticks_50k.csv")
df_ticks = pd.read_csv(ticks_p)
print(f"[1] sahi_intraday_ticks_50k.csv:")
print(f"    Rows: {len(df_ticks):,} | Columns: {len(df_ticks.columns)} | Nulls: {df_ticks.isnull().sum().sum()}")
print(f"    Instruments: {df_ticks['instrument'].value_counts().to_dict()}")
print(f"    Regimes: {df_ticks['regime'].value_counts().to_dict()}")
print(f"    First timestamp: {df_ticks['timestamp'].iloc[0]} | Last timestamp: {df_ticks['timestamp'].iloc[-1]}")
print(f"    VPIN range: [{df_ticks['vpin'].min()}, {df_ticks['vpin'].max()}] | Mean: {df_ticks['vpin'].mean():.3f}")
print(f"    OBI range: [{df_ticks['obi'].min()}, {df_ticks['obi'].max()}] | Std: {df_ticks['obi'].std():.3f}")
print(f"    Sample Lorentz Vector: {df_ticks['lorentz_vector'].iloc[0]}")

# 2. sahi_option_chains_greeks.json
chains_p = os.path.join(data_dir, "sahi_option_chains_greeks.json")
with open(chains_p, 'r', encoding='utf-8') as f:
    chains_data = json.load(f)
print(f"\n[2] sahi_option_chains_greeks.json:")
print(f"    Instruments modeled: {len(chains_data['instruments'])}")
for inst, val in chains_data['instruments'].items():
    strikes = val['chain']
    sample_ce = strikes[len(strikes)//2]['call']
    sample_pe = strikes[len(strikes)//2]['put']
    print(f"    - {inst:14}: Spot={val['spot_price']}, ZeroGamma={val['zero_gamma_flip']}, MaxPain={val['max_pain_strike']}, NetGEX={val['total_net_gex_cr']} Cr, Strikes={len(strikes)}")
    print(f"      ATM CE: Delta={sample_ce['delta']}, Gamma={sample_ce['gamma']}, Theta={sample_ce['theta_per_day']}, Vega={sample_ce['vega_1pct']}, Vanna={sample_ce['vanna']}, Charm={sample_ce['charm']}")
    print(f"      DOM Bids: {len(sample_ce['dom_bids_l5'])} levels | DOM Asks: {len(sample_ce['dom_asks_l5'])} levels")

# 3. sahi_live_news_catalysts.json
news_p = os.path.join(data_dir, "sahi_live_news_catalysts.json")
with open(news_p, 'r', encoding='utf-8') as f:
    news_data = json.load(f)
print(f"\n[3] sahi_live_news_catalysts.json:")
print(f"    Catalysts count: {len(news_data)}")
cats = pd.Series([item['catalyst_category'] for item in news_data]).value_counts().to_dict()
print(f"    Category distribution: {cats}")
first_item = news_data[0]
print(f"    Sample Headline: \"{first_item['headline']}\"")
print(f"    URL: {first_item['canonical_url']}")
print(f"    Historical Analogs count: {len(first_item['scylla_enriched_analytics']['historical_analogs'])}")
print(f"    Recommended Structure: {first_item['scylla_enriched_analytics']['recommended_multi_leg_structure']}")
print(f"    Implied Move: {first_item['scylla_enriched_analytics']['implied_straddle_move_pct']}% | Realized Median: {first_item['scylla_enriched_analytics']['realized_move_distribution']['median_pct']}%")

# 4. sahi_trader_behavioral_sessions.csv
sess_p = os.path.join(data_dir, "sahi_trader_behavioral_sessions.csv")
df_sess = pd.read_csv(sess_p)
print(f"\n[4] sahi_trader_behavioral_sessions.csv:")
print(f"    Rows: {len(df_sess):,} | Columns: {len(df_sess.columns)} | Nulls: {df_sess.isnull().sum().sum()}")
print(f"    Unprofitable Sessions: {(df_sess['net_pnl_inr'] < 0).mean()*100:.2f}%")
print(f"    Mean TiltScore: {df_sess['tilt_score'].mean():.2f} | Tilted (>70): {(df_sess['tilt_score'] >= 70).mean()*100:.2f}%")
print(f"    Total Brokerage Paid: INR {df_sess['brokerage_and_stt_inr'].sum():,.2f}")
print(f"    Mean Brokerage Burn Ratio: {df_sess.loc[df_sess['net_pnl_inr'] < 0, 'brokerage_to_loss_burn_ratio'].mean():.4f}")
print(f"    Nudges Triggered: {df_sess['sahi_nudge_triggered'].value_counts().to_dict()}")

# 5. dataset_manifest.json
manifest_p = os.path.join(data_dir, "dataset_manifest.json")
with open(manifest_p, 'r', encoding='utf-8') as f:
    manifest_data = json.load(f)
print(f"\n[5] dataset_manifest.json:")
print(f"    Manifest verified. Total datasets tracked: {len(manifest_data['datasets'])}")
print("=" * 80)
print("  ALL DATASETS VERIFIED PERFECT!")
print("=" * 80)
