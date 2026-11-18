"""'Explain this to me': the LLM explains *our* computed numbers — it never invents data."""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from ai.guardrails import sanitize_output
from ai.llm import create_message, llm_available, text_of
from ai.prompts import EXPLAIN_SYSTEM, LANG_HINT
from backend.cache import cache
from core.config import get_settings

log = logging.getLogger("wealthlens.explain")


def pct(x: float | None, digits: int = 1) -> str:
    return "n/a" if x is None else f"{x*100:+.{digits}f}%"


def pct0(x: float | None, digits: int = 1) -> str:
    """Unsigned percentage, for levels like volatility or inflation."""
    return "n/a" if x is None else f"{x*100:.{digits}f}%"


def _facts(asset: dict, snap: dict) -> dict[str, Any]:
    """Compact, model-friendly subset of the snapshot (fewer tokens, less room for confusion)."""
    tr = snap.get("trailing", {})
    return {
        "asset": asset["name"], "type": asset["asset_class"], "unit": asset["unit"],
        "data_from": snap.get("start_date"), "data_to": snap.get("end_date"),
        "latest_price": snap.get("latest_price"),
        "returns": {k: v for k, v in tr.items() if v},
        "cagr_since_start": snap.get("cagr_since_start"),
        "volatility_annual": snap.get("volatility"), "risk_label": snap.get("risk_label"),
        "max_drawdown": snap.get("max_drawdown"), "current_drawdown": snap.get("current_drawdown"),
        "best_day": snap.get("best_day"), "worst_day": snap.get("worst_day"),
        "benchmarks": snap.get("benchmarks"), "rolling_5y": (snap.get("rolling") or {}).get("5y"),
        "dip_10pct_history": (snap.get("dips") or {}).get("10"),
        "is_sample_data": asset.get("is_sample_data"),
    }


def template_explanation(asset: dict, snap: dict, lang: str = "en") -> str:
    """Deterministic fallback used when no LLM key is configured."""
    f = _facts(asset, snap)
    tr = f["returns"]
    mdd = f["max_drawdown"] or {}
    b = f["benchmarks"] or {}
    d10 = (f["dip_10pct_history"] or {}).get("summary", {}).get("3y") or {}
    y5 = (tr.get("5Y") or {}).get("cagr")
    if lang == "hi":
        parts = [
            f"**{f['asset']}** ने {f['data_from']} से अब तक लगभग **{pct(f['cagr_since_start'])} सालाना (CAGR)** की दर से बढ़त दिखाई है।",
            f"इसी अवधि में औसत महंगाई लगभग {pct0(b.get('avg_inflation'))} और FD दर लगभग {pct0(b.get('avg_fd_rate'))} रही, यानी महंगाई के बाद असली रिटर्न लगभग **{pct(b.get('real_cagr'))}** रहा।",
            f"उतार-चढ़ाव: सालाना वोलैटिलिटी {pct0(f['volatility_annual'])} — जोखिम स्तर **{f['risk_label']}**। सबसे बड़ी गिरावट **{pct(mdd.get('depth'))}** ({mdd.get('peak_date')} से {mdd.get('trough_date')}) थी।",
        ]
        if d10:
            parts.append(f"इतिहास: जब भी यह अपने शिखर से 10% गिरा, 3 साल बाद {d10.get('win_rate', 0)*100:.0f}% मामलों में यह ऊपर था (औसत {pct(d10.get('avg_return'))})। भविष्य अलग हो सकता है।")
        return "\n\n".join(parts)
    parts = [
        f"**{f['asset']}** has grown at about **{pct(f['cagr_since_start'])} a year (CAGR)** since {f['data_from']}"
        + (f", and {pct(y5)} a year over the last 5 years." if y5 is not None else "."),
        f"Over the same period inflation averaged about {pct0(b.get('avg_inflation'))} and 1-year FDs about "
        f"{pct0(b.get('avg_fd_rate'))}, so the *real* (after-inflation) growth was roughly **{pct(b.get('real_cagr'))} a year**.",
        f"The ride: annual volatility of {pct0(f['volatility_annual'])} puts it in the **{f['risk_label']}** risk bucket. "
        f"Its worst fall (max drawdown — the drop from a peak to the lowest point after it) was **{pct(mdd.get('depth'))}**, "
        f"from {mdd.get('peak_date')} to {mdd.get('trough_date')}"
        + (f", and it took about {mdd.get('months_peak_to_recovery')} months from that peak to fully recover." if mdd.get("recovered") else ", and it has not yet fully recovered."),
    ]
    if d10:
        parts.append(f"History check: each time it fell 10%+ from a peak, it was higher 3 years later in "
                     f"{d10.get('win_rate', 0)*100:.0f}% of {d10.get('observations')} cases (average {pct(d10.get('avg_return'))}). "
                     "That's history, not a promise about the future.")
    return "\n\n".join(parts)


def explain_asset(asset: dict, snap: dict, lang: str = "en") -> dict[str, Any]:
    lang = lang if lang in LANG_HINT else "en"
    key_src = json.dumps([asset["id"], lang, snap.get("end_date"), snap.get("latest_price")], default=str)
    key = "ai:explain:" + hashlib.md5(key_src.encode()).hexdigest()
    if (hit := cache.get(key)) is not None:
        return {**hit, "cached": True}

    source = "template"
    text = None
    if llm_available():
        try:
            data = json.dumps(_facts(asset, snap), default=str)
            resp = create_message(
                EXPLAIN_SYSTEM + "\n" + LANG_HINT[lang],
                [{"role": "user", "content": f"<data>\n{data}\n</data>\n\nExplain this asset to me."}],
                max_tokens=2000,
            )
            if resp.stop_reason != "refusal":
                text = text_of(resp)
                source = "llm"
        except Exception as e:
            log.warning("LLM explain failed, using template: %s", e)
    if not text:
        text = template_explanation(asset, snap, lang)
    text, flagged = sanitize_output(text, lang)
    result = {"asset_id": asset["id"], "lang": lang, "text": text, "source": source, "guardrail_flags": len(flagged)}
    cache.set(key, result, get_settings().ai_cache_ttl_seconds)
    return {**result, "cached": False}
