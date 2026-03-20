"use client";
import { Position } from "../types";

interface PositionsTableProps {
  positions: Position[];
}

export default function PositionsTable({ positions }: PositionsTableProps) {
  if (positions.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 text-sm">
        No positions
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider border-b border-[#21262d]">
        Positions
      </div>
      <div className="flex-1 overflow-y-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-gray-500 border-b border-[#21262d]">
              <th className="text-left px-2 py-1">Ticker</th>
              <th className="text-right px-2 py-1">Qty</th>
              <th className="text-right px-2 py-1">Avg Cost</th>
              <th className="text-right px-2 py-1">Price</th>
              <th className="text-right px-2 py-1">P&L</th>
              <th className="text-right px-2 py-1">%</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((p) => (
              <tr key={p.ticker} className="border-b border-[#21262d]/50 hover:bg-[#1a1a2e]">
                <td className="px-2 py-1 font-semibold text-white">{p.ticker}</td>
                <td className="px-2 py-1 text-right font-mono text-gray-300">{p.quantity}</td>
                <td className="px-2 py-1 text-right font-mono text-gray-300">${p.avg_cost.toFixed(2)}</td>
                <td className="px-2 py-1 text-right font-mono text-white">${p.current_price.toFixed(2)}</td>
                <td className={`px-2 py-1 text-right font-mono ${p.unrealized_pnl >= 0 ? "text-[#3fb950]" : "text-[#f85149]"}`}>
                  ${p.unrealized_pnl.toFixed(2)}
                </td>
                <td className={`px-2 py-1 text-right font-mono ${p.pnl_pct >= 0 ? "text-[#3fb950]" : "text-[#f85149]"}`}>
                  {p.pnl_pct >= 0 ? "+" : ""}{p.pnl_pct.toFixed(2)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
