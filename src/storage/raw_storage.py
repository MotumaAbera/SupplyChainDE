"""Persist raw ingested data in the two required storage formats:
SQLite (data/raw/supply_chain_raw.db) and Parquet (data/raw/parquet/)."""
import os
import sqlite3
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
PARQUET_DIR = os.path.join(RAW_DIR, "parquet")
SQLITE_PATH = os.path.join(RAW_DIR, "supply_chain_raw.db")

os.makedirs(PARQUET_DIR, exist_ok=True)


def store_raw(orders_df: pd.DataFrame, events_df: pd.DataFrame, carrier_perf_df: pd.DataFrame):
    # --- SQLite ---
    conn = sqlite3.connect(SQLITE_PATH)
    orders_df.to_sql("orders_raw", conn, if_exists="replace", index=False)
    events_df.to_sql("shipping_events_raw", conn, if_exists="replace", index=False)
    carrier_perf_df.to_sql("carrier_performance_raw", conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()
    print(f"[raw_storage] SQLite: wrote orders_raw({len(orders_df):,}), "
          f"shipping_events_raw({len(events_df):,}), carrier_performance_raw({len(carrier_perf_df)}) "
          f"-> {SQLITE_PATH}")

    # --- Parquet ---
    orders_df.to_parquet(os.path.join(PARQUET_DIR, "orders_raw.parquet"), index=False)
    events_df.to_parquet(os.path.join(PARQUET_DIR, "shipping_events_raw.parquet"), index=False)
    carrier_perf_df.to_parquet(os.path.join(PARQUET_DIR, "carrier_performance_raw.parquet"), index=False)
    print(f"[raw_storage] Parquet files written to {PARQUET_DIR}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    from src.ingestion.extract_csv import extract_orders_csv
    from src.ingestion.extract_shipping_api import extract_shipping_events, extract_carrier_performance

    orders = extract_orders_csv()
    events = extract_shipping_events()
    perf = extract_carrier_performance()
    store_raw(orders, events, perf)
