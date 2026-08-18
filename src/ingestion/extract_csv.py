"""Data Source #1 (files): the real order-level CSV exports.

Two independent real datasets are ingested and unioned into the shared schema
documented in docs/data_dictionary.md:

  data/raw/kaggle_supply_chain_orders.csv   DataCo Smart Supply Chain (Kaggle)
  data/raw/olist_orders_mapped.csv          Olist Brazilian E-Commerce (Kaggle)

They describe different orders and share no key, so they are stacked rather
than joined. Every row carries a `source_system` column recording where it
came from, because the two datasets have different strengths: DataCo has real
discount rates and shipping modes; Olist has real freight charges, package
weights and geodesic distances. Columns a source genuinely lacks are left
null here and handled by the cleaning stage.
"""
import os

import pandas as pd

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw")
CSV_PATH = os.path.join(RAW_DIR, "kaggle_supply_chain_orders.csv")
OLIST_PATH = os.path.join(RAW_DIR, "olist_orders_mapped.csv")


def extract_orders_csv(path: str = CSV_PATH, olist_path: str = OLIST_PATH) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found. Run `python -m src.ingestion.download_kaggle` "
            f"(or `generate_seed_dataset` for the synthetic fallback) first."
        )

    frames = []

    dataco = pd.read_csv(path, low_memory=False)
    dataco["source_system"] = "dataco"
    frames.append(dataco)
    print(f"[extract_csv] DataCo: {len(dataco):,} rows, {dataco.shape[1] - 1} columns")

    if os.path.exists(olist_path):
        olist = pd.read_csv(olist_path, low_memory=False)
        olist["source_system"] = "olist"
        frames.append(olist)
        print(f"[extract_csv] Olist : {len(olist):,} rows, {olist.shape[1] - 1} columns")
    else:
        print(f"[extract_csv] Olist : not present (run "
              f"`python -m src.ingestion.download_olist`), continuing with DataCo only")

    df = pd.concat(frames, ignore_index=True, sort=False)

    # The two sources type their identifiers differently -- DataCo's are
    # numeric, Olist's are prefixed strings -- so the concatenated columns hold
    # a mix of int and str. Parquet cannot store that ("Could not convert
    # 'CUST-...' with type str: tried to convert to int64"), and these are
    # labels rather than quantities, so they are normalised to string here.
    id_columns = ["order_id", "customer_id", "product_id", "origin_warehouse_id",
                  "carrier", "shipping_mode", "product_category", "order_status",
                  "origin_region", "destination_city", "destination_country",
                  "destination_region", "delay_reason", "customer_segment"]
    for column in id_columns:
        if column in df.columns:
            df[column] = df[column].astype("string").astype(object).where(
                df[column].notna(), None)

    print(f"[extract_csv] union : {len(df):,} rows from {len(frames)} real dataset(s)")
    return df


if __name__ == "__main__":
    extract_orders_csv()
