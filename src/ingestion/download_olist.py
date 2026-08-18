"""Second real dataset: Olist Brazilian E-Commerce (Kaggle).

Why a second source
-------------------
DataCo (Source #1) has real delivery dates, coordinates, categories, prices,
discounts and shipping modes, but carries no shipping cost, package weight,
distance or carrier. Olist carries exactly those: a real freight charge per
item, a real product weight, and postcode-level coordinates for *both* the
seller and the customer, so the shipping distance can be computed as a real
geodesic rather than invented.

The two datasets describe different orders and cannot be joined, so they are
*unioned* into the shared schema with a `source_system` column recording each
row's provenance. Anything a source genuinely lacks is left null for the
cleaning stage, rather than fabricated.

This module produces two outputs:

  data/raw/olist_orders_mapped.csv      canonical-schema orders (Source #2, file)
  data/seed/olist_tracking_events.parquet
                                        real delivery milestones, served by the
                                        carrier API (Source #2, REST)

Olist records four genuine timestamps per order -- purchased, approved,
handed to the carrier, delivered -- so the tracking events the API serves are
real events with real timings, not simulated ones.

Usage
-----
    export KAGGLE_API_TOKEN=<token>
    python -m src.ingestion.download_olist
    python -m src.ingestion.download_olist --skip-download   # reuse local copy
"""
import argparse
import os
import shutil
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.utils.parquet_io import write_parquet

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
SEED_DIR = os.path.join(PROJECT_ROOT, "data", "seed")
DOWNLOAD_DIR = os.path.join(RAW_DIR, "olist_download")
TARGET_CSV = os.path.join(RAW_DIR, "olist_orders_mapped.csv")
EVENTS_PARQUET = os.path.join(SEED_DIR, "olist_tracking_events.parquet")

DATASET = "olistbr/brazilian-ecommerce"
EARTH_RADIUS_KM = 6371.0


def download():
    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    if os.path.isdir(DOWNLOAD_DIR):
        shutil.rmtree(DOWNLOAD_DIR)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    print(f"[olist] downloading {DATASET} ...")
    api.dataset_download_files(DATASET, path=DOWNLOAD_DIR, unzip=True, quiet=False)
    return DOWNLOAD_DIR


def _haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two coordinate arrays, in km."""
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def load_and_join(directory: str) -> pd.DataFrame:
    def read(name, **kw):
        return pd.read_csv(os.path.join(directory, name), low_memory=False, **kw)

    orders = read("olist_orders_dataset.csv", parse_dates=[
        "order_purchase_timestamp", "order_approved_at",
        "order_delivered_carrier_date", "order_delivered_customer_date",
        "order_estimated_delivery_date"])
    items = read("olist_order_items_dataset.csv")
    products = read("olist_products_dataset.csv")
    customers = read("olist_customers_dataset.csv")
    sellers = read("olist_sellers_dataset.csv")
    geo = read("olist_geolocation_dataset.csv")
    translation = read("product_category_name_translation.csv")

    # Postcode prefixes repeat across many rows; average to one point each.
    geo_points = (geo.groupby("geolocation_zip_code_prefix")[
        ["geolocation_lat", "geolocation_lng"]].mean())

    df = (items
          .merge(orders, on="order_id", how="inner")
          .merge(products, on="product_id", how="left")
          .merge(customers, on="customer_id", how="left")
          .merge(sellers, on="seller_id", how="left")
          .merge(translation, on="product_category_name", how="left"))

    df = df.merge(geo_points, left_on="customer_zip_code_prefix",
                  right_index=True, how="left")
    df = df.merge(geo_points, left_on="seller_zip_code_prefix",
                  right_index=True, how="left", suffixes=("_cust", "_sell"))

    print(f"[olist] joined {len(df):,} order items across 7 tables")
    return df


def map_to_schema(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)

    # --- identifiers -----------------------------------------------------
    out["order_id"] = ["ORD-OLIST-" + f"{i:07d}" for i in range(1, len(df) + 1)]
    out["order_date"] = df["order_purchase_timestamp"]
    out["customer_id"] = "CUST-" + df["customer_id"].astype(str).str[:12]

    # Olist has no segment field, but it does record whether a customer is a
    # repeat buyer, which is a real behavioural distinction.
    repeat = df["customer_unique_id"].duplicated(keep=False)
    out["customer_segment"] = np.where(repeat, "Returning", "New")

    out["product_id"] = "PROD-" + df["product_id"].astype(str).str[:12]
    category = df["product_category_name_english"].fillna(
        df["product_category_name"])
    out["product_category"] = (category.astype(str)
                               .str.replace("_", " ", regex=False)
                               .str.title()
                               .replace("Nan", np.nan))

    # --- real commercial values -----------------------------------------
    out["quantity"] = df["order_item_id"]          # item sequence => units on the order
    out["unit_price"] = df["price"]
    out["discount_rate"] = 0.0                     # Olist prices are net of discount
    out["weight_kg"] = df["product_weight_g"] / 1000.0
    out["shipping_cost"] = df["freight_value"]     # REAL per-item freight charge

    # --- origin / destination -------------------------------------------
    out["origin_warehouse_id"] = "SELLER-" + df["seller_id"].astype(str).str[:8]
    out["origin_region"] = df["seller_state"]
    out["destination_city"] = df["customer_city"].astype(str).str.title()
    out["destination_country"] = "Brazil"
    out["destination_region"] = df["customer_state"]
    out["destination_latitude"] = df["geolocation_lat_cust"]
    out["destination_longitude"] = df["geolocation_lng_cust"]

    # REAL geodesic distance between the seller's and the customer's postcode.
    out["distance_km"] = _haversine_km(
        df["geolocation_lat_sell"], df["geolocation_lng_sell"],
        df["geolocation_lat_cust"], df["geolocation_lng_cust"]).round(2)

    # Olist names no carrier; the seller is the real fulfilment party, and
    # order_delivered_carrier_date marks the real handover.
    out["carrier"] = "Seller-" + df["seller_id"].astype(str).str[:6]

    # No shipping-mode field exists. Left null rather than invented; the
    # cleaning stage imputes it like any other missing categorical.
    out["shipping_mode"] = np.nan

    # --- REAL delivery timings ------------------------------------------
    out["promised_delivery_days"] = (
        df["order_estimated_delivery_date"] - df["order_purchase_timestamp"]
    ).dt.days
    out["actual_delivery_days"] = (
        df["order_delivered_customer_date"] - df["order_purchase_timestamp"]
    ).dt.days

    out["order_status"] = df["order_status"].astype(str).str.upper()

    late = out["actual_delivery_days"] > out["promised_delivery_days"]
    out["delay_reason"] = np.where(
        out["actual_delivery_days"].isna(), "Not delivered",
        np.where(late, "Late delivery", "None"))

    return out


def build_tracking_events(df: pd.DataFrame, mapped: pd.DataFrame) -> pd.DataFrame:
    """Real delivery milestones, served by the carrier API as Source #2.

    Unlike the synthetic generator, every event here is a real recorded
    timestamp from the Olist order lifecycle.
    """
    milestones = [
        ("order_purchase_timestamp", "ORDER_PLACED"),
        ("order_approved_at", "PAYMENT_APPROVED"),
        ("order_delivered_carrier_date", "HANDED_TO_CARRIER"),
        ("order_delivered_customer_date", "DELIVERED"),
    ]
    frames = []
    for column, event_type in milestones:
        stamp = df[column]
        keep = stamp.notna()
        frames.append(pd.DataFrame({
            "order_id": mapped.loc[keep, "order_id"],
            "carrier": mapped.loc[keep, "carrier"],
            "event_timestamp": stamp[keep],
            "event_type": event_type,
            "location": mapped.loc[keep, "destination_city"],
            "delay_reason": np.where(
                (event_type == "DELIVERED") &
                (mapped.loc[keep, "delay_reason"] == "Late delivery"),
                "Late delivery", "None"),
        }))

    events = pd.concat(frames, ignore_index=True)
    events = events.sort_values(["order_id", "event_timestamp"]).reset_index(drop=True)
    events["event_timestamp"] = pd.to_datetime(events["event_timestamp"])
    return events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-download", action="store_true",
                        help="Reuse an existing copy in data/raw/olist_download/")
    args = parser.parse_args()

    directory = DOWNLOAD_DIR if args.skip_download else download()
    if not os.path.isdir(directory):
        raise RuntimeError(f"{directory} not found -- run without --skip-download first.")

    joined = load_and_join(directory)
    mapped = map_to_schema(joined)

    os.makedirs(SEED_DIR, exist_ok=True)
    mapped.to_csv(TARGET_CSV, index=False)
    print(f"[olist] wrote {len(mapped):,} orders -> {TARGET_CSV}")

    events = build_tracking_events(joined, mapped)
    write_parquet(events, EVENTS_PARQUET)
    print(f"[olist] wrote {len(events):,} REAL tracking events -> {EVENTS_PARQUET}")

    real = ["shipping_cost", "weight_kg", "distance_km",
            "promised_delivery_days", "actual_delivery_days"]
    print("[olist] real-value coverage:")
    for col in real:
        filled = mapped[col].notna().mean() * 100
        print(f"           {col:24} {filled:5.1f}% populated")


if __name__ == "__main__":
    main()
