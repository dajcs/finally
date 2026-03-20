"use client";
import { useEffect, useRef } from "react";

interface MainChartProps {
  ticker: string | null;
  sparklineData: number[];
}

/* eslint-disable @typescript-eslint/no-explicit-any */
export default function MainChart({ ticker, sparklineData }: MainChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const seriesRef = useRef<any>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    let cancelled = false;

    import("lightweight-charts").then((lc) => {
      if (cancelled || !containerRef.current) return;

      if (chartRef.current) {
        chartRef.current.remove();
      }

      const chart = lc.createChart(containerRef.current!, {
        layout: {
          background: { type: lc.ColorType.Solid, color: "#0d1117" },
          textColor: "#8b949e",
        },
        grid: {
          vertLines: { color: "#21262d" },
          horzLines: { color: "#21262d" },
        },
        width: containerRef.current!.clientWidth,
        height: containerRef.current!.clientHeight,
        timeScale: { visible: false },
        rightPriceScale: { borderColor: "#21262d" },
      });

      const series = chart.addSeries(lc.LineSeries, {
        color: "#209dd7",
        lineWidth: 2,
      });

      chartRef.current = chart;
      seriesRef.current = series;

      const el = containerRef.current!;
      const ro = new ResizeObserver(() => {
        chart.applyOptions({
          width: el.clientWidth,
          height: el.clientHeight,
        });
      });
      ro.observe(el);
    });

    return () => {
      cancelled = true;
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
        seriesRef.current = null;
      }
    };
  }, [ticker]);

  useEffect(() => {
    if (!seriesRef.current || sparklineData.length === 0) return;
    const now = Math.floor(Date.now() / 1000);
    const data = sparklineData.map((value, i) => ({
      time: now - (sparklineData.length - 1 - i),
      value,
    }));
    seriesRef.current.setData(data);
  }, [sparklineData]);

  if (!ticker) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 text-sm">
        Select a ticker to view chart
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 text-xs font-semibold text-[#ecad0a] uppercase tracking-wider border-b border-[#21262d]">
        {ticker}
      </div>
      <div ref={containerRef} className="flex-1 min-h-0" />
    </div>
  );
}
