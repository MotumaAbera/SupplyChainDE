#!/usr/bin/env bash
# Run one full, synchronous Airflow DAG run -- no scheduler or webserver.
# This is the evidence command: it executes every task in dependency order and
# exits non-zero if any task fails.
set -euo pipefail

cd /opt/project

# The extract_sources task pulls from the simulated carrier API on
# 127.0.0.1:5055, so that server has to be up inside this container.
echo "[entrypoint] starting simulated shipping API..."
python -m src.ingestion.shipping_api_server > /tmp/api.log 2>&1 &

for _ in $(seq 1 30); do
    if curl -sf http://127.0.0.1:5055/api/v1/health > /dev/null 2>&1; then
        echo "[entrypoint] shipping API is up"
        break
    fi
    sleep 1
done

# Seed data is generated on the host and mounted in, but regenerate if absent
# so the container works from a clean checkout too.
if [ ! -f data/seed/shipping_events_seed.parquet ]; then
    echo "[entrypoint] no seed data found, generating..."
    python -m src.ingestion.generate_seed_dataset
fi

echo "[entrypoint] initialising Airflow metadata DB..."
airflow db migrate

echo "[entrypoint] listing DAGs..."
airflow dags list

echo "[entrypoint] running supply_chain_logistics_pipeline end to end..."
airflow dags test supply_chain_logistics_pipeline "$(date +%F)"
