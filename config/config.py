"""
config.py
Central configuration for the Forest Fire Prediction System.
All modules (preprocessing, training, API) import settings from here
instead of hardcoding paths or hyperparameters.
"""

import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@dataclass
class PathConfig:
    base_dir: str = BASE_DIR
    raw_data_dir: str = os.path.join(BASE_DIR, "dataset", "raw")
    processed_data_dir: str = os.path.join(BASE_DIR, "dataset", "processed")
    models_dir: str = os.path.join(BASE_DIR, "models", "saved")
    logs_dir: str = os.path.join(BASE_DIR, "backend", "logs")
    reports_dir: str = os.path.join(BASE_DIR, "research", "reports")
    shap_dir: str = os.path.join(BASE_DIR, "research", "shap")


@dataclass
class DataConfig:
    """Column names expected in the merged dataset after ingestion."""
    target_column: str = "fire_risk_level"          # multi-class target
    binary_target_column: str = "fire_occurred"      # legacy binary target
    numeric_features: List[str] = field(default_factory=lambda: [
        "temperature", "humidity", "wind_speed", "rainfall", "pressure",
        "ndvi", "land_surface_temp", "elevation", "slope", "soil_moisture",
        "fire_weather_index", "heat_index", "vegetation_dryness_score",
        "temp_humidity_ratio", "wind_risk_score", "slope_risk",
        "historical_fire_frequency",
    ])
    categorical_features: List[str] = field(default_factory=lambda: [
        "season", "land_cover_type", "region"
    ])
    test_size: float = 0.2
    val_size: float = 0.1
    random_state: int = 42
    smote_k_neighbors: int = 5


@dataclass
class ModelConfig:
    random_state: int = 42
    cv_folds: int = 5
    n_jobs: int = -1
    risk_labels: List[str] = field(default_factory=lambda: [
        "Low", "Moderate", "High", "Very High", "Extreme"
    ])
    # probability threshold (of the top-2 highest classes combined)
    # above which an automated alert is triggered
    alert_probability_threshold: float = 0.90


@dataclass
class APIConfig:
    openweather_api_key: str = os.environ.get("OPENWEATHER_API_KEY", "")
    firms_api_key: str = os.environ.get("NASA_FIRMS_API_KEY", "")
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = os.environ.get("FLASK_DEBUG", "false").lower() == "true"


@dataclass
class DBConfig:
    host: str = os.environ.get("DB_HOST", "localhost")
    port: int = int(os.environ.get("DB_PORT", "3306"))
    user: str = os.environ.get("DB_USER", "root")
    password: str = os.environ.get("DB_PASSWORD", "")
    database: str = os.environ.get("DB_NAME", "forest_fire_db")


PATHS = PathConfig()
DATA = DataConfig()
MODEL = ModelConfig()
API = APIConfig()
DB = DBConfig()

for _dir in (PATHS.processed_data_dir, PATHS.models_dir, PATHS.logs_dir,
             PATHS.reports_dir, PATHS.shap_dir):
    os.makedirs(_dir, exist_ok=True)
