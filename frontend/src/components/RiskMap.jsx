import React from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import { riskColorForLabel, formatPercent, formatTimestamp } from "../services/riskUtils";

function FlyTo({ center }) {
  const map = useMap();
  React.useEffect(() => {
    if (center) map.flyTo(center, 8, { duration: 1.1 });
  }, [center, map]);
  return null;
}

export default function RiskMap({ predictions = [], focusLocation }) {
  const center = focusLocation || [20.5937, 78.9629]; // default: India centroid

  return (
    <div className="h-full w-full rounded-lg overflow-hidden border border-char-border">
      <MapContainer center={center} zoom={5} scrollWheelZoom style={{ height: "100%", width: "100%" }}>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; OpenStreetMap contributors'
        />
        {focusLocation && <FlyTo center={focusLocation} />}
        {predictions.map((p) => {
          const color = riskColorForLabel(p.risk_level);
          return (
            <CircleMarker
              key={p.id || `${p.latitude}-${p.longitude}`}
              center={[p.latitude, p.longitude]}
              radius={9}
              pathOptions={{ color, fillColor: color, fillOpacity: 0.75, weight: 2 }}
            >
              <Popup>
                <div className="font-mono text-xs">
                  <p className="font-bold" style={{ color }}>
                    {p.risk_level} · {formatPercent(p.fire_probability)}
                  </p>
                  <p>{p.city_name || p.region || "Unnamed location"}</p>
                  <p className="text-gray-500">{formatTimestamp(p.predicted_at)}</p>
                  <p className="text-gray-500">model: {p.model_name}</p>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}
