import pandas as pd

path = "data/raw/NHS_2021_2025_master_combined.csv"

# header only
cols = pd.read_csv(path, nrows=0).columns.tolist()
print(len(cols))
print(cols)

# tiny sample to see real values
sample = pd.read_csv(path, nrows=5_000, low_memory=False)
print(sample.head())

# find likely pathway / part column
for c in sample.columns:
    if sample[c].dtype == object:
        vals = sample[c].dropna().astype(str).str.lower().unique()[:20]
        if any(v in " ".join(vals) for v in ["par", "incomplete", "admited"]):
            print(c, "->", vals[:10])

print(sample["rtt_part_type"].value_counts(dropna=False))
print(sample["rtt_part_description"].value_counts(dropna=False))