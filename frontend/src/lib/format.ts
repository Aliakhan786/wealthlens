import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export const cn = (...c: ClassValue[]) => twMerge(clsx(c));

export function pct(x: number | null | undefined, digits = 1, sign = true): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  const v = (x * 100).toFixed(digits);
  return `${sign && x > 0 ? "+" : ""}${v}%`;
}

export function inr(x: number | null | undefined, opts: { compact?: boolean; decimals?: number } = {}): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  if (opts.compact) {
    const a = Math.abs(x);
    if (a >= 1e7) return `₹${(x / 1e7).toFixed(2)} Cr`;
    if (a >= 1e5) return `₹${(x / 1e5).toFixed(2)} L`;
    if (a >= 1e3) return `₹${(x / 1e3).toFixed(1)}K`;
  }
  return "₹" + x.toLocaleString("en-IN", { maximumFractionDigits: opts.decimals ?? 0 });
}

/** Price formatting that respects the asset's unit (index points vs rupees). */
export function price(x: number | null | undefined, unit?: string): string {
  if (x === null || x === undefined) return "—";
  const decimals = x < 100 ? 2 : x < 10000 ? 1 : 0;
  const s = x.toLocaleString("en-IN", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  return unit === "points" ? s : `₹${s}`;
}

export const tone = (x: number | null | undefined) =>
  x === null || x === undefined ? "text-subtle" : x >= 0 ? "text-up" : "text-down";

export const fmtDate = (d: string | null | undefined) =>
  d ? new Date(d).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "—";

export const CLASS_LABEL: Record<string, string> = {
  commodity: "Commodity", etf: "ETF", index: "Index", mutual_fund: "Mutual fund", fx: "Currency",
};
