"""
prediction_service.py
Loads the best trained model + preprocessing artifacts once (module-level
singletons) and exposes a single predict() function used by the Flask API.
Applies the exact same feature engineering + scaling used at training time,
then runs SHAP on the single input row for local explainability.
"""

from __future__ import annotations

import json
import os
import sys
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd
import shap

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.config import DATA, MODEL, PATHS
from backend.utils.logger import get_logger
from backend.utils.feature_engineering import engineer_all_features, compute_risk_label

logger = get_logger(__name__)


class ModelNotTrainedError(Exception):
    pass


@lru_cache(maxsize=1)
def load_best_model():
    model_path = os.path.join(PATHS.models_dir, "best_model.joblib")
    meta_path = os.path.join(PATHS.models_dir, "best_model_meta.json")
    if not (os.path.exists(model_path) and os.path.exists(meta_path)):
        raise ModelNotTrainedError(
            "No trained model found. Run backend/training/train_models.py first."
        )
    model = joblib.load(model_path)
    with open(meta_path) as f:
        meta = json.load(f)
    logger.info(f"Loaded best model: {meta['model_name']}")
    return model, meta


@lru_cache(maxsize=1)
def load_preprocess_artifacts():
    path = os.path.join(PATHS.models_dir, "preprocess_artifacts.joblib")
    if not os.path.exists(path):
        raise ModelNotTrainedError(
            "No preprocessing artifacts found. Run the training pipeline first."
        )
    return joblib.load(path)


def _build_feature_row(raw_input: dict, feature_columns: list) -> pd.DataFrame:
    """
    raw_input: dict with at minimum temperature, humidity, wind_speed,
    rainfall, and optionally ndvi, elevation, slope, region, season,
    land_cover_type, soil_moisture, pressure.
    Missing engineered/optional fields default sensibly so a live
    OpenWeather-only request still produces a usable prediction.
    """
    row = {
        "temperature": raw_input.get("temperature", 25.0),
        "humidity": raw_input.get("humidity", 50.0),
        "wind_speed": raw_input.get("wind_speed", 10.0),
        "rainfall": raw_input.get("rainfall", 0.0),
        "pressure": raw_input.get("pressure", 1013.0),
        "ndvi": raw_input.get("ndvi", 0.4),
        "land_surface_temp": raw_input.get("land_surface_temp", raw_input.get("temperature", 25.0)),
        "elevation": raw_input.get("elevation", 200.0),
        "slope": raw_input.get("slope", 5.0),
        "soil_moisture": raw_input.get("soil_moisture", 30.0),
        "region": raw_input.get("region", "unknown"),
        "season": raw_input.get("season", "unknown"),
        "land_cover_type": raw_input.get("land_cover_type", "unknown"),
        "date": raw_input.get("date", pd.Timestamp.now()),
        "fire_occurred": 0,  # placeholder, not used for inference features
    }
    df = pd.DataFrame([row])
    df = engineer_all_features(df)

    for col in feature_columns:
        if col not in df.columns:
            df[col] = 0.0

    return df[feature_columns]


def predict(raw_input: dict) -> dict:
    """
    Runs the full inference pipeline on one location's data and returns:
    {
        model_name, fire_probability, risk_level, fire_weather_index,
        top_features: [{feature, impact}, ...],
        shap_values: [...]
    }
    """
    model, meta = load_best_model()
    artifacts = load_preprocess_artifacts()
    feature_columns = meta["feature_columns"]

    feature_row = _build_feature_row(raw_input, feature_columns)

    for col, encoder in artifacts.label_encoders.items():
        if col in feature_row.columns:
            val = str(feature_row.at[0, col])
            if val in encoder.classes_:
                feature_row[col] = encoder.transform([val])
            else:
                feature_row[col] = 0  # unseen category -> fallback

    numeric_present = [c for c in DATA.numeric_features if c in feature_columns]
    feature_row[numeric_present] = artifacts.scaler.transform(feature_row[numeric_present])

    X = feature_row.values

    try:
        proba = model.predict_proba(X)[0]
        fire_probability = float(proba[1]) if len(proba) > 1 else float(proba[0])
    except Exception as e:
        logger.error(f"predict_proba failed: {e}")
        raise

    risk_level = compute_risk_label(fire_probability, MODEL.risk_labels)

    top_features, shap_list = _explain_single_prediction(model, X, feature_columns)

    return {
        "model_name": meta["model_name"],
        "fire_probability": round(fire_probability, 4),
        "risk_level": risk_level,
        "fire_weather_index": float(
            feature_row["fire_weather_index"].iloc[0]
        ) if "fire_weather_index" in feature_row.columns else None,
        "top_features": top_features,
        "shap_values": shap_list,
        "alert_recommended": fire_probability >= MODEL.alert_probability_threshold,
    }


def _explain_single_prediction(model, X: np.ndarray, feature_columns: list):
    try:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)
        if isinstance(shap_values, list):
            shap_values = shap_values[1]
        row_shap = shap_values[0]
    except Exception as e:
        logger.warning(f"SHAP explanation failed, returning empty explanation: {e}")
        return [], []

    impacts = sorted(
        zip(feature_columns, row_shap.tolist()), key=lambda t: abs(t[1]), reverse=True
    )
    top_features = [{"feature": f, "impact": round(v, 4)} for f, v in impacts[:5]]
    return top_features, [round(v, 4) for v in row_shap.tolist()]
