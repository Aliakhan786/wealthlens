"""Guardrails: keep the assistant educational. No buy/sell calls, no price predictions, always a disclaimer."""
from __future__ import annotations

import re

DISCLAIMER = ("Educational information based on historical data only. Not investment advice. "
              "WealthLens is not SEBI-registered.")
DISCLAIMER_HI = "यह केवल ऐतिहासिक डेटा पर आधारित शैक्षिक जानकारी है। निवेश सलाह नहीं। WealthLens SEBI-पंजीकृत नहीं है।"

PREDICTION_PATTERNS = [
    r"\bwill\b.{0,40}\b(go up|go down|rise|fall|crash|rally|reach|hit|touch|cross)\b",
    r"\b(predict|prediction|forecast|price target|target price)\b",
    r"\b(tomorrow|next week|next month|next year|by (19|20)\d\d)\b.{0,30}\b(price|level|value)\b",
    r"\bwhere will\b",
    r"(बढ़ेगा|गिरेगा|बढ़ेगी|गिरेगी|भविष्यवाणी)",  # Hindi: "will rise / will fall / prediction"
]
ADVICE_PATTERNS = [
    r"\bshould i (buy|sell|invest|exit|redeem|book profit)",
    r"\b(is it|is now) (a )?(good|right|best) time to (buy|sell|invest)",
    r"\bwhich (fund|stock|asset) (should|to) (i )?(buy|pick|choose)",
    r"\b(buy|sell) (or|vs) (hold|sell|buy)\b",
    r"\b(best|top) (fund|stock|investment) (to|for) (buy|invest)",
    r"(खरीद|बेच|निवेश)\S*\s+(करना\s+)?चाहिए",  # Hindi: "should (I) buy / sell / invest"
]
UNSAFE_OUTPUT_PATTERNS = [
    r"\byou should (buy|sell|invest in|exit|redeem|switch to)\b",
    r"\bi (would )?(recommend|suggest|advise) (you )?(buy|sell|invest|exit)",
    r"\b(strong )?(buy|sell) (signal|call|rating|recommendation)\b",
    r"\b(will|is going to|is likely to|is expected to) (rise|fall|reach|hit|cross|double|crash|go up|go down)\b",
    r"\b(price target|target price) of\b",
    r"\bguaranteed (return|profit)s?\b",
]
_P = [re.compile(p, re.I) for p in PREDICTION_PATTERNS]
_A = [re.compile(p, re.I) for p in ADVICE_PATTERNS]
_U = [re.compile(p, re.I) for p in UNSAFE_OUTPUT_PATTERNS]
SENTENCE_RE = re.compile(r"(?<=[.!?।])\s+")


def classify_input(text: str) -> str:
    """Return 'prediction', 'advice', or 'ok'. Used to steer (not block) the reply."""
    if any(p.search(text) for p in _P):
        return "prediction"
    if any(p.search(text) for p in _A):
        return "advice"
    return "ok"


REFRAME = {
    "prediction": ("I can't predict future prices — nobody reliably can. What I can do is show what happened "
                   "historically in similar situations, which is often more useful."),
    "advice": ("I can't tell you what to buy or sell, because I don't know your goals, timeline or situation, and "
               "I'm not a registered adviser. Here are the historical facts that can help you decide yourself."),
}


def sanitize_output(text: str, lang: str = "en") -> tuple[str, list[str]]:
    """Strip sentences that read like advice or forecasts; ensure the disclaimer is present."""
    flagged: list[str] = []
    kept = []
    for sentence in SENTENCE_RE.split(text.strip()):
        if any(p.search(sentence) for p in _U):
            flagged.append(sentence)
            continue
        kept.append(sentence)
    out = " ".join(kept).strip()
    if flagged:
        out += "\n\n_(Some wording was removed because WealthLens doesn't give buy/sell calls or forecasts.)_"
    disclaimer = DISCLAIMER_HI if lang == "hi" else DISCLAIMER
    if disclaimer not in out:
        out += f"\n\n> {disclaimer}"
    return out, flagged


def is_compliant(text: str) -> bool:
    return not any(p.search(text) for p in _U) and (DISCLAIMER in text or DISCLAIMER_HI in text)
