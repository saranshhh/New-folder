import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta

# --------------------------------------------------
# Page Configuration
# --------------------------------------------------
st.set_page_config(
    page_title="Delhi Fog Live Tracker",
    page_icon="🌫️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------
# Global Styling + Mobile Responsiveness
# --------------------------------------------------
st.markdown("""
<style>

/* ---------- Global ---------- */
html, body, [class*="css"] {
    font-family: 'Inter', system-ui, sans-serif;
}

.main {
    background: radial-gradient(circle at top, #0f172a 0%, #020617 65%);
}

/* ---------- Header ---------- */
.app-title {
    font-size: 3rem;
    font-weight: 700;
    letter-spacing: -0.02em;
}

.subtitle {
    color: #94a3b8;
    font-size: 1.05rem;
}

/* ---------- Metric Cards ---------- */
div[data-testid="metric-container"] {
    background: linear-gradient(135deg,
        rgba(255,255,255,0.06),
        rgba(255,255,255,0.02)
    );
    border: 1px solid rgba(255,255,255,0.08);
    padding: 22px;
    border-radius: 16px;
    box-shadow: 0 12px 30px rgba(0,0,0,0.35);
    transition: all 0.2s ease;
}

div[data-testid="metric-container"]:hover {
    transform: translateY(-4px);
    box-shadow: 0 18px 40px rgba(0,0,0,0.5);
}

div[data-testid="stMetricLabel"] {
    font-size: 0.9rem;
    color: #cbd5f5;
}

div[data-testid="stMetricValue"] {
    font-size: 2.4rem;
    font-weight: 700;
    color: #38bdf8;
}

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #020617, #000);
    border-right: 1px solid rgba(255,255,255,0.06);
}

.sidebar-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #e5e7eb;
    margin-bottom: 0.5rem;
}

/* ---------- Radio Buttons ---------- */
div[role="radiogroup"] label {
    background: rgba(255,255,255,0.05);
    padding: 10px 14px;
    border-radius: 12px;
    margin-right: 8px;
    border: 1px solid rgba(255,255,255,0.08);
}

div[role="radiogroup"] label:hover {
    background: rgba(56,189,248,0.15);
    border-color: rgba(56,189,248,0.4);
}

/* ---------- Mobile Responsive ---------- */
@media (max-width: 768px) {

    .app-title {
        font-size: 2.1rem;
    }

    /* Stack metric cards vertically */
    div[data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        max-width: 100% !important;
    }

    /* Reduce chart height on mobile */
    .js-plotly-plot {
        height: 420px !important;
    }
}

/* ---------- Tables ---------- */
[data-testid="stDataFrame"] {
    border-radius: 16px;
    overflow: hidden;
}

</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# Data Source
# --------------------------------------------------
DATA_URL = "https://raw.githubusercontent.com/saranshhh/fog_log_checker_delhi/main/delhi_fog_data.csv"

def load_data_safe():
    df_raw = pd.read_csv(DATA_URL)

    df_raw['Timestamp'] = pd.to_datetime(df_raw['Timestamp'])
    if df_raw['Timestamp'].dt.tz is None:
        df_raw['Timestamp'] = df_raw['Timestamp'].dt.tz_localize('UTC')
    df_raw['Timestamp'] = df_raw['Timestamp'].dt.tz_convert('Asia/Kolkata')

    df_gen = df_raw[df_raw['Data_Row'].str.contains('GEN. VIS.', na=False)].copy()
    df_gen['vis'] = pd.to_numeric(
        df_gen['Data_Row'].str.extract(r'GEN\. VIS\.\s+:(\d+)')[0]
    )

    df_rvr = df_raw[df_raw['Data_Row'].str.contains('RVR', na=False)].copy()
    rvr_ext = df_rvr['Data_Row'].str.extract(r'RVR\s+([\w\d]+)\s+:(\d+)')
    df_rvr['runway'] = rvr_ext[0]
    df_rvr['vis'] = pd.to_numeric(rvr_ext[1])

    df_gen = df_gen[(df_gen['vis'] >= 0) & (df_gen['vis'] <= 5000)].dropna()
    df_rvr = df_rvr[(df_rvr['vis'] >= 0) & (df_rvr['vis'] <= 5000)].dropna()

    return df_gen, df_rvr

# --------------------------------------------------
# Main App
# --------------------------------------------------
def main():

    header_col, update_col = st.columns([3, 1.2])

    try:
        df_gen, df_rvr = load_data_safe()
        latest_time = df_gen['Timestamp'].max()

        # ---------- Header ----------
        with header_col:
            st.markdown("""
                <div class="app-title">🌫️ Delhi Airport Fog Tracker</div>
                <div class="subtitle">
                    Live operational visibility feed • IGI Airport (DEL)
                </div>
            """, unsafe_allow_html=True)

        with update_col:
            st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #0ea5e9, #0284c7);
                    padding: 16px;
                    border-radius: 14px;
                    color: white;
                    text-align: center;
                    margin-top: 14px;
                    box-shadow: 0 8px 25px rgba(14,165,233,0.4);
                ">
                    <div style="font-size:0.75rem; opacity:0.85;">
                        LAST DATA SYNC (IST)
                    </div>
                    <div style="font-size:1.25rem; font-weight:700;">
                        {latest_time.strftime('%d %b, %H:%M:%S')}
                    </div>
                </div>
            """, unsafe_allow_html=True)

        # ---------- Sidebar ----------
        st.sidebar.markdown("<div class='sidebar-title'>🧭 Navigation</div>", unsafe_allow_html=True)

        time_range = st.sidebar.selectbox(
            "History Depth",
            ["Last 6 Hours", "Last 24 Hours", "Last 7 Days"],
            index=1
        )

        hours_map = {"Last 6 Hours": 6, "Last 24 Hours": 24, "Last 7 Days": 168}
        cutoff = latest_time - timedelta(hours=hours_map[time_range])

        f_gen = df_gen[df_gen['Timestamp'] >= cutoff]
        f_rvr = df_rvr[df_rvr['Timestamp'] >= cutoff]

        # ---------- Metrics (Auto-stack on Mobile) ----------
        curr_vis = int(f_gen.iloc[-1]['vis']) if not f_gen.empty else 0
        avg_vis = int(f_gen['vis'].mean()) if not f_gen.empty else 0

        fog_type = (
            "Dense" if curr_vis <= 50 else
            "Moderate" if curr_vis <= 200 else
            "Shallow" if curr_vis <= 500 else
            "Clear"
        )

        fog_color = (
            "#dc2626" if curr_vis <= 50 else
            "#f97316" if curr_vis <= 200 else
            "#eab308" if curr_vis <= 500 else
            "#22c55e"
        )

        m1, m2, m3, m4 = st.columns(4)

        m1.metric("General Visibility", f"{curr_vis} m")
        m2.metric("Critical Runway RVR",
                  f"{int(f_rvr['vis'].min()) if not f_rvr.empty else 0} m")
        m3.metric("Period Average", f"{avg_vis} m")

        with m4:
            st.markdown(f"""
                <div style="text-align:center;">
                    <div style="color:#cbd5f5; font-size:0.9rem;">Fog Status</div>
                    <div style="font-size:2rem; font-weight:700; color:{fog_color};">
                        {fog_type}
                    </div>
                </div>
            """, unsafe_allow_html=True)

        # ---------- View Selector ----------
        view = st.radio(
            "View Mode",
            ["📈 Visibility Trend", "🛫 Runway Analysis", "📋 Data Logs"],
            horizontal=True
        )

        # ---------- Charts ----------
        if "Visibility" in view:
            fig = px.area(
                f_gen,
                x="Timestamp",
                y="vis",
                labels={"vis": "Visibility (m)", "Timestamp": "Time (IST)"},
                title="General Visibility Trend",
                color_discrete_sequence=["#38bdf8"]
            )

            fig.add_hrect(y0=0, y1=50, fillcolor="red", opacity=0.35, layer="above")
            fig.add_hrect(y0=50, y1=200, fillcolor="orange", opacity=0.25, layer="above")

            fig.update_layout(
                template="plotly_dark",
                hovermode="x unified",
                height=900,
                margin=dict(l=20, r=20, t=50, b=20)
            )

            st.plotly_chart(fig, use_container_width=True)

        elif "Runway" in view:
            if not f_rvr.empty:
                fig = px.line(
                    f_rvr,
                    x="Timestamp",
                    y="vis",
                    color="runway",
                    labels={"vis": "RVR (m)", "runway": "Runway"},
                    title="Runway Visual Range Comparison",
                    color_discrete_sequence=px.colors.qualitative.Safe
                )

                fig.update_layout(
                    template="plotly_dark",
                    hovermode="x unified",
                    height=900
                )

                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No runway RVR data available.")

        else:
            st.dataframe(
                f_gen[["Timestamp", "vis"]]
                .sort_values("Timestamp", ascending=False),
                use_container_width=True
            )

    except Exception as e:
        st.error(f"Data sync error: {e}")

# --------------------------------------------------
if __name__ == "__main__":
    main()
