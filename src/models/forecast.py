import numpy as np
import pandas as pd

TARGET_PCT = 92.0
DEFAULT_HORIZONS = (1, 3, 6)
DRIFT_LOOKBACK = 12


def forecast_national_backlog(
    national: pd.DataFrame,
    horizons=DEFAULT_HORIZONS,
    lookback: int = DRIFT_LOOKBACK,
) -> pd.DataFrame:
    """
    Drift forecast on national backlog.

    last_backlog + h * average monthly change over the previous `lookback` months.
    Chosen because it beat naive and the previous lag-based random forest on a
    12-origin walk-forward holdout (horizons 1/3/6).
    """
    df = national.sort_values("period").copy()
    if df.empty:
        return pd.DataFrame(columns=["horizon_months", "period", "backlog_forecast"])

    last = df.iloc[-1]
    last_val = float(last["backlog"])
    window = df["backlog"].tail(lookback + 1)
    if len(window) < 2:
        monthly_drift = 0.0
    else:
        monthly_drift = float(window.iloc[-1] - window.iloc[0]) / (len(window) - 1)

    rows = []
    for h in horizons:
        period = (last["period"] + pd.offsets.MonthBegin(int(h))).strftime("%Y-%m")
        rows.append({
            "horizon_months": int(h),
            "period": period,
            "backlog_forecast": last_val + int(h) * monthly_drift,
        })
    return pd.DataFrame(rows)


def _naive_forecast(history: pd.DataFrame, horizons=DEFAULT_HORIZONS) -> pd.DataFrame:
    last = history.iloc[-1]
    last_val = float(last["backlog"])
    rows = []
    for h in horizons:
        period = (last["period"] + pd.offsets.MonthBegin(int(h))).strftime("%Y-%m")
        rows.append({
            "horizon_months": int(h),
            "period": period,
            "backlog_forecast": last_val,
        })
    return pd.DataFrame(rows)


def backtest_national_backlog(
    national: pd.DataFrame,
    horizons=DEFAULT_HORIZONS,
    n_origins: int = 12,
    lookback: int = DRIFT_LOOKBACK,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Walk-forward holdout comparing drift vs naive at each horizon.

    Returns (detail errors, mae summary pivoted by model x horizon).
    """
    full = national.sort_values("period").reset_index(drop=True)
    max_h = max(horizons)
    last_origin_idx = len(full) - 1 - max_h
    first_origin_idx = max(lookback + 1, last_origin_idx - n_origins + 1)
    if last_origin_idx < first_origin_idx:
        raise ValueError("Not enough history for the requested backtest window.")

    detail_rows = []
    for origin_idx in range(first_origin_idx, last_origin_idx + 1):
        history = full.iloc[: origin_idx + 1].copy()
        origin_period = history.iloc[-1]["period"].strftime("%Y-%m")
        preds = {
            "drift": forecast_national_backlog(history, horizons=horizons, lookback=lookback),
            "naive": _naive_forecast(history, horizons=horizons),
        }
        for model_name, fc in preds.items():
            for _, row in fc.iterrows():
                h = int(row["horizon_months"])
                actual = float(full.iloc[origin_idx + h]["backlog"])
                pred = float(row["backlog_forecast"])
                detail_rows.append({
                    "origin_period": origin_period,
                    "model": model_name,
                    "horizon_months": h,
                    "period": row["period"],
                    "backlog_actual": actual,
                    "backlog_forecast": pred,
                    "abs_error": abs(pred - actual),
                })

    detail = pd.DataFrame(detail_rows)
    mae = (
        detail.groupby(["model", "horizon_months"], as_index=False)["abs_error"]
        .mean()
        .rename(columns={"abs_error": "mae"})
    )
    mae_table = mae.pivot(index="model", columns="horizon_months", values="mae")
    mae_table = mae_table.reindex(["drift", "naive"])
    mae_table.columns = [f"h{h}_mae" for h in mae_table.columns]
    return detail, mae_table


def breach_risk_table(ts: pd.DataFrame, min_backlog: float = 2000) -> pd.DataFrame:
    """
    Latest-month Trust x specialty current-severity ranking.

    Score = gap below 92% + backlog size + recent % drop. Use for triage of
    pockets that are already weak/large — not as a forecast of next-month
    deterioration (walk-forward checks did not beat chance on % within 18).
    """
    df = ts.sort_values(["provider_org_code", "treatment_function_code", "period"]).copy()
    df["pct_lag1"] = df.groupby(
        ["provider_org_code", "treatment_function_code"]
    )["pct_within_18"].shift(1)
    df["pct_delta"] = df["pct_within_18"] - df["pct_lag1"]

    latest = df["period"].max()
    now = df[df["period"] == latest].copy()
    now = now[now["backlog"] >= min_backlog].copy()

    # risk: farther below 92, bigger backlog, declining performance
    now["gap_vs_92"] = TARGET_PCT - now["pct_within_18"]
    now["risk_score"] = (
        now["gap_vs_92"].clip(lower=0)
        + 10 * np.log1p(now["backlog"]) / np.log1p(now["backlog"].max())
        + (-now["pct_delta"].fillna(0)).clip(lower=0)
    )
    now = now.sort_values("risk_score", ascending=False)
    return now[[
        "period_yyyymm",
        "provider_org_name",
        "treatment_function_name",
        "backlog",
        "pct_within_18",
        "gap_vs_92",
        "pct_delta",
        "over_52",
        "risk_score",
    ]].head(25)
