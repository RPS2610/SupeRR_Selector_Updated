# SupeRR Selector — Updated Data Edition

## What changed
- Replaced the old `data/ball_by_ball.csv` with the updated ball-by-ball CSV supplied on 16 November 2026.
- Kept the supporting competition, match, team, playing-eleven and player-mapping files.
- Added `analysis_pipeline.py` as the single source of truth for recalculating pressure labels, player metrics and rankings.
- Rebuilt the Streamlit dashboard with updated methodology, data-quality metrics, downloadable rankings and clear interpretation limits.
- Corrected legal-ball, batter-ball, extras and bowler-wicket accounting in the pipeline.

## Run locally (Windows PowerShell)
```powershell
cd SupeRR_Selector
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements_dashboard.txt
python analysis_pipeline.py
streamlit run dashboard.py
```

## Deploy on Streamlit Community Cloud
- Push this project folder to your GitHub repository.
- Set the app's main file path to `dashboard.py`.
- Set Python dependencies from `requirements_dashboard.txt` (or rename it to `requirements.txt` if the deployment configuration expects that filename).
- The pipeline outputs are committed under `notebooks/` and `results/`; run `analysis_pipeline.py` locally after replacing the ball-by-ball file, then commit the regenerated outputs.

## Model definitions
Pressure is a transparent proxy combining innings stage, wickets lost and second-innings required run rate where target data is available. Rankings use high and very-high pressure deliveries. Batting weights: average 35%, strike rate 25%, boundary rate 15%, dot-ball avoidance 25%. Bowling weights: wicket rate 35%, dot-ball rate 25%, economy 25%, boundary prevention 15%. Minimum sample thresholds are 50 batter balls / 3 matches and 50 legal bowling balls / 3 matches.

A bounded sample-volume adjustment is applied to the weighted percentile score. It is a ranking aid, not a predictive probability.

## Important limitations
The supplied CSV files do not establish player date of birth, international-capping status, auction availability or current squad fit. Verify these independently before presenting final recommendations. Pressure labels are model-defined and not an official competition definition. All scores are relative to the supplied dataset.
