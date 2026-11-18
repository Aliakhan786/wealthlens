"use client";

import { motion, useInView, useMotionValue, useSpring } from "framer-motion";
import { Info } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { GLOSSARY } from "@/lib/glossary";
import { cn } from "@/lib/format";

export function Skeleton({ className }: { className?: string }) {
  return (
    <div className={cn("relative overflow-hidden rounded-xl bg-muted", className)}>
      <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/10 to-transparent" />
    </div>
  );
}

export function Card({ className, children, ...rest }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("card p-5", className)} {...rest}>
      {children}
    </div>
  );
}

export function Button({
  className, variant = "primary", ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "outline" }) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition-all disabled:opacity-50",
        variant === "primary" && "bg-brand text-white shadow-lg shadow-brand/20 hover:brightness-110 active:scale-[.98] dark:text-slate-900",
        variant === "outline" && "border border-border hover:border-brand hover:text-brand",
        variant === "ghost" && "hover:bg-muted",
        className,
      )}
      {...rest}
    />
  );
}

export function Segmented<T extends string>({
  options, value, onChange, className,
}: { options: { value: T; label: string }[]; value: T; onChange: (v: T) => void; className?: string }) {
  return (
    <div className={cn("relative inline-flex rounded-xl border border-border bg-muted p-1", className)}>
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={cn("relative z-10 rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors",
            value === o.value ? "text-fg" : "text-subtle hover:text-fg")}
        >
          {value === o.value && (
            <motion.span layoutId={`seg-${options.map((x) => x.value).join("")}`}
              className="absolute inset-0 -z-10 rounded-lg bg-card shadow"
              transition={{ type: "spring", stiffness: 400, damping: 32 }} />
          )}
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function RiskBadge({ risk }: { risk: string | null }) {
  if (!risk) return null;
  const c = risk === "Low" ? "bg-sky-500/15 text-sky-500" : risk === "Medium" ? "bg-amber-500/15 text-amber-500" : "bg-rose-500/15 text-rose-500";
  return <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide", c)}>{risk} risk</span>;
}

/** Glossary term with an accessible hover/focus tooltip. */
export function Term({ k, children }: { k: keyof typeof GLOSSARY | string; children?: React.ReactNode }) {
  const g = GLOSSARY[k];
  const [open, setOpen] = useState(false);
  if (!g) return <>{children}</>;
  return (
    <span className="relative inline-flex items-center gap-1" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button type="button" className="cursor-help border-b border-dotted border-subtle" onFocus={() => setOpen(true)} onBlur={() => setOpen(false)} aria-label={`${g.term}: ${g.short}`}>
        {children ?? g.term}
      </button>
      <Info className="h-3 w-3 text-subtle" />
      {open && (
        <motion.span initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}
          className="absolute bottom-full left-0 z-50 mb-2 w-64 rounded-xl border border-border bg-card p-3 text-left text-xs font-normal normal-case leading-relaxed text-fg shadow-xl">
          <span className="mb-1 block font-semibold">{g.term}</span>
          {g.long}
        </motion.span>
      )}
    </span>
  );
}

/** Animated number that counts up when scrolled into view. */
export function CountUp({ value, format, className }: { value: number; format: (n: number) => string; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const mv = useMotionValue(0);
  const spring = useSpring(mv, { stiffness: 60, damping: 18 });
  const [display, setDisplay] = useState(format(0));
  useEffect(() => { if (inView) mv.set(value); }, [inView, value, mv]);
  useEffect(() => spring.on("change", (v) => setDisplay(format(v))), [spring, format]);
  return <span ref={ref} className={cn("num", className)}>{display}</span>;
}

export function SectionTitle({ title, sub, right }: { title: string; sub?: string; right?: React.ReactNode }) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 className="text-lg font-bold tracking-tight">{title}</h2>
        {sub && <p className="text-sm text-subtle">{sub}</p>}
      </div>
      {right}
    </div>
  );
}

export function PageHeader({ eyebrow, title, sub }: { eyebrow?: string; title: string; sub?: string }) {
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
      {eyebrow && <p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-brand">{eyebrow}</p>}
      <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">{title}</h1>
      {sub && <p className="mt-2 max-w-2xl text-subtle">{sub}</p>}
    </motion.div>
  );
}

export function ErrorBox({ error }: { error: unknown }) {
  return (
    <Card className="border-down/40 text-sm">
      <p className="font-semibold text-down">Couldn&apos;t load data</p>
      <p className="mt-1 text-subtle">
        {error instanceof Error ? error.message : "Unknown error"}. Is the API running on port 8000? (First start can take
        1–3 minutes while 20 years of history download.)
      </p>
    </Card>
  );
}

export function Sparkline({ data, className, positive }: { data: number[]; className?: string; positive?: boolean }) {
  if (!data || data.length < 2) return <div className={className} />;
  const min = Math.min(...data), max = Math.max(...data);
  const w = 120, h = 36;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / (max - min || 1)) * h}`).join(" ");
  const up = positive ?? data[data.length - 1] >= data[0];
  const color = up ? "rgb(var(--up))" : "rgb(var(--down))";
  const id = `sg-${Math.round(data[0] * 1000)}-${data.length}-${up}`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className={className} preserveAspectRatio="none">
      <defs>
        <linearGradient id={id} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={`0,${h} ${pts} ${w},${h}`} fill={`url(#${id})`} />
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.6" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}
