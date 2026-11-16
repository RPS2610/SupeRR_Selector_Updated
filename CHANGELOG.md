# Change log — updated data edition

## Updated 16 November 2026
- Replaced the original delivery CSV with the newly supplied updated file.
- Rebuilt all model outputs using the updated delivery data.
- Corrected `extras1_runs` handling: the updated file records zero extras on deliveries with no extras; the old file had a spurious value of 6 on 189,167 such rows.
- Rebuilt pressure context using innings stage, wickets lost and second-innings required run rate where target information is available.
- Interpreted the revised second-innings limit values as ball counts (the supplied values are multiples of six, e.g. 114), rather than multiplying them as if they were overs.
- Excluded super-over innings (innings 3 and 4) from the primary T20 player rankings.
- Batting: batter balls faced exclude wides; dismissals are attributed to the dismissed striker; sample minimum is 50 balls across 3 matches.
- Bowling: legal balls exclude wides and no-balls; bowler wickets are limited to caught, bowled, LBW, stumped and hit wicket; economy uses bowler-conceded runs (batter runs plus wide/no-ball penalties); sample minimum is 50 legal balls across 3 matches.
- Added economy to the bowling score and applied a bounded sample-volume confidence adjustment.
- Rebuilt the Streamlit dashboard so metrics are read from generated data rather than hardcoded.
- Preserved previous notebook scripts in `archive/legacy_notebooks/`; notebook entrypoints now call the canonical `analysis_pipeline.py`.

## Current preliminary rankings
Batting top 10:
1. Phil Salt
2. Virat Kohli
3. Suryakumar Yadav
4. Babar Azam
5. Reeza Hendricks
6. Shreyas Iyer
7. Tom Banton
8. Naman Dhir
9. Kamil Mishara
10. Jos Buttler

Bowling top 10:
1. Sufiyan Muqeem
2. Imad Wasim
3. Matthew Humphreys
4. Mohammad Nawaz
5. Usman Tariq
6. Kartik Meiyappan
7. Rakibul Hasan
8. Dushan Hemantha
9. George Linde
10. Mujeeb Ur Rahman

These are model outputs from the supplied data and current scoring design, not verified final auction recommendations. Confirm player eligibility, availability and squad fit separately.
