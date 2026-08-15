"""Data Source #2: extract shipment tracking events + carrier performance
from the simulated shipping-carrier REST API (shipping_api_server.py).

Handles pagination and retries against transient 503s, the way a real
integration against a third-party carrier API would.
"""
import time
import pandas as pd
import requests

BASE_URL = "http://127.0.0.1:5055/api/v1"
MAX_RETRIES = 4


def _get_with_retry(url, params=None):
    for attempt in range(MAX_RETRIES):
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        time.sleep(0.2 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url} after {MAX_RETRIES} retries (last status={resp.status_code})")


def extract_shipping_events() -> pd.DataFrame:
    all_rows = []
    page = 1
    while True:
        data = _get_with_retry(f"{BASE_URL}/shipments/events", params={"page": page})
        rows = data["results"]
        if not rows:
            break
        all_rows.extend(rows)
        if len(all_rows) >= data["total_rows"]:
            break
        page += 1
    df = pd.DataFrame(all_rows)
    print(f"[extract_shipping_api] pulled {len(df):,} tracking events across {page} page(s)")
    return df


def extract_carrier_performance() -> pd.DataFrame:
    data = _get_with_retry(f"{BASE_URL}/carriers/performance")
    df = pd.DataFrame(list(data.items()), columns=["carrier", "api_on_time_rate"])
    print(f"[extract_shipping_api] pulled carrier performance for {len(df)} carriers")
    return df


if __name__ == "__main__":
    events = extract_shipping_events()
    perf = extract_carrier_performance()
    print(events.head())
    print(perf)
