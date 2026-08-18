"""
Apache Airflow DAG: Supply Chain Logistics Pipeline
extract (CSV + shipping API) -> store raw -> clean -> engineer features ->
validate (Great Expectations) -> Spark processing -> generate ML-ready dataset

Schedule: daily at 02:00, with retries and failure alerting hooks.

To run locally:
    export AIRFLOW_HOME=$(pwd)/.airflow
    airflow db migrate
    cp dags/supply_chain_dag.py $AIRFLOW_HOME/dags/
    airflow standalone
    # then trigger `supply_chain_logistics_pipeline` from the Airflow UI
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

log = logging.getLogger(__name__)

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=3),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=15),
    "execution_timeout": timedelta(minutes=30),
}


def on_failure_callback(context):
    ti = context["task_instance"]
    log.error(f"[ALERT] Task {ti.task_id} failed in DAG {ti.dag_id} run {ti.run_id}. "
              f"Exception: {context.get('exception')}")
    # In production this would page/notify (Slack, email, PagerDuty, etc.)


def _extract_sources(**_):
    from src.ingestion.extract_csv import extract_orders_csv
    from src.ingestion.extract_shipping_api import extract_shipping_events, extract_carrier_performance
    orders = extract_orders_csv()
    events = extract_shipping_events()
    perf = extract_carrier_performance()
    from src.utils.parquet_io import write_parquet
    write_parquet(orders, os.path.join(PROJECT_ROOT, "data", "raw", "_tmp_orders.parquet"))
    write_parquet(events, os.path.join(PROJECT_ROOT, "data", "raw", "_tmp_events.parquet"))
    write_parquet(perf, os.path.join(PROJECT_ROOT, "data", "raw", "_tmp_perf.parquet"))
    if len(orders) == 0:
        raise ValueError("extract_sources: orders extract returned 0 rows -- aborting pipeline")


def _store_raw(**_):
    import pandas as pd
    from src.storage.raw_storage import store_raw
    tmp = os.path.join(PROJECT_ROOT, "data", "raw")
    orders = pd.read_parquet(os.path.join(tmp, "_tmp_orders.parquet"))
    events = pd.read_parquet(os.path.join(tmp, "_tmp_events.parquet"))
    perf = pd.read_parquet(os.path.join(tmp, "_tmp_perf.parquet"))
    store_raw(orders, events, perf)


def _clean(**_):
    from src.transformation.clean import main as clean_main
    stats = clean_main()
    if stats["output_rows"] == 0:
        raise ValueError("clean: 0 rows survived cleaning -- aborting pipeline")


def _engineer_features(**_):
    from src.features.engineer import main as engineer_main
    engineer_main()


def _validate_quality(**_):
    from src.quality.gx_validation import main as gx_main
    summary = gx_main()
    if summary["success_rate_pct"] < 90:
        raise ValueError(
            f"Data quality gate failed: only {summary['success_rate_pct']}% of expectations passed "
            f"(threshold 90%). See docs/data_quality_report.md"
        )


def _spark_processing(**_):
    from src.processing.spark_processing import run as spark_run
    spark_run()


def _generate_ml_ready(**_):
    from src.ml_ready.build_ml_dataset import main as ml_main
    ml_main()


with DAG(
    dag_id="supply_chain_logistics_pipeline",
    description="End-to-end supply chain logistics data pipeline for ML-ready delivery-delay data",
    default_args=default_args,
    schedule="0 2 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["assessment-2", "supply-chain", "data-engineering"],
    on_failure_callback=on_failure_callback,
) as dag:

    extract = PythonOperator(task_id="extract_sources", python_callable=_extract_sources)
    store = PythonOperator(task_id="store_raw", python_callable=_store_raw)
    clean = PythonOperator(task_id="clean_transform", python_callable=_clean)
    engineer = PythonOperator(task_id="engineer_features", python_callable=_engineer_features)
    validate = PythonOperator(task_id="validate_quality", python_callable=_validate_quality)
    spark_process = PythonOperator(task_id="spark_processing", python_callable=_spark_processing)
    ml_ready = PythonOperator(task_id="generate_ml_ready_dataset", python_callable=_generate_ml_ready)

    extract >> store >> clean >> engineer >> validate >> spark_process >> ml_ready
