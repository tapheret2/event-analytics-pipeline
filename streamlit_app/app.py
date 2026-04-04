"""
=============================================================================
Event Analytics Dashboard - Streamlit Application
=============================================================================
Interactive KPI dashboard for the Event Analytics Pipeline.
Displays DAU/WAU, revenue, conversion funnel, retention heatmap,
and event distribution charts.

Usage:
    streamlit run streamlit_app/app.py
=============================================================================
"""

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from sqlalchemy import create_engine, text

# =============================================================================
# Configuration
# =============================================================================

st.set_page_config(
    page_title="Event Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for premium look
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #1a1a2e 50%, #16213e 100%);
    }

    /* Metric cards */
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: #00d4ff;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.9rem;
        color: #a0aec0;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    div[data-testid="stMetricDelta"] > div {
        font-size: 0.85rem;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #0f0c29 100%);
    }

    /* Headers */
    h1, h2, h3 {
        color: #e2e8f0 !important;
    }

    /* Cards */
    div[data-testid="stHorizontalBlock"] > div {
        border-radius: 12px;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #a0aec0;
        border-radius: 8px;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(0, 212, 255, 0.15);
        color: #00d4ff;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# Database Connection
# =============================================================================

@st.cache_resource
def get_engine():
    """Create cached SQLAlchemy engine."""
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "pipeline")
    password = os.environ.get("POSTGRES_PASSWORD", "pipeline123")
    database = os.environ.get("POSTGRES_DB", "event_analytics")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    return create_engine(url, pool_pre_ping=True)


@st.cache_data(ttl=300)
def run_query(query: str) -> pd.DataFrame:
    """Execute a SQL query and return results as DataFrame."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            return pd.read_sql(text(query), conn)
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()


# =============================================================================
# Data Loading Functions
# =============================================================================

def load_daily_kpis() -> pd.DataFrame:
    return run_query("SELECT * FROM gold.daily_kpis ORDER BY event_date")


def load_funnel() -> pd.DataFrame:
    return run_query("SELECT * FROM gold.funnel_analysis ORDER BY stage_order")


def load_retention() -> pd.DataFrame:
    return run_query("SELECT * FROM gold.retention ORDER BY cohort_week")


def load_dim_users() -> pd.DataFrame:
    return run_query("SELECT * FROM gold.dim_users")


def load_event_distribution() -> pd.DataFrame:
    return run_query("""
        SELECT event_type, event_date, COUNT(*) as event_count
        FROM gold.fact_events
        GROUP BY event_type, event_date
        ORDER BY event_date, event_type
    """)


# =============================================================================
# Chart Theme
# =============================================================================

CHART_THEME = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"color": "#e2e8f0", "family": "Inter, sans-serif"},
    "xaxis": {
        "gridcolor": "rgba(255,255,255,0.05)",
        "zerolinecolor": "rgba(255,255,255,0.1)",
    },
    "yaxis": {
        "gridcolor": "rgba(255,255,255,0.05)",
        "zerolinecolor": "rgba(255,255,255,0.1)",
    },
}

COLOR_PALETTE = [
    "#00d4ff", "#7c3aed", "#10b981", "#f59e0b",
    "#ef4444", "#ec4899", "#06b6d4", "#8b5cf6",
]


def apply_theme(fig):
    """Apply consistent dark theme to plotly figures."""
    fig.update_layout(**CHART_THEME)
    fig.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color="#a0aec0"),
        ),
    )
    return fig


# =============================================================================
# Sidebar
# =============================================================================

with st.sidebar:
    st.markdown("## 🚀 Event Analytics")
    st.markdown("---")
    st.markdown("### 📡 Pipeline Status")

    # Check data availability
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM gold.daily_kpis")).scalar()
            if result and result > 0:
                st.success(f"✅ Connected — {result} days of data")
            else:
                st.warning("⚠️ Connected but no data yet")
    except Exception:
        st.error("❌ Database unavailable")
        st.info("Run `docker compose up -d` and trigger the Airflow DAG first.")
        st.stop()

    st.markdown("---")
    st.markdown("### 🔗 Quick Links")
    st.markdown("- [Airflow UI](http://localhost:8080)")
    st.markdown("- [Pipeline Repo](https://github.com/tapheret2/event-analytics-pipeline)")

    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; color:#64748b; font-size:0.75rem;'>"
        "Built with ❤️ using Streamlit"
        "</div>",
        unsafe_allow_html=True,
    )

# =============================================================================
# Main Dashboard
# =============================================================================

st.markdown("# 📊 Event Analytics Dashboard")
st.markdown("*Real-time KPIs for your e-commerce cashback platform*")
st.markdown("---")

# Load data
df_kpis = load_daily_kpis()
df_funnel = load_funnel()
df_retention = load_retention()
df_users = load_dim_users()

if df_kpis.empty:
    st.warning("No KPI data available yet. Please run the pipeline first.")
    st.info("1. Go to Airflow → Trigger `event_analytics_pipeline`\n2. Wait for completion\n3. Refresh this page")
    st.stop()

# =============================================================================
# KPI Cards (Top Row)
# =============================================================================

latest = df_kpis.iloc[-1]  # Most recent day
prev = df_kpis.iloc[-2] if len(df_kpis) > 1 else latest

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    delta_dau = int(latest["dau"] - prev["dau"]) if len(df_kpis) > 1 else 0
    st.metric("📈 DAU", f"{int(latest['dau']):,}", delta=f"{delta_dau:+d}")

with col2:
    wau_val = int(latest.get("wau", 0))
    st.metric("📊 WAU", f"{wau_val:,}")

with col3:
    rev = float(latest.get("daily_revenue", 0))
    delta_rev = float(latest["daily_revenue"] - prev["daily_revenue"]) if len(df_kpis) > 1 else 0
    st.metric("💰 Revenue", f"${rev:,.2f}", delta=f"${delta_rev:+,.2f}")

with col4:
    cashback = float(latest.get("daily_cashback", 0))
    st.metric("🎁 Cashback", f"${cashback:,.2f}")

with col5:
    conv = float(latest.get("conversion_rate", 0))
    st.metric("🔄 Conv. Rate", f"{conv:.2f}%")

st.markdown("---")

# =============================================================================
# Tabs
# =============================================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Trends", "🔍 Funnel", "🔄 Retention", "👥 Users", "📋 Events"
])

# --- Tab 1: Trends ---
with tab1:
    st.subheader("Daily Trends")

    col_left, col_right = st.columns(2)

    with col_left:
        # DAU / WAU trend
        fig_users = go.Figure()
        fig_users.add_trace(go.Scatter(
            x=df_kpis["event_date"], y=df_kpis["dau"],
            name="DAU", line=dict(color="#00d4ff", width=2),
            fill="tozeroy", fillcolor="rgba(0,212,255,0.1)",
        ))
        if "wau" in df_kpis.columns:
            fig_users.add_trace(go.Scatter(
                x=df_kpis["event_date"], y=df_kpis["wau"],
                name="WAU", line=dict(color="#7c3aed", width=2, dash="dash"),
            ))
        fig_users.update_layout(title="Active Users", height=350)
        st.plotly_chart(apply_theme(fig_users), use_container_width=True)

    with col_right:
        # Revenue trend
        fig_rev = go.Figure()
        fig_rev.add_trace(go.Bar(
            x=df_kpis["event_date"], y=df_kpis["daily_revenue"],
            name="Revenue", marker_color="#10b981", opacity=0.8,
        ))
        fig_rev.add_trace(go.Scatter(
            x=df_kpis["event_date"], y=df_kpis["daily_cashback"],
            name="Cashback", line=dict(color="#f59e0b", width=2),
            yaxis="y2",
        ))
        fig_rev.update_layout(
            title="Revenue & Cashback",
            yaxis2=dict(overlaying="y", side="right", showgrid=False),
            height=350,
        )
        st.plotly_chart(apply_theme(fig_rev), use_container_width=True)

    # Conversion rate
    fig_conv = go.Figure()
    fig_conv.add_trace(go.Scatter(
        x=df_kpis["event_date"], y=df_kpis["conversion_rate"],
        name="Conversion Rate %", line=dict(color="#ec4899", width=2),
        fill="tozeroy", fillcolor="rgba(236,72,153,0.1)",
    ))
    fig_conv.update_layout(title="Conversion Rate Trend", height=300)
    st.plotly_chart(apply_theme(fig_conv), use_container_width=True)

# --- Tab 2: Funnel ---
with tab2:
    st.subheader("Conversion Funnel")

    if not df_funnel.empty:
        col_fun_l, col_fun_r = st.columns([2, 1])

        with col_fun_l:
            fig_funnel = go.Figure(go.Funnel(
                y=df_funnel["stage_name"],
                x=df_funnel["unique_users"],
                textinfo="value+percent initial",
                marker=dict(color=COLOR_PALETTE[:len(df_funnel)]),
                connector=dict(line=dict(color="#4a5568", width=1)),
            ))
            fig_funnel.update_layout(title="User Conversion Funnel", height=450)
            st.plotly_chart(apply_theme(fig_funnel), use_container_width=True)

        with col_fun_r:
            st.markdown("#### Step Metrics")
            for _, row in df_funnel.iterrows():
                stage = row["stage_name"]
                users = int(row["unique_users"])
                step_rate = float(row["step_conversion_rate"])
                dropoff = int(row["dropoff_count"])

                icon = {"page_view": "👁️", "click": "👆", "add_to_cart": "🛒",
                        "purchase": "💳", "cashback_earned": "🎁"}.get(stage, "📌")

                st.markdown(f"""
                **{icon} {stage.replace('_', ' ').title()}**
                - Users: **{users:,}**
                - Step Rate: **{step_rate:.1f}%**
                - Drop-off: **{dropoff:,}**
                """)
    else:
        st.info("No funnel data available yet.")

# --- Tab 3: Retention ---
with tab3:
    st.subheader("Cohort Retention")

    if not df_retention.empty:
        # Build retention heatmap
        retention_cols = [c for c in df_retention.columns if c.startswith("retention_rate_")]
        if retention_cols:
            heatmap_data = df_retention[["cohort_week"] + retention_cols].set_index("cohort_week")
            heatmap_data.columns = [c.replace("retention_rate_", "").replace("_", " ").title()
                                    for c in heatmap_data.columns]

            fig_heat = px.imshow(
                heatmap_data.values,
                x=heatmap_data.columns.tolist(),
                y=[str(d) for d in heatmap_data.index],
                color_continuous_scale="Viridis",
                aspect="auto",
                text_auto=".1f",
            )
            fig_heat.update_layout(
                title="Retention Rate Heatmap (%)",
                xaxis_title="Retention Period",
                yaxis_title="Cohort Week",
                height=400,
            )
            st.plotly_chart(apply_theme(fig_heat), use_container_width=True)

        # Cohort size chart
        fig_cohort = px.bar(
            df_retention, x="cohort_week", y="cohort_size",
            title="Cohort Sizes",
            color_discrete_sequence=["#7c3aed"],
        )
        fig_cohort.update_layout(height=300)
        st.plotly_chart(apply_theme(fig_cohort), use_container_width=True)
    else:
        st.info("No retention data available yet.")

# --- Tab 4: Users ---
with tab4:
    st.subheader("User Analytics")

    if not df_users.empty:
        col_u1, col_u2 = st.columns(2)

        with col_u1:
            # User segments
            segment_counts = df_users["user_segment"].value_counts().reset_index()
            segment_counts.columns = ["segment", "count"]

            fig_seg = px.pie(
                segment_counts, values="count", names="segment",
                title="User Segments",
                color_discrete_sequence=COLOR_PALETTE,
                hole=0.45,
            )
            fig_seg.update_traces(textposition="inside", textinfo="percent+label")
            fig_seg.update_layout(height=400)
            st.plotly_chart(apply_theme(fig_seg), use_container_width=True)

        with col_u2:
            # Lifecycle stages
            lifecycle_counts = df_users["lifecycle_stage"].value_counts().reset_index()
            lifecycle_counts.columns = ["stage", "count"]

            fig_life = px.bar(
                lifecycle_counts, x="stage", y="count",
                title="Lifecycle Stages",
                color="stage",
                color_discrete_sequence=COLOR_PALETTE,
            )
            fig_life.update_layout(height=400, showlegend=False)
            st.plotly_chart(apply_theme(fig_life), use_container_width=True)

        # Revenue distribution
        if "total_revenue" in df_users.columns:
            buyers = df_users[df_users["total_revenue"] > 0]
            if not buyers.empty:
                fig_rev_dist = px.histogram(
                    buyers, x="total_revenue", nbins=50,
                    title="Revenue Distribution (Paying Users)",
                    color_discrete_sequence=["#10b981"],
                )
                fig_rev_dist.update_layout(height=300)
                st.plotly_chart(apply_theme(fig_rev_dist), use_container_width=True)

        # Summary stats
        st.markdown("#### User Summary")
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        with col_s1:
            st.metric("Total Users", f"{len(df_users):,}")
        with col_s2:
            avg_rev = df_users["total_revenue"].mean() if "total_revenue" in df_users.columns else 0
            st.metric("Avg Revenue", f"${avg_rev:,.2f}")
        with col_s3:
            buyers_pct = (len(df_users[df_users.get("purchases", 0) > 0]) / len(df_users) * 100
                         if "purchases" in df_users.columns and len(df_users) > 0 else 0)
            st.metric("Buyer %", f"{buyers_pct:.1f}%")
        with col_s4:
            avg_sessions = df_users["total_sessions"].mean() if "total_sessions" in df_users.columns else 0
            st.metric("Avg Sessions", f"{avg_sessions:.1f}")
    else:
        st.info("No user data available yet.")

# --- Tab 5: Events ---
with tab5:
    st.subheader("Event Distribution")

    df_events = load_event_distribution()

    if not df_events.empty:
        col_e1, col_e2 = st.columns(2)

        with col_e1:
            # Event type breakdown (total)
            event_totals = df_events.groupby("event_type")["event_count"].sum().reset_index()
            event_totals = event_totals.sort_values("event_count", ascending=True)

            fig_events = px.bar(
                event_totals, y="event_type", x="event_count",
                title="Total Events by Type",
                orientation="h",
                color="event_type",
                color_discrete_sequence=COLOR_PALETTE,
            )
            fig_events.update_layout(height=400, showlegend=False)
            st.plotly_chart(apply_theme(fig_events), use_container_width=True)

        with col_e2:
            # Event trend by type (stacked area)
            fig_trend = px.area(
                df_events, x="event_date", y="event_count",
                color="event_type",
                title="Daily Event Volume by Type",
                color_discrete_sequence=COLOR_PALETTE,
            )
            fig_trend.update_layout(height=400)
            st.plotly_chart(apply_theme(fig_trend), use_container_width=True)

        # Device breakdown from KPIs
        if not df_kpis.empty and "mobile_users" in df_kpis.columns:
            latest_kpi = df_kpis.iloc[-1]
            device_data = pd.DataFrame({
                "device": ["Mobile", "Desktop", "Tablet"],
                "users": [
                    int(latest_kpi.get("mobile_users", 0)),
                    int(latest_kpi.get("desktop_users", 0)),
                    int(latest_kpi.get("tablet_users", 0)),
                ],
            })

            fig_device = px.pie(
                device_data, values="users", names="device",
                title="Users by Device (Latest Day)",
                color_discrete_sequence=["#00d4ff", "#7c3aed", "#f59e0b"],
                hole=0.5,
            )
            fig_device.update_layout(height=350)
            st.plotly_chart(apply_theme(fig_device), use_container_width=True)
    else:
        st.info("No event data available yet.")

# =============================================================================
# Footer
# =============================================================================

st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#64748b; font-size:0.8rem; padding:1rem;'>"
    "📊 Event Analytics Pipeline • Built for Data Engineering • "
    "<a href='https://github.com/tapheret2/event-analytics-pipeline' style='color:#00d4ff;'>GitHub</a>"
    "</div>",
    unsafe_allow_html=True,
)
