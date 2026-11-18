"use client";

import { motion } from "framer-motion";
import { ArrowRight, BarChart3, Brain, Calculator, History, ShieldCheck, Sparkles } from "lucide-react";
import Link from "next/link";
import { AssetCard, AssetCardSkeleton } from "@/components/asset-card";
import { LiveTicker } from "@/components/ticker";
import { Button, CountUp } from "@/components/ui";
import { useAssets } from "@/lib/hooks";

const FEATURES = [
  { icon: BarChart3, title: "20 years of history", text: "Returns, risk and worst falls for gold, silver, indices and mutual funds — on one honest page.", href: "/explore" },
  { icon: Calculator, title: "What-if simulator", text: "SIP vs lump sum on real historical prices, compared against FDs and inflation.", href: "/simulator" },
  { icon: History, title: "History says", text: "When gold fell 10%, what happened 1, 3 and 5 years later? Win rates from real data.", href: "/dips" },
  { icon: Brain, title: "Ask WealthLens", text: "An AI assistant that calls our own analytics as tools — and never tells you what to buy.", href: "/ask" },
];

const container = { hidden: {}, show: { transition: { staggerChildren: 0.08 } } };
const item = { hidden: { opacity: 0, y: 18 }, show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 220, damping: 24 } } };

export default function Home() {
  const { data } = useAssets();
  const years = data?.length ? Math.max(...data.map((a) => (a.first_date ? new Date().getFullYear() - +a.first_date.slice(0, 4) : 0))) : 20;
  const highlights = data ? ["gold", "nifty50", "silver", "ppfas-flexi"].map((id) => data.find((a) => a.id === id)).filter(Boolean) : [];

  return (
    <>
      <section className="relative overflow-hidden">
        <div className="grid-bg absolute inset-0" />
        <div className="pointer-events-none absolute left-1/2 top-[-10%] h-[480px] w-[780px] -translate-x-1/2 rounded-full bg-brand/20 blur-[120px]" />
        <div className="pointer-events-none absolute right-[-10%] top-[30%] h-[300px] w-[400px] rounded-full bg-gold/15 blur-[120px]" />
        <motion.div variants={container} initial="hidden" animate="show" className="relative mx-auto max-w-5xl px-4 pb-16 pt-20 text-center sm:pt-28">
          <motion.div variants={item} className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-card/70 px-4 py-1.5 text-xs font-medium backdrop-blur">
            <Sparkles className="h-3.5 w-3.5 text-gold" /> Historical facts, explained by AI — never buy/sell tips
          </motion.div>
          <motion.h1 variants={item} className="text-4xl font-black tracking-tight sm:text-6xl md:text-7xl">
            Make sense of <br className="hidden sm:block" />
            <span className="text-gradient">your savings</span>
          </motion.h1>
          <motion.p variants={item} className="mx-auto mt-6 max-w-2xl text-lg text-subtle">
            Gold or Nifty? SIP or lump sum? FD or mutual fund? See how India&apos;s most popular savings options really behaved over
            two decades — the growth, the crashes, and the recoveries.
          </motion.p>
          <motion.div variants={item} className="mt-8 flex flex-wrap justify-center gap-3">
            <Link href="/explore"><Button className="px-6 py-3 text-base">Explore assets <ArrowRight className="h-4 w-4" /></Button></Link>
            <Link href="/simulator"><Button variant="outline" className="px-6 py-3 text-base">Try the what-if simulator</Button></Link>
          </motion.div>
          <motion.div variants={item} className="mx-auto mt-14 grid max-w-3xl grid-cols-3 gap-4">
            {[
              { v: data?.length ?? 18, f: (n: number) => Math.round(n).toString(), l: "assets tracked" },
              { v: years, f: (n: number) => `${Math.round(n)}+`, l: "years of history" },
              { v: (data?.length ?? 18) * years * 250, f: (n: number) => `${Math.round(n / 1000)}K+`, l: "daily data points" },
            ].map((s) => (
              <div key={s.l} className="glass p-4">
                <CountUp value={s.v} format={s.f} className="text-2xl font-extrabold sm:text-4xl" />
                <p className="mt-1 text-xs text-subtle sm:text-sm">{s.l}</p>
              </div>
            ))}
          </motion.div>
        </motion.div>
      </section>

      <LiveTicker />

      <section className="mx-auto max-w-7xl px-4 py-16">
        <div className="mb-6 flex items-end justify-between">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Popular right now</h2>
            <p className="text-sm text-subtle">Prices are delayed and indicative. Tap any card for 20 years of history.</p>
          </div>
          <Link href="/explore" className="text-sm font-semibold text-brand">See all →</Link>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {highlights.length ? highlights.map((a, i) => <AssetCard key={a!.id} a={a!} index={i} />) : Array.from({ length: 4 }, (_, i) => <AssetCardSkeleton key={i} />)}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4">
        <motion.div variants={container} initial="hidden" whileInView="show" viewport={{ once: true, margin: "-80px" }} className="grid gap-4 md:grid-cols-2">
          {FEATURES.map((f) => (
            <motion.div key={f.title} variants={item} whileHover={{ y: -4 }}>
              <Link href={f.href} className="card group flex h-full gap-4 p-6 hover:border-brand/50">
                <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-brand-soft text-brand transition-transform group-hover:scale-110"><f.icon className="h-5 w-5" /></span>
                <div>
                  <h3 className="font-semibold">{f.title}</h3>
                  <p className="mt-1 text-sm text-subtle">{f.text}</p>
                </div>
              </Link>
            </motion.div>
          ))}
        </motion.div>
        <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} className="card mt-8 flex flex-col items-start gap-4 p-6 sm:flex-row sm:items-center">
          <ShieldCheck className="h-8 w-8 shrink-0 text-gold" />
          <p className="text-sm text-subtle">
            <b className="text-fg">Built responsibly.</b> WealthLens shows historical facts only. It doesn&apos;t give buy/sell signals, doesn&apos;t
            predict prices, doesn&apos;t handle money and doesn&apos;t need your personal financial data. It&apos;s not SEBI-registered — for a
            personal plan, talk to a registered adviser.
          </p>
        </motion.div>
      </section>
    </>
  );
}
