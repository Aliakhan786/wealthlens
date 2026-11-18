"use client";

import { motion } from "framer-motion";
import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import type { AssetSummary } from "@/lib/api";
import { CLASS_LABEL, cn, pct, price, tone } from "@/lib/format";
import { useLive } from "./providers";
import { RiskBadge, Sparkline } from "./ui";

export function AssetCard({ a, index = 0 }: { a: AssetSummary; index?: number }) {
  const { quotes } = useLive();
  const q = quotes[a.id];
  const p = q?.price ?? a.price;
  const chg = q?.change_pct ?? a.change_pct;
  const prev = useRef(p);
  const [flash, setFlash] = useState<"" | "up" | "down">("");

  useEffect(() => {
    if (p != null && prev.current != null && p !== prev.current) {
      setFlash(p > prev.current ? "up" : "down");
      const t = setTimeout(() => setFlash(""), 1200);
      prev.current = p;
      return () => clearTimeout(t);
    }
    prev.current = p;
  }, [p]);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.96 }}
      transition={{ delay: Math.min(index * 0.04, 0.5), type: "spring", stiffness: 260, damping: 26 }}
      whileHover={{ y: -4 }}
    >
      <Link href={`/asset/${a.id}`}
        className="group card relative block overflow-hidden p-5 transition-shadow hover:border-brand/50 hover:shadow-xl hover:shadow-brand/5">
        <div className="pointer-events-none absolute -right-16 -top-16 h-40 w-40 rounded-full bg-brand/10 opacity-0 blur-3xl transition-opacity group-hover:opacity-100" />
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-[10px] font-bold uppercase tracking-wider text-subtle">{CLASS_LABEL[a.asset_class] ?? a.asset_class}</p>
            <h3 className="mt-1 truncate font-semibold">{a.name}</h3>
          </div>
          <ArrowUpRight className="h-4 w-4 shrink-0 text-subtle transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-brand" />
        </div>
        <div className="mt-3 flex items-end justify-between">
          <div>
            <p className={cn("num rounded px-1 -mx-1 text-xl font-bold", flash === "up" && "animate-flash-up", flash === "down" && "animate-flash-down")}>
              {price(p, a.unit)}
            </p>
            <p className={cn("num text-xs font-semibold", tone(chg))}>{pct(chg, 2)} today</p>
          </div>
          <Sparkline data={a.sparkline} className="h-10 w-28" />
        </div>
        <div className="mt-4 grid grid-cols-3 gap-2 border-t border-border pt-3 text-xs">
          <div><p className="text-subtle">1Y</p><p className={cn("num font-semibold", tone(a.return_1y))}>{pct(a.return_1y)}</p></div>
          <div><p className="text-subtle">5Y CAGR</p><p className={cn("num font-semibold", tone(a.cagr_5y))}>{pct(a.cagr_5y)}</p></div>
          <div><p className="text-subtle">Worst fall</p><p className="num font-semibold text-down">{pct(a.max_drawdown, 0)}</p></div>
        </div>
        <div className="mt-3 flex items-center gap-2">
          <RiskBadge risk={a.risk} />
          {a.is_sample_data && <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] text-subtle">sample data</span>}
        </div>
      </Link>
    </motion.div>
  );
}

export function AssetCardSkeleton() {
  return <div className="card h-[214px] animate-pulse bg-muted/40" />;
}
