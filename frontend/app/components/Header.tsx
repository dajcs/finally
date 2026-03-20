"use client";
import { ConnectionStatus } from "../hooks/usePrices";

const STATUS_COLORS: Record<ConnectionStatus, string> = {
  connected: "#3fb950",
  reconnecting: "#ecad0a",
  disconnected: "#f85149",
};

interface HeaderProps {
  totalValue: number;
  cash: number;
  connectionStatus: ConnectionStatus;
}

export default function Header({ totalValue, cash, connectionStatus }: HeaderProps) {
  return (
    <header className="flex items-center justify-between px-4 py-2 border-b border-[#21262d] bg-[#0d1117]">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-bold text-[#ecad0a] tracking-wide">FinAlly</h1>
      </div>
      <div className="flex items-center gap-6 text-sm">
        <div>
          <span className="text-gray-400 mr-1">Portfolio:</span>
          <span className="text-white font-mono font-semibold">${totalValue.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
        </div>
        <div>
          <span className="text-gray-400 mr-1">Cash:</span>
          <span className="text-white font-mono">${cash.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
        </div>
        <div
          className="w-2.5 h-2.5 rounded-full"
          style={{ backgroundColor: STATUS_COLORS[connectionStatus] }}
          title={connectionStatus}
        />
      </div>
    </header>
  );
}
