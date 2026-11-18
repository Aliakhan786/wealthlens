"""Risk-profile quiz. Output is an *educational* example mix, not a recommendation."""
from __future__ import annotations

QUESTIONS = [
    {"id": "horizon", "text": "When will you likely need this money?", "options": [
        {"label": "Within 1 year", "score": 0}, {"label": "1–3 years", "score": 1},
        {"label": "3–7 years", "score": 3}, {"label": "More than 7 years", "score": 4}]},
    {"id": "reaction", "text": "Your investment falls 20% in a month. What do you most likely do?", "options": [
        {"label": "Sell everything to stop the loss", "score": 0}, {"label": "Sell some", "score": 1},
        {"label": "Do nothing and wait", "score": 3}, {"label": "Invest more", "score": 4}]},
    {"id": "goal", "text": "What matters most to you?", "options": [
        {"label": "Never losing money", "score": 0}, {"label": "Beating FD returns a little", "score": 1},
        {"label": "Steady growth above inflation", "score": 3}, {"label": "Maximum long-term growth", "score": 4}]},
    {"id": "emergency", "text": "Do you have an emergency fund (3–6 months of expenses)?", "options": [
        {"label": "No", "score": 0}, {"label": "Partly", "score": 1}, {"label": "Yes", "score": 3}]},
    {"id": "experience", "text": "Have you invested in equity / mutual funds before?", "options": [
        {"label": "Never", "score": 0}, {"label": "A little", "score": 1},
        {"label": "Yes, through ups and downs", "score": 3}]},
    {"id": "income", "text": "How stable is your income?", "options": [
        {"label": "Irregular", "score": 0}, {"label": "Mostly stable", "score": 2}, {"label": "Very stable", "score": 3}]},
]
MAX_SCORE = sum(max(o["score"] for o in q["options"]) for q in QUESTIONS)

PROFILES = [
    (0.25, "Conservative", {"Debt / FD": 70, "Gold": 15, "Large-cap equity": 15}),
    (0.45, "Moderately conservative", {"Debt / FD": 50, "Gold": 15, "Large-cap equity": 30, "Flexi / mid-cap": 5}),
    (0.65, "Balanced", {"Debt / FD": 35, "Gold": 10, "Large-cap equity": 35, "Flexi / mid-cap": 20}),
    (0.82, "Growth", {"Debt / FD": 20, "Gold": 10, "Large-cap equity": 40, "Flexi / mid-cap": 20, "Small-cap": 10}),
    (1.01, "Aggressive", {"Debt / FD": 10, "Gold": 5, "Large-cap equity": 40, "Flexi / mid-cap": 30, "Small-cap": 15}),
]
EXAMPLE_ASSETS = {"Gold": ["gold", "goldbees"], "Large-cap equity": ["nifty50", "uti-nifty50", "sbi-largecap"],
                  "Flexi / mid-cap": ["ppfas-flexi", "hdfc-midcap", "motilal-midcap150"],
                  "Small-cap": ["sbi-smallcap", "nippon-smallcap"], "Debt / FD": []}


def score_quiz(answers: dict[str, int]) -> dict:
    """answers: question id -> chosen option index."""
    total = 0
    for q in QUESTIONS:
        idx = answers.get(q["id"])
        if idx is None or not 0 <= idx < len(q["options"]):
            raise ValueError(f"Missing or invalid answer for '{q['id']}'")
        total += q["options"][idx]["score"]
    ratio = total / MAX_SCORE
    # Safety override: no emergency fund or a <1y horizon caps the profile
    capped = answers["emergency"] == 0 or answers["horizon"] == 0
    name, mix = next((n, m) for cutoff, n, m in PROFILES if ratio < cutoff)
    if capped and name not in ("Conservative", "Moderately conservative"):
        name, mix = PROFILES[1][1], PROFILES[1][2]
    return {
        "score": total, "max_score": MAX_SCORE, "profile": name,
        "mix": [{"bucket": k, "pct": v, "examples": EXAMPLE_ASSETS.get(k, [])} for k, v in mix.items()],
        "capped": capped,
        "note": ("This is an educational example of how people with similar answers often think about mixing assets. "
                 "It is not a recommendation. A SEBI-registered investment adviser can help with a personal plan."),
    }
