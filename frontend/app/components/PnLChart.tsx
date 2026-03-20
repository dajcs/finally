"use client";
import { PortfolioSnapshot } from "../types";

interface PnLChartProps {
  snapshots: PortfolioSnapshot[];
}

export default function PnLChart({ snapshots }: PnLChartProps) {
  if (snapshots.length < 2) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 text-sm">
        Collecting portfolio data...
      </div>
    );
  }

  const values = snapshots.map((s) => s.total_value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const width = 400;
  const height = 80;

  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * width;
      const y = height - ((v - min) / range) * (height - 4) - 2;
      return `${x},${y}`;
    })
    .join(" ");

  const trend = values[values.length - 1] >= values[0];

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider border-b border-[#21262d]">
        P&L
      </div>
      <div className="flex-1 flex items-center justify-center p-2">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full" preserveAspectRatio="none">
          <polyline
            fill="none"
            stroke={trend ? "#3fb950" : "#f85149"}
            strokeWidth="2"
            points={points}
          />
        </svg>
      </div>
    </div>
  );
}
