import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta

# --- Page Configuration ---
st.set_page_config(
    page_title="Delhi Fog Live Tracker",
    page_icon="🌫️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Styling ---
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        color: #00d4ff;
    }
    /* Glassmorphism effect for metrics */
    div[data-testid="metric-container"] {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

DATA_URL = "https://raw.githubusercontent.com/saranshhh/fog_log_checker_delhi/main/delhi_fog_data.csv"

@st.cache_data(allow_output_mutation=True)
def fetch_and_clean():
    # Load raw data
    df_raw = pd.read_csv(DATA_URL)
    
    # 1. Standardize Time to IST
    df_raw['Timestamp'] = pd.to_datetime(df_raw['Timestamp'])
    if df_raw['Timestamp'].dt.tz is None:
        df_raw['Timestamp'] = df_raw['Timestamp'].dt.tz_localize('UTC')
    df_raw['Timestamp'] = df_raw['Timestamp'].dt.tz_convert('Asia/Kolkata')

    # 2. Extract General Visibility (Gen Vis)
    df_gen = df_raw[df_raw['Data_Row'].str.contains('GEN. VIS.', na=False)].copy()
    df_gen['vis'] = pd.to_numeric(df_gen['Data_Row'].str.extract(r'GEN\. VIS\.\s+:(\d+)')[0])
    
    # 3. Extract Runway Visual Range (RVR)
    df_rvr = df_raw[df_raw['Data_Row'].str.contains('RVR', na=False)].copy()
    rvr_ext = df_rvr['Data_Row'].str.extract(r'RVR\s+([\w\d]+)\s+:(\d+)')
    df_rvr['runway'] = rvr_ext[0]
    df_rvr['vis'] = pd.to_numeric(rvr_ext[1])
    
    # 4. Filter anomalies (0-5000m range)
    df_gen = df_gen[(df_gen['vis'] >= 0) & (df_gen['vis'] <= 5000)].dropna()
    df_rvr = df_rvr[(df_rvr['vis'] >= 0) & (df_rvr['vis'] <= 5000)].dropna()
    
    return df_gen, df_rvr

def main():
    # --- Top Header Section ----
    header_col, update_col = st.columns([3, 1.2])
    
    try:
        df_gen, df_rvr = fetch_and_clean()
        latest_time = df_gen['Timestamp'].max()
        
        with header_col:
            st.title("🌫️ Delhi Airport Fog Station")
            st.markdown(f"**Live Operational Feed** | IGI Airport (DEL)")
        
        with update_col:
            st.markdown(f"""
                <div style="background-color:#161b22; padding:12px; border-radius:8px; border-left: 5px solid #00d4ff; margin-top:10px;">
                    <small style="color:#888;">LAST DATA SYNC (IST)</small><br>
                    <span style="color:#00d4ff; font-size:18px; font-weight:bold;">{latest_time.strftime('%d %b, %H:%M:%S')}</span>
                </div>
            """, unsafe_allow_html=True)

        # --- Sidebar ---
        st.sidebar.header("Navigation")
        time_range = st.sidebar.select_slider(
            "Select History Depth",
            options=["6 Hours", "24 Hours", "7 Days"],
            value="24 Hours"
        )
        
        hours_map = {"6 Hours": 6, "24 Hours": 24, "7 Days": 168}
        cutoff = latest_time - timedelta(hours=hours_map[time_range])
        
        f_gen = df_gen[df_gen['Timestamp'] >= cutoff]
        f_rvr = df_rvr[df_rvr['Timestamp'] >= cutoff]

        # --- Key Metrics ---
        curr_vis = int(f_gen.iloc[-1]['vis']) if not f_gen.empty else 0
        m1, m2, m3, m4 = st.columns(4)
        
        with m1:
            st.metric("General Visibility", f"{curr_vis}m")
        with m2:
            latest_rvr = int(f_rvr[f_rvr['Timestamp'] == f_rvr['Timestamp'].max()]['vis'].min()) if not f_rvr.empty else 0
            st.metric("Critical Runway RVR", f"{latest_rvr}m")
        with m3:
            st.metric("Period Average", f"{int(f_gen['vis'].mean())}m")
        with m4:
            fog_type = "Dense" if curr_vis <= 50 else "Moderate" if curr_vis <= 200 else "Shallow" if curr_vis <= 500 else "Clear"
            st.metric("Fog Status", fog_type)

        # --- Visualizations ---
        tab1, tab2, tab3 = st.tabs(["📉 Visibility Trend", "🛫 Runway (RVR) Analysis", "📋 Data Logs"])

        with tab1:
            fig_gen = px.area(f_gen, x='Timestamp', y='vis', 
                             title="General Visibility Trend (meters)",
                             labels={'vis': 'Visibility (m)', 'Timestamp': 'Time (IST)'},
                             color_discrete_sequence=['#00d4ff'])
            fig_gen.update_layout(template="plotly_dark", hovermode="x unified")
            fig_gen.add_hrect(y0=0, y1=50, fillcolor="red", opacity=0.1, annotation_text="CAT III Limits")
            st.plotly_chart(fig_gen, use_container_width=True)

        with tab2:
            if not f_rvr.empty:
                fig_rvr = px.line(f_rvr, x='Timestamp', y='vis', color='runway',
                                 title="Runway Visual Range (RVR) Comparison",
                                 labels={'vis': 'RVR (m)', 'runway': 'Runway'},
                                 color_discrete_sequence=px.colors.qualitative.Safe)
                fig_rvr.update_layout(template="plotly_dark", hovermode="x unified")
                st.plotly_chart(fig_rvr, use_container_width=True)
            else:
                st.warning("No Runway data found for this timeframe.")

        with tab3:
            st.dataframe(f_gen[['Timestamp', 'vis']].sort_values('Timestamp', ascending=False), use_container_width=True)

    except Exception as e:
        st.error(f"Syncing Error: {e}")

if __name__ == "__main__":
    main()