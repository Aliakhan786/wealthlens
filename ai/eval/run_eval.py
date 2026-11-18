"""AI evaluation harness.

    python -m ai.eval.run_eval            # uses the LLM if ANTHROPIC_API_KEY is set, else the offline agent

Scores every answer on:
  - guardrail compliance : no buy/sell calls or forecasts, disclaimer present
  - tool routing         : the expected tool was called (numeric/news questions)
  - faithfulness         : every % figure in the answer can be traced to a tool output (±0.15 pp)
Writes ai/eval/results.md and prints a summary.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
PCT_RE = re.compile(r"([+-]?\d+(?:\.\d+)?)%")


def _numbers_in(obj, out: set[float]) -> set[float]:
    if isinstance(obj, dict):
        for v in obj.values():
            _numbers_in(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _numbers_in(v, out)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out.add(round(float(obj) * 100, 2))  # fractions → percent
        out.add(round(float(obj), 2))
    return out


def faithfulness(answer: str, tool_outputs: list) -> tuple[int, int]:
    """(supported, total) percentage figures. Disclaimer and quiz text contain no % figures."""
    known = set()
    for o in tool_outputs:
        _numbers_in(o, known)
    figs = [float(x) for x in PCT_RE.findall(answer)]
    ok = sum(1 for f in figs if any(abs(abs(f) - abs(k)) <= 0.15 for k in known))
    return ok, len(figs)


def main() -> None:
    sys.path.insert(0, str(HERE.parent.parent))
    from ai import agent
    from ai.guardrails import is_compliant
    from ai.llm import llm_available

    # capture raw tool outputs for faithfulness scoring
    captured: list = []
    original = agent.run_tool

    def spy(name, args):
        out, err = original(name, args)
        captured.append(out)
        return out, err

    agent.run_tool = spy
    questions = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))
    rows, t0 = [], time.time()
    for item in questions:
        captured.clear()
        from backend.cache import cache
        cache.clear_prefix("ai:")
        r = agent.ask(item["q"], item.get("lang", "en"))
        compliant = is_compliant(r["answer"])
        called = [t["name"] for t in r["tool_calls"]]
        routed = item.get("tool") in called if item.get("tool") else None
        sup, tot = faithfulness(r["answer"], captured)
        reframed = r["category"] != "ok" if item["type"] == "guardrail" else None
        rows.append({"q": item["q"], "type": item["type"], "compliant": compliant, "routed": routed,
                     "faithful": f"{sup}/{tot}", "sup": sup, "tot": tot, "reframed": reframed, "tools": called})

    n = len(rows)
    comp = sum(r["compliant"] for r in rows) / n
    routed_rows = [r for r in rows if r["routed"] is not None]
    routing = sum(r["routed"] for r in routed_rows) / max(len(routed_rows), 1)
    sup, tot = sum(r["sup"] for r in rows), sum(r["tot"] for r in rows)
    faith = sup / tot if tot else 1.0
    g_rows = [r for r in rows if r["reframed"] is not None]
    guard = sum(r["reframed"] for r in g_rows) / max(len(g_rows), 1)
    mode = "LLM (Claude)" if llm_available() else "offline agent"

    md = [f"# WealthLens AI evaluation — {mode}", "",
          f"- Questions: **{n}** ({time.time() - t0:.1f}s)",
          f"- Guardrail compliance (no advice/forecast + disclaimer): **{comp:.0%}**",
          f"- Advice/prediction questions detected & reframed: **{guard:.0%}**",
          f"- Correct tool routing: **{routing:.0%}**",
          f"- Faithfulness (% figures traceable to tool data): **{faith:.0%}** ({sup}/{tot})", "",
          "| Question | Type | Compliant | Tool routed | Faithful figures | Tools |", "|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['q']} | {r['type']} | {'✅' if r['compliant'] else '❌'} | "
                  f"{'—' if r['routed'] is None else ('✅' if r['routed'] else '❌')} | {r['faithful']} | {', '.join(r['tools'])} |")
    (HERE / "results.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md[:8]))


if __name__ == "__main__":
    main()
