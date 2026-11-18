"""'Ask WealthLens' — an agent that answers questions by calling WealthLens's own analytics as tools.

With an API key: Claude decides which tools to call (manual tool-use loop, max 6 steps).
Without a key: a deterministic intent parser calls the same tools, so the feature still works offline.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from collections.abc import Callable
from typing import Any

from ai.guardrails import REFRAME, classify_input, sanitize_output
from ai.llm import create_message, llm_available, text_of
from ai.prompts import AGENT_SYSTEM, LANG_HINT
from ai.rag import search_news
from backend import services
from backend.cache import cache
from core.config import get_settings

log = logging.getLogger("wealthlens.agent")
MAX_STEPS = 6

# ----------------------------------------------------------------------------- tools
TOOLS: list[dict[str, Any]] = [
    {
        "name": "list_assets",
        "description": "List every asset WealthLens tracks with its id, name, type, risk label and recent returns. "
                       "Call this first if you are unsure of an asset id.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_metrics",
        "description": "Historical metrics for one asset: trailing returns (1M..20Y), CAGR, volatility and risk "
                       "label, max drawdown and recovery time, best/worst day, real return vs inflation and FD, "
                       "and recent 1-week / 1-month change.",
        "input_schema": {"type": "object", "properties": {"asset_id": {"type": "string"}},
                         "required": ["asset_id"], "additionalProperties": False},
    },
    {
        "name": "simulate",
        "description": "Back-test what an investment would have become using real historical prices. "
                       "mode 'lumpsum' invests `amount` once; mode 'sip' invests `amount` every month. "
                       "Returns invested, final value, XIRR/CAGR, and the same money in an FD and vs inflation.",
        "input_schema": {"type": "object", "properties": {
            "asset_id": {"type": "string"},
            "mode": {"type": "string", "enum": ["lumpsum", "sip"]},
            "amount": {"type": "number", "description": "Rupees (one-time for lumpsum, per month for sip)"},
            "years": {"type": "number", "description": "How many years back from the latest date"},
        }, "required": ["asset_id", "mode", "amount", "years"], "additionalProperties": False},
    },
    {
        "name": "dip_history",
        "description": "History of past falls: every time the asset dropped `threshold_pct`% from its peak, what "
                       "its return was 1, 3 and 5 years later (win rate, average, best, worst).",
        "input_schema": {"type": "object", "properties": {
            "asset_id": {"type": "string"},
            "threshold_pct": {"type": "number", "description": "e.g. 10 for a 10% fall"},
        }, "required": ["asset_id", "threshold_pct"], "additionalProperties": False},
    },
    {
        "name": "search_news",
        "description": "Search recent market news (last 30 days) from Indian financial outlets. Use for 'why did X "
                       "move' questions. Returns numbered articles with title, summary, source and link.",
        "input_schema": {"type": "object", "properties": {
            "query": {"type": "string"},
            "asset_id": {"type": "string", "description": "Optional asset id to focus on"},
        }, "required": ["query"], "additionalProperties": False},
    },
]
for _t in TOOLS:
    _t["strict"] = True


def _t_list_assets() -> list[dict]:
    return [{k: a[k] for k in ("id", "name", "asset_class", "risk", "return_1y", "cagr_5y", "is_sample_data")}
            for a in services.list_assets()]


def _t_get_metrics(asset_id: str) -> dict:
    snap = services.get_metrics(asset_id)
    keep = ("start_date", "end_date", "latest_price", "trailing", "cagr_since_start", "volatility", "risk_label",
            "max_drawdown", "current_drawdown", "best_day", "worst_day", "benchmarks", "recent")
    return {"asset": services.get_asset(asset_id)["name"], **{k: snap.get(k) for k in keep}}


def _t_simulate(asset_id: str, mode: str, amount: float, years: float) -> dict:
    r = services.simulate(asset_id, mode, float(amount), years=float(years))
    r.pop("path", None)
    return r


def _t_dip_history(asset_id: str, threshold_pct: float) -> dict:
    r = services.get_dip_history(asset_id, float(threshold_pct) / 100)
    r["events"] = r["events"][-8:]  # most recent episodes are enough context
    return r


_NEWS_SOURCES: list[dict] = []


def _t_search_news(query: str, asset_id: str | None = None) -> list[dict]:
    hits = search_news(query, asset_id)
    out = []
    for h in hits:
        _NEWS_SOURCES.append(h)
        out.append({"n": len(_NEWS_SOURCES), **{k: h[k] for k in ("title", "summary", "source", "published", "link")}})
    return out


IMPLS: dict[str, Callable[..., Any]] = {
    "list_assets": _t_list_assets, "get_metrics": _t_get_metrics, "simulate": _t_simulate,
    "dip_history": _t_dip_history, "search_news": _t_search_news,
}


def run_tool(name: str, args: dict) -> tuple[Any, bool]:
    try:
        return IMPLS[name](**args), False
    except services.NotFound as e:
        return {"error": f"Unknown asset id '{e}'. Call list_assets to see valid ids."}, True
    except Exception as e:  # report tool errors back to the model instead of crashing
        log.exception("Tool %s failed", name)
        return {"error": str(e)}, True


# ----------------------------------------------------------------------------- entry point
def ask(question: str, lang: str = "en", history: list[dict] | None = None) -> dict[str, Any]:
    lang = lang if lang in LANG_HINT else "en"
    category = classify_input(question)
    key = "ai:ask:" + hashlib.md5(json.dumps([question.strip().lower(), lang, history or []]).encode()).hexdigest()
    if (hit := cache.get(key)) is not None:
        return {**hit, "cached": True}

    _NEWS_SOURCES.clear()
    if llm_available():
        try:
            result = _ask_llm(question, lang, category, history or [])
        except Exception as e:
            log.warning("LLM agent failed, using offline agent: %s", e)
            result = _ask_offline(question, lang, category)
    else:
        result = _ask_offline(question, lang, category)

    result["answer"], flagged = sanitize_output(result["answer"], lang)
    result.update({"category": category, "guardrail_flags": len(flagged), "sources": list(_NEWS_SOURCES)})
    cache.set(key, result, get_settings().ai_cache_ttl_seconds)
    return {**result, "cached": False}


def _ask_llm(question: str, lang: str, category: str, history: list[dict]) -> dict[str, Any]:
    system = AGENT_SYSTEM + "\n" + LANG_HINT[lang]
    if category != "ok":
        system += f"\n\nNote: this question asks for a {category}. Start by saying briefly why you can't give one, then help with historical facts."
    messages: list[dict[str, Any]] = [
        {"role": h["role"], "content": h["content"]} for h in history[-6:] if h.get("role") in ("user", "assistant")
    ]
    messages.append({"role": "user", "content": question})
    trace = []
    for _ in range(MAX_STEPS):
        resp = create_message(system, messages, tools=TOOLS, max_tokens=4000)
        if resp.stop_reason == "refusal":
            return {"answer": REFRAME["advice"], "tool_calls": trace, "mode": "llm"}
        if resp.stop_reason != "tool_use":
            return {"answer": text_of(resp), "tool_calls": trace, "mode": "llm"}
        messages.append({"role": "assistant", "content": resp.content})  # keep thinking + tool_use blocks intact
        results = []
        for block in resp.content:
            if getattr(block, "type", None) != "tool_use":
                continue
            out, is_err = run_tool(block.name, dict(block.input))
            trace.append({"name": block.name, "input": dict(block.input), "error": is_err})
            results.append({"type": "tool_result", "tool_use_id": block.id,
                            "content": json.dumps(out, default=str)[:12000], "is_error": is_err})
        messages.append({"role": "user", "content": results})
    return {"answer": "I needed too many steps to answer that. Could you ask a more specific question?",
            "tool_calls": trace, "mode": "llm"}


# ----------------------------------------------------------------------------- offline agent
ALIASES = [
    ("nifty bank", "niftybank"), ("bank nifty", "niftybank"), ("nifty it", "niftyit"), ("it stocks", "niftyit"),
    ("gold etf", "goldbees"), ("goldbees", "goldbees"), ("nifty 50", "nifty50"), ("index fund", "uti-nifty50"),
    ("midcap 150", "motilal-midcap150"), ("small cap", "sbi-smallcap"), ("smallcap", "sbi-smallcap"),
    ("mid cap", "hdfc-midcap"), ("midcap", "hdfc-midcap"), ("flexi", "ppfas-flexi"), ("parag", "ppfas-flexi"),
    ("elss", "axis-elss"), ("tax saver", "axis-elss"), ("large cap", "sbi-largecap"), ("bluechip", "icici-largecap"),
    ("mirae", "mirae-largemid"), ("nippon", "nippon-smallcap"), ("sensex", "sensex"), ("nifty", "nifty50"),
    ("silver", "silver"), ("gold", "gold"), ("dollar", "usdinr"), ("usd", "usdinr"), ("rupee", "usdinr"),
    ("सोना", "gold"), ("चांदी", "silver"), ("निफ्टी", "nifty50"),
]
AMOUNT_RE = re.compile(r"(?:₹|rs\.?|inr)?\s*(\d[\d,]*(?:\.\d+)?)\s*(lakh|lakhs|lac|l\b|crore|cr\b|k\b|thousand|लाख|करोड़)?", re.I)
YEARS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?|y\b|साल)", re.I)
MULT = {"लाख": 1e5, "करोड़": 1e7, "lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "l": 1e5, "crore": 1e7, "cr": 1e7, "k": 1e3, "thousand": 1e3}


def find_asset(text: str) -> str | None:
    t = text.lower()
    for alias, aid in ALIASES:
        if alias in t:
            return aid
    return None


def parse_amount(text: str) -> float | None:
    best = None
    for m_ in AMOUNT_RE.finditer(text):
        num = float(m_.group(1).replace(",", ""))
        unit = (m_.group(2) or "").lower()
        if YEARS_RE.match(text[m_.start():].strip()) and not unit:
            continue  # "5 years" is not an amount
        val = num * MULT.get(unit, 1)
        if val >= 100 and (best is None or val > best):
            best = val
    return best


def _fmt_inr(x: float | None) -> str:
    if x is None:
        return "n/a"
    if x >= 1e7:
        return f"₹{x/1e7:.2f} crore"
    if x >= 1e5:
        return f"₹{x/1e5:.2f} lakh"
    return f"₹{x:,.0f}"


def _p(x: float | None) -> str:
    return "n/a" if x is None else f"{x*100:+.1f}%"


def _ask_offline(question: str, lang: str, category: str) -> dict[str, Any]:
    q = question.lower()
    trace: list[dict] = []
    asset_id = find_asset(q)
    lines: list[str] = []
    if category != "ok":
        lines.append(REFRAME[category])

    def call(name, **kw):
        out, err = run_tool(name, kw)
        trace.append({"name": name, "input": kw, "error": err})
        return out

    amount = parse_amount(question)
    ym = YEARS_RE.search(question)
    years = float(ym.group(1)) if ym else None

    wants_news = re.search(r"why|news|this week|recently|लिए क्यों|क्यों", q)
    wants_dips = re.search(r"dip|crash|correction|fell \d+|fall of|dropped \d+|\d+%", q)
    if asset_id and amount and (years or "invest" in q or "put" in q):
        mode = "sip" if re.search(r"\bsip\b|monthly|per month|every month|हर महीने", q) else "lumpsum"
        r = call("simulate", asset_id=asset_id, mode=mode, amount=amount, years=years or 5)
        if "error" not in r:
            name = services.get_asset(asset_id)["name"]
            what = f"{_fmt_inr(amount)} every month" if mode == "sip" else f"{_fmt_inr(amount)} once"
            lines.append(
                f"If you had invested **{what}** in **{name}** from {r['start']} to {r['end']} ({r['years']} years), "
                f"you'd have put in {_fmt_inr(r['invested'])} and it would have been worth **{_fmt_inr(r['final_value'])}** "
                f"— a gain of {_fmt_inr(r['gain'])} ({_p(r['absolute_return'])}). Annualised return (XIRR): **{_p(r['xirr'])}**.")
            if r.get("fd_final"):
                lines.append(f"For comparison, the same money in a 1-year FD (rolled over) would be about {_fmt_inr(r['fd_final'])}, "
                             f"and just keeping pace with inflation needed {_fmt_inr(r['inflation_final'])}.")
    elif asset_id and wants_news:
        mtr = call("get_metrics", asset_id=asset_id)
        news = call("search_news", query=question, asset_id=asset_id)
        rec = mtr.get("recent", {})
        lines.append(f"**{mtr['asset']}** moved {_p(rec.get('1W'))} over the past week and {_p(rec.get('1M'))} over the past month.")
        if news:
            lines.append("Recent headlines that may be related:")
            lines += [f"- [{n['n']}] {n['title']} — *{n['source']}*" for n in news[:4]]
            lines.append("Markets move for many reasons at once; headlines show what was in the news, not a proven cause.")
        else:
            lines.append("I don't have recent news stored yet (run `python -m pipeline news`).")
    elif asset_id and (wants_dips or category == "prediction"):
        thr = 20.0 if "20" in q else 10.0
        r = call("dip_history", asset_id=asset_id, threshold_pct=thr)
        s3 = (r.get("summary") or {}).get("3y") or {}
        s1 = (r.get("summary") or {}).get("1y") or {}
        name = services.get_asset(asset_id)["name"]
        lines.append(f"Since its data begins, **{name}** fell {thr:.0f}%+ from a peak **{r['event_count']} times**.")
        if s1:
            lines.append(f"1 year after those falls it was higher in **{s1['win_rate']*100:.0f}%** of cases (average {_p(s1['avg_return'])}).")
        if s3:
            lines.append(f"3 years later: higher in **{s3['win_rate']*100:.0f}%** of cases (average {_p(s3['avg_return'])}, worst {_p(s3['worst'])}).")
        lines.append(f"Right now it is {_p(r['current_drawdown'])} from its all-time high. Past patterns may not repeat.")
    elif asset_id:
        mtr = call("get_metrics", asset_id=asset_id)
        tr = mtr.get("trailing") or {}
        mdd = mtr.get("max_drawdown") or {}
        lines.append(
            f"**{mtr['asset']}**: 1-year return {_p((tr.get('1Y') or {}).get('absolute'))}, 5-year CAGR "
            f"{_p((tr.get('5Y') or {}).get('cagr'))}, long-run CAGR {_p(mtr.get('cagr_since_start'))} since {mtr['start_date']}. "
            f"Risk: **{mtr.get('risk_label')}** (volatility {_p(mtr.get('volatility'))}). Worst fall: {_p(mdd.get('depth'))}.")
        lines.append(f"After inflation, the long-run real return was about {_p((mtr.get('benchmarks') or {}).get('real_cagr'))} a year.")
    else:
        assets = call("list_assets")
        lines.append("I can answer questions about these assets: " + ", ".join(a["name"] for a in assets[:18]) + ".")
        lines.append("Try: *“What if I put ₹1 lakh in Nifty for 5 years?”*, *“₹5000 monthly SIP in gold for 10 years”*, "
                     "*“What happened after gold fell 10%?”* or *“Why did silver fall this week?”*")
    if lang == "hi":
        lines.insert(0, "_(ऑफ़लाइन मोड: हिंदी उत्तर के लिए ANTHROPIC_API_KEY सेट करें।)_")
    return {"answer": "\n\n".join(lines), "tool_calls": trace, "mode": "offline"}
