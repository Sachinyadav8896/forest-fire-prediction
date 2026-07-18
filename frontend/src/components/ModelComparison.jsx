import React, { useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from "recharts";

const METRIC_OPTIONS = [
  { key: "f1_score", label: "F1 Score" },
  { key: "accuracy", label: "Accuracy" },
  { key: "roc_auc", label: "ROC AUC" },
  { key: "precision", label: "Precision" },
  { key: "recall", label: "Recall" },
];

const BAR_PALETTE = ["#E8542C", "#D97B29", "#C9A227", "#5B8C5B", "#4A8C82", "#6B8CC2", "#9A6BC2", "#C26BA0"];

export default function ModelComparison({ data = [] }) {
  const [metric, setMetric] = useState("f1_score");

  if (!data.length) {
    return (
      <div className="bg-char-surface border border-char-border rounded-lg p-4">
        <h3 className="font-display text-lg font-bold tracking-wide mb-1">MODEL COMPARISON</h3>
        <p className="text-ink-faint text-sm font-mono">
          No comparison report yet. Run backend/training/train_models.py first.
        </p>
      </div>
    );
  }

  const sorted = [...data].sort((a, b) => (b[metric] || 0) - (a[metric] || 0));
  const best = sorted[0]?.model_name;

  return (
    <div className="bg-char-surface border border-char-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <h3 className="font-display text-lg font-bold tracking-wide">MODEL COMPARISON</h3>
        <div className="flex text-[11px] font-mono rounded overflow-hidden border border-char-border">
          {METRIC_OPTIONS.map((m) => (
            <button
              key={m.key}
              onClick={() => setMetric(m.key)}
              className={`px-2.5 py-1 uppercase tracking-wide transition-colors ${
                metric === m.key ? "bg-ember text-char-950" : "text-ink-muted hover:text-ink"
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={sorted} layout="vertical" margin={{ left: 20, right: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2C2822" horizontal={false} />
          <XAxis type="number" domain={[0, 1]} stroke="#8C867A" fontSize={11} fontFamily="IBM Plex Mono" />
          <YAxis
            type="category" dataKey="model_name" stroke="#8C867A" fontSize={11}
            fontFamily="IBM Plex Mono" width={130}
          />
          <Tooltip
            contentStyle={{ background: "#1B1815", border: "1px solid #2C2822", fontFamily: "IBM Plex Mono", fontSize: 12 }}
            formatter={(v) => v.toFixed?.(4) ?? v}
          />
          <Bar dataKey={metric} radius={[0, 4, 4, 0]}>
            {sorted.map((entry, i) => (
              <Cell key={entry.model_name} fill={BAR_PALETTE[i % BAR_PALETTE.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <p className="text-[11px] font-mono text-ink-faint mt-2">
        Best on {METRIC_OPTIONS.find((m) => m.key === metric)?.label}: <span className="text-ember">{best}</span>
      </p>
    </div>
  );
}
