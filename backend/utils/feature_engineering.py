"""
feature_engineering.py
Implements the domain-specific engineered features that differentiate this
system from plain weather-only fire prediction baselines:

    - Fire Weather Index (simplified FWI-style composite)
    - Heat Index (Rothfusz regression, NOAA)
    - Vegetation Dryness Score (from NDVI + rainfall)
    - Temperature-Humidity Ratio
    - Wind Risk Score
    - Slope Risk
    - Historical Fire Frequency (region-level rolling count)

Each function is pure (no side effects) and vectorized with pandas/numpy so
it can be applied to a full dataframe or a single live-weather row.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def heat_index(temp_c: pd.Series, humidity: pd.Series) -> pd.Series:
    """NOAA Rothfusz regression heat index, converted from/to Celsius."""
    temp_f = temp_c * 9 / 5 + 32
    hi_f = (
        -42.379 + 2.04901523 * temp_f + 10.14333127 * humidity
        - 0.22475541 * temp_f * humidity - 0.00683783 * temp_f ** 2
        - 0.05481717 * humidity ** 2 + 0.00122874 * temp_f ** 2 * humidity
        + 0.00085282 * temp_f * humidity ** 2
        - 0.00000199 * temp_f ** 2 * humidity ** 2
    )
    hi_c = (hi_f - 32) * 5 / 9
    # Rothfusz formula is only valid above ~27C / 80F; fall back to temp otherwise
    return np.where(temp_c >= 26.7, hi_c, temp_c)


def temp_humidity_ratio(temp_c: pd.Series, humidity: pd.Series) -> pd.Series:
    """Higher ratio => hotter and drier => higher fire potential."""
    return temp_c / (humidity.clip(lower=1))


def wind_risk_score(wind_speed_kmh: pd.Series) -> pd.Series:
    """Piecewise scoring: fire spread risk grows non-linearly with wind."""
    return np.select(
        [wind_speed_kmh < 10, wind_speed_kmh < 20, wind_speed_kmh < 35, wind_speed_kmh < 50],
        [0.1, 0.35, 0.6, 0.85],
        default=1.0,
    )


def slope_risk(slope_degrees: pd.Series) -> pd.Series:
    """Fire moves faster uphill; risk scaled 0-1 with a cap at 45 degrees."""
    return (slope_degrees.clip(lower=0, upper=45) / 45).astype(float)


def vegetation_dryness_score(ndvi: pd.Series, rainfall_mm: pd.Series,
                              lookback_rain_mm: pd.Series | None = None) -> pd.Series:
    """
    Low NDVI (sparse/stressed vegetation) + low recent rainfall => high dryness.
    NDVI is normalized in [-1, 1]; we rescale to [0, 1] and invert so that
    LOW vegetation health/moisture yields a HIGH dryness score.
    """
    ndvi_norm = (ndvi.clip(-1, 1) + 1) / 2  # 0 (bare) -> 1 (dense healthy veg)
    rain_component = 1 / (1 + rainfall_mm.clip(lower=0))  # decays as rainfall increases
    dryness = (1 - ndvi_norm) * 0.6 + rain_component * 0.4
    return dryness.clip(0, 1)


def fire_weather_index(temp_c: pd.Series, humidity: pd.Series,
                        wind_speed_kmh: pd.Series, rainfall_mm: pd.Series) -> pd.Series:
    """
    Simplified composite Fire Weather Index (0-100 scale), inspired by the
    Canadian FWI system but reduced to inputs available from OpenWeather.
    Components: temperature, dryness (inverse humidity), wind, rain suppression.
    """
    temp_component = (temp_c.clip(lower=0) / 45).clip(0, 1)
    dryness_component = (1 - humidity.clip(0, 100) / 100)
    wind_component = (wind_speed_kmh.clip(lower=0) / 60).clip(0, 1)
    rain_suppression = 1 / (1 + rainfall_mm.clip(lower=0))

    fwi = (
        0.35 * temp_component +
        0.30 * dryness_component +
        0.20 * wind_component +
        0.15 * rain_suppression
    ) * 100
    return fwi.clip(0, 100)


def historical_fire_frequency(df: pd.DataFrame, region_col: str = "region",
                               date_col: str = "date",
                               fire_flag_col: str = "fire_occurred",
                               window_days: int = 365) -> pd.Series:
    """
    Rolling count of fires in the same region over the trailing `window_days`,
    computed per-row without leaking the current row's own label.
    Requires df sorted is NOT assumed; sorting is done internally per region.
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    result = pd.Series(index=df.index, dtype=float)

    for region, group in df.groupby(region_col):
        group_sorted = group.sort_values(date_col)
        counts = []
        dates = group_sorted[date_col].values
        flags = group_sorted[fire_flag_col].values
        for i in range(len(group_sorted)):
            current_date = dates[i]
            window_start = current_date - np.timedelta64(window_days, "D")
            mask = (dates < current_date) & (dates >= window_start)
            counts.append(int(flags[mask].sum()))
        result.loc[group_sorted.index] = counts

    return result.fillna(0)


def engineer_all_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies every engineered feature to a raw merged dataframe and returns
    an augmented copy. Expects columns:
    temperature, humidity, wind_speed, rainfall, ndvi, elevation, slope,
    region, date, fire_occurred.
    Missing optional columns are handled gracefully.
    """
    df = df.copy()

    df["heat_index"] = heat_index(df["temperature"], df["humidity"])
    df["temp_humidity_ratio"] = temp_humidity_ratio(df["temperature"], df["humidity"])
    df["wind_risk_score"] = wind_risk_score(df["wind_speed"])
    df["fire_weather_index"] = fire_weather_index(
        df["temperature"], df["humidity"], df["wind_speed"], df["rainfall"]
    )

    if "ndvi" in df.columns:
        df["vegetation_dryness_score"] = vegetation_dryness_score(df["ndvi"], df["rainfall"])
    if "slope" in df.columns:
        df["slope_risk"] = slope_risk(df["slope"])
    if {"region", "date", "fire_occurred"}.issubset(df.columns):
        df["historical_fire_frequency"] = historical_fire_frequency(df)
    else:
        df["historical_fire_frequency"] = 0.0

    return df


def compute_risk_label(probability: float, risk_labels=None) -> str:
    """
    Maps a model's positive-class probability (0-1) to one of five
    human-readable risk categories used throughout the dashboard.
    """
    if risk_labels is None:
        risk_labels = ["Low", "Moderate", "High", "Very High", "Extreme"]

    if probability < 0.20:
        return risk_labels[0]
    elif probability < 0.40:
        return risk_labels[1]
    elif probability < 0.60:
        return risk_labels[2]
    elif probability < 0.85:
        return risk_labels[3]
    else:
        return risk_labels[4]
