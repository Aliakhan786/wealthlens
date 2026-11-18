"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { AssetSelect } from "@/components/asset-picker";
import { Card, ErrorBox, PageHeader, Skeleton, Term } from "@/components/ui";
import { api, type DipHistory } from "@/lib/api";
import { cn, fmtDate, pct, tone } from "@/lib/format";
import { useDebounced } from "@/lib/hooks";

function Ring({ value, label, sub }: { value: number; label: string; sub: string }) {
  const r = 42, c = 2 * Math.PI * r;
  return (
    <div className="card flex flex-col items-center p-5 text-center">
      <svg viewBox="0 0 100 100" className="h-28 w-28 -rotate-90">
        <circle cx="50" cy="50" r={r} fill="none" stroke="rgb(var(--muted))" strokeWidth="9" />
        <motion.circle cx="50" cy="50" r={r} fill="none" stroke={value >= 0.5 ? "rgb(var(--up))" : "rgb(var(--down))"} strokeWidth="9" strokeLinecap="round"
          strokeDasharray={c} initial={{ strokeDashoffset: c }} animate={{ strokeDashoffset: c * (1 - value) }} transition={{ duration: 1.1, ease: "easeOut" }} />
      </svg>
      <p className="-mt-[78px] mb-[46px] text-2xl font-extrabold num">{Math.round(value * 100)}%</p>
      <p className="font-semibold">{label}</p>
      <p className="text-xs text-subtle">{sub}</p>
    </div>
  );
}

function DipAnalyzer() {
  const sp = useSearchParams();
  const [asset, setAsset] = useState(sp.get("asset") || "gold");
  const [thr, setThr] = useState(10);
  const t = useDebounced(thr, 250);
  const q = useQuery({ queryKey: ["dips", asset, t], queryFn: () => api<DipHistory>(`/assets/${asset}/dip-history?threshold=${t}`), placeholderData: (p) => p });
  const d = q.data;

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <PageHeader eyebrow="History says" title="What happened after past falls?"
        sub="Pick an asset and a fall size. We find every time it dropped that much from its peak, then check where it was 1, 3 and 5 years later. Facts from the past — not a forecast." />
      <Card className="mb-6 grid gap-5 md:grid-cols-2">
        <div><p className="mb-1 text-sm text-subtle">Asset</p><AssetSelect value={asset} onChange={setAsset} /></div>
        <label>
          <div className="mb-1 flex justify-between text-sm"><span className="text-subtle"><Term k="drawdown">Fall from peak</Term></span><b className="num">{thr}%</b></div>
          <input type="range" min={5} max={40} step={1} value={thr} onChange={(e) => setThr(+e.target.value)} className="w-full" />
        </label>
      </Card>

      {q.error ? <ErrorBox error={q.error} /> : !d ? <Skeleton className="h-96" /> : (
        <>
          <motion.p key={`${asset}-${t}`} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mb-6 text-lg">
            Found <b className="text-gold">{d.event_count}</b> separate falls of {t}%+.{" "}
            {d.avg_days_to_recover && <>On average it took <b>{Math.round(d.avg_days_to_recover / 30.4)} months</b> to climb back to the old peak. </>}
            Right now it is <b className={tone(d.current_drawdown)}>{pct(d.current_drawdown)}</b> from its all-time high
            {d.currently_in_dip ? " — inside a fall of this size." : "."}
          </motion.p>

          <div className="grid gap-4 sm:grid-cols-3">
            {(["1y", "3y", "5y"] as const).map((h) => {
              const s = d.summary[h];
              return s ? (
                <div key={h}>
                  <Ring value={s.win_rate} label={`Higher after ${h.replace("y", " year")}${h === "1y" ? "" : "s"}`} sub={`${s.observations} cases · avg ${pct(s.avg_return)} · worst ${pct(s.worst)}`} />
                </div>
              ) : (
                <Card key={h} className="grid place-items-center text-center text-sm text-subtle">Not enough history for {h}</Card>
              );
            })}
          </div>
          <p className="mt-2 text-xs text-subtle"><Term k="win_rate">Win rate</Term> = share of past falls after which the price was higher at that horizon.</p>

          <h2 className="mb-4 mt-10 text-lg font-bold">Timeline of every fall</h2>
          <div className="relative space-y-4 border-l-2 border-border pl-6">
            {[...d.events].reverse().map((e, i) => (
              <motion.div key={e.date} initial={{ opacity: 0, x: -16 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ delay: Math.min(i * 0.05, 0.4) }} className="relative">
                <span className="absolute -left-[33px] top-4 h-4 w-4 rounded-full border-4 border-bg bg-down" />
                <Card className="p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-semibold">{fmtDate(e.date)} <span className="text-sm font-normal text-subtle">— crossed {pct(e.drawdown)} from peak of {fmtDate(e.peak_date)}</span></p>
                    <span className={cn("rounded-full px-2 py-0.5 text-xs", e.recovered_on ? "bg-up/15 text-up" : "bg-gold/15 text-gold")}>
                      {e.recovered_on ? `back to peak in ${Math.round((e.days_to_recover ?? 0) / 30.4)} mo` : "not yet back to peak"}
                    </span>
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-2 text-center text-sm">
                    {Object.entries(e.forward).map(([h, v]) => (
                      <div key={h} className="rounded-lg bg-muted py-2"><p className="text-[10px] uppercase text-subtle">{h} later</p><p className={cn("num font-bold", tone(v))}>{v === null ? "—" : pct(v)}</p></div>
                    ))}
                  </div>
                </Card>
              </motion.div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default function Page() {
  return <Suspense><DipAnalyzer /></Suspense>;
}
