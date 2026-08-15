"""Data Source #1: extract the raw order-level CSV file (simulated Kaggle
Supply Chain Analytics export)."""
import os
import pandas as pd

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw")
CSV_PATH = os.path.join(RAW_DIR, "kaggle_supply_chain_orders.csv")


def extract_orders_csv(path: str = CSV_PATH) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found. Run `python -m src.ingestion.generate_seed_dataset` first."
        )
    df = pd.read_csv(path)
    print(f"[extract_csv] loaded {len(df):,} rows, {df.shape[1]} columns from {os.path.basename(path)}")
    return df


if __name__ == "__main__":
    extract_orders_csv()
