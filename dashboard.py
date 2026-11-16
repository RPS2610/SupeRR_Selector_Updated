from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="SupeRR Selector | IPL 2027", page_icon="🏏", layout="wide")

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"
NOTEBOOKS = ROOT / "notebooks"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');
.stApp {background: #0b1018; color: #f4f1ed; font-family: 'DM Sans', sans-serif;}
[data-testid="stHeader"] {background: rgba(11,16,24,0.92);}
.block-container {padding-top: 1.5rem; max-width: 1500px;}
.hero {background: linear-gradient(115deg,#67172e 0%,#321522 55%,#151c29 100%);
       border:1px solid #74304a; padding:30px 34px; border-radius:18px; margin-bottom:18px;}
.hero h1 {font-family:'Manrope',sans-serif; color:#fff; font-size:2.25rem; margin:0;}
.hero p {color:#f0d8df; margin:8px 0 0 0; font-size:1.02rem;}
.kicker {color:#e4b85f; font-weight:700; letter-spacing:.12em; font-size:.72rem; text-transform:uppercase;}
.note {background:#211d1b; border:1px solid #75572b; border-left:4px solid #d7a94e;
       border-radius:9px; padding:13px 16px; color:#f2e7d4; margin:12px 0 20px;}
.section-title {font-family:'Manrope',sans-serif; color:#f8e8d0; font-size:1.35rem; font-weight:800;}
div[data-testid="stMetric"] {background:#141c28; border:1px solid #293648; padding:14px 16px; border-radius:13px;}
div[data-testid="stMetricLabel"] {color:#b8c3d1;}
div[data-testid="stMetricValue"] {color:#f5d18a;}
.stTabs [data-baseweb="tab"] {color:#d9dce2;}
.stTabs [aria-selected="true"] {color:#f2c66d;}
[data-testid="stDataFrame"] {border:1px solid #283546; border-radius:10px;}
footer {visibility:hidden;}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_csv(path):
    return pd.read_csv(path) if path.exists() else pd.DataFrame()

batting = load_csv(NOTEBOOKS / "improved_batting_rankings.csv")
bowling = load_csv(NOTEBOOKS / "improved_bowling_rankings.csv")
shortlist = load_csv(NOTEBOOKS / "final_top10_shortlist.csv")
pressure = load_csv(RESULTS / "pressure_summary.csv")
stages = load_csv(RESULTS / "stage_summary.csv")
validation = load_csv(RESULTS / "data_validation_summary.csv")
model_validation = load_csv(RESULTS / "model_validation_summary.csv")
season = load_csv(RESULTS / "season_analysis.csv")

st.markdown("""
<div class="hero">
  <div class="kicker">Rajasthan Royals · IPL 2027 auction intelligence</div>
  <h1>🏏 SupeRR Selector</h1>
  <p>Finding players who deliver when the match gets difficult — through pressure-aware T20 performance analysis.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="note"><b>Data and interpretation note:</b> This edition recalculates the analysis using the updated ball-by-ball file supplied on 16 November 2026. The reliability scores are relative model scores within this dataset, not probabilities, official player ratings, or auction valuations. The supplied files do not contain verified dates of birth or international-capping status, so this dashboard does not certify player eligibility.</div>
""", unsafe_allow_html=True)

total_deliveries = int(validation.loc[validation["Metric"].eq("Total delivery records"), "Value"].iloc[0]) if not validation.empty else 0
matches_count = int(validation.loc[validation["Metric"].eq("Unique matches"), "Value"].iloc[0]) if not validation.empty else 0
bat_count = len(batting)
bowl_count = len(bowling)
pressure_count = int(validation.loc[validation["Metric"].eq("Pressure deliveries (High + Very High)"), "Value"].iloc[0]) if not validation.empty else 0

c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("Deliveries analysed", f"{total_deliveries:,}")
c2.metric("Matches", f"{matches_count:,}")
c3.metric("Batters ranked", f"{bat_count:,}")
c4.metric("Bowlers ranked", f"{bowl_count:,}")
c5.metric("High-pressure balls", f"{pressure_count:,}")

tab1,tab2,tab3,tab4,tab5 = st.tabs([
    "🏏 Batting", "🎯 Bowling", "⚡ Pressure map", "📊 Data audit", "🧠 Methodology"
])

with tab1:
    st.markdown('<div class="section-title">Batting reliability under pressure</div>', unsafe_allow_html=True)
    if batting.empty:
        st.error("Batting rankings are missing. Run analysis_pipeline.py first.")
    else:
        col_a,col_b = st.columns([1,2])
        with col_a:
            top_n = st.slider("Players to display", 5, min(30,len(batting)), 10, key="bat_n")
            metric = st.selectbox("Compare using", ["reliability_score","strike_rate","batting_average","boundary_percentage","dot_percentage"], key="bat_metric")
        view = batting.sort_values(metric, ascending=(metric=="dot_percentage")).head(top_n)
        label_map = {"reliability_score":"Reliability score","strike_rate":"Strike rate","batting_average":"Batting average","boundary_percentage":"Boundary %","dot_percentage":"Dot-ball %"}
        fig = px.bar(view.sort_values(metric), x=metric, y="striker_name", orientation="h",
                     color=metric, color_continuous_scale=["#6e9bb5","#d8ad59"],
                     labels={metric:label_map.get(metric,metric),"striker_name":"Player"})
        fig.update_layout(height=max(420,top_n*35),paper_bgcolor="#0b1018",plot_bgcolor="#0b1018",
                          font_color="#e9edf2",coloraxis_showscale=False,margin=dict(l=8,r=12,t=20,b=10))
        st.plotly_chart(fig,use_container_width=True)
        cols=[c for c in ["rank","striker_name","runs","balls","dismissals","matches","batting_average","strike_rate","boundary_percentage","dot_percentage","reliability_score"] if c in view.columns]
        st.dataframe(view[cols].round(2),use_container_width=True,hide_index=True)
        st.download_button("Download complete batting rankings",batting.to_csv(index=False).encode("utf-8"),"supeRR_updated_batting_rankings.csv","text/csv")

with tab2:
    st.markdown('<div class="section-title">Bowling reliability under pressure</div>', unsafe_allow_html=True)
    if bowling.empty:
        st.error("Bowling rankings are missing. Run analysis_pipeline.py first.")
    else:
        top_n_b = st.slider("Bowlers to display",5,min(30,len(bowling)),10,key="bowl_n")
        bowl_metric=st.selectbox("Compare using",["reliability_score","economy","wicket_rate","dot_percentage","boundary_percentage"],key="bowl_metric")
        ascending=bowl_metric in ["economy","boundary_percentage"]
        view=bowling.sort_values(bowl_metric,ascending=ascending).head(top_n_b)
        label_map={"reliability_score":"Reliability score","economy":"Economy rate","wicket_rate":"Wickets per 100 legal balls","dot_percentage":"Dot-ball %","boundary_percentage":"Boundary conceded %"}
        fig=px.bar(view.sort_values(bowl_metric,ascending=ascending),x=bowl_metric,y="bowler_name",orientation="h",
                   color=bowl_metric,color_continuous_scale=["#6e9bb5","#d8ad59"],
                   labels={bowl_metric:label_map.get(bowl_metric,bowl_metric),"bowler_name":"Player"})
        fig.update_layout(height=max(420,top_n_b*35),paper_bgcolor="#0b1018",plot_bgcolor="#0b1018",
                          font_color="#e9edf2",coloraxis_showscale=False,margin=dict(l=8,r=12,t=20,b=10))
        st.plotly_chart(fig,use_container_width=True)
        cols=[c for c in ["rank","bowler_name","wickets","legal_balls","overs","matches","economy","wicket_rate","dot_percentage","boundary_percentage","reliability_score"] if c in view.columns]
        st.dataframe(view[cols].round(2),use_container_width=True,hide_index=True)
        st.download_button("Download complete bowling rankings",bowling.to_csv(index=False).encode("utf-8"),"supeRR_updated_bowling_rankings.csv","text/csv")

with tab3:
    st.markdown('<div class="section-title">Where pressure builds in a T20 innings</div>', unsafe_allow_html=True)
    left,right=st.columns(2)
    with left:
        if not pressure.empty:
            fig=px.bar(pressure,x="pressure_level",y="total_deliveries",color="pressure_level",
                       category_orders={"pressure_level":["Low","Medium","High","Very High"]},
                       color_discrete_map={"Low":"#547d91","Medium":"#9b9c8b","High":"#d4a64f","Very High":"#a9475f"},
                       labels={"pressure_level":"Pressure level","total_deliveries":"Deliveries"})
            fig.update_layout(paper_bgcolor="#0b1018",plot_bgcolor="#0b1018",font_color="#e9edf2",showlegend=False)
            st.plotly_chart(fig,use_container_width=True)
            st.dataframe(pressure,use_container_width=True,hide_index=True)
    with right:
        if not stages.empty:
            fig=px.bar(stages,x="innings_stage",y="total_wickets",color="innings_stage",
                       color_discrete_sequence=["#d4a64f","#a9475f","#547d91"],
                       labels={"innings_stage":"Innings stage","total_wickets":"Wickets"})
            fig.update_layout(paper_bgcolor="#0b1018",plot_bgcolor="#0b1018",font_color="#e9edf2",showlegend=False)
            st.plotly_chart(fig,use_container_width=True)
            st.dataframe(stages,use_container_width=True,hide_index=True)
    st.caption("Pressure levels combine innings phase, wickets already lost and (in second innings) required run rate where a target can be derived.")

with tab4:
    st.markdown('<div class="section-title">Data quality and model coverage</div>', unsafe_allow_html=True)
    if not validation.empty:
        st.dataframe(validation,use_container_width=True,hide_index=True)
    if not model_validation.empty:
        st.markdown("**Player sample coverage**")
        st.dataframe(model_validation,use_container_width=True,hide_index=True)
    if not season.empty:
        st.markdown("**Matches by season and format**")
        fig=px.bar(season,x="season",y="total_matches",color="match_format",barmode="group")
        fig.update_layout(paper_bgcolor="#0b1018",plot_bgcolor="#0b1018",font_color="#e9edf2")
        st.plotly_chart(fig,use_container_width=True)

with tab5:
    st.markdown('<div class="section-title">How the model works</div>', unsafe_allow_html=True)
    st.markdown("""
**1 · Pressure identification**

- Innings phase: Powerplay (overs 1–6), middle overs (7–15), death overs (16–20).
- Wicket context: pressure increases as wickets are lost.
- Chase context: for second innings, required run rate is calculated from the target, runs already scored and balls remaining, where match data permits.
- High and Very High pressure deliveries feed the player rankings.

**2 · Batting reliability score**

- Batting average percentile: **35%**
- Strike-rate percentile: **25%**
- Boundary percentage percentile: **15%**
- Lower dot-ball percentage percentile: **25%**
- Minimum sample: **50 balls faced across at least 3 matches**.

**3 · Bowling reliability score**

- Wicket rate percentile: **35%**
- Dot-ball percentage percentile: **25%**
- Lower economy-rate percentile: **25%**
- Lower boundary-conceded percentage percentile: **15%**
- Minimum sample: **50 legal balls across at least 3 matches**.
- Run-outs and other non-bowler dismissals are excluded from bowler wickets.

**4 · Sample confidence adjustment**

The weighted percentile score receives a bounded adjustment based on sample volume (maximum adjustment 15%). This reduces, but does not eliminate, the effect of small samples.

**Important interpretation limits**

- Scores compare players within the current dataset; they are not success probabilities.
- Player age, uncapped status, auction availability, salary expectations and squad-role fit require separate verification.
- Pressure labels are a transparent analytical proxy, not an official competition definition.
- Bowling runs conceded include wides and no-ball penalties; byes and leg-byes are excluded from bowler-conceded runs.
""")
    if not shortlist.empty:
        st.markdown("**Current top-10 batting and bowling shortlist**")
        st.dataframe(shortlist.round(2),use_container_width=True,hide_index=True)
        st.download_button("Download combined shortlist",shortlist.to_csv(index=False).encode("utf-8"),"supeRR_updated_shortlist.csv","text/csv")

st.caption("SupeRR Selector · Updated-data analytical edition · Rajasthan Royals IPL 2027")
