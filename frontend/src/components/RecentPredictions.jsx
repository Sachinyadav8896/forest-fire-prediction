import React from "react";
import { riskColorForLabel, formatPercent, formatTimestamp } from "../services/riskUtils";

export default function RecentPredictions({ predictions = [], onSelect }) {
  return (
    <div className="bg-char-surface border border-char-border rounded-lg p-4 flex flex-col min-h-0">
      <h3 className="font-display text-lg font-bold tracking-wide mb-3">RECENT READINGS</h3>
      <div className="space-y-1.5 overflow-y-auto scrollbar-thin pr-1">
        {predictions.length === 0 && (
          <p className="text-ink-faint text-sm font-mono">No predictions yet.</p>
        )}
        {predictions.map((p) => {
          const color = riskColorForLabel(p.risk_level);
          return (
            <button
              key={p.id}
              onClick={() => onSelect?.(p)}
              className="w-full flex items-center justify-between text-left px-2.5 py-2 rounded hover:bg-char-950/60 transition-colors group"
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="w-2 h-2 rounded-full shrink-0" style={{ background: color }} />
                <span className="truncate text-sm text-ink group-hover:text-ember transition-colors">
                  {p.city_name || p.region || `${p.latitude?.toFixed(2)}, ${p.longitude?.toFixed(2)}`}
                </span>
              </div>
              <div className="text-right shrink-0 ml-2">
                <p className="font-mono text-xs" style={{ color }}>{formatPercent(p.fire_probability)}</p>
                <p className="font-mono text-[10px] text-ink-faint">{formatTimestamp(p.predicted_at)}</p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
