"""
routes.py
All REST endpoints for the Forest Fire Prediction System.

    POST /api/predict              body: raw feature dict -> full prediction
    POST /api/predict/live         body: {latitude, longitude} or {city_name} -> live weather + prediction
    GET  /api/predictions/recent   query: ?limit=50
    GET  /api/predictions/map      latest prediction per location, for the Leaflet dashboard
    GET  /api/models/compare       model_comparison.csv as JSON
    GET  /api/alerts/recent        recent alerts (for browser notification polling)
    GET  /api/health               liveness check
"""

from __future__ import annotations

import os
import sys

import pandas as pd
from flask import Blueprint, jsonify, request

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.config import PATHS
from backend.utils.logger import get_logger
from backend.utils import db
from backend.utils.prediction_service import predict as run_prediction, ModelNotTrainedError
from backend.utils.weather_service import fetch_live_weather, WeatherServiceError
from backend.utils.alert_service import dispatch_alerts

logger = get_logger(__name__)
api = Blueprint("api", __name__, url_prefix="/api")


def _persist_prediction(location_data: dict, weather_data: dict, prediction: dict) -> int:
    location_id = db.upsert_location(
        latitude=location_data["latitude"], longitude=location_data["longitude"],
        city_name=location_data.get("city_name"), region=location_data.get("region"),
        country=location_data.get("country"), elevation=location_data.get("elevation"),
        slope=location_data.get("slope"),
    )
    weather_snapshot_id = None
    if weather_data:
        weather_snapshot_id = db.insert_weather_snapshot(location_id, weather_data)

    prediction_id = db.insert_prediction(
        location_id=location_id, weather_snapshot_id=weather_snapshot_id,
        model_name=prediction["model_name"], fire_probability=prediction["fire_probability"],
        risk_level=prediction["risk_level"], fire_weather_index=prediction["fire_weather_index"],
        top_features=prediction["top_features"], shap_values=prediction["shap_values"],
    )
    return location_id, prediction_id


@api.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@api.route("/predict", methods=["POST"])
def predict_route():
    """Accepts a raw feature dict (manual input, e.g. from a form) and returns a prediction."""
    payload = request.get_json(silent=True) or {}
    if "latitude" not in payload or "longitude" not in payload:
        return jsonify({"error": "latitude and longitude are required"}), 400

    try:
        prediction = run_prediction(payload)
    except ModelNotTrainedError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        logger.exception("Prediction failed")
        return jsonify({"error": f"Prediction failed: {e}"}), 500

    try:
        location_id, prediction_id = _persist_prediction(
            location_data=payload, weather_data=None, prediction=prediction
        )
        alert_result = dispatch_alerts(
            prediction_id=prediction_id,
            city_name=payload.get("city_name", "the requested location"),
            probability=prediction["fire_probability"], risk_level=prediction["risk_level"],
            email_recipient=payload.get("alert_email"),
        )
        prediction["prediction_id"] = prediction_id
        prediction["alert"] = alert_result
    except Exception as e:
        logger.error(f"Persistence/alert step failed (prediction still returned): {e}")

    return jsonify(prediction), 200


@api.route("/predict/live", methods=["POST"])
def predict_live_route():
    """Fetches live weather for a lat/lon or city name, then predicts."""
    payload = request.get_json(silent=True) or {}
    latitude = payload.get("latitude")
    longitude = payload.get("longitude")
    city_name = payload.get("city_name")

    try:
        weather = fetch_live_weather(latitude=latitude, longitude=longitude, city_name=city_name)
    except WeatherServiceError as e:
        return jsonify({"error": str(e)}), 400

    feature_input = {**weather, **{k: v for k, v in payload.items() if k not in weather}}

    try:
        prediction = run_prediction(feature_input)
    except ModelNotTrainedError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        logger.exception("Live prediction failed")
        return jsonify({"error": f"Prediction failed: {e}"}), 500

    try:
        location_id, prediction_id = _persist_prediction(
            location_data=weather, weather_data=weather, prediction=prediction
        )
        alert_result = dispatch_alerts(
            prediction_id=prediction_id, city_name=weather.get("city_name", city_name or "location"),
            probability=prediction["fire_probability"], risk_level=prediction["risk_level"],
            email_recipient=payload.get("alert_email"),
        )
        prediction["prediction_id"] = prediction_id
        prediction["alert"] = alert_result
    except Exception as e:
        logger.error(f"Persistence/alert step failed (prediction still returned): {e}")

    prediction["weather"] = weather
    return jsonify(prediction), 200


@api.route("/predictions/recent", methods=["GET"])
def recent_predictions_route():
    limit = int(request.args.get("limit", 50))
    try:
        rows = db.get_recent_predictions(limit=limit)
    except Exception as e:
        logger.exception("Failed to fetch recent predictions")
        return jsonify({"error": str(e)}), 500
    return jsonify(rows), 200


@api.route("/predictions/map", methods=["GET"])
def predictions_map_route():
    try:
        rows = db.get_latest_predictions_for_map()
    except Exception as e:
        logger.exception("Failed to fetch map predictions")
        return jsonify({"error": str(e)}), 500
    return jsonify(rows), 200


@api.route("/models/compare", methods=["GET"])
def models_compare_route():
    report_path = os.path.join(PATHS.reports_dir, "model_comparison.csv")
    if not os.path.exists(report_path):
        return jsonify({"error": "No model comparison report found. Run training first."}), 404
    df = pd.read_csv(report_path, index_col=0)
    return jsonify(df.reset_index().rename(columns={"index": "model_name"}).to_dict(orient="records")), 200


@api.route("/alerts/recent", methods=["GET"])
def recent_alerts_route():
    limit = int(request.args.get("limit", 20))
    try:
        with db.get_cursor() as cur:
            cur.execute(
                """SELECT a.*, p.risk_level, p.fire_probability, l.city_name
                   FROM alerts a
                   JOIN predictions p ON a.prediction_id = p.id
                   JOIN locations l ON p.location_id = l.id
                   ORDER BY a.created_at DESC LIMIT %s""",
                (limit,),
            )
            rows = cur.fetchall()
    except Exception as e:
        logger.exception("Failed to fetch recent alerts")
        return jsonify({"error": str(e)}), 500
    return jsonify(rows), 200
