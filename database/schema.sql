-- =====================================================================
-- schema.sql
-- Forest Fire Prediction System — MySQL schema
-- Run: mysql -u root -p < database/schema.sql
-- =====================================================================

CREATE DATABASE IF NOT EXISTS forest_fire_db
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE forest_fire_db;

-- ---------------------------------------------------------------------
-- locations: every place a prediction has ever been requested for
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS locations (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    latitude        DECIMAL(9,6) NOT NULL,
    longitude       DECIMAL(9,6) NOT NULL,
    city_name       VARCHAR(120),
    region          VARCHAR(120),
    country         VARCHAR(80),
    elevation       FLOAT,
    slope           FLOAT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_lat_lng (latitude, longitude)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- weather_snapshots: raw weather pulled from OpenWeather at prediction time
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS weather_snapshots (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    location_id         INT NOT NULL,
    temperature         FLOAT,
    humidity            FLOAT,
    wind_speed          FLOAT,
    rainfall            FLOAT,
    pressure            FLOAT,
    ndvi                FLOAT,
    land_surface_temp   FLOAT,
    soil_moisture       FLOAT,
    source              VARCHAR(50) DEFAULT 'openweather',
    fetched_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE,
    INDEX idx_location_time (location_id, fetched_at)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- predictions: one row per model inference
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS predictions (
    id                      INT AUTO_INCREMENT PRIMARY KEY,
    location_id             INT NOT NULL,
    weather_snapshot_id     INT,
    model_name              VARCHAR(80) NOT NULL,
    fire_probability        FLOAT NOT NULL,
    risk_level              ENUM('Low','Moderate','High','Very High','Extreme') NOT NULL,
    fire_weather_index      FLOAT,
    top_feature_1           VARCHAR(80),
    top_feature_1_impact    FLOAT,
    top_feature_2           VARCHAR(80),
    top_feature_2_impact    FLOAT,
    top_feature_3           VARCHAR(80),
    top_feature_3_impact    FLOAT,
    shap_values_json        JSON,
    predicted_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE,
    FOREIGN KEY (weather_snapshot_id) REFERENCES weather_snapshots(id) ON DELETE SET NULL,
    INDEX idx_predicted_at (predicted_at),
    INDEX idx_risk_level (risk_level)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- alerts: fired whenever probability crosses the configured threshold
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alerts (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    prediction_id   INT NOT NULL,
    channel         ENUM('email','sms','browser') NOT NULL,
    recipient       VARCHAR(255),
    status          ENUM('pending','sent','failed') DEFAULT 'pending',
    sent_at         TIMESTAMP NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prediction_id) REFERENCES predictions(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- model_metrics: snapshot of the model comparison table, for the dashboard
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS model_metrics (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    model_name          VARCHAR(80) NOT NULL,
    accuracy            FLOAT,
    precision_score     FLOAT,
    recall_score        FLOAT,
    f1_score            FLOAT,
    roc_auc             FLOAT,
    training_time_sec   FLOAT,
    prediction_time_sec FLOAT,
    is_best_model       BOOLEAN DEFAULT FALSE,
    trained_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- helpful view: latest prediction per location (feeds the map)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW latest_predictions_by_location AS
SELECT p.*
FROM predictions p
INNER JOIN (
    SELECT location_id, MAX(predicted_at) AS max_time
    FROM predictions
    GROUP BY location_id
) latest ON p.location_id = latest.location_id AND p.predicted_at = latest.max_time;
