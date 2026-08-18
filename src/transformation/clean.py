"""Cleaning & transformation stage.

Tasks (per assessment spec):
  - handle missing values
  - standardize product categories (casing/whitespace)
  - validate dates (drop/repair malformed order_date)
  - remove invalid coordinates (lat/lon out of valid range)
  - convert types
  - remove duplicate rows
"""
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.utils.parquet_io import write_parquet

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)


def clean_orders(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    stats = {"input_rows": len(df)}
    df = df.copy()

    # 1. Remove exact duplicate rows
    before = len(df)
    df = df.drop_duplicates()
    stats["duplicates_removed"] = before - len(df)

    # 2. Validate / repair dates -> coerce invalid to NaT, then drop
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    stats["invalid_dates_dropped"] = int(df["order_date"].isna().sum())
    df = df.dropna(subset=["order_date"])

    # 3. Standardize categorical text (casing / whitespace)
    df["product_category"] = df["product_category"].str.strip().str.title()
    df["carrier"] = df["carrier"].str.strip()
    df["order_status"] = df["order_status"].str.strip().str.upper()

    # 4. Remove invalid coordinates (valid lat in [-90,90], lon in [-180,180])
    valid_coords = df["destination_latitude"].between(-90, 90) & df["destination_longitude"].between(-180, 180)
    stats["invalid_coordinates_removed"] = int((~valid_coords).sum())
    df = df[valid_coords]

    # 5. Handle missing values
    #    - actual_delivery_days: impute with per-(carrier, shipping_mode) median, else global median
    stats["missing_actual_delivery_days_before"] = int(df["actual_delivery_days"].isna().sum())
    df["actual_delivery_days"] = df.groupby(["carrier", "shipping_mode"])["actual_delivery_days"].transform(
        lambda s: s.fillna(s.median())
    )
    df["actual_delivery_days"] = df["actual_delivery_days"].fillna(df["actual_delivery_days"].median())

    #    - shipping_cost: impute with per-shipping_mode median
    stats["missing_shipping_cost_before"] = int(df["shipping_cost"].isna().sum())
    df["shipping_cost"] = df.groupby("shipping_mode")["shipping_cost"].transform(lambda s: s.fillna(s.median()))
    df["shipping_cost"] = df["shipping_cost"].fillna(df["shipping_cost"].median())

    # 6. Convert types
    df["quantity"] = df["quantity"].astype(int)
    df["actual_delivery_days"] = df["actual_delivery_days"].round().astype(int)
    df["promised_delivery_days"] = df["promised_delivery_days"].astype(int)
    df["unit_price"] = df["unit_price"].astype(float).round(2)
    df["shipping_cost"] = df["shipping_cost"].astype(float).round(2)
    df["order_date"] = pd.to_datetime(df["order_date"])

    stats["output_rows"] = len(df)
    stats["rows_dropped_total"] = stats["input_rows"] - stats["output_rows"]
    return df.reset_index(drop=True), stats


def clean_events(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.drop_duplicates()
    df["event_timestamp"] = pd.to_datetime(df["event_timestamp"], errors="coerce")
    df = df.dropna(subset=["event_timestamp"])
    df["event_type"] = df["event_type"].str.strip().str.upper()
    return df.reset_index(drop=True)


def main():
    import sqlite3
    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "supply_chain_raw.db"))
    orders_raw = pd.read_sql("SELECT * FROM orders_raw", conn)
    events_raw = pd.read_sql("SELECT * FROM shipping_events_raw", conn)
    conn.close()

    orders_clean, stats = clean_orders(orders_raw)
    events_clean = clean_events(events_raw)

    write_parquet(orders_clean, os.path.join(PROCESSED_DIR, "orders_clean.parquet"))
    write_parquet(events_clean, os.path.join(PROCESSED_DIR, "events_clean.parquet"))

    print("[clean] Cleaning summary:")
    for k, v in stats.items():
        print(f"    {k}: {v}")
    print(f"[clean] wrote {len(orders_clean):,} clean order rows, {len(events_clean):,} clean event rows")
    return stats


if __name__ == "__main__":
    main()
