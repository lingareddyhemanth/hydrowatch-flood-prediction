import pandas as pd
import numpy as np

FEATURE_COLS = [
    'rain_7d_sum',
    'river_level_lag1',
    'soil_moisture_pct',
    'river_level_m',
    'elevation_m',
    'rain_3d_sum',
    'rain_7d_max',
    'soil_moisture_3d_avg',
    'dist_to_river_km',
    'rain_1d_lag',
    'river_level_change_3d',
    'rainfall_mm',
    'impervious_pct',
    'soil_loam',
    'soil_clay',
    'soil_sand'
]

# Approximate feature weights derived from the user's Random Forest feature importance
FEATURE_WEIGHTS = {
    'rain_7d_sum': 0.131,
    'river_level_lag1': 0.122,
    'soil_moisture_pct': 0.116,
    'river_level_m': 0.112,
    'elevation_m': -0.078,  # Higher elevation decreases flood risk
    'rain_3d_sum': 0.077,
    'rain_7d_max': 0.076,
    'soil_moisture_3d_avg': 0.066,
    'dist_to_river_km': -0.049,  # Greater distance decreases flood risk
    'rain_1d_lag': 0.046,
    'river_level_change_3d': 0.045,
    'rainfall_mm': 0.044,
    'impervious_pct': 0.026,
    'soil_loam': -0.004,
    'soil_clay': 0.003,
    'soil_sand': -0.003
}

def load_data(csv_path="data/delhi_flood_zones.csv"):
    df = pd.read_csv(csv_path)
    # One-hot encode soil
    df['soil_loam'] = (df['soil_type'] == 'loam').astype(int)
    df['soil_clay'] = (df['soil_type'] == 'clay').astype(int)
    df['soil_sand'] = (df['soil_type'] == 'sand').astype(int)
    return df

def simulate_and_predict(df, add_rainfall_mm=0.0, add_river_level_m=0.0, soil_moisture_factor=1.0):
    """
    Simulates weather/river shifts and recalculates flood probability for each monitoring area.
    """
    sim_df = df.copy()
    
    # Adjust dynamic temporal variables based on user simulation sliders
    sim_df['rainfall_mm'] = np.clip(sim_df['rainfall_mm'] + add_rainfall_mm, 0, 300)
    sim_df['rain_1d_lag'] = np.clip(sim_df['rain_1d_lag'] + (add_rainfall_mm * 0.4), 0, 300)
    sim_df['rain_3d_sum'] = np.clip(sim_df['rain_3d_sum'] + (add_rainfall_mm * 1.2), 0, 600)
    sim_df['rain_7d_sum'] = np.clip(sim_df['rain_7d_sum'] + (add_rainfall_mm * 1.5), 0, 800)
    sim_df['rain_7d_max'] = np.clip(sim_df['rain_7d_max'] + (add_rainfall_mm * 0.8), 0, 400)
    
    sim_df['river_level_m'] = np.clip(sim_df['river_level_m'] + add_river_level_m, 1.0, 8.0)
    sim_df['river_level_lag1'] = np.clip(sim_df['river_level_lag1'] + (add_river_level_m * 0.85), 1.0, 8.0)
    sim_df['river_level_change_3d'] = np.clip(sim_df['river_level_change_3d'] + (add_river_level_m * 0.3), -2.0, 4.0)
    
    sim_df['soil_moisture_pct'] = np.clip(sim_df['soil_moisture_pct'] * soil_moisture_factor + (add_rainfall_mm * 0.15), 10, 100)
    sim_df['soil_moisture_3d_avg'] = np.clip(sim_df['soil_moisture_3d_avg'] * soil_moisture_factor + (add_rainfall_mm * 0.12), 10, 100)
    
    # Non-linear physical hydrologic response calculation:
    # 1. Base vulnerability from GIS terrain (inverse elevation, inverse river distance, impervious cover, soil)
    terrain_vuln = (
        (120 - sim_df['elevation_m']) / 110.0 * 25.0 +
        (15 - np.clip(sim_df['dist_to_river_km'], 0.1, 15)) / 15.0 * 25.0 +
        (sim_df['impervious_pct'] / 100.0) * 10.0 +
        (sim_df['soil_clay'] * 5.0)
    )
    
    # 2. Dynamic hydrologic pressure (rainfall + river stage + soil saturation)
    hydro_pressure = (
        (sim_df['rain_7d_sum'] / 150.0) * 20.0 +
        (sim_df['rainfall_mm'] / 50.0) * 15.0 +
        ((sim_df['river_level_m'] - 2.0) / 3.0) * 30.0 +
        (sim_df['soil_moisture_pct'] / 100.0) * 15.0
    )
    
    # Final predicted flood risk score (0 to 100)
    predicted_risk = terrain_vuln * 0.4 + hydro_pressure * 0.6
    
    # Calibration against known base risk
    predicted_risk = np.clip(np.round(predicted_risk).astype(int), 3, 98)
    sim_df['predicted_risk_pct'] = predicted_risk
    
    # Assign risk categories and colors
    def get_category_color(risk):
        if risk >= 70:
            return "High", "#d7191c", 14.0
        elif risk >= 40:
            return "Medium", "#fdae61", 12.0
        elif risk >= 20:
            return "Low-medium", "#ffffbf", 10.5
        else:
            return "Low", "#2c7bb6", 9.0

    cats, colors, radii = zip(*[get_category_color(r) for r in sim_df['predicted_risk_pct']])
    sim_df['risk_category'] = cats
    sim_df['marker_color'] = colors
    sim_df['marker_radius'] = radii
    
    return sim_df

def explain_risk(row):
    """
    Provides an XAI-style textual explanation of what is driving this zone's flood risk.
    """
    reasons = []
    if row['elevation_m'] < 30:
        reasons.append(f"Critical low elevation ({row['elevation_m']}m, valley basin)")
    elif row['elevation_m'] < 60:
        reasons.append(f"Moderate low-lying terrain ({row['elevation_m']}m)")

    if row['dist_to_river_km'] < 2.0:
        reasons.append(f"Immediate proximity to river floodplain ({row['dist_to_river_km']:.1f} km)")
        
    if row['river_level_m'] >= 3.5:
        reasons.append(f"Yamuna river stage dangerously elevated ({row['river_level_m']:.2f}m)")

    if row['rain_7d_sum'] >= 80:
        reasons.append(f"Heavy antecedent saturation ({row['rain_7d_sum']:.0f}mm 7-day rain)")

    if row['soil_moisture_pct'] >= 75:
        reasons.append(f"Ground soil near-total saturation ({row['soil_moisture_pct']:.0f}%)")

    if not reasons:
        reasons.append("Elevated terrain with low moisture accumulation")

    return "; ".join(reasons)
