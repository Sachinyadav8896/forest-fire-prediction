import React, { useEffect, useState, useCallback } from "react";
import Header from "../components/Header";
import LocationSearch from "../components/LocationSearch";
import RiskDial from "../components/RiskDial";
import ShapExplanation from "../components/ShapExplanation";
import RiskMap from "../components/RiskMap";
import ModelComparison from "../components/ModelComparison";
import RecentPredictions from "../components/RecentPredictions";
import AlertToaster from "../components/AlertToaster";
import {
  predictLive, getMapPredictions, getRecentPredictions, getModelComparison, extractErrorMessage,
} from "../services/api";

export default function Dashboard() {
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [mapPredictions, setMapPredictions] = useState([]);
  const [recent, setRecent] = useState([]);
  const [comparison, setComparison] = useState([]);
  const [focusLocation, setFocusLocation] = useState(null);

  const refreshLists = useCallback(async () => {
    try {
      const [mapData, recentData] = await Promise.all([
        getMapPredictions(), getRecentPredictions(30),
      ]);
      setMapPredictions(mapData);
      setRecent(recentData);
    } catch {
      // dashboards should stay usable even if history/map calls fail
    }
  }, []);

  useEffect(() => {
    refreshLists();
    getModelComparison().then(setComparison).catch(() => {});
    const interval = setInterval(refreshLists, 30000);
    return () => clearInterval(interval);
  }, [refreshLists]);

  async function handleSearch(params) {
    setLoading(true);
    setError(null);
    try {
      const result = await predictLive(params);
      setPrediction(result);
      if (result.weather?.latitude) {
        setFocusLocation([result.weather.latitude, result.weather.longitude]);
      }
      refreshLists();
    } catch (e) {
      setError(extractErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }

  function handleSelectRecent(p) {
    setFocusLocation([p.latitude, p.longitude]);
  }

  return (
    <div className="h-screen flex flex-col contour-bg">
      <AlertToaster />
      <Header modelName={prediction?.model_name} />

      <main className="flex-1 grid grid-cols-1 lg:grid-cols-[360px_1fr_320px] gap-4 p-4 min-h-0">
        {/* Left rail: search + risk dial + SHAP */}
        <div className="flex flex-col gap-4 min-h-0 overflow-y-auto scrollbar-thin">
          <LocationSearch onSearch={handleSearch} loading={loading} />

          {error && (
            <div className="bg-risk-extreme/10 border border-risk-extreme/40 rounded-lg p-3 text-sm font-mono text-risk-veryhigh">
              {error}
            </div>
          )}

          <div className="bg-char-surface border border-char-border rounded-lg p-5 flex justify-center">
            <RiskDial
              probability={prediction?.fire_probability ?? 0}
              riskLevel={prediction?.risk_level ?? "Low"}
              modelName={prediction?.model_name}
            />
          </div>

          <ShapExplanation topFeatures={prediction?.top_features} />
        </div>

        {/* Center: map */}
        <div className="min-h-[320px] lg:min-h-0">
          <RiskMap predictions={mapPredictions} focusLocation={focusLocation} />
        </div>

        {/* Right rail: recent + model comparison */}
        <div className="flex flex-col gap-4 min-h-0 overflow-y-auto scrollbar-thin">
          <RecentPredictions predictions={recent} onSelect={handleSelectRecent} />
          <ModelComparison data={comparison} />
        </div>
      </main>
    </div>
  );
}
