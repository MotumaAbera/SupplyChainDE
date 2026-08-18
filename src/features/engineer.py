"""
Feature engineering stage. Creates the 10 domain-relevant features named
in the assessment brief for Topic 9 (Supply Chain Logistics Pipeline):

  1. delivery_delay              - actual vs promised delivery days (+ binary flag)
  2. shipping_cost_per_unit      - shipping_cost / quantity
  3. route_efficiency_score      - normalized speed (distance / time), by route
  4. carrier_performance_score   - historical on-time rate per carrier
  5. seasonal_demand_index       - relative order volume by month vs. yearly average
  6. distance_category           - binned shipping distance
  7. warehouse_utilization       - daily order load vs. warehouse capacity
  8. inventory_turnover          - proxy: units shipped / avg. daily category demand
  9. reorder_risk_score          - composite of delay history + demand volatility
  10. shipment_size_category     - binned by weight x quantity

Each feature's rationale is documented inline and mirrored in the data
dictionary (docs/data_dictionary.md).
"""
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.utils.parquet_io import write_parquet

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")


def engineer_features(orders: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    df = orders.copy()

    # --- 1. delivery_delay -----------------------------------------------
    # Rationale: direct measure of the prediction target; also drives several
    # other features below.
    df["delivery_delay"] = df["actual_delivery_days"] - df["promised_delivery_days"]
    df["is_delayed"] = (df["delivery_delay"] > 0).astype(int)

    # --- 2. shipping_cost_per_unit -----------------------------------------
    # Rationale: normalizes cost across orders of different sizes; a raw
    # shipping_cost is not comparable between a 1-unit and 24-unit order.
    df["shipping_cost_per_unit"] = (df["shipping_cost"] / df["quantity"].replace(0, np.nan)).round(3)
    df["shipping_cost_per_unit"] = df["shipping_cost_per_unit"].fillna(df["shipping_cost_per_unit"].median())

    # --- 3. route_efficiency_score ------------------------------------------
    # Rationale: km covered per actual delivery day, min-max normalized to
    # [0, 1] within each destination_region so routes are compared fairly
    # against similar-distance peers rather than a single global scale.
    speed = df["distance_km"] / df["actual_delivery_days"].replace(0, np.nan)
    df["_speed_km_per_day"] = speed
    def _norm(s):
        rng = s.max() - s.min()
        return (s - s.min()) / rng if rng > 0 else 0.5
    df["route_efficiency_score"] = (
        df.groupby("destination_region")["_speed_km_per_day"].transform(_norm).round(4)
    )
    df.drop(columns=["_speed_km_per_day"], inplace=True)

    # --- 4. carrier_performance_score ----------------------------------------
    # Rationale: historical on-time delivery rate per carrier -- a strong
    # predictor of future delay risk; computed from the cleaned order history
    # (cross-checked against the shipping API's independent carrier stats in
    # the data-quality report).
    carrier_rate = 1 - df.groupby("carrier")["is_delayed"].transform("mean")
    df["carrier_performance_score"] = carrier_rate.round(4)

    # --- 5. seasonal_demand_index --------------------------------------------
    # Rationale: order volume in a given month relative to the dataset's
    # monthly average -- captures holiday/peak-season surges that strain
    # warehouses and carriers.
    df["_order_month"] = df["order_date"].dt.to_period("M")
    monthly_counts = df.groupby("_order_month")["order_id"].transform("count")
    avg_monthly = df.groupby("_order_month")["order_id"].count().mean()
    df["seasonal_demand_index"] = (monthly_counts / avg_monthly).round(4)
    df.drop(columns=["_order_month"], inplace=True)

    # --- 6. distance_category -------------------------------------------------
    # Rationale: non-linear relationship between distance and delay risk;
    # binning lets tree-based and linear models both pick up the effect.
    # include_lowest: a real 0 km shipment (seller and customer share a
    # postcode) sits exactly on the first edge. Without it pd.cut leaves the
    # interval open at the bottom, those rows become NaN, and the category
    # ends up as the string "nan" -- which then fails the value-set check.
    df["distance_category"] = pd.cut(
        df["distance_km"], bins=[0, 500, 2000, 6000, np.inf],
        labels=["Local", "Regional", "Long-Haul", "International"],
        include_lowest=True,
    ).astype(str)

    # --- 7. warehouse_utilization ------------------------------------------
    # Rationale: proxy for operational strain -- orders shipped from a
    # warehouse on a given day, relative to that warehouse's stated daily
    # capacity (joined from reference data via origin_warehouse_id).
    from src.utils.reference_data import WAREHOUSES
    cap_map = {w["warehouse_id"]: w["capacity_units_per_day"] for w in WAREHOUSES}
    df["_order_day"] = df["order_date"].dt.date
    daily_wh_units = df.groupby(["origin_warehouse_id", "_order_day"])["quantity"].transform("sum")

    # Origins outside the reference table (e.g. Olist's real sellers, which
    # have no published capacity) get an observed capacity instead: that
    # origin's own busiest observed day. Utilization stays on a comparable
    # 0-1-ish scale across both sources rather than going null.
    capacity = df["origin_warehouse_id"].map(cap_map)
    observed_peak = daily_wh_units.groupby(df["origin_warehouse_id"]).transform("max")
    capacity = capacity.fillna(observed_peak).replace(0, np.nan)

    df["warehouse_utilization"] = (daily_wh_units / capacity).round(4)
    df.drop(columns=["_order_day"], inplace=True)

    # --- 8. inventory_turnover ------------------------------------------------
    # Rationale: proxy metric (no live inventory table exists) approximating
    # how quickly stock moves for a product category: units shipped per day
    # for that category, relative to the category's average daily demand
    # across the whole dataset. >1 indicates faster-than-average turnover.
    df["_order_day2"] = df["order_date"].dt.date
    daily_cat_units = df.groupby(["product_category", "_order_day2"])["quantity"].transform("sum")
    cat_avg_daily = df.groupby("product_category")["quantity"].transform("mean")
    df["inventory_turnover"] = (daily_cat_units / (cat_avg_daily * 30)).round(4)
    df.drop(columns=["_order_day2"], inplace=True)

    # --- 9. reorder_risk_score -------------------------------------------------
    # Rationale: composite score (0-1) blending (a) how delay-prone the
    # carrier+category combination has been historically and (b) demand
    # volatility for that category -- higher score = higher risk of needing
    # an expedited reorder due to disruption.
    delay_rate_combo = df.groupby(["carrier", "product_category"])["is_delayed"].transform("mean")
    demand_volatility = df.groupby("product_category")["seasonal_demand_index"].transform("std").fillna(0)
    demand_volatility_norm = (demand_volatility - demand_volatility.min()) / (
        demand_volatility.max() - demand_volatility.min() + 1e-9
    )
    df["reorder_risk_score"] = (0.65 * delay_rate_combo + 0.35 * demand_volatility_norm).round(4)

    # --- 10. shipment_size_category ---------------------------------------------
    # Rationale: weight x quantity captures physical shipment bulk, which
    # affects handling time and carrier selection more than either alone.
    bulk = df["weight_kg"] * df["quantity"]
    # include_lowest for the same reason as distance_category: some real
    # products carry a recorded weight of 0 g.
    df["shipment_size_category"] = pd.cut(
        bulk, bins=[0, 5, 25, 100, np.inf],
        labels=["Small", "Medium", "Large", "Bulk"],
        include_lowest=True,
    ).astype(str)

    return df


def main():
    orders = pd.read_parquet(os.path.join(PROCESSED_DIR, "orders_clean.parquet"))
    events = pd.read_parquet(os.path.join(PROCESSED_DIR, "events_clean.parquet"))
    featured = engineer_features(orders, events)
    out_path = os.path.join(PROCESSED_DIR, "orders_featured.parquet")
    write_parquet(featured, out_path)

    new_feature_cols = [
        "delivery_delay", "is_delayed", "shipping_cost_per_unit", "route_efficiency_score",
        "carrier_performance_score", "seasonal_demand_index", "distance_category",
        "warehouse_utilization", "inventory_turnover", "reorder_risk_score", "shipment_size_category",
    ]
    print(f"[engineer] added {len(new_feature_cols)} engineered features "
          f"(+ is_delayed helper) to {len(featured):,} rows")
    print(featured[new_feature_cols].describe(include="all").T[["count"]])
    print(f"[engineer] wrote {out_path}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    main()
