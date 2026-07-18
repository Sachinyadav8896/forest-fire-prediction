export const RISK_LEVELS = [
  { label: "Low", color: "#5B8C5B", threshold: 0.0 },
  { label: "Moderate", color: "#C9A227", threshold: 0.2 },
  { label: "High", color: "#D97B29", threshold: 0.4 },
  { label: "Very High", color: "#C24A1F", threshold: 0.6 },
  { label: "Extreme", color: "#A61C1C", threshold: 0.85 },
];

export function riskColorForLabel(label) {
  const found = RISK_LEVELS.find((r) => r.label === label);
  return found ? found.color : "#8C867A";
}

export function riskColorForProbability(p) {
  const sorted = [...RISK_LEVELS].reverse();
  const match = sorted.find((r) => p >= r.threshold);
  return (match || RISK_LEVELS[0]).color;
}

export function formatPercent(p) {
  return `${(p * 100).toFixed(1)}%`;
}

export function formatTimestamp(ts) {
  if (!ts) return "—";
  const d = new Date(ts);
  return d.toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}
