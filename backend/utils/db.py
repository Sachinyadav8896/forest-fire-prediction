"""
db.py
Thin MySQL access layer used by the Flask API. Uses a connection pool so
concurrent requests don't each open a fresh TCP connection, and every
public function returns plain dicts/lists (never cursor objects) so
routes can json.dumps the result directly.
"""

from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager
from typing import Any, Optional

import mysql.connector
from mysql.connector import pooling

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.config import DB
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_POOL: Optional[pooling.MySQLConnectionPool] = None


def get_pool() -> pooling.MySQLConnectionPool:
    global _POOL
    if _POOL is None:
        _POOL = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="fire_pool",
            pool_size=5,
            host=DB.host, port=DB.port, user=DB.user,
            password=DB.password, database=DB.database,
        )
        logger.info("MySQL connection pool initialized.")
    return _POOL


@contextmanager
def get_cursor(dictionary: bool = True, commit: bool = False):
    conn = get_pool().get_connection()
    cursor = conn.cursor(dictionary=dictionary)
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def upsert_location(latitude: float, longitude: float, city_name: str = None,
                     region: str = None, country: str = None,
                     elevation: float = None, slope: float = None) -> int:
    with get_cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO locations (latitude, longitude, city_name, region, country, elevation, slope)
               VALUES (%s,%s,%s,%s,%s,%s,%s)
               ON DUPLICATE KEY UPDATE
                   city_name=VALUES(city_name), region=VALUES(region),
                   country=VALUES(country), elevation=VALUES(elevation), slope=VALUES(slope)""",
            (latitude, longitude, city_name, region, country, elevation, slope),
        )
        cur.execute(
            "SELECT id FROM locations WHERE latitude=%s AND longitude=%s",
            (latitude, longitude),
        )
        return cur.fetchone()["id"]


def insert_weather_snapshot(location_id: int, weather: dict) -> int:
    with get_cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO weather_snapshots
               (location_id, temperature, humidity, wind_speed, rainfall, pressure,
                ndvi, land_surface_temp, soil_moisture, source)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                location_id, weather.get("temperature"), weather.get("humidity"),
                weather.get("wind_speed"), weather.get("rainfall"), weather.get("pressure"),
                weather.get("ndvi"), weather.get("land_surface_temp"),
                weather.get("soil_moisture"), weather.get("source", "openweather"),
            ),
        )
        return cur.lastrowid


def insert_prediction(location_id: int, weather_snapshot_id: Optional[int],
                       model_name: str, fire_probability: float, risk_level: str,
                       fire_weather_index: float, top_features: list,
                       shap_values: Optional[list] = None) -> int:
    top = (top_features + [{}, {}, {}])[:3]
    with get_cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO predictions
               (location_id, weather_snapshot_id, model_name, fire_probability, risk_level,
                fire_weather_index, top_feature_1, top_feature_1_impact,
                top_feature_2, top_feature_2_impact, top_feature_3, top_feature_3_impact,
                shap_values_json)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                location_id, weather_snapshot_id, model_name, fire_probability, risk_level,
                fire_weather_index,
                top[0].get("feature"), top[0].get("impact"),
                top[1].get("feature"), top[1].get("impact"),
                top[2].get("feature"), top[2].get("impact"),
                json.dumps(shap_values) if shap_values is not None else None,
            ),
        )
        return cur.lastrowid


def insert_alert(prediction_id: int, channel: str, recipient: str, status: str = "pending") -> int:
    with get_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO alerts (prediction_id, channel, recipient, status) VALUES (%s,%s,%s,%s)",
            (prediction_id, channel, recipient, status),
        )
        return cur.lastrowid


def mark_alert_sent(alert_id: int):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE alerts SET status='sent', sent_at=NOW() WHERE id=%s", (alert_id,)
        )


def get_recent_predictions(limit: int = 50) -> list:
    with get_cursor() as cur:
        cur.execute(
            """SELECT p.*, l.latitude, l.longitude, l.city_name, l.region
               FROM predictions p JOIN locations l ON p.location_id = l.id
               ORDER BY p.predicted_at DESC LIMIT %s""",
            (limit,),
        )
        return cur.fetchall()


def get_latest_predictions_for_map() -> list:
    with get_cursor() as cur:
        cur.execute(
            """SELECT lp.*, l.latitude, l.longitude, l.city_name, l.region
               FROM latest_predictions_by_location lp
               JOIN locations l ON lp.location_id = l.id"""
        )
        return cur.fetchall()


def save_model_metrics(rows: list, best_model_name: str):
    with get_cursor(commit=True) as cur:
        for row in rows:
            cur.execute(
                """INSERT INTO model_metrics
                   (model_name, accuracy, precision_score, recall_score, f1_score,
                    roc_auc, training_time_sec, prediction_time_sec, is_best_model)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    row["model_name"], row.get("accuracy"), row.get("precision"),
                    row.get("recall"), row.get("f1_score"), row.get("roc_auc"),
                    row.get("training_time_sec"), row.get("prediction_time_sec"),
                    row["model_name"] == best_model_name,
                ),
            )


def get_model_metrics() -> list:
    with get_cursor() as cur:
        cur.execute(
            """SELECT * FROM model_metrics
               WHERE trained_at = (SELECT MAX(trained_at) FROM model_metrics)
               ORDER BY f1_score DESC"""
        )
        return cur.fetchall()
