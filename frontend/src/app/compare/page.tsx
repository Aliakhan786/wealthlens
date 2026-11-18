"use client";

import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import { useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, ErrorBox, PageHeader, RiskBadge, Skeleton, Term } from "@/components/ui";
import { api, type AssetDetail, type Metrics } from "@/lib/api";
import { cn, fmtDate, pct, tone } from "@/lib/format";
import { useAssets } from "@/lib/hooks";

const COLORS = ["rgb(var(--brand))", "rgb(var(--gold))", "#8b5cf6", "#f43f5e"];
interface CompareResp { assets: { asset: AssetDetail; metrics: Metrics }[]; growth_of_100: Record<string, { date: string; value: number }[]>; common_start: string }

export default function Compare() {
  const { data: all } = useAssets();
  const [ids, setIds] = useState(["gold", "nifty50", "ppfas-flexi"]);
  const q = useQuery({ queryKey: ["compare", ids], queryFn: () => api<CompareResp>(`/compare?ids=${ids.join(",")}`), enabled: ids.length >= 2, placeholderData: (p) => p });

  const chart = useMemo(() => {
    if (!q.data) return [];
    const map = new Map<string, Record<string, number | string>>();
    Object.entries(q.data.growth_of_100).forEach(([id, pts]) => pts.forEach((p) => {
      const row = map.get(p.date) ?? { date: p.date };
      row[id] = p.value;
      map.set(p.date, row);
    }));
    return [...map.values()].sort((a, b) => String(a.date).localeCompare(String(b.date)));
  }, [q.data]);

  const rows: { label: React.ReactNode; get: (m: Metrics) => number | null | undefined; signed?: boolean }[] = [
    { label: "1-year return", get: (m) => m.trailing["1Y"]?.absolute },
    { label: <Term k="cagr">3Y CAGR</Term>, get: (m) => m.trailing["3Y"]?.cagr },
    { label: <Term k="cagr">5Y CAGR</Term>, get: (m) => m.trailing["5Y"]?.cagr },
    { label: <Term k="cagr">10Y CAGR</Term>, get: (m) => m.trailing["10Y"]?.cagr },
    { label: <Term k="real_return">Real return (since start)</Term>, get: (m) => m.benchmarks.real_cagr },
    { label: <Term k="volatility">Volatility</Term>, get: (m) => m.volatility, signed: false },
    { label: <Term k="drawdown">Worst fall</Term>, get: (m) => m.max_drawdown?.depth },
    { label: "Worst day", get: (m) => m.worst_day?.return },
    { label: "5Y holds that were positive", get: (m) => m.rolling["5y"]?.pct_positive, signed: false },
  ];

  return (
    <div className="mx-auto max-w-7xl px-4 py-10">
      <PageHeader eyebrow="Compare" title="Side by side" sub="Pick 2–4 assets. The chart shows how ₹100 invested on the first common date would have grown." />
      <div className="mb-6 flex flex-wrap items-center gap-2">
        {ids.map((id, i) => (
          <span key={id} className="chip chip-active" style={{ borderColor: COLORS[i], color: COLORS[i] }}>
            {all?.find((a) => a.id === id)?.name ?? id}
            {ids.length > 2 && <button aria-label="remove" onClick={() => setIds(ids.filter((x) => x !== id))}><X className="h-3 w-3" /></button>}
          </span>
        ))}
        {ids.length < 4 && (
          <select value="" onChange={(e) => e.target.value && setIds([...ids, e.target.value])} className="rounded-full border border-dashed border-border bg-card px-3 py-1 text-xs">
            <option value="">+ Add asset</option>
            {all?.filter((a) => !ids.includes(a.id)).map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
        )}
      </div>
      {q.error ? <ErrorBox error={q.error} /> : !q.data ? <Skeleton className="h-[500px]" /> : (
        <div className="space-y-6">
          <Card>
            <p className="mb-2 text-sm text-subtle">Growth of ₹100 since {fmtDate(q.data.common_start)}</p>
            <ResponsiveContainer width="100%" height={380}>
              <LineChart data={chart} margin={{ left: 0, right: 12, top: 8 }}>
                <CartesianGrid vertical={false} stroke="rgb(var(--border))" strokeOpacity={0.5} />
                <XAxis dataKey="date" tickFormatter={(d) => String(d).slice(0, 4)} minTickGap={40} tick={{ fontSize: 11, fill: "rgb(var(--subtle))" }} axisLine={false} tickLine={false} />
                <YAxis tickFormatter={(v) => `₹${Math.round(v)}`} tick={{ fontSize: 11, fill: "rgb(var(--subtle))" }} axisLine={false} tickLine={false} width={56} />
                <Tooltip contentStyle={{ background: "rgb(var(--card))", border: "1px solid rgb(var(--border))", borderRadius: 12, fontSize: 12 }}
                  labelFormatter={(d) => fmtDate(d as string)} formatter={(v: number, n: string) => [`₹${v.toFixed(0)}`, all?.find((a) => a.id === n)?.name ?? n]} />
                <Legend formatter={(v) => all?.find((a) => a.id === v)?.name ?? v} wrapperStyle={{ fontSize: 12 }} />
                {ids.map((id, i) => <Line key={id} dataKey={id} stroke={COLORS[i]} strokeWidth={2} dot={false} animationDuration={800} connectNulls />)}
              </LineChart>
            </ResponsiveContainer>
          </Card>
          <Card className="overflow-x-auto p-0">
            <table className="w-full min-w-[560px] text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="p-4 text-left font-medium text-subtle">Metric</th>
                  {q.data.assets.map((x, i) => (
                    <th key={x.asset.id} className="p-4 text-right"><span style={{ color: COLORS[i] }}>{x.asset.name}</span><div className="mt-1"><RiskBadge risk={x.asset.risk} /></div></th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r, ri) => (
                  <tr key={ri} className="border-b border-border/60 last:border-0">
                    <td className="p-4 text-subtle">{r.label}</td>
                    {q.data!.assets.map((x) => {
                      const v = r.get(x.metrics);
                      return <td key={x.asset.id} className={cn("num p-4 text-right font-semibold", r.signed === false ? "" : tone(v))}>{pct(v, 1, r.signed !== false)}</td>;
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>
      )}
    </div>
  );
}
