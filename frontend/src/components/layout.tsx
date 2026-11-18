"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Menu, Moon, Sun, X, Eye } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { cn } from "@/lib/format";

const LINKS = [
  { href: "/explore", label: "Explore" },
  { href: "/simulator", label: "What-if" },
  { href: "/dips", label: "History says" },
  { href: "/compare", label: "Compare" },
  { href: "/quiz", label: "Risk quiz" },
  { href: "/ask", label: "Ask AI" },
  { href: "/learn", label: "Learn" },
];

export function DisclaimerBar() {
  return (
    <div className="bg-gold/10 px-4 py-1.5 text-center text-[11px] font-medium text-gold">
      Educational tool · Not investment advice · Not SEBI-registered · Market data is delayed &amp; indicative
    </div>
  );
}

function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) return <div className="h-9 w-9" />;
  const dark = resolvedTheme === "dark";
  return (
    <button aria-label="Toggle theme" onClick={() => setTheme(dark ? "light" : "dark")}
      className="grid h-9 w-9 place-items-center rounded-xl border border-border hover:border-brand">
      <AnimatePresence mode="wait" initial={false}>
        <motion.span key={dark ? "d" : "l"} initial={{ rotate: -90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: 90, opacity: 0 }}>
          {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </motion.span>
      </AnimatePresence>
    </button>
  );
}

export function Navbar() {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [path]);
  return (
    <header className="sticky top-0 z-40 border-b border-border/60 bg-bg/75 backdrop-blur-xl">
      <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2 font-extrabold tracking-tight">
          <span className="grid h-8 w-8 place-items-center rounded-xl bg-gradient-to-br from-brand to-gold text-slate-900">
            <Eye className="h-4 w-4" />
          </span>
          <span>Wealth<span className="text-brand">Lens</span></span>
        </Link>
        <div className="hidden items-center gap-1 lg:flex">
          {LINKS.map((l) => {
            const active = path.startsWith(l.href);
            return (
              <Link key={l.href} href={l.href}
                className={cn("relative rounded-lg px-3 py-2 text-sm font-medium transition-colors", active ? "text-fg" : "text-subtle hover:text-fg")}>
                {active && <motion.span layoutId="nav-pill" className="absolute inset-0 -z-10 rounded-lg bg-muted" transition={{ type: "spring", stiffness: 400, damping: 35 }} />}
                {l.label}
              </Link>
            );
          })}
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <button className="grid h-9 w-9 place-items-center rounded-xl border border-border lg:hidden" onClick={() => setOpen(!open)} aria-label="Menu">
            {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>
      </nav>
      <AnimatePresence>
        {open && (
          <motion.div initial={{ height: 0 }} animate={{ height: "auto" }} exit={{ height: 0 }} className="overflow-hidden border-t border-border lg:hidden">
            <div className="grid gap-1 p-3">
              {[...LINKS, { href: "/about", label: "About & disclaimer" }].map((l) => (
                <Link key={l.href} href={l.href} className="rounded-lg px-3 py-2 text-sm hover:bg-muted">{l.label}</Link>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="mt-24 border-t border-border">
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 text-sm text-subtle md:grid-cols-3">
        <div>
          <p className="font-bold text-fg">WealthLens</p>
          <p className="mt-2">Make sense of your savings with 20 years of history — explained in plain language.</p>
        </div>
        <div>
          <p className="font-semibold text-fg">Important</p>
          <p className="mt-2">
            Educational tool only. Not investment advice. WealthLens is not registered with SEBI. Past performance does not
            guarantee future results. No buy/sell signals, no predictions.
          </p>
        </div>
        <div>
          <p className="font-semibold text-fg">Data sources</p>
          <p className="mt-2">
            Yahoo Finance (via yfinance), mfapi.in (AMFI NAVs), RSS feeds from Economic Times, Moneycontrol and Livemint.
            Data is delayed (~15 min) and indicative, not official exchange data. Gold/silver in ₹ are derived from
            international prices × USD/INR and exclude duties &amp; GST.
          </p>
          <Link href="/about" className="mt-2 inline-block text-brand">Full disclaimer →</Link>
        </div>
      </div>
    </footer>
  );
}
