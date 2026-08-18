"""
Generates the two raw source datasets for the Supply Chain Logistics Pipeline:

  1. data/raw/kaggle_supply_chain_orders.csv
     -- simulates the "Kaggle Supply Chain Analytics" order-level extract.
        Deliberately contains realistic data-quality issues (missing values,
        inconsistent category casing, invalid coordinates, duplicate rows,
        malformed dates) that the cleaning stage must handle.

  2. data/seed/shipping_events_seed.parquet
     -- backing data for the simulated shipping-carrier REST API (source #2).
        Tracking events per order: pickup, in-transit scans, delivery,
        delay reasons, carrier performance history.

Run: python -m src.ingestion.generate_seed_dataset
"""
import os
import sys
import random
import string
import datetime as dt

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.utils.reference_data import (
    RANDOM_SEED, CARRIERS, SHIPPING_MODES, PRODUCT_CATEGORIES,
    CUSTOMER_SEGMENTS, ORDER_STATUSES, DELAY_REASONS, REGIONS, WAREHOUSES,
)

N_ORDERS = 105_000
START_DATE = dt.date(2023, 1, 1)
END_DATE = dt.date(2025, 12, 31)
DATE_SPAN_DAYS = (END_DATE - START_DATE).days

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw")
SEED_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "seed")
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(SEED_DIR, exist_ok=True)

rng = random.Random(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# Per-carrier "true" reliability, used to bias delay simulation realistically.
CARRIER_RELIABILITY = {
    "DHL Express": 0.90, "FedEx": 0.88, "UPS": 0.87,
    "Maersk Line": 0.78, "DB Schenker": 0.84, "Local Courier Co": 0.72,
}
# Seasonal demand multiplier by month (peaks around Nov/Dec holiday shopping).
MONTH_DEMAND_INDEX = {1: 0.85, 2: 0.82, 3: 0.90, 4: 0.92, 5: 0.95, 6: 0.98,
                      7: 1.00, 8: 1.02, 9: 1.05, 10: 1.15, 11: 1.45, 12: 1.55}


def _rand_region():
    return rng.choice(list(REGIONS.keys()))


def _coords_for_region(region, invalid=False):
    spec = REGIONS[region]
    if invalid:
        # Inject an out-of-range coordinate (must be caught by validation).
        return round(rng.uniform(-200, 200), 5), round(rng.uniform(-300, 300), 5)
    lat = round(rng.uniform(*spec["lat_range"]), 5)
    lon = round(rng.uniform(*spec["lon_range"]), 5)
    return lat, lon


def _order_id(i):
    return f"ORD-{100000 + i}"


def _customer_id(i):
    return f"CUST-{20000 + (i % 38000)}"


def _product_id(category, i):
    return f"PRD-{category[:3].upper()}-{1000 + (i % 4000)}"


def build_orders():
    rows = []
    for i in range(N_ORDERS):
        order_id = _order_id(i)
        order_days_offset = rng.randint(0, DATE_SPAN_DAYS)
        order_date = START_DATE + dt.timedelta(days=order_days_offset)
        month = order_date.month

        region = _rand_region()
        spec = REGIONS[region]
        dest_country = rng.choice(spec["countries"])
        dest_city = rng.choice(spec["cities"])

        origin_wh = rng.choice([w for w in WAREHOUSES] )
        carrier = rng.choices(CARRIERS, weights=[18, 20, 20, 12, 15, 15])[0]
        shipping_mode = rng.choices(SHIPPING_MODES, weights=[55, 15, 20, 10])[0]
        category = rng.choice(PRODUCT_CATEGORIES)
        segment = rng.choice(CUSTOMER_SEGMENTS)

        quantity = rng.choices([1, 2, 3, 4, 5, 8, 12, 24], weights=[35, 25, 15, 10, 6, 4, 3, 2])[0]
        unit_price = round(np.random.lognormal(mean=3.4, sigma=0.9), 2)
        unit_price = float(min(max(unit_price, 3.5), 3800.0))
        discount_rate = rng.choice([0, 0, 0, 0.05, 0.10, 0.15, 0.20, 0.25])

        weight_kg = round(max(0.1, np.random.gamma(2.0, 2.2)), 2)

        # base distance proxy via region "distance tier"
        distance_km = round(rng.uniform(50, 500) if region in ("North America", "Europe")
                             else rng.uniform(500, 14000), 1)

        promised_days = {"Same Day": 1, "First Class": 2, "Second Class": 4, "Standard Class": 6}[shipping_mode]
        # scale promise slightly by distance
        promised_days = promised_days + (1 if distance_km > 4000 else 0) + (1 if distance_km > 9000 else 0)

        reliability = CARRIER_RELIABILITY[carrier]
        demand_idx = MONTH_DEMAND_INDEX[month]
        # higher demand -> slightly higher chance of delay (warehouse strain)
        delay_prob = (1 - reliability) * (0.85 + 0.3 * (demand_idx - 1))
        delay_prob = min(max(delay_prob, 0.03), 0.65)

        is_delayed = rng.random() < delay_prob
        if is_delayed:
            extra_days = rng.choices([1, 2, 3, 4, 5, 7, 10], weights=[30, 25, 18, 12, 8, 5, 2])[0]
            delay_reason = rng.choice([d for d in DELAY_REASONS if d != "None"])
        else:
            extra_days = rng.choice([-1, 0, 0, 0, 0, 1])  # occasionally early
            delay_reason = "None"
        actual_days = max(1, promised_days + extra_days)

        shipping_cost = round(
            (2.5 + 0.015 * distance_km + 0.9 * weight_kg) *
            (1.6 if shipping_mode == "Same Day" else 1.25 if shipping_mode == "First Class" else 1.0),
            2,
        )

        order_status = rng.choices(ORDER_STATUSES, weights=[78, 6, 6, 7, 3])[0]

        lat, lon = _coords_for_region(region, invalid=(rng.random() < 0.015))

        row = {
            "order_id": order_id,
            "order_date": order_date.isoformat(),
            "customer_id": _customer_id(i),
            "customer_segment": segment,
            "product_id": _product_id(category, i),
            "product_category": category if rng.random() > 0.04 else category.upper(),  # inconsistent casing
            "quantity": quantity,
            "unit_price": unit_price,
            "discount_rate": discount_rate,
            "weight_kg": weight_kg,
            "origin_warehouse_id": origin_wh["warehouse_id"],
            "origin_region": origin_wh["region"],
            "destination_city": dest_city,
            "destination_country": dest_country,
            "destination_region": region,
            "destination_latitude": lat,
            "destination_longitude": lon,
            "distance_km": distance_km,
            "carrier": carrier,
            "shipping_mode": shipping_mode,
            "promised_delivery_days": promised_days,
            "actual_delivery_days": actual_days if rng.random() > 0.02 else np.nan,  # ~2% missing
            "shipping_cost": shipping_cost if rng.random() > 0.01 else np.nan,       # ~1% missing
            "order_status": order_status,
            "delay_reason": delay_reason,
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Inject duplicate rows (~0.5%) to be caught by dedup step.
    dupes = df.sample(frac=0.005, random_state=RANDOM_SEED)
    df = pd.concat([df, dupes], ignore_index=True)

    # Inject a handful of malformed date strings (~0.3%) to be caught by date validation.
    malformed_idx = df.sample(frac=0.003, random_state=RANDOM_SEED + 1).index
    df.loc[malformed_idx, "order_date"] = "2025-13-45"  # invalid month/day

    # Shuffle rows so quality issues aren't clustered.
    df = df.sample(frac=1.0, random_state=RANDOM_SEED).reset_index(drop=True)
    return df


def build_shipping_events(orders_df):
    """Second-source seed data: granular tracking events per order, used by
    the simulated shipping-carrier API (src/ingestion/shipping_api_server.py)."""
    events = []
    base_flow = ["PICKED_UP", "IN_TRANSIT", "CUSTOMS", "OUT_FOR_DELIVERY", "DELIVERED"]
    for _, r in orders_df.iterrows():
        try:
            base_date = dt.date.fromisoformat(str(r["order_date"]))
        except ValueError:
            base_date = START_DATE
        was_delayed = str(r["delay_reason"]) != "None"
        n_steps = rng.randint(2, 4)
        flow = base_flow[:n_steps] if n_steps < len(base_flow) else list(base_flow)
        if was_delayed:
            # insert a DELAYED event before final delivery
            flow = flow[:-1] + ["DELAYED"] + [flow[-1]]
        t = base_date
        for etype in flow:
            t = t + dt.timedelta(days=rng.randint(0, 2))
            events.append({
                "order_id": r["order_id"],
                "carrier": r["carrier"],
                "event_timestamp": t.isoformat(),
                "event_type": etype,
                "location": r["destination_city"],
                "delay_reason": r["delay_reason"] if etype == "DELAYED" else "None",
            })
    return pd.DataFrame(events)


def build_events_only(orders_csv=None, sample_size=60000):
    """Regenerate only the tracking events, keyed to an existing orders CSV.

    Source #2 (the simulated carrier API) serves events joined to orders on
    order_id. When Source #1 is the real Kaggle dataset, events generated
    against the *synthetic* order ids would not join to anything, so the
    events must be rebuilt from whichever orders file is actually in place.
    """
    if orders_csv is None:
        orders_csv = os.path.join(RAW_DIR, "kaggle_supply_chain_orders.csv")
    orders_df = pd.read_csv(orders_csv, low_memory=False)
    print(f"Building tracking events from {len(orders_df):,} orders in "
          f"{os.path.basename(orders_csv)} ...")

    # build_shipping_events needs these columns; fill any the source lacks.
    for col, default in [("carrier", "Local Courier Co"),
                         ("destination_city", "Unknown"),
                         ("delay_reason", "None")]:
        if col not in orders_df.columns:
            orders_df[col] = default
        else:
            orders_df[col] = orders_df[col].fillna(default)

    sample = orders_df.sample(n=min(sample_size, len(orders_df)),
                              random_state=RANDOM_SEED)
    events_df = build_shipping_events(sample)
    os.makedirs(SEED_DIR, exist_ok=True)
    events_out = os.path.join(SEED_DIR, "shipping_events_seed.parquet")
    events_df.to_parquet(events_out, index=False)
    print(f"  -> wrote {len(events_df):,} tracking events to {events_out}")
    return events_df


def main():
    print(f"Generating {N_ORDERS:,} synthetic supply-chain orders (seed={RANDOM_SEED})...")
    orders_df = build_orders()
    out_csv = os.path.join(RAW_DIR, "kaggle_supply_chain_orders.csv")
    orders_df.to_csv(out_csv, index=False)
    print(f"  -> wrote {len(orders_df):,} rows to {out_csv}")

    print("Generating shipping tracking-event seed data (source for simulated API)...")
    events_df = build_shipping_events(orders_df.sample(n=min(60000, len(orders_df)), random_state=RANDOM_SEED))
    events_out = os.path.join(SEED_DIR, "shipping_events_seed.parquet")
    events_df.to_parquet(events_out, index=False)
    print(f"  -> wrote {len(events_df):,} tracking events to {events_out}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--events-only", action="store_true",
        help="Rebuild only the API's tracking events, keyed to the orders CSV "
             "already in data/raw/ (use after importing the real Kaggle data).")
    parser.add_argument("--orders-csv", default=None,
                        help="Orders CSV to key the events to.")
    args = parser.parse_args()

    if args.events_only:
        build_events_only(args.orders_csv)
    else:
        main()
