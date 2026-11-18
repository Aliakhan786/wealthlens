"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowLeft, ExternalLink } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { ExplainPanel } from "@/components/ai";
import { CalendarHeatmap, DrawdownChart, MonthlyReturnsGrid, PriceChart, YearlyBars } from "@/components/charts";
import { useLive } from "@/components/providers";
import { Card, ErrorBox, RiskBadge, SectionTitle, Segmented, Skeleton, Term } from "@/components/ui";
import { api, type AssetDetail, type CalendarResponse, type DipHistory, type NewsItem, type PricesResponse } from "@/lib/api";
import { CLASS_LABEL, cn, fmtDate, pct, price, tone } from "@/lib/format";
import { useMetrics } from "@/lib/hooks";

const RANGES = ["1M", "6M", "1Y", "3Y", "5Y", "10Y", "MAX"] as const;
type Range = (typeof RANGES)[number];

function Stat({ label, value, sub, term, className }: { label: React.ReactNode; value: string; sub?: string; term?: string; className?: string }) {
  return (
    <motion.div initial={{ opacity: 0, y: 14 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} className="card p-4">
      <p className="text-xs text-subtle">{term ? <Term k={term}>{label}</Term> : label}</p>
      <p className={cn("num mt-1 text-xl font-bold", className)}>{value}</p>
      {sub && <p className="mt-0.5 text-[11px] text-subtle">{sub}</p>}
    </motion.div>
  );
}

export default function AssetPage({ params }: { params: { id: string } }) {
  const id = params.id;
  const [range, setRange] = useState<Range>("1Y");
  const [mode, setMode] = useState<"area" | "candles">("area");
  const [showMA, setShowMA] = useState(false);
  const [year, setYear] = useState<number | null>(null);
  const { quotes } = useLive();

  const asset = useQuery({ queryKey: ["asset", id], queryFn: () => api<AssetDetail>(`/assets/${id}`) });
  const prices = useQuery({ queryKey: ["prices", id, range], queryFn: () => api<PricesResponse>(`/assets/${id}/prices?range=${range}`), placeholderData: (p) => p });
  const metrics = useMetrics(id);
  const dd = useQuery({ queryKey: ["dd", id], queryFn: () => api<{ series: { date: string; drawdown: number }[] }>(`/assets/${id}/drawdown`) });
  const cal = useQuery({ queryKey: ["cal", id, year], queryFn: () => api<CalendarResponse>(`/assets/${id}/calendar${year ? `?year=${year}` : ""}`), placeholderData: (p) => p });
  const dips = useQuery({ queryKey: ["dips", id, 10], queryFn: () => api<DipHistory>(`/assets/${id}/dip-history?threshold=10`) });
  const news = useQuery({ queryKey: ["news", id], queryFn: () => api<NewsItem[]>(`/news/${id}`) });

  if (asset.error) return <div className="mx-auto max-w-7xl px-4 py-10"><ErrorBox error={asset.error} /></div>;
  const a = asset.data;
  const live = quotes[id] ?? a?.live;
  const m = metrics.data;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <Link href="/explore" className="mb-6 inline-flex items-center gap-1 text-sm text-subtle hover:text-fg"><ArrowLeft className="h-4 w-4" /> All assets</Link>

      {/* Header */}
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          {a ? (
            <>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-subtle">{CLASS_LABEL[a.asset_class]}</span>
                <RiskBadge risk={a.risk} />
                {a.is_sample_data && <span className="rounded-full bg-gold/15 px-2 py-0.5 text-[10px] font-semibold text-gold">Sample data (offline)</span>}
              </div>
              <h1 className="mt-1 text-3xl font-extrabold tracking-tight">{a.name}</h1>
              <p className="mt-1 max-w-2xl text-sm text-subtle">{a.description}</p>
            </>
          ) : <Skeleton className="h-16 w-80" />}
        </div>
        <div className="text-right">
          <motion.p key={live?.price} initial={{ opacity: 0.4 }} animate={{ opacity: 1 }} className="num text-3xl font-extrabold">{price(live?.price ?? m?.latest_price, a?.unit)}</motion.p>
          <p className={cn("num text-sm font-semibold", tone(live?.change_pct))}>{pct(live?.change_pct ?? null, 2)} today</p>
          <p className="text-[11px] text-subtle">{a?.unit} · delayed/indicative{live?.ts ? ` · ${new Date(live.ts + "Z").toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}` : ""}</p>
        </div>
      </div>

      {/* Chart */}
      <Card className="p-3 sm:p-5">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <Segmented value={range} onChange={setRange} options={RANGES.map((r) => ({ value: r, label: r }))} />
          <div className="flex items-center gap-2">
            {prices.data && <span className={cn("num text-sm font-bold", tone(prices.data.change))}>{pct(prices.data.change)} in {range}</span>}
            <button onClick={() => setShowMA(!showMA)} className={cn("chip", showMA && "chip-active")}>50/200-day avg</button>
            <Segmented value={mode} onChange={setMode} options={[{ value: "area", label: "Line" }, { value: "candles", label: "Candles" }]} />
          </div>
        </div>
        {prices.data ? <PriceChart data={prices.data} mode={mode} showMA={showMA} /> : <Skeleton className="h-[420px]" />}
        {showMA && <p className="mt-2 text-[11px] text-subtle"><span className="text-gold">━</span> 50-day average · <span className="text-violet-500">━</span> 200-day average</p>}
      </Card>

      {/* Key metrics */}
      <section className="mt-8">
        <SectionTitle title="The numbers" sub={m ? `Based on ${m.years_of_data} years of data (${fmtDate(m.start_date)} – ${fmtDate(m.end_date)})` : undefined} />
        {m ? (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label="1-year return" value={pct(m.trailing["1Y"]?.absolute)} className={tone(m.trailing["1Y"]?.absolute)} />
            <Stat label="5-year CAGR" term="cagr" value={pct(m.trailing["5Y"]?.cagr)} className={tone(m.trailing["5Y"]?.cagr)} sub="per year" />
            <Stat label="10-year CAGR" term="cagr" value={pct(m.trailing["10Y"]?.cagr)} className={tone(m.trailing["10Y"]?.cagr)} sub="per year" />
            <Stat label="Real return (since start)" term="real_return" value={pct(m.benchmarks.real_cagr)} className={tone(m.benchmarks.real_cagr)} sub={`after ~${pct(m.benchmarks.avg_inflation, 1, false)} avg inflation`} />
            <Stat label="Volatility" term="volatility" value={pct(m.volatility, 1, false)} sub={`${m.risk_label} risk`} />
            <Stat label="Worst fall" term="drawdown" value={pct(m.max_drawdown?.depth)} className="text-down"
              sub={m.max_drawdown?.recovered ? `recovered in ${m.max_drawdown.months_peak_to_recovery} months from peak` : "not yet recovered"} />
            <Stat label="Best day" value={pct(m.best_day?.return, 2)} className="text-up" sub={fmtDate(m.best_day?.date)} />
            <Stat label="Worst day" value={pct(m.worst_day?.return, 2)} className="text-down" sub={fmtDate(m.worst_day?.date)} />
            <Stat label="vs FD (per year)" term="fd" value={pct(m.benchmarks.excess_over_fd)} className={tone(m.benchmarks.excess_over_fd)} sub={`FD avg ${pct(m.benchmarks.avg_fd_rate, 1, false)}`} />
            <Stat label="Up days" value={pct(m.pct_positive_days ?? null, 0, false)} sub="share of trading days" />
            <Stat label="Longest winning streak" value={`${m.streaks.up.days} days`} sub={fmtDate(m.streaks.up.end)} />
            <Stat label="Now vs all-time high" term="drawdown" value={pct(m.current_drawdown)} className={tone(m.current_drawdown)} />
          </div>
        ) : <div className="grid grid-cols-2 gap-3 md:grid-cols-4">{Array.from({ length: 8 }, (_, i) => <Skeleton key={i} className="h-24" />)}</div>}
      </section>

      {/* AI explain */}
      <section className="mt-8"><ExplainPanel assetId={id} /></section>

      {/* Rolling + yearly */}
      {m && (
        <section className="mt-8 grid gap-4 lg:grid-cols-2">
          <Card>
            <SectionTitle title="Rolling returns" sub="Every possible holding period of that length in history" />
            <div className="space-y-4">
              {(["1y", "3y", "5y"] as const).map((k) => {
                const r = m.rolling[k];
                if (!r) return null;
                const lo = Math.min(r.min, -0.1), hi = Math.max(r.max, 0.3);
                const x = (v: number) => `${((v - lo) / (hi - lo)) * 100}%`;
                return (
                  <div key={k}>
                    <div className="mb-1 flex justify-between text-xs"><span className="font-semibold"><Term k="rolling">{k.replace("y", "-year")} holds</Term></span>
                      <span className="text-subtle">positive {pct(r.pct_positive, 0, false)} of the time · beat 7% {pct(r.pct_above_7, 0, false)}</span></div>
                    <div className="relative h-3 rounded-full bg-muted">
                      <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} transition={{ duration: 0.8 }} style={{ left: x(r.min), width: `calc(${x(r.max)} - ${x(r.min)})` }}
                        className="absolute h-3 rounded-full bg-gradient-to-r from-down/70 via-gold/70 to-up/70" />
                      <div className="absolute top-[-3px] h-[18px] w-1 rounded bg-fg" style={{ left: x(r.median) }} />
                      <div className="absolute top-[-2px] h-4 w-px bg-subtle" style={{ left: x(0) }} />
                    </div>
                    <div className="num mt-1 flex justify-between text-[11px] text-subtle"><span>worst {pct(r.min)}</span><span>median {pct(r.median)}</span><span>best {pct(r.max)}</span></div>
                  </div>
                );
              })}
            </div>
          </Card>
          <Card>
            <SectionTitle title="Calendar-year returns" />
            <YearlyBars data={m.yearly_returns.slice(-20)} />
          </Card>
        </section>
      )}

      {/* Drawdown */}
      <section className="mt-8">
        <Card>
          <SectionTitle title="Drawdown: how far below its peak" sub="0% means at an all-time high. Deep valleys are the crashes — and the climbs back out are the recoveries." />
          {dd.data ? <DrawdownChart series={dd.data.series} /> : <Skeleton className="h-[220px]" />}
        </Card>
      </section>

      {/* Calendar heatmap */}
      <section className="mt-8 grid gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <SectionTitle title="Daily profit / loss calendar" right={cal.data && (
            <select value={cal.data.year} onChange={(e) => setYear(+e.target.value)} className="rounded-lg border border-border bg-card px-2 py-1 text-xs">
              {cal.data.years_available.map((y) => <option key={y}>{y}</option>)}
            </select>)} />
          {cal.data ? <CalendarHeatmap data={cal.data} /> : <Skeleton className="h-28" />}
        </Card>
        <Card className="lg:col-span-2">
          <SectionTitle title="Monthly returns (%)" />
          {cal.data ? <MonthlyReturnsGrid monthly={cal.data.monthly} years={8} /> : <Skeleton className="h-40" />}
        </Card>
      </section>

      {/* Dip summary */}
      {dips.data && (
        <section className="mt-8">
          <Card className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-brand">History says</p>
              <p className="mt-1 text-lg font-semibold">
                {a?.name.split(" (")[0]} fell 10%+ from a peak <span className="text-gold">{dips.data.event_count} times</span>.
                {dips.data.summary["3y"] && <> 3 years later it was higher in <span className="text-up">{pct(dips.data.summary["3y"].win_rate, 0, false)}</span> of cases.</>}
              </p>
              <p className="text-xs text-subtle">History, not a prediction.</p>
            </div>
            <Link href={`/dips?asset=${id}`} className="chip chip-active shrink-0 px-4 py-2 text-sm">Open dip analyzer →</Link>
          </Card>
        </section>
      )}

      {/* News */}
      <section className="mt-8">
        <SectionTitle title="Recent news" sub="Headlines that mention this asset (from public RSS feeds)" />
        {news.data?.length ? (
          <div className="grid gap-3 md:grid-cols-2">
            {news.data.slice(0, 6).map((n) => (
              <a key={n.link} href={n.link} target="_blank" rel="noopener noreferrer" className="card group p-4 hover:border-brand/50">
                <p className="text-[11px] text-subtle">{n.source} · {fmtDate(n.published)}</p>
                <p className="mt-1 font-medium group-hover:text-brand">{n.title} <ExternalLink className="inline h-3 w-3" /></p>
              </a>
            ))}
          </div>
        ) : <p className="text-sm text-subtle">{news.isLoading ? "Loading…" : "No recent news stored for this asset yet."}</p>}
      </section>
    </div>
  );
}
