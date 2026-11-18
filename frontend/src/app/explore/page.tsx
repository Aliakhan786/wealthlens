"use client";

import { AnimatePresence } from "framer-motion";
import { Search } from "lucide-react";
import { useMemo, useState } from "react";
import { AssetCard, AssetCardSkeleton } from "@/components/asset-card";
import { ErrorBox, PageHeader, Segmented } from "@/components/ui";
import { useAssets } from "@/lib/hooks";
import { cn } from "@/lib/format";

const CLASSES = [
  { value: "all", label: "All" }, { value: "commodity", label: "Gold & silver" }, { value: "index", label: "Indices" },
  { value: "mutual_fund", label: "Mutual funds" }, { value: "etf", label: "ETFs" }, { value: "fx", label: "Currency" },
];
type Sort = "name" | "return_1y" | "cagr_5y" | "volatility";

export default function Explore() {
  const { data, isLoading, error } = useAssets();
  const [cls, setCls] = useState("all");
  const [risk, setRisk] = useState<"all" | "Low" | "Medium" | "High">("all");
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<Sort>("cagr_5y");

  const rows = useMemo(() => {
    let r = (data ?? []).filter((a) => (cls === "all" || a.asset_class === cls) && (risk === "all" || a.risk === risk));
    if (q) r = r.filter((a) => a.name.toLowerCase().includes(q.toLowerCase()));
    return [...r].sort((a, b) => (sort === "name" ? a.name.localeCompare(b.name) : ((b[sort] ?? -9) as number) - ((a[sort] ?? -9) as number)));
  }, [data, cls, risk, q, sort]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-10">
      <PageHeader eyebrow="Explore" title="Every asset, one honest view" sub="Filter by type or risk. Risk labels come from how bumpy each asset's price has been historically (annualised volatility)." />
      <div className="mb-6 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap gap-2">
          {CLASSES.map((c) => (
            <button key={c.value} onClick={() => setCls(c.value)} className={cn("chip", cls === c.value ? "chip-active" : "hover:border-brand/50")}>{c.label}</button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Segmented value={risk} onChange={setRisk} options={[{ value: "all", label: "Any risk" }, { value: "Low", label: "Low" }, { value: "Medium", label: "Medium" }, { value: "High", label: "High" }]} />
          <select value={sort} onChange={(e) => setSort(e.target.value as Sort)} className="rounded-xl border border-border bg-card px-3 py-2 text-xs font-semibold">
            <option value="cagr_5y">Sort: 5Y CAGR</option><option value="return_1y">Sort: 1Y return</option>
            <option value="volatility">Sort: Volatility</option><option value="name">Sort: Name</option>
          </select>
          <label className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-subtle" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search…" className="w-44 rounded-xl border border-border bg-card py-2 pl-9 pr-3 text-sm outline-none focus:border-brand" />
          </label>
        </div>
      </div>
      {error ? <ErrorBox error={error} /> : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {isLoading ? Array.from({ length: 8 }, (_, i) => <AssetCardSkeleton key={i} />) : (
            <AnimatePresence>{rows.map((a, i) => <AssetCard key={a.id} a={a} index={i} />)}</AnimatePresence>
          )}
        </div>
      )}
      {!isLoading && !rows.length && !error && <p className="py-20 text-center text-subtle">No assets match those filters.</p>}
    </div>
  );
}
