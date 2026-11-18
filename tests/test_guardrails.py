from ai.agent import find_asset, parse_amount
from ai.guardrails import DISCLAIMER, classify_input, is_compliant, sanitize_output


def test_classify_input():
    assert classify_input("Will gold go up next month?") == "prediction"
    assert classify_input("What is the price target for Nifty?") == "prediction"
    assert classify_input("Should I buy silver now?") == "advice"
    assert classify_input("How did gold do in 2020?") == "ok"
    assert classify_input("क्या मुझे अभी सोना खरीदना चाहिए?") == "advice"


def test_sanitize_removes_advice_and_adds_disclaimer():
    text = "Gold returned 12% last year. You should buy gold now. It will rise further."
    out, flagged = sanitize_output(text)
    assert "You should buy" not in out and "will rise" not in out
    assert len(flagged) == 2
    assert DISCLAIMER in out and is_compliant(out)


def test_parse_amount_and_asset():
    assert parse_amount("₹1 lakh in nifty for 5 years") == 100000
    assert parse_amount("5000 monthly SIP for 10 years") == 5000
    assert parse_amount("10k every month") == 10000
    assert parse_amount("2 crore") == 2e7
    assert parse_amount("₹1 लाख निफ्टी में 5 साल") == 1e5
    assert find_asset("bank nifty returns") == "niftybank"
    assert find_asset("what about gold etf") == "goldbees"
