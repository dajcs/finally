"use client";
import { useState } from "react";
import { executeTrade } from "../lib/api";

interface TradeBarProps {
  onTradeExecuted: () => void;
  selectedTicker?: string | null;
}

export default function TradeBar({ onTradeExecuted, selectedTicker }: TradeBarProps) {
  const [ticker, setTicker] = useState("");
  const [quantity, setQuantity] = useState("");
  const [status, setStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const activeTicker = ticker || selectedTicker || "";

  const handleTrade = async (side: "buy" | "sell") => {
    const t = activeTicker.trim().toUpperCase();
    const q = parseFloat(quantity);
    if (!t || isNaN(q) || q <= 0) {
      setStatus({ type: "error", message: "Enter valid ticker and quantity" });
      return;
    }
    try {
      await executeTrade(t, q, side);
      setStatus({ type: "success", message: `${side === "buy" ? "Bought" : "Sold"} ${q} ${t}` });
      setTicker("");
      setQuantity("");
      onTradeExecuted();
    } catch (err: unknown) {
      setStatus({ type: "error", message: err instanceof Error ? err.message : "Trade failed" });
    }
    setTimeout(() => setStatus(null), 3000);
  };

  return (
    <div className="flex flex-col border-t border-[#21262d]">
      <div className="px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider border-b border-[#21262d]">
        Trade
      </div>
      <div className="flex items-center gap-2 p-2">
        <input
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          placeholder={selectedTicker || "Ticker"}
          className="w-20 bg-[#1a1a2e] text-white text-xs px-2 py-1.5 rounded border border-[#21262d] outline-none focus:border-[#209dd7] uppercase"
        />
        <input
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          placeholder="Qty"
          type="number"
          step="any"
          className="w-20 bg-[#1a1a2e] text-white text-xs px-2 py-1.5 rounded border border-[#21262d] outline-none focus:border-[#209dd7]"
        />
        <button
          onClick={() => handleTrade("buy")}
          className="bg-[#753991] text-white text-xs px-3 py-1.5 rounded font-semibold hover:brightness-110"
        >
          Buy
        </button>
        <button
          onClick={() => handleTrade("sell")}
          className="bg-[#f85149] text-white text-xs px-3 py-1.5 rounded font-semibold hover:brightness-110"
        >
          Sell
        </button>
        {status && (
          <span className={`text-xs ${status.type === "success" ? "text-[#3fb950]" : "text-[#f85149]"}`}>
            {status.message}
          </span>
        )}
      </div>
    </div>
  );
}
