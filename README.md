# NHS RTT waiting-list analytics

England still has a statutory target that **92% of incomplete RTT pathways** should be waiting **18 weeks or less**. For years the national figure has sat well below that. This repo takes a public consultant-led RTT extract (Jan 2021–Dec 2025), cleans it into something queryable, and answers a few practical questions:

- How big is the incomplete backlog, and how far off the 92% standard are we?
- Which trusts and specialties carry the most pressure?
- Where does a simple forward look and a rough “breach risk” ranking point next?

It is an analytics project, not an operational tool. Numbers come from published NHS England-style RTT tables compiled on [Kaggle](https://www.kaggle.com/datasets/hammad9191/nhs-consultant-led-rtt-waiting-times20212025). Treat them as directional, not as a live waiting-list system.

## What’s in here

1. **Ingest** — filter to incomplete pathways, derive week-band metrics, write parquet + SQLite  
2. **SQL** — national KPIs, trust performance, specialty backlog  
3. **Notebooks** — charts/tables for the same questions, plus a small forecast and risk ranking  
4. **A short write-up** — `reports/executive_summary.md`

The useful table is `fact_rtt_monthly` in `data/processed/nhs_rtt.db`.

## Setup

Python 3.12 works (that’s what the project venv was built with). Do everything from the **repo root**.

**Linux / macOS**

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Windows (Command Prompt)**

```bat
py -3.12 -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

**Windows (PowerShell)** — same as above, but activate with:

```powershell
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks the script, run once:  
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

(`py` is the usual Windows launcher. Plain `python` is fine if that’s what `python --version` shows as 3.12.)

### Data

The raw CSV is large (~7GB). Either place  
`NHS_2021_2025_master_combined.csv` under `data/raw/`, or download it:

```bash
python temporary_files/import_kaggle.py
```

You need Kaggle credentials for `kagglehub`:

- Linux/macOS: `~/.kaggle/kaggle.json`
- Windows: `%USERPROFILE%\.kaggle\kaggle.json`  
  (e.g. `C:\Users\<you>\.kaggle\kaggle.json`)

Same file either way — download an API token from your Kaggle account settings and put it there. Env vars work too if you prefer.

### Build the database

```bash
python src/ingest.py
```

That writes:

- `data/interim/rtt_incomplete.parquet`
- `data/processed/nhs_rtt.db` (table `fact_rtt_monthly`)

Ingest walks the CSV in chunks — expect it to take a while on a laptop. Give the process enough free disk (raw + parquet + DB is on the order of ~8GB+).

### Queries and notebooks

If you have the `sqlite3` CLI:

```bash
sqlite3 -header -column data/processed/nhs_rtt.db < sql/00_sanity.sql
sqlite3 -header -column data/processed/nhs_rtt.db < sql/01_kpis_national.sql
```

On Windows, `sqlite3` often isn’t installed by default. Options:

1. Install the [SQLite command-line tools](https://www.sqlite.org/download.html) and add them to `PATH`, or  
2. Skip the CLI and run the same SQL from a notebook / Python:

```python
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("sqlite:///data/processed/nhs_rtt.db")
print(pd.read_sql(open("sql/00_sanity.sql").read().split(";")[0], engine))
```

Then open the notebooks under `notebooks/` with the **venv** kernel selected (in VS Code / Cursor: pick `venv\Scripts\python.exe` on Windows):

- `01_business_kpis.ipynb` — trusts / specialties / national trend  
- `02_forecast_breach_risk.ipynb` — national backlog forecast and trust×specialty risk table  

Run notebook cells with the working directory set to `notebooks/` (paths assume that).

## Layout

```
data/raw/               # original CSV (gitignored; download locally)
data/interim/           # cleaned parquet
data/processed/         # SQLite DB
src/ingest.py           # raw → parquet → SQLite
src/features.py         # helpers to pull series out of the DB
src/models/             # backlog forecast + breach-risk ranking
sql/                    # numbered ad-hoc queries (00–03)
notebooks/              # exploration and charts
reports/                # executive summary (and figures when saved)
temporary_files/        # Kaggle download helper
peek_raw_columns.py     # quick peek at raw columns
```

There is no `main.py` on purpose. Ingest is the batch job; SQL and notebooks are how you look at the results.

## Findings (snapshot)

From the latest month in this extract (Dec 2025), roughly:

- National incomplete backlog ≈ **7.2M**
- % within 18 weeks ≈ **61%** (about **30 points** under the 92% standard)
- Biggest specialty volumes: trauma & orthopaedics, ophthalmology, ENT, gynaecology
- Weakest trust performance and highest-risk trust×specialty pockets are listed in the executive summary and notebook outputs

Those are from a completed run of this pipeline, not live NHS feeds.

## Honest limits

- The forecast is a **simple lag-based random forest** on the national series. It’s a sketch, not a capacity model.
- “Breach risk” is a **heuristic score** (distance from 92%, backlog size, recent deterioration) — useful for triage, not a clinical priority score.
- Specialty “Total” rows are dropped in ingest so we don’t double-count. If your question needs a different slice of RTT (e.g. completed pathways), you’ll need to change the filter.

## If something looks empty

If SQLite returns 0 rows, ingest didn’t finish loading the DB (the parquet step can succeed and `to_sql` still get interrupted). Re-run `python src/ingest.py`, or load from the existing parquet into SQLite yourself.
