"""Load test: simulates visitors browsing the app.

    locust -f tests/load/locustfile.py --host http://localhost:8000 --headless -u 500 -r 50 -t 1m --csv docs/loadtest
"""
import random

from locust import HttpUser, between, task

ASSETS = ["gold", "silver", "nifty50", "sensex", "niftybank", "ppfas-flexi", "sbi-smallcap", "uti-nifty50"]
RANGES = ["1M", "1Y", "5Y", "MAX"]


class Visitor(HttpUser):
    wait_time = between(1, 3)

    @task(5)
    def explore(self):
        self.client.get("/assets")

    @task(4)
    def asset_page(self):
        a = random.choice(ASSETS)
        self.client.get(f"/assets/{a}/prices?range={random.choice(RANGES)}", name="/assets/[id]/prices")
        self.client.get(f"/assets/{a}/metrics", name="/assets/[id]/metrics")
        self.client.get(f"/assets/{a}/drawdown", name="/assets/[id]/drawdown")

    @task(2)
    def dips(self):
        self.client.get(f"/assets/{random.choice(ASSETS)}/dip-history?threshold=10", name="/assets/[id]/dip-history")

    @task(2)
    def simulate(self):
        self.client.post("/simulate/sip", json={"asset_id": random.choice(ASSETS), "amount": 5000,
                                                 "years": random.choice([3, 5, 10])}, name="/simulate/sip")

    @task(1)
    def live(self):
        self.client.get("/live")
