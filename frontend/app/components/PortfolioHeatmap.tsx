"use client";
import { Position } from "../types";

interface PortfolioHeatmapProps {
  positions: Position[];
}

function pnlColor(pnlPct: number): string {
  if (pnlPct > 0) {
    const intensity = Math.min(pnlPct / 10, 1);
    return `rgba(63, 185, 80, ${0.2 + intensity * 0.6})`;
  } else if (pnlPct < 0) {
    const intensity = Math.min(Math.abs(pnlPct) / 10, 1);
    return `rgba(248, 81, 73, ${0.2 + intensity * 0.6})`;
  }
  return "rgba(139, 148, 158, 0.2)";
}

export default function PortfolioHeatmap({ positions }: PortfolioHeatmapProps) {
  if (positions.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 text-sm">
        No open positions
      </div>
    );
  }

  const totalValue = positions.reduce((sum, p) => sum + p.current_price * p.quantity, 0);

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider border-b border-[#21262d]">
        Portfolio Heatmap
      </div>
      <div className="flex-1 flex flex-wrap p-1 gap-1 min-h-0 overflow-hidden">
        {positions.map((p) => {
          const weight = totalValue > 0 ? (p.current_price * p.quantity) / totalValue : 1 / positions.length;
          const minWidth = Math.max(weight * 100, 15);
          return (
            <div
              key={p.ticker}
              className="flex flex-col items-center justify-center rounded text-center"
              style={{
                backgroundColor: pnlColor(p.pnl_pct),
                flexBasis: `${minWidth}%`,
                flexGrow: weight,
                minHeight: "40px",
              }}
            >
              <span className="text-xs font-bold text-white">{p.ticker}</span>
              <span className={`text-xs font-mono ${p.pnl_pct >= 0 ? "text-[#3fb950]" : "text-[#f85149]"}`}>
                {p.pnl_pct >= 0 ? "+" : ""}{p.pnl_pct.toFixed(1)}%
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
