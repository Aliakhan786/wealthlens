"use client";

import { useAssets } from "@/lib/hooks";

export function AssetSelect({ value, onChange, className }: { value: string; onChange: (id: string) => void; className?: string }) {
  const { data } = useAssets();
  const groups = new Map<string, { id: string; name: string }[]>();
  (data ?? []).forEach((a) => {
    const g = a.asset_class === "mutual_fund" ? "Mutual funds" : a.asset_class === "index" ? "Indices" : "Gold, silver & more";
    groups.set(g, [...(groups.get(g) ?? []), { id: a.id, name: a.name }]);
  });
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}
      className={`w-full rounded-xl border border-border bg-card px-3 py-2.5 text-sm font-medium outline-none focus:border-brand ${className ?? ""}`}>
      {[...groups.entries()].map(([g, items]) => (
        <optgroup key={g} label={g}>
          {items.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
        </optgroup>
      ))}
    </select>
  );
}
