from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine

RAW = Path("data/raw/NHS_2021_2025_master_combined.csv")
OUT_PARQUET = Path("data/interim/rtt_incomplete.parquet")
OUT_DB = Path("data/processed/nhs_rtt.db")

OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
OUT_DB.parent.mkdir(parents=True, exist_ok=True)

# Week bands
WITHIN_18 = [f"gt_{i:02d}_to_{i+1:02d}_weeks_sum_1" for i in range(0, 18)]
BANDS_18_TO_52 = [f"gt_{i:02d}_to_{i+1:02d}_weeks_sum_1" for i in range(18, 52)]
OVER_52_SIMPLE = ["gt_52_weeks_sum_1"]
OVER_52_DETAIL = (
    [f"gt_{i:02d}_to_{i+1:02d}_weeks_sum_1" for i in range(52, 104)]
    + ["gt_104_weeks_sum_1"]
)
ALL_BANDS = WITHIN_18 + BANDS_18_TO_52 + OVER_52_SIMPLE + OVER_52_DETAIL

KEEP = [
    "period",
    "provider_org_code", "provider_org_name",
    "commissioner_org_code", "commissioner_org_name",
    "rtt_part_type", "rtt_part_description",
    "treatment_function_code", "treatment_function_name",
    "source_file",
] + ALL_BANDS

header = pd.read_csv(RAW, nrows=0).columns.tolist()
usecols = [c for c in KEEP if c in header]
all_bands = [c for c in ALL_BANDS if c in usecols]
within_18 = [c for c in WITHIN_18 if c in usecols]
over_52 = [c for c in (OVER_52_SIMPLE + OVER_52_DETAIL) if c in usecols]


def parse_period(s: str) -> str:
    months = {
        "JANUARY": "01", "FEBRUARY": "02", "MARCH": "03", "APRIL": "04",
        "MAY": "05", "JUNE": "06", "JULY": "07", "AUGUST": "08",
        "SEPTEMBER": "09", "OCTOBER": "10", "NOVEMBER": "11", "DECEMBER": "12",
    }
    parts = str(s).upper().split("-")
    if len(parts) >= 3 and parts[1] in months:
        return f"{parts[2]}-{months[parts[1]]}"
    return pd.NA


pieces = []
for i, chunk in enumerate(pd.read_csv(
    RAW, usecols=usecols, chunksize=200_000, low_memory=False
)):
    # Incomplete = Part 2
    mask = chunk["rtt_part_type"].astype(str).str.upper().isin(
        ["PART_2", "PART2", "2", "PART 2"]
    )
    if not mask.any():
        mask = chunk["rtt_part_description"].astype(str).str.contains(
            "incomplete", case=False, na=False
        )
    chunk = chunk.loc[mask].copy()
    if chunk.empty:
        print(f"chunk {i}: kept 0")
        continue

    # Drop specialty totals (avoid double-counting)
    chunk = chunk[
        ~chunk["treatment_function_code"].astype(str).isin(["C_999", "999"])
        & ~chunk["treatment_function_name"].astype(str).str.lower().eq("total")
    ]
    if chunk.empty:
        print(f"chunk {i}: kept 0 after dropping totals")
        continue

    for c in all_bands:
        chunk[c] = pd.to_numeric(chunk[c], errors="coerce").fillna(0)

    # Derive metrics from week bands (do NOT use CSV "total")
    chunk["total_waiting"] = chunk[all_bands].sum(axis=1)
    chunk["within_18_weeks"] = chunk[within_18].sum(axis=1)
    chunk["over_18_weeks"] = (
        chunk["total_waiting"] - chunk["within_18_weeks"]
    ).clip(lower=0)
    chunk["over_52_weeks"] = chunk[over_52].sum(axis=1)

    chunk["pct_within_18_weeks"] = (
        chunk["within_18_weeks"] / chunk["total_waiting"].replace(0, pd.NA)
    )
    chunk["pct_over_52_weeks"] = (
        chunk["over_52_weeks"] / chunk["total_waiting"].replace(0, pd.NA)
    )
    chunk["period_yyyymm"] = chunk["period"].map(parse_period)
    chunk["pathway_type"] = "Incomplete"

    out = chunk[[
        "period", "period_yyyymm",
        "provider_org_code", "provider_org_name",
        "commissioner_org_code", "commissioner_org_name",
        "treatment_function_code", "treatment_function_name",
        "pathway_type",
        "total_waiting", "within_18_weeks", "over_18_weeks", "over_52_weeks",
        "pct_within_18_weeks", "pct_over_52_weeks",
        "source_file",
    ]]
    pieces.append(out)
    print(f"chunk {i}: kept {len(out):,}")

df = pd.concat(pieces, ignore_index=True)
df.to_parquet(OUT_PARQUET, index=False)
print("saved", OUT_PARQUET, "rows=", f"{len(df):,}")
print(
    df.groupby("period_yyyymm")["total_waiting"]
    .sum()
    .tail(6)
)

# Load into SQL
engine = create_engine(f"sqlite:///{OUT_DB}")
df.to_sql(
    "fact_rtt_monthly",
    engine,
    if_exists="replace",
    index=False,
    chunksize=50_000,
)

print(pd.read_sql("SELECT COUNT(*) AS n FROM fact_rtt_monthly", engine))
print(pd.read_sql(
    """
    SELECT period_yyyymm,
           SUM(total_waiting) AS backlog,
           ROUND(100.0 * SUM(within_18_weeks) / SUM(total_waiting), 2) AS pct_within_18
    FROM fact_rtt_monthly
    GROUP BY period_yyyymm
    ORDER BY period_yyyymm DESC
    LIMIT 6
    """,
    engine,
))