import React from "react";

const FEATURE_LABELS = {
  temperature: "Temperature",
  humidity: "Humidity",
  wind_speed: "Wind speed",
  rainfall: "Rainfall",
  pressure: "Pressure",
  ndvi: "Vegetation index (NDVI)",
  land_surface_temp: "Land surface temp",
  elevation: "Elevation",
  slope: "Slope",
  soil_moisture: "Soil moisture",
  fire_weather_index: "Fire Weather Index",
  heat_index: "Heat index",
  vegetation_dryness_score: "Vegetation dryness",
  temp_humidity_ratio: "Temp/Humidity ratio",
  wind_risk_score: "Wind risk score",
  slope_risk: "Slope risk",
  historical_fire_frequency: "Historical fire frequency",
  region: "Region",
  season: "Season",
  land_cover_type: "Land cover type",
};

export default function ShapExplanation({ topFeatures = [] }) {
  if (!topFeatures.length) {
    return (
      <div className="bg-char-surface border border-char-border rounded-lg p-4">
        <h3 className="font-display text-lg font-bold tracking-wide mb-1">WHY THIS SCORE</h3>
        <p className="text-ink-faint text-sm font-mono">Run a prediction to see the drivers.</p>
      </div>
    );
  }

  const maxAbs = Math.max(...topFeatures.map((f) => Math.abs(f.impact)), 0.0001);

  return (
    <div className="bg-char-surface border border-char-border rounded-lg p-4">
      <h3 className="font-display text-lg font-bold tracking-wide mb-3">WHY THIS SCORE</h3>
      <div className="space-y-2.5">
        {topFeatures.map((f) => {
          const pct = (Math.abs(f.impact) / maxAbs) * 100;
          const pushesUp = f.impact > 0;
          return (
            <div key={f.feature}>
              <div className="flex justify-between text-xs font-mono mb-1">
                <span className="text-ink-muted">{FEATURE_LABELS[f.feature] || f.feature}</span>
                <span className={pushesUp ? "text-risk-veryhigh" : "text-risk-low"}>
                  {pushesUp ? "+" : ""}{f.impact.toFixed(3)}
                </span>
              </div>
              <div className="h-1.5 bg-char-950 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${pct}%`,
                    background: pushesUp ? "#C24A1F" : "#5B8C5B",
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
      <p className="text-[11px] text-ink-faint font-mono mt-3 leading-relaxed">
        Red bars push the fire risk up. Green bars pull it down. Length is the size of the effect (SHAP value).
      </p>
    </div>
  );
}
