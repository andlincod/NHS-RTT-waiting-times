import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[1]  # nhs-rtt-analytics/
DB_PATH = ROOT / "data" / "processed" / "nhs_rtt.db"
DB = f"sqlite:///{DB_PATH}"


def load_national_series(engine=None) -> pd.DataFrame:
    engine = engine or create_engine(DB)
    df = pd.read_sql(
        """
        SELECT period_yyyymm,
               SUM(total_waiting) AS backlog,
               100.0 * SUM(within_18_weeks) / SUM(total_waiting) AS pct_within_18
        FROM fact_rtt_monthly
        GROUP BY period_yyyymm
        ORDER BY period_yyyymm
        """,
        engine,
    )
    df["period"] = pd.to_datetime(df["period_yyyymm"] + "-01")
    return df


def load_trust_specialty_monthly(engine=None) -> pd.DataFrame:
    engine = engine or create_engine(DB)
    df = pd.read_sql(
        """
        SELECT period_yyyymm,
               provider_org_code,
               provider_org_name,
               treatment_function_code,
               treatment_function_name,
               SUM(total_waiting) AS backlog,
               SUM(within_18_weeks) AS within_18,
               SUM(over_52_weeks) AS over_52,
               100.0 * SUM(within_18_weeks) / SUM(total_waiting) AS pct_within_18
        FROM fact_rtt_monthly
        GROUP BY 1, 2, 3, 4, 5
        HAVING SUM(total_waiting) > 0
        ORDER BY 1, 2, 4
        """,
        engine,
    )
    df["period"] = pd.to_datetime(df["period_yyyymm"] + "-01")
    return df
