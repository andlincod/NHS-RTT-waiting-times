WITH latest AS (
  SELECT MAX(period_yyyymm) AS m FROM fact_rtt_monthly
)
SELECT
  f.provider_org_code,
  f.provider_org_name,
  SUM(f.total_waiting) AS backlog,
  ROUND(100.0 * SUM(f.within_18_weeks) / SUM(f.total_waiting), 2) AS pct_within_18,
  ROUND(92.0 - (100.0 * SUM(f.within_18_weeks) / SUM(f.total_waiting)), 2) AS gap_vs_92
FROM fact_rtt_monthly f
JOIN latest ON f.period_yyyymm = latest.m
GROUP BY f.provider_org_code, f.provider_org_name
HAVING SUM(f.total_waiting) > 1000
ORDER BY pct_within_18 ASC
LIMIT 20;