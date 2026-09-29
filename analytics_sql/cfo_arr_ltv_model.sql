-- =============================================================================
-- SAHI (AARITYA BROKING) SERIES-B CFO ARR & RETENTION MULTIPLIER OLAP MODEL
-- Target Engine: ClickHouse / DuckDB / ScyllaDB Analytics
-- Evaluates the P&L impact of deploying Kyro WebMCP + TiltGuard 1-Lot Governor
-- across Sahi's 50,000-session empirical retail F&O dataset.
-- =============================================================================

WITH cohort_metrics AS (
    SELECT
        archetype,
        COUNT(*)                                                AS total_sessions,
        AVG(orders_executed)                                    AS avg_orders_per_session,
        AVG(brokerage_and_taxes_inr)                            AS avg_brokerage_inr,
        AVG(net_pnl_inr)                                        AS avg_net_pnl_inr,
        SUM(CASE WHEN net_pnl_inr < 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS loss_rate_ratio,
        AVG(estimated_capital_saved_inr)                        AS avg_tiltguard_capital_saved_inr
    FROM read_csv_auto('sahi/data/sahi_trader_behavioral_sessions_50k.csv')
    GROUP BY archetype
),
series_b_projection AS (
    SELECT
        150000                                                  AS active_fno_dau,
        248                                                     AS trading_days_per_year,
        10.0                                                    AS flat_brokerage_per_order_inr,
        -- Pillar 2: WebMCP shifts 28% of 1-leg scalps (Rs 10) to 2.6-leg hedged baskets (Rs 26)
        (150000 * 0.28 * (2.6 - 1.0) * 2.0 * 10.0 * 248) / 1e7  AS webmcp_incremental_arr_cr,
        -- Pillar 3: TiltGuard Yellow-Card 1-Lot Governor preserves 15.4% afternoon flow vs 11:59PM lockout
        (150000 * 0.154 * 6.5 * 10.0 * 248) / 1e7               AS tiltguard_retained_arr_cr,
        -- LTV expansion from extending retail cohort survival from 3.2 months to 8.9 months
        8.9 / 3.2                                               AS ltv_survival_multiplier
)
SELECT
    c.archetype,
    c.total_sessions,
    ROUND(c.avg_orders_per_session, 1)                          AS avg_orders,
    ROUND(c.loss_rate_ratio * 100.0, 2)                         AS loss_rate_pct,
    ROUND(c.avg_tiltguard_capital_saved_inr, 2)                 AS capital_saved_per_session_inr,
    ROUND(p.webmcp_incremental_arr_cr, 2)                       AS projected_webmcp_arr_cr,
    ROUND(p.tiltguard_retained_arr_cr, 2)                       AS projected_tiltguard_arr_cr,
    ROUND(p.webmcp_incremental_arr_cr + p.tiltguard_retained_arr_cr, 2) AS total_incremental_arr_cr,
    ROUND(p.ltv_survival_multiplier, 2)                         AS trader_ltv_multiplier
FROM cohort_metrics c
CROSS JOIN series_b_projection p
ORDER BY c.total_sessions DESC;
