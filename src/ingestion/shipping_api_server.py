"""
Simulated shipping-carrier REST API (Data Source #2).

Represents the kind of third-party carrier tracking API a real supply-chain
pipeline would integrate (e.g. EasyPost, Shippo, carrier-native APIs).
Serves JSON over HTTP from the seed data generated in
generate_seed_dataset.py, including a couple of realistic API quirks
(pagination, rate-limit header, occasional 500) so the extractor has to
handle them the way it would against a real vendor API.

Run:  python -m src.ingestion.shipping_api_server
Then: GET http://127.0.0.1:5055/api/v1/shipments/events?order_id=ORD-100001
      GET http://127.0.0.1:5055/api/v1/carriers/performance
"""
import os
import random
import time

import pandas as pd
from flask import Flask, jsonify, request

SEED_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "seed", "shipping_events_seed.parquet")

app = Flask(__name__)
_events_df = None
_rng = random.Random(7)


def _load():
    global _events_df
    if _events_df is None:
        _events_df = pd.read_parquet(SEED_PATH)
    return _events_df


@app.route("/api/v1/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/v1/shipments/events", methods=["GET"])
def shipment_events():
    df = _load()
    order_id = request.args.get("order_id")
    page = int(request.args.get("page", 1))
    page_size = 500

    if order_id:
        result = df[df["order_id"] == order_id]
    else:
        start = (page - 1) * page_size
        result = df.iloc[start:start + page_size]

    # Simulate occasional transient failure, like a real vendor API.
    if _rng.random() < 0.01:
        return jsonify({"error": "upstream_timeout"}), 503

    resp = jsonify({
        "page": page,
        "page_size": page_size,
        "total_rows": len(df),
        "results": result.to_dict(orient="records"),
    })
    resp.headers["X-RateLimit-Remaining"] = str(_rng.randint(50, 500))
    return resp


@app.route("/api/v1/carriers/performance", methods=["GET"])
def carrier_performance():
    df = _load()
    delayed = df[df["event_type"] == "DELAYED"].groupby("carrier").size()
    total = df.groupby("carrier").size()
    perf = (1 - (delayed / total).fillna(0)).round(4)
    return jsonify(perf.to_dict())


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5055)
