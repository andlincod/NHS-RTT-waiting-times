SELECT
  period_yyyymm,
  SUM(total_waiting) AS backlog,
  SUM(within_18_weeks) AS within_18,
  SUM(over_18_weeks) AS over_18,
  SUM(over_52_weeks) AS over_52,
  ROUND(100.0 * SUM(within_18_weeks) / SUM(total_waiting), 2) AS pct_within_18,
  ROUND(100.0 * SUM(over_52_weeks) / SUM(total_waiting), 2) AS pct_over_52,
  ROUND(92.0 - (100.0 * SUM(within_18_weeks) / SUM(total_waiting)), 2) AS gap_vs_92_target
FROM fact_rtt_monthly
GROUP BY period_yyyymm
ORDER BY period_yyyymm;