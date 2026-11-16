from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"
NOTEBOOKS = ROOT / "notebooks"
RESULTS.mkdir(exist_ok=True)
NOTEBOOKS.mkdir(exist_ok=True)

def numeric(df, cols):
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df

def pct_rank(s, higher=True):
    return (s.rank(pct=True, method="average") if higher else
            (1 - s.rank(pct=True, method="average"))) * 100

def main():
    ball = pd.read_csv(DATA / "ball_by_ball.csv", low_memory=False)
    matches = pd.read_csv(DATA / "matches.csv", low_memory=False)

    required = [
        "match_id", "innings", "overid", "striker_id", "striker_name",
        "bowler_id", "bowler_name", "runs", "is_four", "is_six",
        "is_wicket", "dismissed_player_id", "dismissal_type", "extras_type",
        "extras1_runs", "extras_2_runs"
    ]
    missing = [c for c in required if c not in ball.columns]
    if missing:
        raise ValueError(f"Updated ball-by-ball file is missing columns: {missing}")

    ball = numeric(ball, [
        "match_id", "innings", "overid", "striker_id", "bowler_id", "runs",
        "is_four", "is_six", "is_wicket", "dismissed_player_id",
        "extras1_runs", "extras_2_runs"
    ])
    ball["extras_type"] = ball["extras_type"].fillna("").astype(str).str.strip()
    ball["dismissal_type"] = ball["dismissal_type"].fillna("").astype(str).str.strip()

    # In this data dictionary, runs are batter runs and extras are separate columns.
    # Total innings runs are therefore batter runs plus both extras fields.
    ball["total_extras"] = ball["extras1_runs"] + ball["extras_2_runs"]
    ball["total_runs"] = ball["runs"] + ball["total_extras"]
    ball["is_wide"] = ball["extras_type"].str.lower().eq("wide")
    ball["is_noball"] = ball["extras_type"].str.lower().isin(["overstep", "no ball", "noball"])
    ball["legal_ball"] = (~ball["is_wide"] & ~ball["is_noball"]).astype(int)
    # A batter faces a no-ball, but not a wide.
    ball["batter_ball"] = (~ball["is_wide"]).astype(int)

    # Bowler-credited dismissals only.
    credited = {"caught", "bowled", "lbw", "stump", "hit wicket"}
    ball["bowler_wicket"] = (
        ball["is_wicket"].eq(1) &
        ball["dismissal_type"].str.lower().isin(credited)
    ).astype(int)
    ball["batter_dismissal"] = (
        ball["is_wicket"].eq(1) &
        ball["dismissed_player_id"].eq(ball["striker_id"])
    ).astype(int)

    # Bowler runs conceded: batter runs + wides + no-ball penalty.
    ball["bowler_runs"] = ball["runs"] + ball["is_wide"].astype(int) + ball["is_noball"].astype(int)
    ball["bowler_dot"] = (ball["bowler_runs"].eq(0) & ball["legal_ball"].eq(1)).astype(int)
    ball["batter_dot"] = (ball["runs"].eq(0) & ~ball["is_wide"]).astype(int)

    # Build chase context for innings 2 using the innings-1 score, or the
    # official revised target when supplied. Super overs are excluded.
    innings_totals = (
        ball[ball["innings"].eq(1)]
        .groupby("match_id")["total_runs"].sum()
        .rename("first_innings_total")
    )
    match_cols = ["match_id", "second_inn_revised_overs", "revised_target"]
    available_match_cols = [c for c in match_cols if c in matches.columns]
    match_meta = matches[available_match_cols].drop_duplicates("match_id").set_index("match_id")
    chase_meta = match_meta.join(innings_totals, how="left")
    chase_meta["target"] = chase_meta.get("revised_target", pd.Series(index=chase_meta.index, dtype=float))
    chase_meta["target"] = chase_meta["target"].where(chase_meta["target"].notna(),
                                                        chase_meta["first_innings_total"] + 1)
    # Despite the source column name, observed revised-innings limits are
    # stored as ball counts (e.g. 114 = 19 overs); preserve that unit.
    if "second_inn_revised_overs" in chase_meta:
        chase_meta["innings_balls"] = chase_meta["second_inn_revised_overs"].fillna(120)
    else:
        chase_meta["innings_balls"] = 120
    chase_meta["innings_balls"] = chase_meta["innings_balls"].clip(lower=6, upper=120)

    ball = ball.sort_values(["match_id", "innings", "overid", "over_ball_num"] if "over_ball_num" in ball.columns
                            else ["match_id", "innings", "overid"]).reset_index(drop=True)
    group = ball.groupby(["match_id", "innings"], sort=False)
    ball["wickets_before"] = group["is_wicket"].cumsum() - ball["is_wicket"]
    ball["wickets_remaining"] = (10 - ball["wickets_before"]).clip(lower=0)
    ball["runs_before"] = group["total_runs"].cumsum() - ball["total_runs"]
    ball["legal_balls_before"] = group["legal_ball"].cumsum() - ball["legal_ball"]

    ball["innings_stage"] = np.select(
        [ball["overid"] <= 6, ball["overid"] <= 15],
        ["Powerplay", "Middle Overs"], default="Death Overs"
    )
    stage_score = ball["innings_stage"].map({"Powerplay": 0, "Middle Overs": 1, "Death Overs": 2}).astype(int)
    wicket_score = np.select(
        [ball["wickets_before"] >= 6, ball["wickets_before"] >= 4, ball["wickets_before"] >= 2],
        [3, 2, 1], default=0
    )
    ball["runs_required"] = np.nan
    ball["balls_remaining"] = np.nan
    ball["required_run_rate"] = np.nan
    chase_rows = ball["innings"].eq(2)
    if not chase_meta.empty:
        ball.loc[chase_rows, "target"] = ball.loc[chase_rows, "match_id"].map(chase_meta["target"])
        ball.loc[chase_rows, "innings_balls"] = ball.loc[chase_rows, "match_id"].map(chase_meta["innings_balls"])
        ball.loc[chase_rows, "runs_required"] = (
            ball.loc[chase_rows, "target"] - ball.loc[chase_rows, "runs_before"]
        ).clip(lower=0)
        ball.loc[chase_rows, "balls_remaining"] = (
            ball.loc[chase_rows, "innings_balls"] - ball.loc[chase_rows, "legal_balls_before"]
        ).clip(lower=0)
        ball.loc[chase_rows, "required_run_rate"] = np.where(
            ball.loc[chase_rows, "balls_remaining"] > 0,
            ball.loc[chase_rows, "runs_required"] * 6 / ball.loc[chase_rows, "balls_remaining"],
            np.nan
        )

    rrr = ball["required_run_rate"]
    chase_score = np.select(
        [rrr >= 14, rrr >= 10, rrr >= 7],
        [3, 2, 1], default=0
    )
    chase_score = np.where(chase_rows & rrr.notna(), chase_score, 0)
    ball["pressure_score"] = stage_score + wicket_score + chase_score
    ball["pressure_level"] = np.select(
        [ball["pressure_score"] >= 5, ball["pressure_score"] >= 3, ball["pressure_score"] >= 1],
        ["Very High", "High", "Medium"], default="Low"
    )

    pressure = ball[ball["pressure_level"].isin(["High", "Very High"]) & ball["innings"].isin([1, 2])].copy()

    # Batting: calculate on batter balls faced; exclude wides; dismissals are
    # attributed only when the striker is the dismissed player.
    bat = pressure.groupby(["striker_id", "striker_name"], dropna=False).agg(
        runs=("runs", "sum"),
        balls=("batter_ball", "sum"),
        dismissals=("batter_dismissal", "sum"),
        fours=("is_four", "sum"),
        sixes=("is_six", "sum"),
        dot_balls=("batter_dot", "sum"),
        matches=("match_id", "nunique"),
        pressure_deliveries=("match_id", "size")
    ).reset_index()
    bat["batting_average"] = bat["runs"] / bat["dismissals"].replace(0, np.nan)
    bat["strike_rate"] = bat["runs"] / bat["balls"].replace(0, np.nan) * 100
    bat["boundary_percentage"] = (bat["fours"] + bat["sixes"]) / bat["balls"].replace(0, np.nan) * 100
    bat["dot_percentage"] = bat["dot_balls"] / bat["balls"].replace(0, np.nan) * 100
    bat = bat[(bat["balls"] >= 50) & (bat["matches"] >= 3)].copy()

    if not bat.empty:
        bat["average_score"] = pct_rank(bat["batting_average"].fillna(bat["batting_average"].median()))
        bat["strike_rate_score"] = pct_rank(bat["strike_rate"])
        bat["boundary_score"] = pct_rank(bat["boundary_percentage"])
        bat["dot_score"] = pct_rank(bat["dot_percentage"], higher=False)
        raw = (bat["average_score"] * .35 + bat["strike_rate_score"] * .25 +
               bat["boundary_score"] * .15 + bat["dot_score"] * .25)
        # Modest sample-size confidence adjustment, transparent and bounded.
        bat["sample_confidence"] = np.sqrt(np.minimum(bat["balls"] / 200, 1))
        bat["reliability_score"] = raw * (0.85 + 0.15 * bat["sample_confidence"])
        bat = bat.sort_values(["reliability_score", "balls"], ascending=[False, False]).reset_index(drop=True)
        bat.insert(0, "rank", np.arange(1, len(bat) + 1))

    # Bowling: only legal balls count in overs; bowler wickets exclude run-outs etc.
    bowl = pressure.groupby(["bowler_id", "bowler_name"], dropna=False).agg(
        wickets=("bowler_wicket", "sum"),
        legal_balls=("legal_ball", "sum"),
        dot_balls=("bowler_dot", "sum"),
        bowler_runs=("bowler_runs", "sum"),
        boundaries=("is_four", "sum"),
        sixes=("is_six", "sum"),
        matches=("match_id", "nunique"),
        pressure_deliveries=("match_id", "size")
    ).reset_index()
    bowl = bowl[(bowl["legal_balls"] >= 50) & (bowl["matches"] >= 3)].copy()
    bowl["overs"] = bowl["legal_balls"] / 6
    bowl["economy"] = bowl["bowler_runs"] / bowl["overs"].replace(0, np.nan)
    bowl["wicket_rate"] = bowl["wickets"] / bowl["legal_balls"].replace(0, np.nan) * 100
    bowl["dot_percentage"] = bowl["dot_balls"] / bowl["legal_balls"].replace(0, np.nan) * 100
    bowl["boundary_percentage"] = (bowl["boundaries"] + bowl["sixes"]) / bowl["legal_balls"].replace(0, np.nan) * 100
    if not bowl.empty:
        bowl["wicket_score"] = pct_rank(bowl["wicket_rate"])
        bowl["dot_score"] = pct_rank(bowl["dot_percentage"])
        bowl["economy_score"] = pct_rank(bowl["economy"], higher=False)
        bowl["boundary_score"] = pct_rank(bowl["boundary_percentage"], higher=False)
        raw = (bowl["wicket_score"] * .35 + bowl["dot_score"] * .25 +
               bowl["economy_score"] * .25 + bowl["boundary_score"] * .15)
        bowl["sample_confidence"] = np.sqrt(np.minimum(bowl["legal_balls"] / 200, 1))
        bowl["reliability_score"] = raw * (0.85 + 0.15 * bowl["sample_confidence"])
        bowl = bowl.sort_values(["reliability_score", "legal_balls"], ascending=[False, False]).reset_index(drop=True)
        bowl.insert(0, "rank", np.arange(1, len(bowl) + 1))

    bat.to_csv(NOTEBOOKS / "improved_batting_rankings.csv", index=False)
    bowl.to_csv(NOTEBOOKS / "improved_bowling_rankings.csv", index=False)

    top_bat = bat.head(10).copy()
    top_bat["category"] = "Batter"
    top_bat = top_bat.rename(columns={"striker_name": "player_name"})
    top_bowl = bowl.head(10).copy()
    top_bowl["category"] = "Bowler"
    top_bowl = top_bowl.rename(columns={"bowler_name": "player_name"})
    cols = ["rank", "player_name", "reliability_score", "category"]
    shortlist = pd.concat([top_bat[cols], top_bowl[cols]], ignore_index=True)
    shortlist.to_csv(NOTEBOOKS / "final_top10_shortlist.csv", index=False)

    # Data-quality and descriptive outputs for the dashboard.
    pressure_summary = ball[ball["innings"].isin([1, 2])].groupby("pressure_level").agg(
        total_deliveries=("match_id", "size"),
        matches=("match_id", "nunique")
    ).reindex(["Low", "Medium", "High", "Very High"]).fillna(0).reset_index()
    pressure_summary.to_csv(RESULTS / "pressure_summary.csv", index=False)

    stage_summary = ball[ball["innings"].isin([1, 2])].groupby("innings_stage").agg(
        total_deliveries=("match_id", "size"),
        total_wickets=("is_wicket", "sum"),
        matches=("match_id", "nunique")
    ).reindex(["Powerplay", "Middle Overs", "Death Overs"]).fillna(0).reset_index()
    stage_summary.to_csv(RESULTS / "stage_summary.csv", index=False)

    validation = pd.DataFrame({
        "Metric": [
            "Total delivery records", "Unique matches", "Wide deliveries",
            "No-ball deliveries", "Legal deliveries (innings 1-2)",
            "Total wickets", "Bowler-credited wickets", "Non-bowler-credited dismissals",
            "Batter runs", "Extras recorded", "Pressure deliveries (High + Very High)"
        ],
        "Value": [
            len(ball), ball["match_id"].nunique(), int(ball["is_wide"].sum()),
            int(ball["is_noball"].sum()), int(ball.loc[ball["innings"].isin([1,2]), "legal_ball"].sum()),
            int(ball["is_wicket"].sum()), int(ball["bowler_wicket"].sum()),
            int(ball["is_wicket"].sum() - ball["bowler_wicket"].sum()),
            int(ball["runs"].sum()), int(ball["total_extras"].sum()),
            int(pressure.shape[0])
        ]
    })
    validation.to_csv(RESULTS / "data_validation_summary.csv", index=False)

    model_validation = pd.DataFrame({
        "Category": ["Batters", "Bowlers"],
        "Eligible Players": [len(bat), len(bowl)],
        "Minimum Sample": [int(bat["balls"].min()) if not bat.empty else 0,
                           int(bowl["legal_balls"].min()) if not bowl.empty else 0],
        "Maximum Sample": [int(bat["balls"].max()) if not bat.empty else 0,
                           int(bowl["legal_balls"].max()) if not bowl.empty else 0]
    })
    model_validation.to_csv(RESULTS / "model_validation_summary.csv", index=False)

    if "comp_id" in matches.columns:
        comp = pd.read_csv(DATA / "competitions.csv")
        season = matches.merge(comp[["comp_id", "season", "match_format"]], on="comp_id", how="left")
        season.groupby(["season", "match_format"], dropna=False).agg(
            total_matches=("match_id", "nunique")
        ).reset_index().to_csv(RESULTS / "season_analysis.csv", index=False)

    # Retain pressure-level delivery dataset as a downloadable analytical artifact.
    keep = [
        "match_id", "innings", "overid", "striker_id", "striker_name",
        "bowler_id", "bowler_name", "runs", "total_runs", "extras_type",
        "is_wicket", "dismissal_type", "innings_stage", "wickets_before",
        "wickets_remaining", "runs_required", "balls_remaining",
        "required_run_rate", "pressure_score", "pressure_level"
    ]
    ball[keep].to_csv(RESULTS / "pressure_data.csv", index=False)

    print("Updated-data analysis complete")
    print(f"Deliveries: {len(ball):,}; matches: {ball['match_id'].nunique():,}")
    print(f"Batters ranked: {len(bat):,}; bowlers ranked: {len(bowl):,}")
    print("\nTop 10 batters")
    print(bat[["rank", "striker_name", "runs", "balls", "strike_rate", "reliability_score"]].head(10).round(2).to_string(index=False))
    print("\nTop 10 bowlers")
    print(bowl[["rank", "bowler_name", "wickets", "legal_balls", "economy", "reliability_score"]].head(10).round(2).to_string(index=False))

if __name__ == "__main__":
    main()
