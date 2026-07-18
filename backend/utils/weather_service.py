"""
weather_service.py
Fetches live weather from OpenWeather (by lat/lon or city name) and recent
active-fire records from NASA FIRMS, and normalizes both into the flat
feature dict expected by the ML pipeline.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

import pandas as pd
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.config import API
from backend.utils.logger import get_logger

logger = get_logger(__name__)

OPENWEATHER_BASE = "https://api.openweathermap.org/data/2.5/weather"
GEOCODE_BASE = "https://api.openweathermap.org/geo/1.0/direct"
FIRMS_BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


class WeatherServiceError(Exception):
    pass


def geocode_city(city_name: str) -> tuple[float, float]:
    if not API.openweather_api_key:
        raise WeatherServiceError("OPENWEATHER_API_KEY is not configured.")

    resp = requests.get(GEOCODE_BASE, params={
        "q": city_name, "limit": 1, "appid": API.openweather_api_key
    }, timeout=10)
    resp.raise_for_status()
    results = resp.json()
    if not results:
        raise WeatherServiceError(f"City not found: {city_name}")
    return results[0]["lat"], results[0]["lon"]


def fetch_live_weather(
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    city_name: Optional[str] = None,
) -> dict:
    """
    Returns weather either from OpenWeather or from the offline CSV.
    """

    # ---------- OFFLINE MODE ----------
    if not API.openweather_api_key:
        logger.warning("OPENWEATHER API key not found. Using offline weather database.")

        BASE_DIR = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )

        csv_path = os.path.join(
            BASE_DIR,
            "database",
            "offline_weather.csv"
        )

        print(csv_path)
        df = pd.read_csv(csv_path)

        if city_name is None:
            raise WeatherServiceError("City name is required.")

        city = city_name.strip().lower()

        match = df[df["city"].str.lower() == city]

        if match.empty:
            raise WeatherServiceError(
                f"City '{city_name}' not found in offline database."
            )

        row = match.iloc[0]

        return {
            "temperature": float(row["temperature"]),
            "humidity": float(row["humidity"]),
            "pressure": float(row["pressure"]),
            "wind_speed": float(row["wind_speed"]),
            "rainfall": float(row["rainfall"]),
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "city_name": row["city"],
            "country": "India",
            "source": "offline_database",
        }

    # ---------- ONLINE MODE ----------
    if city_name and (latitude is None or longitude is None):
        latitude, longitude = geocode_city(city_name)

    if latitude is None or longitude is None:
        raise WeatherServiceError(
            "Provide either (latitude, longitude) or city_name."
        )

    resp = requests.get(
        OPENWEATHER_BASE,
        params={
            "lat": latitude,
            "lon": longitude,
            "appid": API.openweather_api_key,
            "units": "metric",
        },
        timeout=10,
    )

    if resp.status_code != 200:
        logger.error(f"OpenWeather API error {resp.status_code}: {resp.text}")
        raise WeatherServiceError(f"OpenWeather API returned {resp.status_code}")

    data = resp.json()

    rainfall = data.get("rain", {}).get("1h", 0.0)

    return {
        "temperature": data["main"]["temp"],
        "humidity": data["main"]["humidity"],
        "pressure": data["main"]["pressure"],
        "wind_speed": data["wind"]["speed"] * 3.6,
        "rainfall": rainfall,
        "latitude": latitude,
        "longitude": longitude,
        "city_name": data.get("name", city_name),
        "country": data.get("sys", {}).get("country"),
        "source": "openweather",
    }


def fetch_firms_active_fires(latitude: float, longitude: float,
                              radius_deg: float = 1.0, day_range: int = 1) -> list:
    """
    Queries NASA FIRMS for active-fire detections (VIIRS/MODIS) within a
    bounding box around the given point over the last `day_range` days.
    Returns a list of dicts, or [] if the FIRMS key is not configured/no data.
    """
    if not API.firms_api_key:
        logger.warning("NASA_FIRMS_API_KEY not configured; skipping active-fire lookup.")
        return []

    west, south = longitude - radius_deg, latitude - radius_deg
    east, north = longitude + radius_deg, latitude + radius_deg
    bbox = f"{west},{south},{east},{north}"
    url = f"{FIRMS_BASE}/{API.firms_api_key}/VIIRS_SNPP_NRT/{bbox}/{day_range}"

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        lines = resp.text.strip().split("\n")
        if len(lines) < 2:
            return []
        header = lines[0].split(",")
        records = [dict(zip(header, line.split(","))) for line in lines[1:]]
        return records
    except Exception as e:
        logger.error(f"NASA FIRMS lookup failed: {e}")
        return []
