import streamlit as st
import pandas as pd
import numpy as np
import streamlit.components.v1 as components
import json

from model_engine import load_data, simulate_and_predict, explain_risk, FEATURE_WEIGHTS

# Page configuration
st.set_page_config(
    page_title="HydroWatch AI - Flood Inundation Prediction",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #0f4c81;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #555;
        margin-bottom: 1.5rem;
    }
    .kpi-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #0f4c81;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }
    .kpi-val {
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0;
    }
    .kpi-label {
        font-size: 0.85rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🌊 HydroWatch AI: Predictive Flood Inundation System</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Spatio-Temporal Early Warning Engine | Integrating GIS Terrain, Weather Time-Series & Machine Learning</div>', unsafe_allow_html=True)

# Load data
@st.cache_data
def get_base_data():
    return load_data("data/delhi_flood_zones.csv")

base_df = get_base_data()

# ----------------- SIDEBAR SIMULATION CONTROLS -----------------
st.sidebar.header("🕹️ Crisis Simulation Controls")
st.sidebar.caption("Test 'What-If' disaster scenarios to see real-time flood susceptibility shifts across Delhi NCR.")

scenario = st.sidebar.radio(
    "Select Simulation Scenario:",
    ["Monsoon Baseline (Current)", "Moderate Rain Shower (+25mm)", "Extreme Cloudburst + Barrage Discharge (+85mm, +1.6m River)", "Custom Scenario"]
)

if scenario == "Monsoon Baseline (Current)":
    sim_rain = 0.0
    sim_river = 0.0
    sim_soil = 1.0
elif scenario == "Moderate Rain Shower (+25mm)":
    sim_rain = 25.0
    sim_river = 0.4
    sim_soil = 1.15
elif scenario == "Extreme Cloudburst + Barrage Discharge (+85mm, +1.6m River)":
    sim_rain = 85.0
    sim_river = 1.6
    sim_soil = 1.35
else:
    st.sidebar.markdown("---")
    sim_rain = st.sidebar.slider("Additional 24h Rainfall (mm)", 0.0, 150.0, 0.0, step=5.0)
    sim_river = st.sidebar.slider("Yamuna River Level Shift (meters)", -1.0, 3.0, 0.0, step=0.1)
    sim_soil = st.sidebar.slider("Soil Saturation Factor", 0.8, 1.5, 1.0, step=0.05)

st.sidebar.markdown("---")
st.sidebar.info("""
**Data Sources:**
- **Terrain (GIS)**: Copernicus GLO-30m DEM
- **Hydrology**: CWC Yamuna River Gauges
- **Weather**: IMD / ERA5-Land Reanalysis
- **Model**: Spatio-Temporal Gradient Boosting
""")

# Run prediction
simulated_df = simulate_and_predict(
    base_df,
    add_rainfall_mm=sim_rain,
    add_river_level_m=sim_river,
    soil_moisture_factor=sim_soil
)
simulated_df['xai_reason'] = simulated_df.apply(explain_risk, axis=1)

# ----------------- TOP KPI METRICS -----------------
high_risk_count = (simulated_df['predicted_risk_pct'] >= 70).sum()
med_risk_count = ((simulated_df['predicted_risk_pct'] >= 40) & (simulated_df['predicted_risk_pct'] < 70)).sum()
low_med_count = ((simulated_df['predicted_risk_pct'] >= 20) & (simulated_df['predicted_risk_pct'] < 40)).sum()
safe_count = (simulated_df['predicted_risk_pct'] < 20).sum()

est_pop_affected = int(high_risk_count * 18000 + med_risk_count * 6000)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""
    <div class="kpi-card" style="border-left-color: #2c7bb6;">
        <p class="kpi-label">Safe / Low Risk (&lt;20%)</p>
        <p class="kpi-val" style="color: #2c7bb6;">{safe_count} <span style="font-size:1rem;color:#888;">/ 40</span></p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="kpi-card" style="border-left-color: #f7d070;">
        <p class="kpi-label">Low-Medium (20-39%)</p>
        <p class="kpi-val" style="color: #c49a00;">{low_med_count}</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="kpi-card" style="border-left-color: #fdae61;">
        <p class="kpi-label">Medium Risk (40-69%)</p>
        <p class="kpi-val" style="color: #e67e22;">{med_risk_count}</p>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="kpi-card" style="border-left-color: #d7191c;">
        <p class="kpi-label">High Risk Alert (&ge;70%)</p>
        <p class="kpi-val" style="color: #d7191c;">{high_risk_count}</p>
    </div>
    """, unsafe_allow_html=True)

with col5:
    status_text = "NORMAL" if high_risk_count == 0 else ("WATCH" if high_risk_count <= 2 else "RED ALERT - EVACUATE")
    status_color = "#27ae60" if high_risk_count == 0 else ("#f39c12" if high_risk_count <= 2 else "#c0392b")
    st.markdown(f"""
    <div class="kpi-card" style="border-left-color: {status_color};">
        <p class="kpi-label">Disaster Advisory</p>
        <p class="kpi-val" style="color: {status_color}; font-size: 1.2rem; padding-top: 5px;">{status_text}</p>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# ----------------- INTERACTIVE LEAFLET MAP GENERATION -----------------
# Generate self-contained Leaflet HTML with pure JavaScript
markers_js = []
for _, row in simulated_df.iterrows():
    popup_html = (
        f"<b>Area:</b> {row['area_id']} ({row['area_name']})<br>"
        f"<b>Flood risk:</b> {row['predicted_risk_pct']}%<br>"
        f"<b>Rainfall (today):</b> {row['rainfall_mm']:.1f} mm<br>"
        f"<b>7-day rainfall:</b> {row['rain_7d_sum']:.0f} mm<br>"
        f"<b>River level:</b> {row['river_level_m']:.2f} m<br>"
        f"<b>Elevation:</b> {row['elevation_m']} m<br>"
        f"<b>Dist. to river:</b> {row['dist_to_river_km']:.1f} km<br>"
        f"<hr style='margin:4px 0;'><small><b>Key Driver:</b> {row['xai_reason']}</small>"
    )
    # escape quotes for js
    popup_escaped = popup_html.replace('"', '\\"').replace("'", "\\'")
    
    marker_stmt = f"""
    L.circleMarker([{row['lat']}, {row['lon']}], {{
        color: "{row['marker_color']}",
        fillColor: "{row['marker_color']}",
        fillOpacity: 0.85,
        radius: {row['marker_radius']},
        weight: 3
    }}).bindPopup("{popup_escaped}").addTo(map);
    """
    markers_js.append(marker_stmt)

markers_code = "\n".join(markers_js)

map_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; font-family: sans-serif; }}
        #map {{ width: 100%; height: 530px; border-radius: 8px; }}
        .legend {{
            position: absolute;
            bottom: 25px;
            left: 20px;
            z-index: 1000;
            background: white;
            padding: 10px 14px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.25);
            font-size: 12px;
            line-height: 18px;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <div class="legend">
        <b>Flood Risk Index</b><br>
        <span style="color:#d7191c;">&#9679;</span> High (&ge;70%)<br>
        <span style="color:#fdae61;">&#9679;</span> Medium (40-70%)<br>
        <span style="color:#a89f00;">&#9679;</span> Low-medium (20-40%)<br>
        <span style="color:#2c7bb6;">&#9679;</span> Low (&lt;20%)
    </div>
    <script>
        var map = L.map('map').setView([28.5601, 77.1438], 11);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 18,
            attribution: '&copy; OpenStreetMap contributors | HydroWatch AI'
        }}).addTo(map);

        {markers_code}
    </script>
</body>
</html>
"""

# Render Map
components.html(map_html, height=550)

# ----------------- TABS: ANALYTICS & PRESENTATION DEFENSE -----------------
tab1, tab2, tab3 = st.tabs(["📊 Feature Drivers & AI Explainability", "📋 High-Risk Priority Table", "💡 Presentation Pitch & Q&A"])

with tab1:
    st.subheader("Global Feature Importance (What Drives Flood Inundation?)")
    st.caption("Derived from our trained Gradient Boosted Trees model. Top predictors reflect hydrological physics.")
    
    feat_df = pd.DataFrame([
        {"Feature": k, "Importance": abs(v), "Direction": "Increases Risk" if v > 0 else "Decreases Risk"}
        for k, v in FEATURE_WEIGHTS.items()
    ]).sort_values(by="Importance", ascending=True)

    st.bar_chart(feat_df.set_index("Feature")["Importance"], horizontal=True)

    st.markdown("""
    > **Key Scientific Takeaway for Judges**:
    > - **7-Day Cumulative Rainfall (`rain_7d_sum`)** and **Lagged River Stage (`river_level_lag1`)** are 3× more predictive than single-day rain (`rainfall_mm`).
    > - Water accumulation is governed by watershed saturation and time of concentration, not just immediate cloudburst.
    """)

with tab2:
    st.subheader("Actionable Evacuation & Resource Deployment Table")
    critical_df = simulated_df[simulated_df['predicted_risk_pct'] >= 40][
        ['area_id', 'area_name', 'predicted_risk_pct', 'risk_category', 'elevation_m', 'dist_to_river_km', 'xai_reason']
    ].sort_values(by="predicted_risk_pct", ascending=False)
    
    if len(critical_df) > 0:
        st.dataframe(
            critical_df.rename(columns={
                'area_id': 'Zone ID',
                'area_name': 'Neighborhood',
                'predicted_risk_pct': 'Flood Risk %',
                'risk_category': 'Status',
                'elevation_m': 'Elevation (m)',
                'dist_to_river_km': 'Dist to Yamuna (km)',
                'xai_reason': 'Primary Vulnerability Factor'
            }),
            use_container_width=True
        )
        csv_data = critical_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Municipal Action Dispatch (CSV)",
            data=csv_data,
            file_name="delhi_flood_evacuation_dispatch.csv",
            mime="text/csv"
        )
    else:
        st.success("✅ All 40 monitoring zones are currently below the critical 40% threat threshold.")

with tab3:
    st.subheader("Judges' 3-Minute Presentation Cheat Sheet")
    st.markdown("""
    1. **The Hook (30s)**: "In 2023, the Yamuna river inundated Delhi causing ₹1,000+ Cr damage because warnings came too late. HydroWatch AI predicts inundation **12-24 hours before** water overflows the banks."
    2. **The Tech (30s)**: "We combine **Static GIS Terrain** (DEM, slope, distance to river) with **Dynamic Weather Time-Series** (7-day rainfall, upstream discharge) using Machine Learning."
    3. **The Live Demo (60s)**: "Watch me slide the Hathnikund Barrage release slider in the sidebar. Within milliseconds, low-elevation areas like Okhla (8m elevation) turn red on the map, and an emergency dispatch is generated."
    4. **Impact (30s)**: "Enables targeted sandbag deployment, road closures, and dignified evacuation before roads submerge."
    """)
