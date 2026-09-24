SELECT COUNT(*) AS rows FROM fact_rtt_monthly;

SELECT MIN(period_yyyymm), MAX(period_yyyymm) FROM fact_rtt_monthly;

SELECT period_yyyymm, SUM(total_waiting) AS backlog
FROM fact_rtt_monthly
GROUP BY period_yyyymm
ORDER BY period_yyyymm;