import React from "react";
import { riskColorForProbability, formatPercent } from "../services/riskUtils";

/**
 * RiskDial — the dashboard's signature element. A hand-drawn-feeling
 * topographic dial (concentric arcs like elevation contours) rather than a
 * generic donut chart. The needle sweeps to the fire probability; the arc
 * color encodes the risk band.
 */
export default function RiskDial({ probability = 0, riskLevel = "Low", modelName }) {
  const size = 240;
  const cx = size / 2;
  const cy = size / 2;
  const radius = 92;
  const startAngle = -220;
  const sweepAngle = 260;
  const angle = startAngle + sweepAngle * Math.min(Math.max(probability, 0), 1);
  const color = riskColorForProbability(probability);

  const toXY = (deg, r) => {
    const rad = (deg * Math.PI) / 180;
    return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)];
  };

  const arcPath = (r, a0, a1) => {
    const [x0, y0] = toXY(a0, r);
    const [x1, y1] = toXY(a1, r);
    const largeArc = a1 - a0 > 180 ? 1 : 0;
    return `M ${x0} ${y0} A ${r} ${r} 0 ${largeArc} 1 ${x1} ${y1}`;
  };

  const [needleX, needleY] = toXY(angle, radius - 14);

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* topographic contour rings, faint */}
        {[radius + 24, radius + 12].map((r) => (
          <path
            key={r}
            d={arcPath(r, startAngle, startAngle + sweepAngle)}
            fill="none"
            stroke="#2C2822"
            strokeWidth="1"
          />
        ))}
        {/* track */}
        <path
          d={arcPath(radius, startAngle, startAngle + sweepAngle)}
          fill="none"
          stroke="#2C2822"
          strokeWidth="10"
          strokeLinecap="round"
        />
        {/* filled progress arc */}
        <path
          d={arcPath(radius, startAngle, angle)}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          style={{ transition: "d 0.6s ease, stroke 0.6s ease" }}
        />
        {/* needle */}
        <line
          x1={cx} y1={cy} x2={needleX} y2={needleY}
          stroke={color} strokeWidth="2.5" strokeLinecap="round"
          style={{ transition: "x2 0.6s ease, y2 0.6s ease" }}
        />
        <circle cx={cx} cy={cy} r="5" fill={color} />

        <text x={cx} y={cy - 16} textAnchor="middle" className="fill-ink" style={{ fontFamily: "'Big Shoulders Display'", fontSize: 46, fontWeight: 700 }}>
          {formatPercent(probability)}
        </text>
        <text x={cx} y={cy + 12} textAnchor="middle" fill={color} style={{ fontFamily: "'IBM Plex Mono'", fontSize: 13, letterSpacing: 2, textTransform: "uppercase" }}>
          {riskLevel} risk
        </text>
      </svg>
      {modelName && (
        <p className="text-ink-faint font-mono text-[11px] tracking-wide mt-1">
          model: {modelName}
        </p>
      )}
    </div>
  );
}
