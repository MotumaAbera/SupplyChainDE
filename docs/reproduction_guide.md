# Reproduction Guide — Supply Chain Logistics Pipeline

This guide reproduces the entire pipeline from a clean checkout: environment
setup, data generation/ingestion, storage, cleaning, feature engineering,
quality validation, Spark processing, orchestration, versioning, and the
ML-ready output + dashboard.

## 0. Prerequisites

- Python 3.11+ (a virtualenv is strongly recommended; verified on 3.12)
- Java 17+ (required by PySpark 4.x — **Java 11 will not work**)
- ~2 GB free disk space
- Docker Desktop — only needed for the Airflow stage (Section 5)

### 0.1 Windows-specific setup (skip on Linux/macOS)

The pipeline runs fully on native Windows, but three things must be set up
first. All three fail in confusing ways if skipped.

**a) Point `JAVA_HOME` at a JDK 17+.** PySpark 4.x rejects Java 11, but the
failure mode is a silent *hang* with no output rather than an error — the JVM
never starts. Check what you have, then set it (User scope, no admin needed):

```powershell
[Environment]::GetEnvironmentVariable('JAVA_HOME','User')   # inspect
[Environment]::SetEnvironmentVariable('JAVA_HOME','C:\Program Files\Java\jdk-17','User')
```

Restart your terminal/IDE afterwards — running processes keep the old value.

**b) Install Hadoop `winutils`.** Spark can *read* Parquet on Windows without
it, but *writing* throws `java.io.FileNotFoundException: HADOOP_HOME and
hadoop.home.dir are unset`. Download `winutils.exe` and `hadoop.dll` for
Hadoop 3.3.x into `C:\hadoop\bin`:

```powershell
mkdir C:\hadoop\bin
curl -L -o C:\hadoop\bin\winutils.exe https://raw.githubusercontent.com/cdarlint/winutils/master/hadoop-3.3.6/bin/winutils.exe
curl -L -o C:\hadoop\bin\hadoop.dll  https://raw.githubusercontent.com/cdarlint/winutils/master/hadoop-3.3.6/bin/hadoop.dll
[Environment]::SetEnvironmentVariable('HADOOP_HOME','C:\hadoop','User')
```

Then add `C:\hadoop\bin` to your `Path`.

**c) Airflow cannot be pip-installed on Windows.** It depends on the
POSIX-only `pwd`/`fcntl` modules. Use the Docker route in Section 5 instead.
This is why `apache-airflow` is absent from `requirements.txt`.

## 1. Environment setup

```bash
git clone <this-repo> supply-chain-pipeline
cd supply-chain-pipeline
python3 -m venv venv
source venv/bin/activate            # Windows: .\venv\Scripts\Activate.ps1
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

`requirements.txt` is fully pinned to the versions the pipeline was last
verified against (all stages green, 21/21 quality checks).

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

### 5a. With Docker (required on Windows, works everywhere)

Airflow cannot be pip-installed on native Windows, so the orchestration layer
runs in a container. The repo is mounted at `/opt/project`, so the DAG executes
the *same* `src/` modules as the native pipeline and writes its outputs back
into the host's `data/` and `docs/` directories.

```bash
# One-off synchronous run of every task, in dependency order.
# Exits non-zero if any task fails.
docker compose -f docker/docker-compose.yml run --rm airflow-test

# OR the full stack with the web UI:
docker compose -f docker/docker-compose.yml up airflow-standalone
# open http://localhost:8080, log in as admin / admin,
# then unpause and trigger `supply_chain_logistics_pipeline`
```

Note that `airflow standalone` normally generates a *random* admin password
(it ignores `_AIRFLOW_WWW_USER_*`, which only the official docker-compose
entrypoint reads). The compose command therefore waits for that user to be
created and resets the password to `admin`, so the credentials above are the
ones that work. If you ever need the generated password instead, it is
printed to the container log as `Login with username: admin  password: ...`
and stored in `/opt/airflow/standalone_admin_password.txt`.

The image (`docker/Dockerfile.airflow`) adds OpenJDK 17 on top of
`apache/airflow:2.10.5`, because the `spark_processing` task needs a JVM and
the base image ships without one. The container also starts the simulated
carrier API on `127.0.0.1:5055` before the DAG runs, since `extract_sources`
pulls from it.

### 5b. Natively (Linux/macOS only)

```bash
pip install "apache-airflow==2.10.5"
export AIRFLOW_HOME=$(pwd)/.airflow
export AIRFLOW__CORE__DAGS_FOLDER=$(pwd)/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
airflow db migrate

python -m src.ingestion.shipping_api_server &     # required by extract_sources

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
