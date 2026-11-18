"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AssetSelect } from "@/components/asset-picker";
import { Card, CountUp, ErrorBox, PageHeader, Segmented, Skeleton, Term } from "@/components/ui";
import { post, type SimResult } from "@/lib/api";
import { cn, fmtDate, inr, pct, tone } from "@/lib/format";
import { useDebounced } from "@/lib/hooks";

function Slider({ label, value, min, max, step, onChange, fmt }: { label: React.ReactNode; value: number; min: number; max: number; step: number; onChange: (v: number) => void; fmt: (v: number) => string }) {
  return (
    <label className="block">
      <div className="mb-1 flex justify-between text-sm"><span className="text-subtle">{label}</span><span className="num font-bold">{fmt(value)}</span></div>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(+e.target.value)} className="w-full" />
    </label>
  );
}

export default function Simulator() {
  const [asset, setAsset] = useState("nifty50");
  const [mode, setMode] = useState<"sip" | "lumpsum">("sip");
  const [amount, setAmount] = useState(5000);
  const [years, setYears] = useState(10);
  const [stepUp, setStepUp] = useState(0);
  const params = useDebounced({ asset, mode, amount, years, stepUp }, 200);

  const q = useQuery({
    queryKey: ["sim", params],
    queryFn: () => post<SimResult>(`/simulate/${params.mode}`, { asset_id: params.asset, amount: params.amount, years: params.years, step_up_pct: params.mode === "sip" ? params.stepUp : 0 }),
    placeholderData: (p) => p,
  });
  const r = q.data;

  return (
    <div className="mx-auto max-w-7xl px-4 py-10">
      <PageHeader eyebrow="What-if simulator" title="What would my money have become?" sub="Back-tested on real historical prices. Compare a monthly SIP with a one-time lump sum — and against a bank FD and inflation." />
      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="space-y-5 lg:sticky lg:top-24 lg:self-start">
          <div><p className="mb-1 text-sm text-subtle">Asset</p><AssetSelect value={asset} onChange={setAsset} /></div>
          <Segmented className="w-full [&>button]:flex-1" value={mode} onChange={(m) => { setMode(m); setAmount(m === "sip" ? 5000 : 100000); }}
            options={[{ value: "sip", label: "Monthly SIP" }, { value: "lumpsum", label: "Lump sum" }]} />
          {mode === "sip" ? (
            <Slider label={<Term k="sip">Monthly amount</Term>} value={amount} min={500} max={100000} step={500} onChange={setAmount} fmt={(v) => inr(v)} />
          ) : (
            <Slider label={<Term k="lumpsum">One-time amount</Term>} value={amount} min={10000} max={5000000} step={10000} onChange={setAmount} fmt={(v) => inr(v, { compact: true })} />
          )}
          <Slider label="Years back from today" value={years} min={1} max={20} step={1} onChange={setYears} fmt={(v) => `${v} yrs`} />
          {mode === "sip" && <Slider label="Yearly step-up" value={stepUp} min={0} max={20} step={1} onChange={setStepUp} fmt={(v) => `${v}%`} />}
          <p className="text-[11px] text-subtle">SIP invests on the first trading day of each month. FD uses indicative 1-year rates for each year, before tax. Ignores fund expense ratios already inside NAVs, taxes and exit loads.</p>
        </Card>

        <div className="space-y-6 lg:col-span-2">
          {q.error ? <ErrorBox error={q.error} /> : !r ? <Skeleton className="h-[520px]" /> : (
            <>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                {[
                  { l: "You invested", v: r.invested, c: "" },
                  { l: "Would be worth", v: r.final_value, c: tone(r.gain) },
                  { l: "Same money in FD", v: r.fd_final ?? 0, c: "" },
                  { l: "Needed to beat inflation", v: r.inflation_final ?? 0, c: "" },
                ].map((s) => (
                  <motion.div key={s.l} layout className="card p-4">
                    <p className="text-xs text-subtle">{s.l}</p>
                    <CountUp key={`${s.l}-${Math.round(s.v)}`} value={s.v} format={(n) => inr(n, { compact: true })} className={cn("mt-1 block text-xl font-extrabold", s.c)} />
                  </motion.div>
                ))}
              </div>
              <Card>
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-sm">
                  <span className="text-subtle">{fmtDate(r.start)} → {fmtDate(r.end)} · {r.years} years{r.installments ? ` · ${r.installments} instalments` : ""}</span>
                  <span>
                    <Term k="xirr">XIRR</Term>{" "}
                    <b className={cn("num", tone(r.xirr))}>{pct(r.xirr)}</b> / yr · total <b className={cn("num", tone(r.absolute_return))}>{pct(r.absolute_return)}</b>
                  </span>
                </div>
                <ResponsiveContainer width="100%" height={360}>
                  <LineChart data={r.path} margin={{ left: 4, right: 12, top: 8 }}>
                    <CartesianGrid vertical={false} stroke="rgb(var(--border))" strokeOpacity={0.5} />
                    <XAxis dataKey="date" tickFormatter={(d) => d.slice(0, 4)} minTickGap={40} tick={{ fontSize: 11, fill: "rgb(var(--subtle))" }} axisLine={false} tickLine={false} />
                    <YAxis tickFormatter={(v) => inr(v, { compact: true })} tick={{ fontSize: 11, fill: "rgb(var(--subtle))" }} axisLine={false} tickLine={false} width={70} />
                    <Tooltip contentStyle={{ background: "rgb(var(--card))", border: "1px solid rgb(var(--border))", borderRadius: 12, fontSize: 12 }}
                      labelFormatter={(d) => fmtDate(d as string)} formatter={(v: number, n: string) => [inr(v), n]} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Line type="monotone" dataKey="value" name="Your investment" stroke="rgb(var(--brand))" strokeWidth={2.5} dot={false} animationDuration={600} />
                    <Line type="monotone" dataKey="fd_value" name="Bank FD" stroke="rgb(var(--gold))" strokeWidth={1.5} dot={false} animationDuration={600} />
                    <Line type="monotone" dataKey="inflation_value" name="Inflation" stroke="rgb(var(--down))" strokeDasharray="4 4" strokeWidth={1.5} dot={false} animationDuration={600} />
                    <Line type="stepAfter" dataKey="invested" name="Amount invested" stroke="rgb(var(--subtle))" strokeWidth={1} dot={false} animationDuration={600} />
                  </LineChart>
                </ResponsiveContainer>
              </Card>
              <Card className="text-sm text-subtle">
                <b className="text-fg">Reading this:</b> the green line is what the investment would have been worth on each date, using real prices.
                If it sits below the dashed inflation line, your money lost buying power over that period. Different start dates can give very different
                results — try moving the years slider. Past results don&apos;t predict future ones.
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
