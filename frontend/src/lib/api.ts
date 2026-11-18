export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail ?? j);
    } catch {}
    throw new ApiError(res.status, msg);
  }
  return res.json() as Promise<T>;
}

export const post = <T,>(path: string, body: unknown) => api<T>(path, { method: "POST", body: JSON.stringify(body) });

// ------------------------------------------------------------------ types
export type Risk = "Low" | "Medium" | "High";

export interface AssetSummary {
  id: string;
  name: string;
  asset_class: string;
  symbol: string;
  unit: string;
  description: string;
  risk: Risk | null;
  is_sample_data: boolean;
  first_date: string | null;
  last_date: string | null;
  price: number | null;
  change_pct: number | null;
  price_ts: string | null;
  return_1y: number | null;
  cagr_5y: number | null;
  cagr_10y: number | null;
  volatility: number | null;
  max_drawdown: number | null;
  sparkline: number[];
}

export interface AssetDetail extends Omit<AssetSummary, "price" | "change_pct" | "price_ts" | "sparkline" | "return_1y" | "cagr_5y" | "cagr_10y" | "volatility" | "max_drawdown"> {
  live: { price: number; change: number | null; change_pct: number | null; ts: string } | null;
}

export interface Candle { time: string; open: number; high: number; low: number; close: number }
export interface PricesResponse {
  asset_id: string; range: string; interval: string; candles: Candle[];
  ma50: { time: string; value: number }[]; ma200: { time: string; value: number }[]; change: number;
}

export interface Trailing { absolute: number; cagr: number | null }
export interface Metrics {
  start_date: string; end_date: string; latest_price: number; years_of_data: number;
  trailing: Record<string, Trailing | null>;
  cagr_since_start: number | null; volatility: number | null; risk_label: Risk | null;
  max_drawdown: { depth: number; peak_date: string | null; trough_date: string | null; recovery_date: string | null;
    days_to_recover: number | null; months_peak_to_recovery?: number | null; recovered: boolean } | null;
  current_drawdown: number;
  best_day?: { date: string; return: number }; worst_day?: { date: string; return: number };
  pct_positive_days?: number;
  streaks: { up: { days: number; start: string; end: string }; down: { days: number; start: string; end: string } };
  yearly_returns: { year: number; return: number }[];
  rolling: Record<string, { years: number; min: number; median: number; max: number; pct_positive: number; pct_above_7: number } | null>;
  benchmarks: { avg_inflation: number | null; avg_fd_rate: number | null; real_cagr: number | null; excess_over_fd: number | null };
  recent: { "1W": number | null; "1M": number | null };
}

export interface DipEvent {
  date: string; price: number; peak_date: string; peak_price: number; drawdown: number;
  forward: Record<string, number | null>; recovered_on: string | null; days_to_recover: number | null;
}
export interface DipStats { observations: number; win_rate: number; avg_return: number; median_return: number; best: number; worst: number }
export interface DipHistory {
  threshold: number; events: DipEvent[]; summary: Record<string, DipStats | null>; event_count: number;
  avg_days_to_recover: number | null; current_drawdown: number; currently_in_dip: boolean;
}

export interface SimPoint { date: string; invested: number; value: number; fd_value: number | null; inflation_value: number | null }
export interface SimResult {
  mode: "sip" | "lumpsum"; invested: number; final_value: number; gain: number; absolute_return: number;
  xirr: number | null; cagr?: number | null; installments?: number; path: SimPoint[]; start: string; end: string;
  fd_final: number | null; inflation_final: number | null; years: number; asset_id: string;
}

export interface CalendarResponse {
  year: number; years_available: number[];
  days: { date: string; return: number }[];
  monthly: { year: number; month: number; return: number }[];
}

export interface QuizQuestion { id: string; text: string; options: { label: string; score: number }[] }
export interface QuizResult {
  score: number; max_score: number; profile: string; capped: boolean; note: string;
  mix: { bucket: string; pct: number; examples: string[] }[];
}

export interface NewsItem { title: string; summary: string; link: string; source: string; published: string; score?: number }
export interface AskResponse {
  answer: string; mode: "llm" | "offline"; category: string; cached: boolean;
  tool_calls: { name: string; input: Record<string, unknown>; error: boolean }[];
  sources: NewsItem[];
}
export interface LiveQuote { asset_id: string; price: number; change: number | null; change_pct: number | null; ts: string }
