"""
ArcelorMittal Steel Intelligence Dashboard
==========================================
Streamlit multi-page dashboard covering:
  Track 1 — Global Steel Market
  Track 2 — Green Steel & Competitor ESG
  Track 3 — Supply Chain Risk & Logistics

Run:
    pip install streamlit plotly pandas
    streamlit run streamlit_dashboard.py
"""

import os
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# Page config — must be first Streamlit call
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ArcelorMittal Steel Intelligence",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Theme & global CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600&family=Barlow+Condensed:wght@600;700&display=swap');

/* ── FORCE DARK BACKGROUND ON ENTIRE APP ── */
.stApp {
    background-color: #0d1117 !important;
}
.block-container {
    background-color: #0d1117 !important;
}
[data-testid="stAppViewContainer"] {
    background-color: #0d1117 !important;
}
[data-testid="stHeader"] {
    background-color: #0d1117 !important;
}

/* ── FORCE ALL TEXT TO BE VISIBLE ON DARK BG ── */
.stApp, .stApp * {
    color: #e6edf3;
}

/* ── HEADINGS — use dark-mode colors explicitly ── */
h1, h2, h3, h4, h5, h6 {
    color: #ffffff !important;
    font-family: 'Barlow Condensed', sans-serif !important;
    font-weight: 700 !important;
}
h3 {
    font-size: 1.25rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    border-left: 4px solid #388bfd !important;
    padding-left: 14px !important;
    margin: 20px 0 14px !important;
    border-bottom: none !important;
    padding-bottom: 4px !important;
}
h3 a { display: none !important; }

/* ── ALL PARAGRAPH TEXT ── */
p, li, span, label, div {
    color: #e6edf3 !important;
}

html, body, [class*="css"] {
    font-family: 'Barlow', sans-serif;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0d1117;
    border-right: 1px solid #1e2630;
}
[data-testid="stSidebar"] * { color: #c9d1d9 !important; }
[data-testid="stSidebar"] .stRadio label { font-size: 14px !important; }

/* Header banner */
.dash-header {
    background: linear-gradient(135deg, #0d1117 0%, #1a2332 60%, #0d2137 100%);
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    padding: 24px 32px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.dash-header::before {
    content: '';
    position: absolute;
    top: 0; right: 0;
    width: 300px; height: 100%;
    background: repeating-linear-gradient(
        45deg,
        transparent,
        transparent 10px,
        rgba(30,90,160,0.06) 10px,
        rgba(30,90,160,0.06) 20px
    );
}
.dash-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 2.6rem;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin: 0;
    line-height: 1.1;
}
.dash-subtitle {
    font-size: 1.05rem;
    color: #a8c4dc;
    margin-top: 8px;
    font-weight: 500;
    letter-spacing: 0.07em;
    text-transform: uppercase;
}
.dash-badge {
    display: inline-block;
    background: #1e3a5f;
    color: #58a6ff;
    font-size: 11px;
    padding: 3px 10px;
    border-radius: 3px;
    margin-top: 10px;
    margin-right: 6px;
    font-weight: 500;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

/* KPI metric cards */
.kpi-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 18px 20px;
    margin-bottom: 4px;
}
.kpi-label {
    font-size: 13px;
    color: #a8c4dc;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    font-weight: 600;
    margin-bottom: 8px;
}
.kpi-value {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 2.2rem;
    font-weight: 700;
    color: #ffffff;
    line-height: 1;
}
.kpi-delta {
    font-size: 14px;
    margin-top: 6px;
    font-weight: 600;
}
.delta-up      { color: #3fb950; }
.delta-down    { color: #f85149; }
.delta-warn    { color: #e3b341; }
.delta-neutral { color: #8b949e; }

/* Section headers */
.section-header {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.4rem;
    font-weight: 700;
    color: #ffffff !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    border-left: 4px solid #388bfd;
    padding-left: 14px;
    margin: 24px 0 16px;
    text-shadow: 0 0 1px rgba(255,255,255,0.3);
}

/* Risk badges */
.risk-high   { background:#3d1a1a; color:#ff7b72; padding:4px 12px; border-radius:4px; font-size:13px; font-weight:700; }
.risk-medium { background:#2d2208; color:#e3b341; padding:4px 12px; border-radius:4px; font-size:13px; font-weight:700; }
.risk-low    { background:#0f2b12; color:#3fb950; padding:4px 12px; border-radius:4px; font-size:13px; font-weight:700; }

/* Info box */
.info-box {
    background: #0d1f2d;
    border: 1px solid #1e3a5f;
    border-left: 4px solid #388bfd;
    border-radius: 6px;
    padding: 16px 20px;
    font-size: 14px;
    color: #c9d1d9;
    line-height: 1.7;
    margin: 12px 0;
}
.info-box b { color: #e6edf3; font-size: 15px; }

/* Divider */
hr.dash-divider {
    border: none;
    border-top: 1px solid #1e2630;
    margin: 20px 0;
}


/* Streamlit widget text */
[data-testid="stMarkdownContainer"] p { font-size: 15px !important; color: #ffffff !important; }
/* Force section header p tags to always be white */
[data-testid="stMarkdownContainer"] p[style*="text-transform:uppercase"] { 
    color: #FFFFFF !important; 
    opacity: 1 !important;
}
label[data-baseweb="label"] { font-size: 14px !important; color: #c9d1d9 !important; font-weight: 600 !important; }
.stMultiSelect span { font-size: 14px !important; color: #e6edf3 !important; }
[data-testid="stSlider"] p { font-size: 14px !important; color: #c9d1d9 !important; }
[data-testid="stDataFrame"] { font-size: 13px !important; }
[data-testid="stSidebar"] .stRadio label { font-size: 15px !important; font-weight:500 !important; }

/* Force section header visibility */
[data-testid="stMarkdownContainer"] .section-header {
    color: #ffffff !important;
    opacity: 1 !important;
    visibility: visible !important;
}
/* Override Streamlit's p tag color inside custom divs */
[data-testid="stMarkdownContainer"] .section-header * {
    color: #ffffff !important;
}

/* Prevent Streamlit theme from overriding custom HTML */
.stMarkdown p { color: #ffffff !important; }
.stMarkdown [style] { opacity: 1 !important; }

/* Style native st.subheader h3 as section headers */
h3 {
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 1.3rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    color: #ffffff !important;
    border-left: 4px solid #388bfd !important;
    padding-left: 14px !important;
    margin: 20px 0 14px !important;
    border-bottom: none !important;
    padding-bottom: 0 !important;
}
/* Remove default Streamlit h3 underline/divider */
h3 a { display: none !important; }

/* ── Fix selectbox dropdown visibility ── */
div[data-baseweb="select"] > div {
    background-color: #161b22 !important;
    border-color: #30363d !important;
    color: #e6edf3 !important;
}
div[data-baseweb="select"] span {
    color: #e6edf3 !important;
}
/* Dropdown menu list */
ul[data-baseweb="menu"] {
    background-color: #161b22 !important;
    border: 1px solid #30363d !important;
}
ul[data-baseweb="menu"] li {
    background-color: #161b22 !important;
    color: #e6edf3 !important;
}
ul[data-baseweb="menu"] li:hover {
    background-color: #21262d !important;
    color: #ffffff !important;
}
/* Selected option text */
div[data-baseweb="select"] [data-testid="stSelectbox"] {
    color: #e6edf3 !important;
}
/* Selectbox input text */
input[aria-autocomplete="list"] {
    color: #e6edf3 !important;
    background-color: #161b22 !important;
}
/* Option highlighted */
li[aria-selected="true"] {
    background-color: #1e3a5f !important;
    color: #ffffff !important;
}

/* Hide Streamlit default elements */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
.stDeployButton {display: none;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Plotly theme
# ─────────────────────────────────────────────────────────────────────────────
PLOT_THEME = dict(
    paper_bgcolor="#0d1117",
    plot_bgcolor="#0d1117",
    font=dict(family="Barlow, sans-serif", color="#e6edf3", size=13),
    xaxis=dict(gridcolor="#1e2630", linecolor="#1e2630", tickfont=dict(size=12)),
    yaxis=dict(gridcolor="#1e2630", linecolor="#1e2630", tickfont=dict(size=12)),
    margin=dict(l=16, r=16, t=36, b=16),
)

COLORS = {
    "blue":   "#1e5fa0",
    "steel":  "#58a6ff",
    "green":  "#3fb950",
    "amber":  "#e3b341",
    "red":    "#f85149",
    "gray":   "#7d9bb5",
    "teal":   "#1D9E75",
    "purple": "#7F77DD",
}

# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

@st.cache_data(ttl=3600)
def load_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()

def load_all():
    kpi = load_csv("steel_kpi_payload.csv")
    esg = load_csv("green_steel_benchmarks.csv")
    sc  = load_csv("supply_chain_metrics.csv")
    if not kpi.empty and "record_date" in kpi.columns:
        kpi["record_date"] = pd.to_datetime(kpi["record_date"], errors="coerce")
    return kpi, esg, sc

kpi_df, esg_df, sc_df = load_all()

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def kpi_card(label, value, delta="", delta_class="delta-neutral"):
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-delta {delta_class}">{delta}</div>
    </div>""", unsafe_allow_html=True)

def section(title):
    st.markdown(f"### {title}")

def risk_badge(level):
    cls = {"High":"risk-high","Medium":"risk-medium","Low":"risk-low"}.get(level,"risk-low")
    return f'<span class="{cls}">{level}</span>'

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar navigation
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding:16px 0 8px;'>
        <div style='font-family:Barlow Condensed,sans-serif;font-size:1.1rem;
                    font-weight:700;color:#fff;letter-spacing:.1em;text-transform:uppercase;'>
            🏭 Steel Intel
        </div>
        <div style='font-size:11px;color:#7d9bb5;margin-top:2px;letter-spacing:.06em;'>
            ArcelorMittal · BI Bootcamp
        </div>
    </div>
    <hr style='border:none;border-top:1px solid #1e2630;margin:8px 0 16px;'>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigate",
        ["🏠  Executive Summary",
         "📈  Steel Market",
         "🌿  Green Steel ESG",
         "⚓  Supply Chain Risk"],
        label_visibility="collapsed",
    )

    st.markdown("<hr style='border:none;border-top:1px solid #1e2630;margin:16px 0;'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:11px;color:#7d9bb5;padding:0 4px;'>Data sources</div>", unsafe_allow_html=True)
    for src in ["World Bank Pink Sheet","Eurostat COMEXT","SteelOrbis","WSA Press Releases","Argus Media / Platts"]:
        st.markdown(f"<div style='font-size:11px;color:#485b6e;padding:3px 4px;'>· {src}</div>", unsafe_allow_html=True)

    st.markdown(f"""
    <hr style='border:none;border-top:1px solid #1e2630;margin:16px 0 8px;'>
    <div style='font-size:10px;color:#485b6e;padding:0 4px;'>
        Pipeline last run<br>
        <span style='color:#7d9bb5;'>
        {pd.Timestamp('today').strftime('%d %b %Y')}
        </span>
    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Header — shown on all pages
# ─────────────────────────────────────────────────────────────────────────────
PAGE_TITLES = {
    "🏠  Executive Summary": ("Global Steel Intelligence Command Centre",
                               "Executive overview · All three tracks"),
    "📈  Steel Market":       ("Global Steel Market Monitor",
                               "Track 1 · Prices · Trade flows · Market concentration"),
    "🌿  Green Steel ESG":    ("Green Steel & Competitor ESG Benchmark",
                               "Track 2 · Decarbonisation · Green premiums · Net-zero timelines"),
    "⚓  Supply Chain Risk":  ("Supply Chain Risk & Logistics Intelligence",
                               "Track 3 · Freight indexes · Port congestion · Raw material risk"),
}
title, subtitle = PAGE_TITLES[page]

st.markdown(f"""
<div class="dash-header">
    <div class="dash-title">{title}</div>
    <div class="dash-subtitle">{subtitle}</div>
    <span class="dash-badge">ArcelorMittal</span>
    <span class="dash-badge">BI Bootcamp 2025</span>
    <span class="dash-badge">Live Pipeline</span>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Executive Summary
# ─────────────────────────────────────────────────────────────────────────────
if page == "🏠  Executive Summary":

    section("Key performance indicators — all tracks")
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    with c1: kpi_card("HRC Spot Price","$398.50","USD/t · SteelOrbis","delta-warn")
    with c2: kpi_card("Iron Ore CFR","$102.21","USD/dmt · Dec 2024","delta-neutral")
    with c3: kpi_card("HRC–Ore Spread","$296.29","margin proxy USD/t","delta-up")
    with c4: kpi_card("HHI 2024","2,168","moderate concentration","delta-warn")
    with c5: kpi_card("Industry CO₂","1,920","kg CO₂/t steel avg","delta-down")
    with c6: kpi_card("Supply Risk","4 High","of 25 metrics flagged","delta-down")

    st.markdown("<hr class='dash-divider'>", unsafe_allow_html=True)
    section("Strategic findings")

    fa, fb = st.columns(2)
    with fa:
        st.markdown("""
        <div class='info-box'>
            <b style='color:#c9d1d9;'>📈 Track 1 — Margin pressure visible</b><br>
            HRC at $398/t vs iron ore at $102/t gives a spread of $296/t.
            EU Steel PPI peaked at 175 (2022) and has fallen to 156 (Dec 2023),
            signalling weakening EU demand. HHI at 2,168 confirms moderate
            concentration — China drives ~54% of global crude output.
        </div>
        <div class='info-box'>
            <b style='color:#c9d1d9;'>🌿 Track 2 — Green premium opportunity</b><br>
            Green steel commands a €100–200/t premium today. SSAB's HYBRIT
            pilot achieves 25 kg CO₂/t vs the 1,920 kg industry average —
            a 98.7% reduction. Salzgitter targets net zero by 2033, the most
            aggressive timeline. €9.5bn in green investment committed
            across five competitors.
        </div>
        """, unsafe_allow_html=True)
    with fb:
        st.markdown("""
        <div class='info-box'>
            <b style='color:#c9d1d9;'>⚓ Track 3 — Red Sea the dominant risk</b><br>
            Red Sea rerouting adds 12 days and a 45% freight surcharge vs
            pre-crisis levels. The BDI at 1,420 is below the 1,500 risk
            threshold. Coking coal fell $22.5/t in three months — High risk
            trend for procurement planning. Qingdao port at 3.2-day wait
            remains the key Chinese bottleneck.
        </div>
        <div class='info-box'>
            <b style='color:#c9d1d9;'>🎯 Recommended actions</b><br>
            1. Lock in coking coal forward contracts before further price drop reversal.<br>
            2. Monitor BDI weekly — below 1,000 triggers procurement review.<br>
            3. Engage SSAB / H2GS for green steel off-take agreements ahead of 2026 capacity.<br>
            4. Hedge iron ore exposure given $18.3/dmt 30-day volatility.
        </div>
        """, unsafe_allow_html=True)

    # Mini charts row
    section("Trend overview")
    col1, col2, col3 = st.columns(3)

    with col1:
        if not kpi_df.empty:
            ore = kpi_df[kpi_df["metric_name"].str.contains("Iron Ore", na=False)].copy()
            ore = ore.dropna(subset=["record_date","kpi_value"])
            ore = ore[ore["record_date"].dt.year >= 2000].sort_values("record_date")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ore["record_date"], y=ore["kpi_value"],
                line=dict(color=COLORS["steel"], width=2), fill="tozeroy",
                fillcolor="rgba(30,95,160,0.1)", name="Iron Ore"))
            fig.update_layout(**PLOT_THEME, title=dict(text="Iron ore price (USD/dmt)", font=dict(size=12)), height=200)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    with col2:
        companies = ["SSAB","Salzgitter","Tata Steel","thyssenkrupp","Industry Average"]
        co2_vals  = [1610, 1500, 1900, 1850, 1920]
        colors_co2= [COLORS["amber"],COLORS["green"],COLORS["red"],COLORS["amber"],COLORS["gray"]]
        fig2 = go.Figure(go.Bar(x=co2_vals, y=companies, orientation="h",
            marker_color=colors_co2, marker_line_width=0))
        fig2.update_layout(**PLOT_THEME, title=dict(text="CO₂ intensity (kg/t)", font=dict(size=12)), height=200)
        fig2.update_xaxes(title_text="kg CO₂/t steel")
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})

    with col3:
        risk_counts = {"High":4,"Medium":10,"Low":11}
        fig3 = go.Figure(go.Pie(
            labels=list(risk_counts.keys()), values=list(risk_counts.values()),
            hole=0.6, marker_colors=[COLORS["red"],COLORS["amber"],COLORS["green"]],
            textinfo="label+value", textfont_size=11))
        fig3.update_layout(**PLOT_THEME, title=dict(text="Supply chain risk split", font=dict(size=12)),
                           height=200, showlegend=False)
        st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar":False})

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Steel Market
# ─────────────────────────────────────────────────────────────────────────────
elif page == "📈  Steel Market":

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: kpi_card("HRC Spot","$398.50","USD/t Apr 2026","delta-warn")
    with c2: kpi_card("Iron Ore CFR","$102.21","USD/dmt Dec 2024","delta-neutral")
    with c3: kpi_card("EU Steel PPI","155.6","Index 2015=100","delta-down")
    with c4: kpi_card("EU Cold-Drawn PPI","161.6","Index 2015=100","delta-down")
    with c5: kpi_card("HHI 2024","2,168","moderate concentration","delta-warn")

    st.markdown("<hr class='dash-divider'>", unsafe_allow_html=True)

    # Price trend
    section("Price trends — historical series")
    if not kpi_df.empty:
        metrics = kpi_df["metric_name"].dropna().unique().tolist()
        selected = st.multiselect(
            "Select metrics to display",
            options=metrics,
            default=[m for m in metrics if "Iron Ore" in m or "HRC" in m][:2],
        )
        year_range = st.slider("Year range", 1980, 2026, (2000, 2026))

        filtered = kpi_df[
            kpi_df["metric_name"].isin(selected) &
            (kpi_df["record_date"].dt.year >= year_range[0]) &
            (kpi_df["record_date"].dt.year <= year_range[1])
        ].sort_values("record_date")

        fig = px.line(filtered, x="record_date", y="kpi_value", color="metric_name",
                      color_discrete_sequence=[COLORS["steel"],COLORS["amber"],COLORS["green"],COLORS["teal"]])
        fig.update_layout(**PLOT_THEME, height=320,
                          legend=dict(orientation="h", y=-0.2, font=dict(size=11)))
        fig.update_xaxes(title_text=None)
        fig.update_yaxes(title_text="Value")
        fig.update_traces(line_width=2)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

    st.markdown("<hr class='dash-divider'>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        section("HHI producer concentration")
        hhi_data = pd.DataFrame({
            "Year": ["2021","2022","2023","2024"],
            "HHI":  [2076, 2203, 2245, 2168]
        })
        fig_hhi = go.Figure(go.Bar(
            x=hhi_data["Year"], y=hhi_data["HHI"],
            marker_color=[COLORS["blue"],COLORS["blue"],COLORS["red"],COLORS["amber"]],
            marker_line_width=0, text=hhi_data["HHI"],
            textposition="outside", textfont=dict(size=11)
        ))
        fig_hhi.add_hline(y=2500, line_dash="dot", line_color=COLORS["red"],
                          annotation_text="High concentration threshold", annotation_font_size=10)
        fig_hhi.update_layout(**PLOT_THEME, height=260)
        fig_hhi.update_yaxes(range=[1800, 2600], gridcolor="#1e2630", title_text="HHI index")
        st.plotly_chart(fig_hhi, use_container_width=True, config={"displayModeBar":False})

    with col2:
        section("Top steel producers — 2024 share")
        producers = pd.DataFrame({
            "Country": ["China","India","Japan","USA","Russia","South Korea","Germany","Brazil","Others"],
            "Share":   [54, 8, 5, 4, 4, 4, 2, 2, 17]
        })
        fig_pie = go.Figure(go.Pie(
            labels=producers["Country"], values=producers["Share"],
            hole=0.5,
            marker_colors=[COLORS["red"],COLORS["amber"],COLORS["steel"],COLORS["blue"],
                           COLORS["teal"],COLORS["purple"],COLORS["green"],COLORS["gray"],"#485b6e"],
            textinfo="label+percent", textfont_size=10
        ))
        fig_pie.update_layout(**PLOT_THEME, height=260, showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar":False})

    if not kpi_df.empty:
        st.markdown("<hr class='dash-divider'>", unsafe_allow_html=True)
        section("Raw data — KPI payload")

        all_metrics = sorted(kpi_df["metric_name"].dropna().unique().tolist())
        col_f1, col_f2 = st.columns([3,1])
        with col_f1:
            metric_filter = st.selectbox(
                "Filter by metric",
                options=["— Show all metrics —"] + all_metrics,
                index=0,
                key="kpi_metric_filter"
            )
        with col_f2:
            sort_order = st.selectbox("Sort by date", ["Newest first","Oldest first"], key="kpi_sort")

        show_df = kpi_df.copy()
        ascending = sort_order == "Oldest first"
        if "record_date" in show_df.columns:
            show_df = show_df.sort_values("record_date", ascending=ascending)
            show_df["record_date"] = show_df["record_date"].dt.strftime("%Y-%m-%d")

        if metric_filter != "— Show all metrics —":
            show_df = show_df[show_df["metric_name"] == metric_filter]

        st.caption(f"{len(show_df):,} rows matched")
        cols_to_show = ["record_date","metric_name","kpi_value","unit_of_measure","region_or_country"]
        cols_to_show = [c for c in cols_to_show if c in show_df.columns]
        st.dataframe(show_df[cols_to_show].head(400), use_container_width=True, height=320)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Green Steel ESG
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🌿  Green Steel ESG":

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: kpi_card("Industry avg CO₂","1,920","kg CO₂/t steel","delta-down")
    with c2: kpi_card("HYBRIT pilot CO₂","25","kg CO₂/t — SSAB","delta-up")
    with c3: kpi_card("Green premium","€100–200","EUR/t delta","delta-warn")
    with c4: kpi_card("Earliest net zero","2033","Salzgitter SALCOS","delta-up")
    with c5: kpi_card("Total investment","€9.5bn","across 5 peers","delta-up")

    st.markdown("<hr class='dash-divider'>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        section("CO₂ intensity benchmark (kg CO₂/t steel)")
        companies = ["SSAB","Salzgitter","Tata Steel","thyssenkrupp","Industry Avg"]
        co2_vals  = [1610, 1500, 1900, 1850, 1920]
        bar_colors= [COLORS["amber"],COLORS["green"],COLORS["red"],COLORS["amber"],COLORS["gray"]]
        fig_co2 = go.Figure(go.Bar(
            y=companies, x=co2_vals, orientation="h",
            marker_color=bar_colors, marker_line_width=0,
            text=[f"{v:,}" for v in co2_vals], textposition="outside", textfont=dict(size=11)
        ))
        fig_co2.add_vline(x=1920, line_dash="dot", line_color=COLORS["gray"],
                          annotation_text="Industry avg", annotation_font_size=10)
        fig_co2.update_layout(**PLOT_THEME, height=260)
        fig_co2.update_xaxes(range=[0,2200], gridcolor="#1e2630", title_text="kg CO₂/t steel")
        st.plotly_chart(fig_co2, use_container_width=True, config={"displayModeBar":False})

    with col2:
        section("Green investment vs DRI capacity")
        inv_data = pd.DataFrame({
            "Company":    ["Salzgitter","Tata Steel","H2 Green Steel","thyssenkrupp"],
            "Investment": [1.0, 1.0, 3.5, 2.0],
            "Capacity":   [1.9, 6.0, 5.0, 2.5],
        })
        fig_sc = px.scatter(inv_data, x="Investment", y="Capacity", text="Company",
                            color_discrete_sequence=[COLORS["steel"]])
        fig_sc.update_traces(marker=dict(size=14, line=dict(width=1, color="#0d1117")),
                             textposition="top center", textfont=dict(size=11, color="#c9d1d9"))
        fig_sc.update_layout(**PLOT_THEME, height=260)
        fig_sc.update_xaxes(title_text="Investment (€bn)")
        fig_sc.update_yaxes(title_text="DRI capacity (Mt/yr)")
        st.plotly_chart(fig_sc, use_container_width=True, config={"displayModeBar":False})

    st.markdown("<hr class='dash-divider'>", unsafe_allow_html=True)
    section("Net zero target timeline")

    nz_data = pd.DataFrame({
        "Company": ["Salzgitter","SSAB","Tata Steel","thyssenkrupp","H2 Green Steel"],
        "Year":    [2033, 2045, 2045, 2045, 2030],
        "Programme":["SALCOS","HYBRIT","EAF IJmuiden","tkH2Steel","Boden Plant"]
    }).sort_values("Year")

    fig_nz = go.Figure(go.Bar(
        y=nz_data["Company"], x=nz_data["Year"], orientation="h",
        marker_color=[COLORS["green"],COLORS["steel"],COLORS["teal"],COLORS["purple"],COLORS["amber"]],
        marker_line_width=0, text=nz_data["Year"].astype(str) + " · " + nz_data["Programme"],
        textposition="inside", textfont=dict(size=11, color="#ffffff")
    ))
    fig_nz.update_layout(**PLOT_THEME, height=220)
    fig_nz.update_xaxes(range=[2025, 2055], gridcolor="#1e2630")
    st.plotly_chart(fig_nz, use_container_width=True, config={"displayModeBar":False})

    if not esg_df.empty:
        st.markdown("<hr class='dash-divider'>", unsafe_allow_html=True)
        section("Full ESG benchmark dataset")
        company_filter = st.multiselect("Filter by company", sorted(esg_df["company_peer"].unique()),
                                        default=list(esg_df["company_peer"].unique()))
        unit_filter = st.multiselect("Filter by unit", sorted(esg_df["unit_of_measure"].unique()),
                                     default=list(esg_df["unit_of_measure"].unique()))
        filtered_esg = esg_df[
            esg_df["company_peer"].isin(company_filter) &
            esg_df["unit_of_measure"].isin(unit_filter)
        ]
        st.dataframe(filtered_esg, use_container_width=True, height=300)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: Supply Chain Risk
# ─────────────────────────────────────────────────────────────────────────────
elif page == "⚓  Supply Chain Risk":

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: kpi_card("BDI Index","1,420","Below 1,500 — High risk","delta-down")
    with c2: kpi_card("Red Sea delay","+12 days","vs Suez route","delta-down")
    with c3: kpi_card("Coking Coal HCC","$215/t","−$22.5 in 3 months","delta-down")
    with c4: kpi_card("HMS Scrap Rtm","$355/t","Medium risk","delta-warn")
    with c5: kpi_card("High risk items","4 / 25","16% of all metrics","delta-down")

    st.markdown("<hr class='dash-divider'>", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 2])
    with col1:
        section("Risk distribution")
        risk_counts = {"High":4, "Medium":10, "Low":11}
        fig_donut = go.Figure(go.Pie(
            labels=list(risk_counts.keys()), values=list(risk_counts.values()),
            hole=0.6, marker_colors=[COLORS["red"],COLORS["amber"],COLORS["green"]],
            textinfo="label+value", textfont_size=12,
            marker_line=dict(color="#0d1117", width=2)
        ))
        fig_donut.update_layout(**PLOT_THEME, height=240, showlegend=False)
        st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar":False})

    with col2:
        section("Port waiting times (days)")
        ports = pd.DataFrame({
            "Port":  ["Rotterdam","Port Hedland","Singapore","Qingdao"],
            "Days":  [1.2, 1.8, 2.1, 3.2],
            "Risk":  ["Low","Low","Low","Medium"]
        })
        port_colors = [COLORS["green"],COLORS["green"],COLORS["green"],COLORS["amber"]]
        fig_ports = go.Figure(go.Bar(
            x=ports["Port"], y=ports["Days"],
            marker_color=port_colors, marker_line_width=0,
            text=ports["Days"], textposition="outside", textfont=dict(size=12)
        ))
        fig_ports.add_hline(y=5, line_dash="dot", line_color=COLORS["red"],
                             annotation_text="High risk threshold (5 days)",
                             annotation_font_size=10)
        fig_ports.update_layout(**PLOT_THEME, height=240)
        fig_ports.update_yaxes(range=[0,6], gridcolor="#1e2630", title_text="Avg wait (days)")
        st.plotly_chart(fig_ports, use_container_width=True, config={"displayModeBar":False})

    st.markdown("<hr class='dash-divider'>", unsafe_allow_html=True)
    section("Freight rate comparison (USD/day — dry bulk vessels)")
    vessels = pd.DataFrame({
        "Vessel":    ["Capesize","Panamax","Supramax"],
        "Rate USD":  [12500, 10800, 9200],
    })
    fig_freight = go.Figure(go.Bar(
        x=vessels["Vessel"], y=vessels["Rate USD"],
        marker_color=[COLORS["amber"],COLORS["blue"],COLORS["green"]],
        marker_line_width=0,
        text=["$" + f"{v:,}" for v in vessels["Rate USD"]],
        textposition="outside", textfont=dict(size=12)
    ))
    fig_freight.update_layout(**PLOT_THEME, height=220)
    fig_freight.update_yaxes(range=[0,18000], gridcolor="#1e2630", title_text="USD/day charter rate")
    st.plotly_chart(fig_freight, use_container_width=True, config={"displayModeBar":False})

    if not sc_df.empty:
        st.markdown("<hr class='dash-divider'>", unsafe_allow_html=True)
        section("Full supply chain risk table")
        risk_filter = st.multiselect("Filter by risk level",
                                     ["High","Medium","Low"],
                                     default=["High","Medium","Low"])
        filtered_sc = sc_df[sc_df["risk_level_assessment"].isin(risk_filter)]
        filtered_sc = filtered_sc.sort_values("risk_level_assessment",
                                               key=lambda x: x.map({"High":0,"Medium":1,"Low":2}))

        def highlight_risk(val):
            colors = {"High":"background-color:#3d1a1a;color:#f85149",
                      "Medium":"background-color:#2d2208;color:#e3b341",
                      "Low":"background-color:#0f2b12;color:#3fb950"}
            return colors.get(val, "")

        try:
            styled = filtered_sc.style.map(highlight_risk, subset=["risk_level_assessment"])
        except AttributeError:
            styled = filtered_sc.style.applymap(highlight_risk, subset=["risk_level_assessment"])
        st.dataframe(styled, use_container_width=True, height=320)
