import streamlit as st
import pandas as pd
import requests
import json
import time

st.set_page_config(
    page_title="Apex Retail - Store Intelligence",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
    .metric-card {
        background-color: #1e293b;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #334155;
        text-align: center;
        margin-bottom: 10px;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #38bdf8;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #94a3b8;
    }
</style>
""", unsafe_allow_html=True)

st.title("Apex Retail - Live Store Analytics Dashboard")
st.markdown("Real-time metrics, funnel drop-off rates, anomalies, and traffic heatmaps mapped from CCTV feeds.")

import os
API_URL = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000")
STORE_ID = "ST1008"

st.sidebar.header("Settings")
auto_refresh = st.sidebar.checkbox("Auto Refresh (Every 5s)", value=True)
refresh_rate = 5

def fetch_data(endpoint: str):
    try:
        response = requests.get(f"{API_URL}{endpoint}")
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.sidebar.error(f"Error connecting to backend: {e}")
    return None

metrics = fetch_data(f"/stores/{STORE_ID}/metrics")
funnel = fetch_data(f"/stores/{STORE_ID}/funnel")
heatmap = fetch_data(f"/stores/{STORE_ID}/heatmap")
anomalies = fetch_data(f"/stores/{STORE_ID}/anomalies")
health = fetch_data("/health")

if metrics:
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{metrics.get("unique_visitors", 0)}</div>
            <div class="metric-label">Unique Visitors</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        conv_rate = metrics.get("conversion_rate", 0) * 100
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{conv_rate:.1f}%</div>
            <div class="metric-label">Conversion Rate</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{metrics.get("queue_depth", 0)}</div>
            <div class="metric-label">Current Queue Depth</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col4:
        abandon_rate = metrics.get("abandonment_rate", 0) * 100
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{abandon_rate:.1f}%</div>
            <div class="metric-label">Queue Abandonment Rate</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">₹ {metrics.get("total_gmv", 0):,}</div>
            <div class="metric-label">Total NMV (Revenue)</div>
        </div>
        """, unsafe_allow_html=True)

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Conversion Funnel")
    if funnel and "stages" in funnel:
        df_funnel = pd.DataFrame(funnel["stages"])
        st.bar_chart(df_funnel.set_index("stage_name")["count"])
        st.dataframe(df_funnel, hide_index=True)

with col_right:
    st.subheader("Zone Visit Heatmap (Density score 0-100)")
    if heatmap and "zones" in heatmap:
        zone_records = []
        for zone_name, data in heatmap["zones"].items():
            zone_records.append({
                "Zone": zone_name,
                "Visits": data["raw_visits"],
                "Avg Dwell (ms)": data["raw_avg_dwell_ms"],
                "Popularity Density": data["normalized_frequency"]
            })
        if zone_records:
            df_heat = pd.DataFrame(zone_records)
            st.dataframe(df_heat, hide_index=True)
            st.info(f"Data Confidence level: **{heatmap.get('data_confidence', 'LOW')}**")
        else:
            st.write("No visitor presence registered in zones yet.")

col_bot_l, col_bot_r = st.columns(2)

with col_bot_l:
    st.subheader("⚠️ Active Operational Anomalies")
    if anomalies:
        for anomaly in anomalies:
            severity = anomaly["severity"]
            color = "red" if severity == "CRITICAL" else "orange" if severity == "WARN" else "blue"
            st.markdown(f"""
            **Type**: `{anomaly['anomaly_type']}` | Severity: :{color}[{severity}]
            - **Alert**: {anomaly['message']}
            - **Suggested Action**: *{anomaly['suggested_action']}*
            ---
            """)
    else:
        st.success("All store systems operating normally. No active anomalies.")

with col_bot_r:
    st.subheader("🔌 System Feeds & Health")
    if health:
        st.write(f"Database Connectivity: **{health.get('database', 'UNKNOWN')}**")
        st.write(f"System Status: **{health.get('status', 'UNKNOWN')}**")
        if "feeds" in health:
            for store_id, feed_info in health["feeds"].items():
                st.write(f"Feed `{store_id}` status: {feed_info['status']} (Lag: {feed_info['lag_seconds']}s)")
    else:
        st.write("Fetching system status...")

if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()
