import { PageHeader } from "@/components/ui";

export const metadata = { title: "About & disclaimer" };

const SECTIONS = [
  {
    h: "Disclaimer",
    p: [
      "WealthLens is an educational tool. Nothing on this site is investment advice, a recommendation, or an offer to buy or sell any security.",
      "WealthLens and its creator are not registered with the Securities and Exchange Board of India (SEBI) as investment advisers or research analysts.",
      "All figures describe the past. Past performance does not guarantee future results. Mutual fund investments are subject to market risks; read all scheme-related documents carefully.",
      "WealthLens never gives buy/sell signals or price predictions, never handles money, and does not collect personal financial data.",
    ],
  },
  {
    h: "Data & its limits",
    p: [
      "Index, ETF and currency prices come from Yahoo Finance via the open-source yfinance library. Mutual fund NAVs come from mfapi.in (sourced from AMFI). News headlines come from public RSS feeds of Economic Times, Moneycontrol and Livemint and link to the original articles.",
      "Prices are delayed (typically ~15 minutes or more) and indicative. They are not official exchange data and may contain errors or gaps.",
      "Gold and silver in ₹ are calculated from international futures prices × USD/INR. They exclude import duty, GST and local premiums, so they will differ from jeweller or MCX prices.",
      "CPI inflation and FD rates are indicative yearly figures used only as benchmarks. FD returns shown are before tax.",
      "If the data sources are unreachable, the app falls back to clearly labelled sample data so it can still be demonstrated offline.",
    ],
  },
  {
    h: "How it's built",
    p: [
      "Python data pipeline (pandas, yfinance, APScheduler) → PostgreSQL/SQLite → FastAPI with Redis caching, rate limiting and Server-Sent Events → Next.js, Tailwind, Framer Motion, TradingView Lightweight Charts.",
      "The AI layer uses Claude with tool calling: it answers by calling WealthLens's own analytics functions, so explanations are grounded in computed numbers. Guardrails strip buy/sell language and forecasts and always add this disclaimer.",
    ],
  },
];

export default function About() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <PageHeader eyebrow="About" title="About WealthLens" sub="What this is, where the data comes from, and what it is not." />
      <div className="space-y-8">
        {SECTIONS.map((s) => (
          <section key={s.h} className="card p-6">
            <h2 className="mb-3 text-lg font-bold">{s.h}</h2>
            <ul className="list-disc space-y-2 pl-5 text-sm text-subtle">{s.p.map((t) => <li key={t}>{t}</li>)}</ul>
          </section>
        ))}
      </div>
    </div>
  );
}
