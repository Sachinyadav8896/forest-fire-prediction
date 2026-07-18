# Explainable Multi-Source Forest Fire Prediction and Risk Mapping System

## Status: Modules 1–6 complete — Structure, ML Pipeline, Database, Backend API, Frontend, Docker Deployment

This is being built incrementally, one production-ready module at a time, per the project plan.

## Completed so far

```
forest-fire-prediction/
├── config/
│   └── config.py                  # central config: paths, data schema, model + API + DB settings
├── backend/
│   ├── app.py                     # Flask entry point (factory, CORS, error handlers)
│   ├── api/
│   │   └── routes.py              # REST endpoints: predict, predict/live, map, models/compare, alerts
│   ├── utils/
│   │   ├── logger.py              # rotating file + console logger used everywhere
│   │   ├── preprocessing.py       # cleaning, encoding, scaling, SMOTE, leak-free split
│   │   ├── feature_engineering.py # FWI, heat index, dryness score, wind/slope risk, fire history
│   │   ├── db.py                  # MySQL connection pool + query helpers
│   │   ├── weather_service.py     # OpenWeather + NASA FIRMS live data fetching
│   │   ├── alert_service.py       # email + browser alert dispatch at >90% probability
│   │   └── prediction_service.py  # loads trained model, runs live inference + SHAP
│   ├── training/
│   │   └── train_models.py        # trains 8 models, compares, auto-selects best, runs SHAP
│   └── requirements.txt
├── database/
│   └── schema.sql                 # MySQL: locations, weather_snapshots, predictions, alerts, model_metrics
├── dataset/{raw,processed}/
├── models/saved/                  # trained .joblib models + best_model_meta.json land here
├── research/{reports,shap}/       # model_comparison.csv, SHAP importances land here
├── .env.example                   # all required environment variables
└── README.md
```

## What Module 2 already solves (vs. baseline papers)

| Limitation in prior work                 | How this module addresses it |
|---|---|
| Single ML algorithm                      | 8 models trained & compared: RF, XGBoost, LightGBM, CatBoost, ExtraTrees, GradientBoosting, Voting Ensemble, Stacking Ensemble |
| No explainability                        | SHAP TreeExplainer (global + per-sample) run automatically on the winning model |
| Class imbalance ignored                  | SMOTE applied **only to the training split** (val/test untouched — avoids the leakage bug common in baseline papers) |
| Weather-only features                    | Feature engineering module adds FWI, heat index, vegetation dryness (NDVI+rain), wind risk, slope risk, historical fire frequency |
| No model comparison table                | `research/reports/model_comparison.csv` — accuracy, precision, recall, F1, ROC-AUC, CV F1, train time, predict time |
| Arbitrary "best" model choice            | Deterministic rule: highest F1 → tie-break ROC-AUC → tie-break lowest false negatives |

## How to run this module

```bash
cd forest-fire-prediction
pip install -r backend/requirements.txt

# Place your merged historical dataset (Kaggle/UCI + weather + NDVI + elevation) at:
#   dataset/raw/fire_data.csv
# Required columns: temperature, humidity, wind_speed, rainfall, pressure,
# ndvi, elevation, slope, region, date, fire_occurred (0/1), plus any of
# DATA.categorical_features in config/config.py

python backend/training/train_models.py --data dataset/raw/fire_data.csv --target fire_occurred
```

Outputs:
- `models/saved/best_model.joblib` + `best_model_meta.json`
- `models/saved/<EachModelName>.joblib` (all 8, for the dashboard's model-comparison page)
- `research/reports/model_comparison.csv`
- `research/shap/<BestModel>_global_importance.csv` + `_shap_values.npy`

## Module 3 — Database

`database/schema.sql` creates 5 tables (`locations`, `weather_snapshots`, `predictions`, `alerts`, `model_metrics`) plus a `latest_predictions_by_location` view that feeds the map dashboard directly. Foreign keys and indexes are in place for the query patterns the API actually uses.

```bash
mysql -u root -p < database/schema.sql
```

## Module 4 — Backend API

Setup:
```bash
cp .env.example .env   # fill in OPENWEATHER_API_KEY, DB credentials, etc.
pip install -r backend/requirements.txt
python backend/app.py  # runs on http://localhost:5000
```

Endpoints:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness check |
| POST | `/api/predict` | predict from a raw feature dict you supply |
| POST | `/api/predict/live` | fetch live OpenWeather data by `{latitude, longitude}` or `{city_name}`, then predict |
| GET | `/api/predictions/recent?limit=50` | recent prediction history |
| GET | `/api/predictions/map` | latest prediction per location, for the Leaflet map |
| GET | `/api/models/compare` | the model_comparison.csv from training, as JSON |
| GET | `/api/alerts/recent?limit=20` | recent alerts, for the frontend to poll and show browser notifications |

Every predict endpoint automatically: engineers features → scales/encodes with the exact training-time artifacts → runs the best model → runs SHAP for a local explanation → persists to MySQL → dispatches an alert if probability ≥ 90%.

All 11 backend Python files have been syntax-verified (`py_compile`) as part of this build.

## Module 5 — React + Tailwind Frontend

Design: a dark "ranger's terrain map" aesthetic — char-black background, ember-orange accent, a topographic contour texture, condensed display type for headers and monospace for all data readouts (coordinates, percentages, timestamps). The signature element is `RiskDial` — a hand-styled radial gauge with contour rings, not a generic donut chart.

```
frontend/
├── index.html
├── package.json / vite.config.js / tailwind.config.js / postcss.config.js
└── src/
    ├── main.jsx, App.jsx, index.css
    ├── pages/Dashboard.jsx          # map-centric 3-column layout
    ├── components/
    │   ├── Header.jsx               # brand + active model + live indicator
    │   ├── LocationSearch.jsx       # city or lat/lon input, optional alert email
    │   ├── RiskDial.jsx             # signature radial gauge
    │   ├── ShapExplanation.jsx      # local SHAP tornado bars ("why this score")
    │   ├── RiskMap.jsx              # Leaflet map, color-coded risk markers
    │   ├── ModelComparison.jsx      # Recharts bar chart, switchable metric
    │   ├── RecentPredictions.jsx    # scrollable history feed
    │   └── AlertToaster.jsx         # polls /api/alerts/recent, fires browser Notification
    └── services/
        ├── api.js                  # axios client for every backend endpoint
        └── riskUtils.js             # risk color/label/formatting helpers
```

Setup:
```bash
cd frontend
npm install
npm run dev   # http://localhost:5173, proxies /api to the Flask backend on :5000
```

All 13 source files were checked for structural (bracket/brace) integrity as part of this build. Full JSX compilation will happen the first time you run `npm run dev` or `npm run build`, since this sandbox has no network access to install the toolchain.

## Module 6 — Docker + Deployment

```
├── docker-compose.yml       # orchestrates mysql, backend, frontend, and an optional trainer job
├── .dockerignore
├── backend/Dockerfile       # gunicorn-served Flask API
├── backend/Dockerfile.train # one-off training job image
└── frontend/
    ├── Dockerfile           # multi-stage: vite build -> nginx serve
    └── nginx.conf           # SPA fallback + /api/ reverse proxy to the backend container
```

**Deploy the full stack:**
```bash
cp .env.example .env        # fill in OPENWEATHER_API_KEY, DB_PASSWORD, SMTP creds, etc.

# 1. Train models once (writes into the shared `models_data` volume)
#    Put your dataset at dataset/raw/fire_data.csv first.
docker compose run --rm trainer

# 2. Bring up MySQL + backend + frontend
docker compose up -d --build
 
# Frontend:  http://localhost:8080
# Backend:   http://localhost:5000/api/health
# MySQL:     localhost:3306
```

`docker-compose.yml` uses named volumes (`mysql_data`, `models_data`, `reports_data`) so trained models and the database persist across `docker compose down`/`up` cycles, and the schema in `database/schema.sql` is auto-applied to MySQL on first boot via its `docker-entrypoint-initdb.d` mount. The backend container has a healthcheck against `/api/health`; the frontend's nginx proxies every `/api/*` call to the `backend` service by container name, so no CORS/URL configuration is needed at deploy time.

## Coming next (bonus modules, optional)

7. 24-hour probability forecasting
8. Historical fire trend charts
9. PDF report generation
10. Satellite image upload for prediction

The core system (Modules 1–6) is now feature-complete end-to-end: data pipeline → 8-model comparison → SHAP explainability → live weather → REST API → MySQL persistence → alerts → React dashboard with map → Docker deployment. Say "continue" for any of the bonus modules, or tell me what to prioritize.
