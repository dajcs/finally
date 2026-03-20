"use client";
import { useState, useRef, useEffect } from "react";
import { PriceUpdate } from "../types";
import { addToWatchlist, removeFromWatchlist } from "../lib/api";
import Sparkline from "./Sparkline";

interface WatchlistPanelProps {
  prices: Record<string, PriceUpdate>;
  sparklines: Record<string, number[]>;
  watchlistTickers: string[];
  selectedTicker: string | null;
  onSelectTicker: (ticker: string) => void;
  onWatchlistChange: () => void;
}

export default function WatchlistPanel({
  prices,
  sparklines,
  watchlistTickers,
  selectedTicker,
  onSelectTicker,
  onWatchlistChange,
}: WatchlistPanelProps) {
  const [newTicker, setNewTicker] = useState("");
  const [flashState, setFlashState] = useState<Record<string, "up" | "down" | null>>({});
  const prevPrices = useRef<Record<string, number>>({});

  useEffect(() => {
    const flashes: Record<string, "up" | "down" | null> = {};
    for (const ticker of watchlistTickers) {
      const p = prices[ticker];
      if (!p) continue;
      const prev = prevPrices.current[ticker];
      if (prev !== undefined && prev !== p.price) {
        flashes[ticker] = p.price > prev ? "up" : "down";
      }
      prevPrices.current[ticker] = p.price;
    }
    if (Object.keys(flashes).length > 0) {
      setFlashState((prev) => ({ ...prev, ...flashes }));
      const timer = setTimeout(() => {
        setFlashState((prev) => {
          const next = { ...prev };
          for (const k of Object.keys(flashes)) next[k] = null;
          return next;
        });
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [prices, watchlistTickers]);

  const handleAdd = async () => {
    const t = newTicker.trim().toUpperCase();
    if (!t) return;
    await addToWatchlist(t);
    setNewTicker("");
    onWatchlistChange();
  };

  const handleRemove = async (ticker: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await removeFromWatchlist(ticker);
    onWatchlistChange();
  };

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider border-b border-[#21262d]">
        Watchlist
      </div>
      <div className="flex-1 overflow-y-auto">
        {watchlistTickers.map((ticker) => {
          const p = prices[ticker];
          const flash = flashState[ticker];
          const bgFlash =
            flash === "up" ? "bg-[#3fb950]/20" : flash === "down" ? "bg-[#f85149]/20" : "";
          const changeColor = p && p.change_percent >= 0 ? "text-[#3fb950]" : "text-[#f85149]";

          return (
            <div
              key={ticker}
              onClick={() => onSelectTicker(ticker)}
              className={`flex items-center justify-between px-3 py-1.5 cursor-pointer border-b border-[#21262d]/50 transition-colors duration-500 hover:bg-[#1a1a2e] ${
                selectedTicker === ticker ? "bg-[#1a1a2e]" : ""
              } ${bgFlash}`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-sm font-semibold text-white w-12">{ticker}</span>
                <Sparkline data={sparklines[ticker] || []} />
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <div className="text-right">
                  <div className="text-sm font-mono text-white">
                    {p ? p.price.toFixed(2) : "--"}
                  </div>
                  <div className={`text-xs font-mono ${changeColor}`}>
                    {p ? `${p.change_percent >= 0 ? "+" : ""}${p.change_percent.toFixed(2)}%` : ""}
                  </div>
                </div>
                <button
                  onClick={(e) => handleRemove(ticker, e)}
                  className="text-gray-600 hover:text-[#f85149] text-xs ml-1"
                  title="Remove"
                >
                  x
                </button>
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex border-t border-[#21262d] p-2 gap-1">
        <input
          value={newTicker}
          onChange={(e) => setNewTicker(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
          placeholder="Add ticker"
          className="flex-1 bg-[#1a1a2e] text-white text-xs px-2 py-1 rounded border border-[#21262d] outline-none focus:border-[#209dd7]"
        />
        <button onClick={handleAdd} className="bg-[#209dd7] text-white text-xs px-2 py-1 rounded hover:brightness-110">
          +
        </button>
      </div>
    </div>
  );
}
