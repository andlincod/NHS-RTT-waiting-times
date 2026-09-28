# NHS Elective Waiting List — Executive Summary

## Problem
NHS incomplete RTT pathways remain far below the 92% (18-week) standard.

## Key findings
- National backlog (Dec 2025): ~7.23M; % within 18 weeks: ~61.4% (gap ≈ 30.6 pts)
- Largest specialty backlogs: T&O, Ophthalmology, ENT, Gynaecology
- Weakest Trusts (latest month): East Cheshire, Mid & South Essex, RJAH Orthopaedics, ...
- Highest-severity Trust×specialty pockets (latest month): Leicester Oral Surgery; Wolverhampton Gen Surg/ENT; Mid & South Essex ENT/T&O

## Forecast
- Method: 12-month drift (`last backlog + h ×` average monthly change). Beat naive and a lag-based random forest on a 12-origin walk-forward holdout (6-month MAE ≈ 69k vs ≈ 145k naive).
- +1 month (Jan 2026): ~7.21M
- +3 months (Mar 2026): ~7.17M
- +6 months (Jun 2026): ~7.10M
- Sketch only — not a capacity or pathway model. Implies a mild decline if recent monthly change continues.

## Risk ranking (triage, not prediction)
- Score = gap to 92% + backlog size + recent % deterioration.
- Use as a **current-severity** list for where performance is already weak and volume is large.
- Walk-forward check: top-25 packs did **not** predict next-month % within-18 deterioration better than chance (they often improved — mean reversion). There was a weak signal that 52-week waits keep rising in those packs vs random.
- A simpler “gap to 92% only” ranking performed at least as well. Do not treat the table as early warning of who will get worse next month.

## Recommendations
1. Prioritise capacity in ENT, Oral Surgery, and T&O at high-severity Trusts above (current gap/volume, not predicted worsening)
2. Target Mid & South Essex and Leicester for mutual aid / productivity support (high volume + weak performance)
3. Keep monitoring 52-week waits while recovering the 18-week standard
4. Re-run severity ranking monthly as new RTT extracts land; keep the holdout check when the score changes

## Data
NHS England consultant-led RTT incomplete pathways, Jan 2021–Dec 2025 (Kaggle compiled extract).