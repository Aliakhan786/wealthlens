"use client";

import { useTheme } from "next-themes";
import { useEffect, useMemo, useRef, useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CalendarResponse, PricesResponse } from "@/lib/api";
import { cn, pct } from "@/lib/format";

/** Read a CSS variable "r g b" and return an rgb()/rgba() string (charts don't understand Tailwind classes). */
function cssColor(name: string, alpha = 1) {
  if (typeof window === "undefined") return "#888";
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim().split(/\s+/).join(",");
  return alpha === 1 ? `rgb(${v})` : `rgba(${v},${alpha})`;
}

/** TradingView Lightweight Charts: area or candlestick, with 50/200-day moving averages. */
export function PriceChart({ data, mode, showMA }: { data: PricesResponse; mode: "area" | "candles"; showMA: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  const { resolvedTheme } = useTheme();

  useEffect(() => {
    if (!ref.current || !data.candles.length) return;
    let disposed = false;
    let cleanup = () => {};
    import("lightweight-charts").then(({ createChart, ColorType, CrosshairMode }) => {
      if (disposed || !ref.current) return;
      const up = data.change >= 0;
      const line = up ? cssColor("--up") : cssColor("--down");
      const chart = createChart(ref.current, {
        autoSize: true,
        layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: cssColor("--subtle"), fontSize: 11 },
        grid: { vertLines: { visible: false }, horzLines: { color: cssColor("--border", 0.5) } },
        rightPriceScale: { borderVisible: false },
        timeScale: { borderVisible: false, fixLeftEdge: true, fixRightEdge: true },
        crosshair: { mode: CrosshairMode.Magnet },
        localization: { priceFormatter: (p: number) => p.toLocaleString("en-IN", { maximumFractionDigits: p < 100 ? 2 : 0 }) },
        handleScroll: false,
        handleScale: false,
      });
      if (mode === "candles") {
        const s = chart.addCandlestickSeries({
          upColor: cssColor("--up"), downColor: cssColor("--down"), wickUpColor: cssColor("--up"),
          wickDownColor: cssColor("--down"), borderVisible: false,
        });
        s.setData(data.candles);
      } else {
        const s = chart.addAreaSeries({ lineColor: line, topColor: up ? cssColor("--up", 0.28) : cssColor("--down", 0.28), bottomColor: "rgba(0,0,0,0)", lineWidth: 2 });
        s.setData(data.candles.map((c) => ({ time: c.time, value: c.close })));
      }
      if (showMA) {
        chart.addLineSeries({ color: cssColor("--gold"), lineWidth: 1, priceLineVisible: false, lastValueVisible: false }).setData(data.ma50);
        chart.addLineSeries({ color: "rgba(139,92,246,0.9)", lineWidth: 1, priceLineVisible: false, lastValueVisible: false }).setData(data.ma200);
      }
      chart.timeScale().fitContent();
      cleanup = () => chart.remove();
    });
    return () => {
      disposed = true;
      cleanup();
    };
  }, [data, mode, showMA, resolvedTheme]);

  return <div ref={ref} className="h-[340px] w-full sm:h-[420px]" />;
}

export function DrawdownChart({ series }: { series: { date: string; drawdown: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={series} margin={{ left: 0, right: 8, top: 8 }}>
        <defs>
          <linearGradient id="dd" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="rgb(var(--down))" stopOpacity={0.05} />
            <stop offset="100%" stopColor="rgb(var(--down))" stopOpacity={0.45} />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} stroke="rgb(var(--border))" strokeOpacity={0.5} />
        <XAxis dataKey="date" tickFormatter={(d) => d.slice(0, 4)} minTickGap={40} tick={{ fontSize: 11, fill: "rgb(var(--subtle))" }} axisLine={false} tickLine={false} />
        <YAxis tickFormatter={(v) => `${Math.round(v * 100)}%`} tick={{ fontSize: 11, fill: "rgb(var(--subtle))" }} axisLine={false} tickLine={false} width={44} />
        <Tooltip
          contentStyle={{ background: "rgb(var(--card))", border: "1px solid rgb(var(--border))", borderRadius: 12, fontSize: 12 }}
          formatter={(v: number) => [pct(v), "Below peak"]}
        />
        <ReferenceLine y={0} stroke="rgb(var(--border))" />
        <Area type="monotone" dataKey="drawdown" stroke="rgb(var(--down))" strokeWidth={1.5} fill="url(#dd)" isAnimationActive animationDuration={900} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

/** GitHub-style calendar of daily gains/losses. */
export function CalendarHeatmap({ data }: { data: CalendarResponse }) {
  const [hover, setHover] = useState<{ date: string; r: number } | null>(null);
  const { weeks, maxAbs } = useMemo(() => {
    const byDate = new Map(data.days.map((d) => [d.date, d.return]));
    const start = new Date(Date.UTC(data.year, 0, 1));
    start.setUTCDate(start.getUTCDate() - start.getUTCDay()); // back to Sunday
    const end = new Date(Date.UTC(data.year, 11, 31));
    const weeks: { date: string; r: number | undefined; inYear: boolean }[][] = [];
    for (let d = new Date(start); d <= end; ) {
      const week = [];
      for (let i = 0; i < 7; i++) {
        const iso = d.toISOString().slice(0, 10);
        week.push({ date: iso, r: byDate.get(iso), inYear: d.getUTCFullYear() === data.year });
        d.setUTCDate(d.getUTCDate() + 1);
      }
      weeks.push(week);
    }
    const vals = data.days.map((d) => Math.abs(d.return)).sort((a, b) => a - b);
    const maxAbs = vals[Math.floor(vals.length * 0.95)] || 0.02;
    return { weeks, maxAbs };
  }, [data]);

  const color = (r: number | undefined) => {
    if (r === undefined) return "rgb(var(--muted))";
    const a = Math.min(Math.abs(r) / maxAbs, 1) * 0.85 + 0.15;
    return r >= 0 ? `rgb(var(--up) / ${a})` : `rgb(var(--down) / ${a})`;
  };
  const up = data.days.filter((d) => d.return > 0).length;

  return (
    <div>
      <div className="overflow-x-auto pb-2">
        <div className="flex gap-[3px]">
          {weeks.map((w, i) => (
            <div key={i} className="flex flex-col gap-[3px]">
              {w.map((c) => (
                <div key={c.date}
                  onMouseEnter={() => c.r !== undefined && setHover({ date: c.date, r: c.r })}
                  className={cn("h-3 w-3 rounded-[3px] transition-transform hover:scale-150", !c.inYear && "opacity-0")}
                  style={{ background: color(c.r) }} title={c.r !== undefined ? `${c.date}: ${pct(c.r, 2)}` : c.date} />
              ))}
            </div>
          ))}
        </div>
      </div>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-subtle">
        <span>{hover ? <><b className="text-fg">{hover.date}</b>: <span className={hover.r >= 0 ? "text-up" : "text-down"}>{pct(hover.r, 2)}</span></> : "Hover a day"}</span>
        <span>{up} up days · {data.days.length - up} down/flat days in {data.year}</span>
      </div>
    </div>
  );
}

export function YearlyBars({ data }: { data: { year: number; return: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ left: 0, right: 8, top: 8 }}>
        <CartesianGrid vertical={false} stroke="rgb(var(--border))" strokeOpacity={0.5} />
        <XAxis dataKey="year" tick={{ fontSize: 10, fill: "rgb(var(--subtle))" }} axisLine={false} tickLine={false} minTickGap={8} />
        <YAxis tickFormatter={(v) => `${Math.round(v * 100)}%`} tick={{ fontSize: 11, fill: "rgb(var(--subtle))" }} axisLine={false} tickLine={false} width={44} />
        <Tooltip cursor={{ fill: "rgb(var(--muted))" }}
          contentStyle={{ background: "rgb(var(--card))", border: "1px solid rgb(var(--border))", borderRadius: 12, fontSize: 12 }}
          formatter={(v: number) => [pct(v), "Return"]} />
        <ReferenceLine y={0} stroke="rgb(var(--border))" />
        <Bar dataKey="return" radius={[4, 4, 4, 4]} animationDuration={900}>
          {data.map((d) => <Cell key={d.year} fill={d.return >= 0 ? "rgb(var(--up))" : "rgb(var(--down))"} fillOpacity={0.85} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function MonthlyReturnsGrid({ monthly, years }: { monthly: CalendarResponse["monthly"]; years: number }) {
  const latest = Math.max(...monthly.map((m) => m.year));
  const rows = Array.from({ length: years }, (_, i) => latest - i).filter((y) => monthly.some((m) => m.year === y));
  const get = (y: number, mo: number) => monthly.find((m) => m.year === y && m.month === mo)?.return;
  const M = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"];
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[11px]">
        <thead><tr><th className="pr-2 text-left text-subtle">Year</th>{M.map((m, i) => <th key={i} className="text-subtle">{m}</th>)}</tr></thead>
        <tbody>
          {rows.map((y) => (
            <tr key={y}>
              <td className="pr-2 font-semibold">{y}</td>
              {M.map((_, i) => {
                const r = get(y, i + 1);
                return (
                  <td key={i} className="p-[2px]">
                    <div className="num rounded px-1 py-1 text-center"
                      style={{ background: r === undefined ? "transparent" : r >= 0 ? `rgb(var(--up) / ${Math.min(Math.abs(r) * 8, 0.8) + 0.08})` : `rgb(var(--down) / ${Math.min(Math.abs(r) * 8, 0.8) + 0.08})` }}>
                      {r === undefined ? "" : (r * 100).toFixed(1)}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
