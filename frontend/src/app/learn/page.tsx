"use client";

import { motion } from "framer-motion";
import { Search } from "lucide-react";
import { useState } from "react";
import { PageHeader } from "@/components/ui";
import { GLOSSARY } from "@/lib/glossary";

export default function Learn() {
  const [q, setQ] = useState("");
  const items = Object.entries(GLOSSARY).filter(([, g]) => (g.term + g.short + g.long).toLowerCase().includes(q.toLowerCase()));
  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <PageHeader eyebrow="Learn" title="Plain-language glossary" sub="Every term you see underlined across WealthLens, explained without jargon. Hover underlined words anywhere in the app for a quick reminder." />
      <label className="relative mb-6 block">
        <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-subtle" />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search terms…" className="w-full rounded-2xl border border-border bg-card py-3 pl-11 pr-4 outline-none focus:border-brand" />
      </label>
      <div className="grid gap-4 md:grid-cols-2">
        {items.map(([k, g], i) => (
          <motion.div key={k} id={k} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }} className="card p-5">
            <h2 className="text-lg font-bold">{g.term}</h2>
            <p className="mt-1 font-medium text-brand">{g.short}</p>
            <p className="mt-2 text-sm text-subtle">{g.long}</p>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
