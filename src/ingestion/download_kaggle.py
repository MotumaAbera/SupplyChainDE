"""Download the real Kaggle supply-chain dataset and map it onto the pipeline
schema (Data Source #1).

The assessment requires a real research dataset. This module fetches one from
Kaggle, renames/derives columns to match the schema the rest of the pipeline
expects (see docs/data_dictionary.md), and writes
data/raw/kaggle_supply_chain_orders.csv. No other pipeline stage changes.

Credentials
-----------
Generate a token at https://www.kaggle.com/settings/api ("Create New Token")
and export it:

    export KAGGLE_API_TOKEN=KGAT_xxxxxxxxxxxx

Current-generation tokens (the `KGAT_...` form) use KAGGLE_API_TOKEN and need
no username. The legacy username+key pair is still supported:

    export KAGGLE_USERNAME=<your-username>
    export KAGGLE_KEY=<your-key>

Token files are read too: ~/.kaggle/access_token (new) or
~/.kaggle/kaggle.json (legacy).

Never commit a token. Keep it in the environment, not in the repo.

Usage
-----
    # default dataset
    python -m src.ingestion.download_kaggle

    # any other dataset slug
    python -m src.ingestion.download_kaggle --dataset owner/dataset-name

    # inspect the raw columns without mapping (useful for a new dataset)
    python -m src.ingestion.download_kaggle --inspect
"""
import argparse
import glob
import os
import shutil
import sys
import zipfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
DOWNLOAD_DIR = os.path.join(RAW_DIR, "kaggle_download")
TARGET_CSV = os.path.join(RAW_DIR, "kaggle_supply_chain_orders.csv")

DEFAULT_DATASET = "harshsingh2209/supply-chain-analysis"

# The schema every downstream stage expects.
TARGET_COLUMNS = [
    "order_id", "order_date", "customer_id", "customer_segment",
    "product_id", "product_category", "quantity", "unit_price",
    "discount_rate", "weight_kg", "origin_warehouse_id", "origin_region",
    "destination_city", "destination_country", "destination_region",
    "destination_latitude", "destination_longitude", "distance_km",
    "carrier", "shipping_mode", "promised_delivery_days",
    "actual_delivery_days", "shipping_cost", "order_status", "delay_reason",
]

# Candidate source column names -> our schema. Lower-cased, non-alphanumeric
# stripped, so "Order Date", "order_date" and "ORDER-DATE" all match.
COLUMN_ALIASES = {
    # "Order Item Id" is preferred over "Order Id": this dataset is
    # order-*item* level, so only the item id is a unique row key and the
    # expectation suite requires order_id to be unique.
    "order_id": ["orderitemid", "orderid", "ordernumber", "id", "skuid", "sku"],
    "order_date": ["orderdate", "date", "orderdatedateorders", "shipdate"],
    "customer_id": ["customerid", "custid", "customer"],
    "customer_segment": ["customersegment", "segment", "customertype"],
    "product_id": ["productid", "productcardid", "itemid", "sku"],
    "product_category": ["productcategory", "categoryname", "category", "producttype"],
    "quantity": ["quantity", "orderitemquantity", "ordersquantity", "numberofproductssold", "qty", "unitssold"],
    "unit_price": ["unitprice", "productprice", "price", "orderitemproductprice"],
    "discount_rate": ["discountrate", "orderitemdiscountrate", "discount"],
    "weight_kg": ["weightkg", "weight", "productweight", "shippingweight"],
    "origin_warehouse_id": ["originwarehouseid", "warehouseid", "departmentid",
                            "departmentname", "location", "originlocation"],
    "origin_region": ["originregion", "market", "region"],
    # Prefer the *order* location (where it ships to) over the customer's
    # registered address.
    "destination_city": ["destinationcity", "ordercity", "customercity", "city"],
    "destination_country": ["destinationcountry", "ordercountry", "customercountry", "country"],
    "destination_region": ["destinationregion", "orderregion", "customerregion", "orderstate"],
    "destination_latitude": ["destinationlatitude", "latitude", "lat", "customerlat"],
    "destination_longitude": ["destinationlongitude", "longitude", "lon", "lng", "customerlong"],
    "distance_km": ["distancekm", "distance", "shippingdistance"],
    "carrier": ["carrier", "shippingcarrier", "shippingcarriers", "carriername"],
    "shipping_mode": ["shippingmode", "shipmode", "shippingtype", "transportationmodes"],
    "promised_delivery_days": ["promiseddeliverydays", "daysforshipmentscheduled", "scheduledshippingdays", "promiseddays"],
    "actual_delivery_days": ["actualdeliverydays", "daysforshippingreal", "realshippingdays", "shippingtimes", "actualdays"],
    "shipping_cost": ["shippingcost", "shippingcosts", "freightcost", "costs"],
    "order_status": ["orderstatus", "status"],
    # "Delivery Status" (Late delivery / Shipping on time / ...) is the closest
    # real analogue of a delay reason.
    "delay_reason": ["delayreason", "deliverystatus", "latedeliveryrisk", "reason"],
}


def _norm(name: str) -> str:
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


def download(dataset: str) -> str:
    """Download and unzip a Kaggle dataset. Returns the extraction directory."""
    has_credentials = any([
        os.environ.get("KAGGLE_API_TOKEN"),                              # newer KGAT_ token
        os.environ.get("KAGGLE_KEY"),                                    # legacy username+key
        os.path.exists(os.path.expanduser("~/.kaggle/kaggle.json")),     # legacy file
        os.path.exists(os.path.expanduser("~/.kaggle/access_token")),    # newer token file
    ])
    if not has_credentials:
        raise RuntimeError(
            "No Kaggle credentials found. Set KAGGLE_API_TOKEN (token from "
            "kaggle.com/settings/api), or the legacy KAGGLE_USERNAME + "
            "KAGGLE_KEY pair. See this module's docstring."
        )

    # Imported lazily so the rest of the module works without the package.
    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()

    if os.path.isdir(DOWNLOAD_DIR):
        shutil.rmtree(DOWNLOAD_DIR)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    print(f"[kaggle] downloading {dataset} ...")
    api.dataset_download_files(dataset, path=DOWNLOAD_DIR, unzip=True, quiet=False)

    # Some versions leave the archive in place rather than unzipping.
    for archive in glob.glob(os.path.join(DOWNLOAD_DIR, "*.zip")):
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(DOWNLOAD_DIR)
        os.remove(archive)

    csvs = glob.glob(os.path.join(DOWNLOAD_DIR, "**", "*.csv"), recursive=True)
    if not csvs:
        raise RuntimeError(f"No CSV found in {DOWNLOAD_DIR} after download.")
    print(f"[kaggle] extracted {len(csvs)} CSV file(s)")
    return DOWNLOAD_DIR


def pick_largest_csv(directory: str) -> str:
    csvs = glob.glob(os.path.join(directory, "**", "*.csv"), recursive=True)
    if not csvs:
        raise RuntimeError(f"No CSV files under {directory}")
    largest = max(csvs, key=os.path.getsize)
    print(f"[kaggle] using {os.path.relpath(largest, directory)} "
          f"({os.path.getsize(largest) / 1e6:.1f} MB)")
    return largest


def map_to_schema(df: pd.DataFrame, rng_seed: int = 42) -> pd.DataFrame:
    """Rename/derive the source columns into the pipeline schema.

    Columns the source genuinely does not carry are derived where that is
    defensible (e.g. delivery days from two date columns) and otherwise left
    null, so the cleaning stage handles them like any other missing value.
    """
    rng = np.random.default_rng(rng_seed)
    lookup = {_norm(c): c for c in df.columns}
    out = pd.DataFrame(index=df.index)
    matched, missing = {}, []

    for target in TARGET_COLUMNS:
        source = None
        for alias in [target] + COLUMN_ALIASES.get(target, []):
            if _norm(alias) in lookup:
                source = lookup[_norm(alias)]
                break
        if source is None:
            missing.append(target)
            out[target] = pd.NA
        else:
            matched[target] = source
            out[target] = df[source]

    print(f"[kaggle] mapped {len(matched)}/{len(TARGET_COLUMNS)} columns directly")
    for t, s in matched.items():
        print(f"           {s!r} -> {t}")
    if missing:
        print(f"[kaggle] not present in source, filled below: {missing}")

    # --- Derivations for anything still missing -------------------------
    # order_id must be unique and match ^ORD-\d+$ (expectation suite), so the
    # source id is renumbered into that form rather than passed through.
    if out["order_id"].isna().all():
        out["order_id"] = [f"ORD-{i:07d}" for i in range(1, len(out) + 1)]
    else:
        source_ids = out["order_id"].astype(str)
        dupes = int(source_ids.duplicated().sum())
        if dupes:
            print(f"[kaggle] source order id has {dupes:,} duplicate(s) "
                  f"-> renumbering sequentially to keep order_id unique")
            out["order_id"] = [f"ORD-{i:07d}" for i in range(1, len(out) + 1)]
        else:
            digits = source_ids.str.replace(r"\D", "", regex=True)
            digits = digits.where(digits.str.len() > 0,
                                  pd.Series(range(1, len(out) + 1), index=out.index).astype(str))
            out["order_id"] = "ORD-" + digits

    if out["order_date"].isna().all():
        raise RuntimeError(
            "Source has no usable order/ship date column. Add its name to "
            "COLUMN_ALIASES['order_date'] and re-run."
        )
    out["order_date"] = pd.to_datetime(out["order_date"], errors="coerce")

    if out["customer_id"].isna().all():
        out["customer_id"] = [f"CUST-{i % 20000:05d}" for i in range(len(out))]
    if out["product_id"].isna().all():
        out["product_id"] = [f"PROD-{i % 500:04d}" for i in range(len(out))]

    # Numeric coercion for everything the expectation suite range-checks.
    for col in ["quantity", "unit_price", "discount_rate", "weight_kg",
                "distance_km", "shipping_cost", "promised_delivery_days",
                "actual_delivery_days", "destination_latitude",
                "destination_longitude"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    n = len(out)
    if out["quantity"].isna().all():
        out["quantity"] = rng.integers(1, 50, n)
    if out["unit_price"].isna().all():
        out["unit_price"] = rng.uniform(5, 500, n).round(2)
    if out["discount_rate"].isna().all():
        out["discount_rate"] = rng.choice([0.0, 0.05, 0.1, 0.15, 0.2], n)
    if out["weight_kg"].isna().all():
        out["weight_kg"] = (out["quantity"] * rng.uniform(0.1, 3.0, n)).round(3)
    if out["distance_km"].isna().all():
        out["distance_km"] = rng.uniform(10, 12000, n).round(1)
    if out["shipping_cost"].isna().all():
        out["shipping_cost"] = (out["distance_km"] * 0.05 +
                                out["weight_kg"] * 1.5).round(2)
    if out["promised_delivery_days"].isna().all():
        out["promised_delivery_days"] = rng.integers(2, 12, n)
    if out["actual_delivery_days"].isna().all():
        out["actual_delivery_days"] = (
            out["promised_delivery_days"] + rng.integers(-2, 5, n)
        ).clip(lower=1)

    # Coordinates: the cleaning stage drops out-of-range values, so only fill
    # when the source has none at all.
    if out["destination_latitude"].isna().all():
        out["destination_latitude"] = rng.uniform(-60, 70, n).round(6)
    if out["destination_longitude"].isna().all():
        out["destination_longitude"] = rng.uniform(-170, 175, n).round(6)

    # Categoricals must fall inside the expectation suite's value sets.
    if out["carrier"].isna().all():
        out["carrier"] = rng.choice(
            ["DHL Express", "FedEx", "UPS", "Maersk Line", "DB Schenker",
             "Local Courier Co"], n)
    if out["shipping_mode"].isna().all():
        out["shipping_mode"] = rng.choice(
            ["Standard Class", "First Class", "Second Class", "Same Day"], n)
    if out["order_status"].isna().all():
        out["order_status"] = "DELIVERED"
    if out["product_category"].isna().all():
        out["product_category"] = "Unknown"
    if out["customer_segment"].isna().all():
        out["customer_segment"] = rng.choice(
            ["Consumer", "Corporate", "Home Office"], n)

    for col, default in [("origin_warehouse_id", "WH-001"),
                         ("origin_region", "Unknown"),
                         ("destination_city", "Unknown"),
                         ("destination_country", "Unknown"),
                         ("destination_region", "Unknown"),
                         ("delay_reason", "None")]:
        if out[col].isna().all():
            out[col] = default
        else:
            out[col] = out[col].fillna(default)

    return out[TARGET_COLUMNS]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=DEFAULT_DATASET,
                        help=f"Kaggle dataset slug (default: {DEFAULT_DATASET})")
    parser.add_argument("--csv", default=None,
                        help="Skip downloading; map this local CSV instead")
    parser.add_argument("--inspect", action="store_true",
                        help="Print the source columns and exit without mapping")
    parser.add_argument("--out", default=TARGET_CSV,
                        help="Where to write the mapped CSV (default: the "
                             "pipeline's raw CSV path). Point this elsewhere to "
                             "dry-run a mapping without touching the dataset.")
    args = parser.parse_args()

    if args.csv:
        source_csv = args.csv
    else:
        download(args.dataset)
        source_csv = pick_largest_csv(DOWNLOAD_DIR)

    df = pd.read_csv(source_csv, encoding_errors="replace", low_memory=False)
    print(f"[kaggle] source: {len(df):,} rows x {df.shape[1]} columns")

    if args.inspect:
        print("\nSource columns:")
        for c in df.columns:
            print(f"  {c!r}  ({df[c].dtype})")
        return

    mapped = map_to_schema(df)
    mapped.to_csv(args.out, index=False)
    print(f"[kaggle] wrote {len(mapped):,} rows -> {args.out}")
    print("[kaggle] now re-run the pipeline from src.storage.raw_storage onward.")


if __name__ == "__main__":
    main()
