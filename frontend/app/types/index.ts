export interface PriceUpdate {
  ticker: string;
  price: number;
  previous_price: number;
  timestamp: string;
  direction: "up" | "down" | "unchanged";
  change_percent: number;
}

export interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  unrealized_pnl: number;
  pnl_pct: number;
}

export interface Portfolio {
  cash: number;
  positions: Position[];
  total_value: number;
}

export interface Trade {
  ticker: string;
  side: "buy" | "sell";
  quantity: number;
  price: number;
  executed_at: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  actions?: {
    trades_executed?: Trade[];
    watchlist_changes?: { ticker: string; action: "add" | "remove" }[];
    errors?: string[];
  };
  created_at: string;
}

export interface WatchlistEntry {
  ticker: string;
  price: number;
  previous_price: number;
  change_percent: number;
  direction: "up" | "down" | "unchanged";
}

export interface PortfolioSnapshot {
  total_value: number;
  recorded_at: string;
}
