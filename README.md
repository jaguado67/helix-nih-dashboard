# HELIX NIH Schedule Performance Dashboard

Independent Streamlit dashboard for the NIH SRLM Hospital schedule.

## Schedule sources

- **U38** — fixed Baseline, Data Date 01-Oct-2025.
- **U39–U48** — monthly updates used for historical trend.
- **U49** — Current Update.

## Main analytics

- Baseline vs Current completion and finish date shift.
- S-Curve by cumulative activity count.
- Overall activity status.
- Activity Plan vs Actual (U48 vs U49).
- Area progress and Baseline vs Current start/finish comparison.
- Monthly update trend U38–U49.
- Diagnostics for scope changes between U38 and U49.

Deploy on Streamlit Community Cloud with:

- Repository: `jaguado67/helix-nih-dashboard`
- Branch: `main`
- Main file path: `app.py`
