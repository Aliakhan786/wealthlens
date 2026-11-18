"""API tests against the seeded sample database."""


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["db"] is True


def test_assets_list(client):
    r = client.get("/assets")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 15
    gold = next(a for a in rows if a["id"] == "gold")
    assert gold["price"] > 0 and gold["risk"] in {"Low", "Medium", "High"}
    assert gold["sparkline"]


def test_assets_filter_by_risk(client):
    rows = client.get("/assets", params={"risk": "High"}).json()
    assert all(a["risk"] == "High" for a in rows)
    assert client.get("/assets", params={"risk": "Extreme"}).status_code == 422


def test_prices_ranges(client):
    one_y = client.get("/assets/nifty50/prices", params={"range": "1Y"}).json()
    mx = client.get("/assets/nifty50/prices", params={"range": "MAX"}).json()
    assert 200 < len(one_y["candles"]) < 300
    assert mx["interval"] == "1w"
    assert client.get("/assets/nifty50/prices", params={"range": "2D"}).status_code == 422


def test_unknown_asset_404(client):
    assert client.get("/assets/doesnotexist/metrics").status_code == 404


def test_metrics_calendar_drawdown_dips(client):
    assert client.get("/assets/gold/metrics").json()["trailing"]["1Y"] is not None
    cal = client.get("/assets/gold/calendar").json()
    assert cal["days"] and cal["years_available"]
    assert client.get("/assets/gold/drawdown").json()["series"]
    dips = client.get("/assets/gold/dip-history", params={"threshold": 10}).json()
    assert "summary" in dips and "events" in dips


def test_simulators(client):
    sip = client.post("/simulate/sip", json={"asset_id": "nifty50", "amount": 5000, "years": 5}).json()
    assert sip["installments"] in (60, 61) and sip["invested"] > 0 and sip["fd_final"] > 0
    lump = client.post("/simulate/lumpsum", json={"asset_id": "gold", "amount": 100000, "years": 3}).json()
    assert lump["invested"] == 100000 and lump["path"]
    bad = client.post("/simulate/sip", json={"asset_id": "gold", "amount": -5})
    assert bad.status_code == 422


def test_compare(client):
    r = client.get("/compare", params={"ids": "gold,nifty50"}).json()
    assert set(r["growth_of_100"]) == {"gold", "nifty50"}
    assert client.get("/compare", params={"ids": "gold"}).status_code == 422


def test_quiz(client):
    qs = client.get("/quiz/questions").json()
    answers = {q["id"]: len(q["options"]) - 1 for q in qs}
    r = client.post("/quiz/risk-profile", json={"answers": answers}).json()
    assert r["profile"] == "Aggressive" and sum(b["pct"] for b in r["mix"]) == 100
    answers["emergency"] = 0  # safety cap
    assert client.post("/quiz/risk-profile", json={"answers": answers}).json()["profile"] == "Moderately conservative"


def test_live(client):
    rows = client.get("/live").json()
    assert rows and all("price" in r for r in rows)


def test_ai_explain_offline(client):
    r = client.post("/ai/explain", json={"asset_id": "gold", "lang": "en"}).json()
    assert "Not investment advice" in r["text"] and r["source"] == "template"


def test_ai_ask_offline_simulation(client):
    r = client.post("/ai/ask", json={"question": "What if I put ₹1 lakh in Nifty for 5 years?"}).json()
    assert r["tool_calls"][0]["name"] == "simulate"
    assert "Not investment advice" in r["answer"]


def test_ai_ask_guardrail(client):
    r = client.post("/ai/ask", json={"question": "Should I buy gold now? Will gold go up next month?"}).json()
    assert r["category"] in {"prediction", "advice"}
    assert "can't" in r["answer"]
