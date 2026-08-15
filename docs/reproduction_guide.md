# Reproduction Guide — Supply Chain Logistics Pipeline

This guide reproduces the entire pipeline from a clean checkout: environment
setup, data generation/ingestion, storage, cleaning, feature engineering,
quality validation, Spark processing, orchestration, versioning, and the
ML-ready output + dashboard.

## 0. Prerequisites

- Python 3.11 (a virtualenv is strongly recommended)
- Java 17+ (required by PySpark)
- ~2 GB free disk space

## 1. Environment setup

```bash
git clone <this-repo> supply-chain-pipeline
cd supply-chain-pipeline
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

> If you hit a `setuptools`/`distutils` build error on packages like
> `antlr4-python3-runtime` or `unicodecsv` (seen with very new setuptools on
> Python 3.11+), pin `setuptools==68.2.2` before installing the rest:
> `pip install "setuptools==68.2.2"`.

## 2. Dataset

**About the data.** This project ships with a large (105K+ row), seeded,
statistically-realistic synthetic dataset generated to match the exact schema
and relationships of a real Kaggle supply-chain logistics dataset (see
`src/utils/reference_data.py` for full provenance notes — live Kaggle access
was not available in the original build environment). To regenerate it
identically:

```bash
python -m src.ingestion.generate_seed_dataset
```

This writes:
- `data/raw/kaggle_supply_chain_orders.csv` (Source #1 — order-level CSV)
- `data/seed/shipping_events_seed.parquet` (backing data for Source #2)

**To swap in the real Kaggle dataset instead:** download any Kaggle supply
chain / logistics orders dataset with a Kaggle API token
(`kaggle datasets download -d <dataset>`), then map its columns to the schema
documented in `docs/data_dictionary.md` and save the result to
`data/raw/kaggle_supply_chain_orders.csv`. No other pipeline code needs to
change.

## 3. Start the simulated shipping-carrier API (Source #2)

```bash
python -m src.ingestion.shipping_api_server &
# health check:
curl http://127.0.0.1:5055/api/v1/health
```

## 4. Run the pipeline stages manually (for development / debugging)

```bash
python -m src.storage.raw_storage        # extract both sources -> SQLite + Parquet
python -m src.transformation.clean       # clean & standardize
python -m src.features.engineer          # 10 engineered features
python -m src.quality.gx_validation      # Great Expectations suite -> docs/data_quality_report.*
python -m src.processing.spark_processing  # PySpark aggregations + window functions
python -m src.ml_ready.build_ml_dataset  # final ML-ready dataset
python -m src.dashboard.build_dashboard  # docs/dashboard/supply_chain_dashboard.html
```

## 5. Run the full pipeline via Apache Airflow (orchestrated)

```bash
export AIRFLOW_HOME=$(pwd)/.airflow
export AIRFLOW__CORE__DAGS_FOLDER=$(pwd)/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
airflow db migrate

# One-off synchronous test run (no scheduler/webserver needed):
airflow dags test supply_chain_logistics_pipeline $(date +%F)

# OR run the full stack with UI:
airflow standalone
# open http://localhost:8080, log in with the generated admin credentials
# printed to the console, then trigger `supply_chain_logistics_pipeline`
```

The DAG runs: `extract_sources -> store_raw -> clean_transform ->
engineer_features -> validate_quality -> spark_processing ->
generate_ml_ready_dataset`, with retries (2x, exponential backoff), a
30-minute execution timeout per task, and a data-quality gate that fails the
run if fewer than 90% of Great Expectations checks pass.

## 6. Data versioning with DVC

```bash
dvc init                                 # already committed in this repo
dvc remote add -d localremote /path/to/local/storage   # or S3/GCS/Azure in production
dvc add data/raw/kaggle_supply_chain_orders.csv data/raw/supply_chain_raw.db \
        data/processed/orders_clean.parquet data/processed/orders_featured.parquet \
        data/ml_ready/train.parquet data/ml_ready/test.parquet
git add *.dvc data/**/.gitignore
git commit -m "Track pipeline datasets with DVC"
dvc push

# to retrieve a specific historical version of the data later:
git checkout <commit-or-tag>
dvc checkout
```

## 7. Outputs

| Output | Path |
|---|---|
| Raw data (SQLite) | `data/raw/supply_chain_raw.db` |
| Raw data (Parquet) | `data/raw/parquet/` |
| Cleaned data | `data/processed/orders_clean.parquet` |
| Feature-engineered data | `data/processed/orders_featured.parquet` |
| Spark analytics tables | `data/processed/analytics/` |
| Data quality report | `docs/data_quality_report.md` / `.json` |
| ML-ready dataset | `data/ml_ready/train.parquet`, `test.parquet`, `supply_chain_ml_ready.csv` |
| Summary statistics | `docs/summary_statistics.json` |
| Dashboard | `docs/dashboard/supply_chain_dashboard.html` |
| Architecture diagram | `docs/diagrams/architecture_diagram.png` |

## 8. Troubleshooting

- **Flask/Airflow version conflict:** Airflow's `Flask-AppBuilder` requires
  `Flask==2.2.5`. If you `pip install` a newer Flask for the API server
  afterwards, re-pin it: `pip install "Flask==2.2.5"`.
- **PySpark + pandas 3.x warning:** benign; PySpark 4.x has only been
  smoke-tested against pandas 3.x by its maintainers as of this writing.
- **Port 5055 already in use:** `pkill -f shipping_api_server` before
  restarting the API server.
