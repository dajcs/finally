"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { PriceUpdate } from "../types";

export type ConnectionStatus = "connected" | "reconnecting" | "disconnected";

export interface UsePricesResult {
  prices: Record<string, PriceUpdate>;
  sparklines: Record<string, number[]>;
  connectionStatus: ConnectionStatus;
}

export function usePrices(): UsePricesResult {
  const [prices, setPrices] = useState<Record<string, PriceUpdate>>({});
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("disconnected");
  const sparklinesRef = useRef<Record<string, number[]>>({});
  const [sparklines, setSparklines] = useState<Record<string, number[]>>({});

  const updateSparkline = useCallback((ticker: string, price: number) => {
    const current = sparklinesRef.current[ticker] || [];
    const updated = [...current.slice(-59), price];
    sparklinesRef.current[ticker] = updated;
    setSparklines({ ...sparklinesRef.current });
  }, []);

  useEffect(() => {
    const es = new EventSource("/api/stream/prices");

    es.onopen = () => setConnectionStatus("connected");

    es.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (Array.isArray(data)) {
        const updated: Record<string, PriceUpdate> = {};
        data.forEach((p: PriceUpdate) => {
          updated[p.ticker] = p;
          updateSparkline(p.ticker, p.price);
        });
        setPrices((prev) => ({ ...prev, ...updated }));
      } else {
        const p = data as PriceUpdate;
        setPrices((prev) => ({ ...prev, [p.ticker]: p }));
        updateSparkline(p.ticker, p.price);
      }
    };

    es.onerror = () => {
      setConnectionStatus(es.readyState === EventSource.CONNECTING ? "reconnecting" : "disconnected");
    };

    return () => es.close();
  }, [updateSparkline]);

  return { prices, sparklines, connectionStatus };
}
