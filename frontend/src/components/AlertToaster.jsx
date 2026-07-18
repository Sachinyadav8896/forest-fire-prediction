import React, { useEffect, useState, useCallback } from "react";
import { getRecentAlerts } from "../services/api";
import { formatPercent } from "../services/riskUtils";

export default function AlertToaster() {
  const [visibleAlert, setVisibleAlert] = useState(null);
  const [seenIds, setSeenIds] = useState(() => new Set());

  const poll = useCallback(async () => {
    try {
      const alerts = await getRecentAlerts(5);
      const fresh = alerts.find((a) => !seenIds.has(a.id) && a.status === "sent");
      if (fresh) {
        setSeenIds((prev) => new Set(prev).add(fresh.id));
        setVisibleAlert(fresh);
        if (typeof Notification !== "undefined" && Notification.permission === "granted") {
          new Notification(`Fire risk: ${fresh.risk_level}`, {
            body: `${fresh.city_name || "A monitored location"} reached ${formatPercent(fresh.fire_probability)} probability.`,
          });
        }
        setTimeout(() => setVisibleAlert(null), 8000);
      }
    } catch {
      // silent: alert polling is best-effort
    }
  }, [seenIds]);

  useEffect(() => {
    if (typeof Notification !== "undefined" && Notification.permission === "default") {
      Notification.requestPermission();
    }
    const interval = setInterval(poll, 15000);
    return () => clearInterval(interval);
  }, [poll]);

  if (!visibleAlert) return null;

  return (
    <div className="fixed top-4 right-4 z-50 bg-char-surface border border-risk-veryhigh rounded-lg px-4 py-3 shadow-lg shadow-black/40 max-w-xs animate-pulse">
      <p className="font-display font-bold tracking-wide text-risk-veryhigh text-sm">
        🔥 {visibleAlert.risk_level.toUpperCase()} RISK ALERT
      </p>
      <p className="text-xs font-mono text-ink-muted mt-1">
        {visibleAlert.city_name || "Monitored location"} · {formatPercent(visibleAlert.fire_probability)} probability
      </p>
    </div>
  );
}
