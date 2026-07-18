import React, { useState } from "react";

export default function LocationSearch({ onSearch, loading }) {
  const [mode, setMode] = useState("city");
  const [city, setCity] = useState("");
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [alertEmail, setAlertEmail] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    if (mode === "city" && city.trim()) {
      onSearch({ cityName: city.trim(), alertEmail: alertEmail.trim() || undefined });
    } else if (mode === "coords" && lat && lon) {
      onSearch({ latitude: parseFloat(lat), longitude: parseFloat(lon), alertEmail: alertEmail.trim() || undefined });
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-char-surface border border-char-border rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-xl font-bold tracking-wide text-ink">CHECK A LOCATION</h2>
        <div className="flex text-[11px] font-mono rounded overflow-hidden border border-char-border">
          {["city", "coords"].map((m) => (
            <button
              type="button"
              key={m}
              onClick={() => setMode(m)}
              className={`px-2.5 py-1 uppercase tracking-wide transition-colors ${
                mode === m ? "bg-ember text-char-950" : "text-ink-muted hover:text-ink"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {mode === "city" ? (
        <input
          type="text"
          value={city}
          onChange={(e) => setCity(e.target.value)}
          placeholder="City name, e.g. Shimla"
          className="w-full bg-char-950 border border-char-border rounded px-3 py-2 text-sm font-mono text-ink placeholder:text-ink-faint focus:border-ember outline-none"
        />
      ) : (
        <div className="flex gap-2">
          <input
            type="number" step="any" value={lat} onChange={(e) => setLat(e.target.value)}
            placeholder="Latitude"
            className="w-1/2 bg-char-950 border border-char-border rounded px-3 py-2 text-sm font-mono text-ink placeholder:text-ink-faint focus:border-ember outline-none"
          />
          <input
            type="number" step="any" value={lon} onChange={(e) => setLon(e.target.value)}
            placeholder="Longitude"
            className="w-1/2 bg-char-950 border border-char-border rounded px-3 py-2 text-sm font-mono text-ink placeholder:text-ink-faint focus:border-ember outline-none"
          />
        </div>
      )}

      <input
        type="email"
        value={alertEmail}
        onChange={(e) => setAlertEmail(e.target.value)}
        placeholder="Alert email (optional)"
        className="w-full bg-char-950 border border-char-border rounded px-3 py-2 text-sm font-mono text-ink placeholder:text-ink-faint focus:border-ember outline-none"
      />

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-ember hover:bg-ember-bright disabled:opacity-50 text-char-950 font-display font-bold tracking-wide text-sm py-2.5 rounded transition-colors"
      >
        {loading ? "READING THE WIND…" : "RUN PREDICTION"}
      </button>
    </form>
  );
}
