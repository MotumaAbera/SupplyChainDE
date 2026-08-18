"""
Final stage: assemble the ML-ready dataset for delivery-delay prediction,
plus summary statistics used by the report/dashboard.

Target options provided (per assessment spec "Delivery delay (binary/regression)"):
  - is_delayed        (binary classification target)
  - delivery_delay    (regression target, in days)

Output: data/ml_ready/{train,test}.parquet + a combined CSV, and
docs/summary_statistics.json for the report/dashboard.
"""
import hashlib
import json
import os
import sys
import numpy as np
import pandas as pd
import polars as pl

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.utils.parquet_io import write_parquet

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
ML_READY_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "ml_ready")
DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "docs")
os.makedirs(ML_READY_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)

FEATURE_COLUMNS = [
    "quantity", "unit_price", "discount_rate", "weight_kg", "distance_km",
    "promised_delivery_days", "shipping_cost", "shipping_cost_per_unit",
    "route_efficiency_score", "carrier_performance_score", "seasonal_demand_index",
    "warehouse_utilization", "inventory_turnover", "reorder_risk_score",
    "carrier", "shipping_mode", "product_category", "customer_segment",
    "destination_region", "distance_category", "shipment_size_category", "order_status",
]
TARGET_COLUMNS = ["is_delayed", "delivery_delay"]
ID_COLUMNS = ["order_id", "customer_id", "order_date"]


def _stable_fraction(key: str) -> float:
    """Map a key to a stable fraction in [0, 1) via md5.

    Used for the train/test split so the assignment is identical on every
    run, process and machine.
    """
    digest = hashlib.md5(str(key).encode("utf-8")).hexdigest()
    return (int(digest[:8], 16) % 10_000) / 10_000.0


def main(seed: int = 42):
    df = pd.read_parquet(os.path.join(PROCESSED_DIR, "orders_featured.parquet"))

    keep_cols = ID_COLUMNS + FEATURE_COLUMNS + TARGET_COLUMNS
    ml_df = df[keep_cols].copy()

    # Deterministic 80/20 split keyed on order_id.
    #
    # This deliberately uses md5 rather than Python's built-in hash(): hash()
    # is salted per interpreter process (PYTHONHASHSEED), so it returns
    # different values on every run and the "reproducible" split silently
    # drifted between runs. md5 is stable across processes and machines, so
    # the same order_id always lands in the same split.
    hash_frac = ml_df["order_id"].map(_stable_fraction)
    is_test = hash_frac < 0.20
    train_df = ml_df[~is_test].reset_index(drop=True)
    test_df = ml_df[is_test].reset_index(drop=True)

    write_parquet(train_df, os.path.join(ML_READY_DIR, "train.parquet"))
    write_parquet(test_df, os.path.join(ML_READY_DIR, "test.parquet"))

    # Polars handles the flat CSV export: it writes this ~100k-row frame
    # several times faster than pandas' CSV writer, and the export is a
    # straight dump with no pandas-specific dtypes to preserve.
    pl.from_pandas(ml_df).write_csv(os.path.join(ML_READY_DIR, "supply_chain_ml_ready.csv"))

    summary = {
        "total_rows": len(ml_df),
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "n_features": len(FEATURE_COLUMNS),
        "targets": TARGET_COLUMNS,
        "class_balance_is_delayed": ml_df["is_delayed"].value_counts(normalize=True).round(4).to_dict(),
        "delivery_delay_stats": {
            "mean": round(float(ml_df["delivery_delay"].mean()), 3),
            "median": float(ml_df["delivery_delay"].median()),
            "std": round(float(ml_df["delivery_delay"].std()), 3),
            "min": float(ml_df["delivery_delay"].min()),
            "max": float(ml_df["delivery_delay"].max()),
        },
        "carrier_on_time_rate": (1 - df.groupby("carrier")["is_delayed"].mean()).round(4).to_dict(),
        "orders_by_region": df["destination_region"].value_counts().to_dict(),
        "orders_by_category": df["product_category"].value_counts().to_dict(),
        "avg_delay_by_distance_category": df.groupby("distance_category")["delivery_delay"].mean().round(3).to_dict(),
        "monthly_order_volume": (
            df.assign(month=df["order_date"].dt.to_period("M").astype(str))
            .groupby("month")["order_id"].count().to_dict()
        ),
    }
    with open(os.path.join(DOCS_DIR, "summary_statistics.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"[ml_ready] wrote train ({len(train_df):,} rows) / test ({len(test_df):,} rows) sets")
    print(f"[ml_ready] class balance (is_delayed): {summary['class_balance_is_delayed']}")
    print(f"[ml_ready] wrote docs/summary_statistics.json")
    return summary


if __name__ == "__main__":
    main()
