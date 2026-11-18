"use client";

import Link from "next/link";
import { useLive } from "./providers";
import { useAssets } from "@/lib/hooks";
import { cn, pct, price } from "@/lib/format";

export function LiveTicker() {
  const { data } = useAssets();
  const { quotes, connected } = useLive();
  if (!data?.length) return <div className="h-10 border-y border-border/60" />;
  const items = data.map((a) => {
    const q = quotes[a.id];
    return { id: a.id, name: a.name.replace(/\s*\(.*\)/, ""), unit: a.unit, price: q?.price ?? a.price, chg: q?.change_pct ?? a.change_pct };
  });
  const row = (key: string) => (
    <div key={key} className="flex shrink-0 items-center">
      {items.map((i) => (
        <Link href={`/asset/${i.id}`} key={`${key}-${i.id}`} className="flex items-center gap-2 px-5 text-xs hover:text-brand">
          <span className="font-semibold">{i.name}</span>
          <span className="num text-subtle">{price(i.price, i.unit)}</span>
          <span className={cn("num font-semibold", (i.chg ?? 0) >= 0 ? "text-up" : "text-down")}>{pct(i.chg, 2)}</span>
        </Link>
      ))}
    </div>
  );
  return (
    <div className="group relative flex h-10 items-center overflow-hidden border-y border-border/60 bg-card/50">
      <div className="absolute left-0 z-10 flex h-full items-center gap-1.5 bg-gradient-to-r from-bg via-bg to-transparent pl-4 pr-8 text-[10px] font-bold uppercase tracking-wider">
        <span className={cn("h-2 w-2 rounded-full", connected ? "animate-pulse bg-up" : "bg-subtle")} />
        {connected ? "Live · delayed" : "Prices"}
      </div>
      <div className="flex animate-marquee group-hover:[animation-play-state:paused]">
        {row("a")}
        {row("b")}
      </div>
    </div>
  );
}
