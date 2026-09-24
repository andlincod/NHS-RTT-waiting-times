import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

TARGET_PCT = 92.0


def forecast_national_backlog(national: pd.DataFrame, horizons=(1, 3, 6)) -> pd.DataFrame:
    """Simple lag regression on national backlog."""
    df = national.sort_values("period").copy()
    df["t"] = np.arange(len(df))
    df["backlog_lag1"] = df["backlog"].shift(1)
    df["backlog_lag3"] = df["backlog"].shift(3)
    df["backlog_roll3"] = df["backlog"].rolling(3, min_periods=1).mean()
    train = df.dropna().copy()

    features = ["t", "backlog_lag1", "backlog_lag3", "backlog_roll3"]
    model = RandomForestRegressor(n_estimators=200, random_state=42)
    model.fit(train[features], train["backlog"])

    # one-step rolling forecast from latest known point
    history = df.copy()
    rows = []
    for h in range(1, max(horizons) + 1):
        last = history.iloc[-1]
        lag1 = history.iloc[-1]["backlog"]
        lag3 = history.iloc[-3]["backlog"] if len(history) >= 3 else lag1
        roll3 = history["backlog"].tail(3).mean()
        x = pd.DataFrame([{
            "t": last["t"] + 1,
            "backlog_lag1": lag1,
            "backlog_lag3": lag3,
            "backlog_roll3": roll3,
        }])
        pred = float(model.predict(x)[0])
        next_period = last["period"] + pd.offsets.MonthBegin(1)
        history = pd.concat([
            history,
            pd.DataFrame([{
                "period": next_period,
                "period_yyyymm": next_period.strftime("%Y-%m"),
                "backlog": pred,
                "t": last["t"] + 1,
            }]),
        ], ignore_index=True)
        if h in horizons:
            rows.append({"horizon_months": h, "period": next_period.strftime("%Y-%m"), "backlog_forecast": pred})
    return pd.DataFrame(rows)


def breach_risk_table(ts: pd.DataFrame, min_backlog: float = 2000) -> pd.DataFrame:
    """
    Latest-month Trust x specialty risk score.
    High risk = low pct_within_18 + large backlog + worsening trend.
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