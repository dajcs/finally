import { Portfolio, PortfolioSnapshot, WatchlistEntry, ChatMessage } from "../types";

export async function fetchPortfolio(): Promise<Portfolio> {
  const res = await fetch("/api/portfolio");
  if (!res.ok) throw new Error("Failed to fetch portfolio");
  return res.json();
}

export async function executeTrade(ticker: string, quantity: number, side: "buy" | "sell"): Promise<Portfolio> {
  const res = await fetch("/api/portfolio/trade", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker: ticker.toUpperCase(), quantity, side }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Trade failed" }));
    throw new Error(err.detail || "Trade failed");
  }
  return res.json();
}

export async function fetchPortfolioHistory(): Promise<PortfolioSnapshot[]> {
  const res = await fetch("/api/portfolio/history");
  if (!res.ok) throw new Error("Failed to fetch history");
  return res.json();
}

export async function fetchWatchlist(): Promise<WatchlistEntry[]> {
  const res = await fetch("/api/watchlist");
  if (!res.ok) throw new Error("Failed to fetch watchlist");
  return res.json();
}

export async function addToWatchlist(ticker: string): Promise<WatchlistEntry[]> {
  const res = await fetch("/api/watchlist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker: ticker.toUpperCase() }),
  });
  if (!res.ok) throw new Error("Failed to add ticker");
  return res.json();
}

export async function removeFromWatchlist(ticker: string): Promise<void> {
  const res = await fetch(`/api/watchlist/${ticker.toUpperCase()}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to remove ticker");
}

export interface ChatResponse {
  message: string;
  trades_executed: { ticker: string; side: string; quantity: number; price: number }[];
  watchlist_changes: { ticker: string; action: string }[];
  errors: string[];
}

export async function sendChatMessage(message: string): Promise<ChatResponse> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) throw new Error("Chat request failed");
  return res.json();
}
