WITH latest AS (
  SELECT MAX(period_yyyymm) AS m FROM fact_rtt_monthly
)
SELECT
  f.treatment_function_code,
  f.treatment_function_name,
  SUM(f.total_waiting) AS backlog,
  ROUND(100.0 * SUM(f.within_18_weeks) / SUM(f.total_waiting), 2) AS pct_within_18,
  SUM(f.over_52_weeks) AS over_52
FROM fact_rtt_monthly f
JOIN latest ON f.period_yyyymm = latest.m
GROUP BY f.treatment_function_code, f.treatment_function_name
ORDER BY backlog DESC
LIMIT 20;