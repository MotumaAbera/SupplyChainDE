"""
Great Expectations validation suite for the cleaned + feature-engineered
Supply Chain orders dataset. Produces a machine-readable JSON data-quality
report plus a human-readable Markdown summary.

Built against the Great Expectations 1.x Fluent API.
"""
import json
import os
import sys
from datetime import datetime, timezone

import pandas as pd
import great_expectations as gx
from great_expectations.expectations import (
    ExpectColumnValuesToNotBeNull,
    ExpectColumnValuesToBeBetween,
    ExpectColumnValuesToBeInSet,
    ExpectColumnValuesToBeUnique,
    ExpectColumnValuesToMatchRegex,
    ExpectColumnMeanToBeBetween,
)

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "docs")
os.makedirs(REPORT_DIR, exist_ok=True)


def build_suite():
    suite = gx.ExpectationSuite(name="supply_chain_orders_suite")
    expectations = [
        ExpectColumnValuesToBeUnique(column="order_id"),
        ExpectColumnValuesToNotBeNull(column="order_id"),
        ExpectColumnValuesToNotBeNull(column="order_date"),
        ExpectColumnValuesToNotBeNull(column="carrier"),
        ExpectColumnValuesToBeInSet(
            column="carrier",
            value_set=["DHL Express", "FedEx", "UPS", "Maersk Line", "DB Schenker", "Local Courier Co"],
        ),
        ExpectColumnValuesToBeInSet(
            column="shipping_mode",
            value_set=["Standard Class", "First Class", "Second Class", "Same Day"],
        ),
        ExpectColumnValuesToBeBetween(column="quantity", min_value=1, max_value=1000),
        ExpectColumnValuesToBeBetween(column="unit_price", min_value=0, max_value=10000),
        ExpectColumnValuesToBeBetween(column="shipping_cost", min_value=0, max_value=5000),
        ExpectColumnValuesToBeBetween(column="destination_latitude", min_value=-90, max_value=90),
        ExpectColumnValuesToBeBetween(column="destination_longitude", min_value=-180, max_value=180),
        ExpectColumnValuesToBeBetween(column="distance_km", min_value=0, max_value=25000),
        ExpectColumnValuesToBeBetween(column="promised_delivery_days", min_value=1, max_value=15),
        ExpectColumnValuesToBeBetween(column="actual_delivery_days", min_value=1, max_value=60),
        ExpectColumnValuesToMatchRegex(column="order_id", regex=r"^ORD-\d+$"),
        # Feature-level sanity checks
        ExpectColumnValuesToBeBetween(column="carrier_performance_score", min_value=0, max_value=1),
        ExpectColumnValuesToBeBetween(column="route_efficiency_score", min_value=0, max_value=1),
        ExpectColumnValuesToBeBetween(column="reorder_risk_score", min_value=0, max_value=1),
        ExpectColumnValuesToBeInSet(
            column="distance_category", value_set=["Local", "Regional", "Long-Haul", "International"]
        ),
        ExpectColumnValuesToBeInSet(
            column="shipment_size_category", value_set=["Small", "Medium", "Large", "Bulk"]
        ),
        ExpectColumnMeanToBeBetween(column="is_delayed", min_value=0.0, max_value=0.6),
    ]
    for e in expectations:
        suite.add_expectation(e)
    return suite


def run_validation(df: pd.DataFrame):
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas("pandas_supply_chain")
    data_asset = data_source.add_dataframe_asset(name="orders_featured")
    batch_definition = data_asset.add_batch_definition_whole_dataframe("full_table")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

    suite = build_suite()
    result = batch.validate(suite, result_format="SUMMARY")
    return result


def summarize(result, df) -> dict:
    raw = result.to_json_dict()
    total = len(raw["results"])
    passed = sum(1 for r in raw["results"] if r["success"])
    failed_details = []
    for r in raw["results"]:
        if not r["success"]:
            failed_details.append({
                "expectation_type": r["expectation_config"]["type"],
                "kwargs": {k: v for k, v in r["expectation_config"]["kwargs"].items() if k != "batch_id"},
                "unexpected_count": r.get("result", {}).get("unexpected_count"),
                "unexpected_percent": r.get("result", {}).get("unexpected_percent"),
            })
    summary = {
        "run_timestamp": None,  # filled by caller (Date.now unavailable in some contexts)
        "dataset_rows": len(df),
        "dataset_columns": df.shape[1],
        "total_expectations": total,
        "passed": passed,
        "failed": total - passed,
        "success_rate_pct": round(100 * passed / total, 2) if total else None,
        "overall_success": bool(raw["success"]),
        "failed_expectations": failed_details,
    }
    return summary


def main():
    df = pd.read_parquet(os.path.join(PROCESSED_DIR, "orders_featured.parquet"))
    result = run_validation(df)
    summary = summarize(result, df)
    summary["run_timestamp"] = datetime.now(timezone.utc).isoformat()

    json_path = os.path.join(REPORT_DIR, "data_quality_report.json")
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)

    md_path = os.path.join(REPORT_DIR, "data_quality_report.md")
    with open(md_path, "w") as f:
        f.write("# Data Quality Report — Great Expectations\n\n")
        f.write(f"Run at: {summary['run_timestamp']}\n\n")
        f.write(f"- Dataset: `orders_featured.parquet` ({summary['dataset_rows']:,} rows, "
                f"{summary['dataset_columns']} columns)\n")
        f.write(f"- Expectations run: **{summary['total_expectations']}**\n")
        f.write(f"- Passed: **{summary['passed']}**  |  Failed: **{summary['failed']}**\n")
        f.write(f"- Success rate: **{summary['success_rate_pct']}%**\n")
        f.write(f"- Overall suite result: **{'PASS' if summary['overall_success'] else 'FAIL'}**\n\n")
        if summary["failed_expectations"]:
            f.write("## Failed expectations\n\n")
            for fe in summary["failed_expectations"]:
                f.write(f"- `{fe['expectation_type']}` on {fe['kwargs']} — "
                        f"{fe['unexpected_count']} unexpected values "
                        f"({fe['unexpected_percent']}%)\n")
        else:
            f.write("All expectations passed. No failed expectations.\n")

    print(f"[gx_validation] {summary['passed']}/{summary['total_expectations']} expectations passed "
          f"({summary['success_rate_pct']}%)")
    print(f"[gx_validation] wrote {json_path}")
    print(f"[gx_validation] wrote {md_path}")
    return summary


if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    main()
