# Airflow DAG run evidence

Command: docker compose -f docker/docker-compose.yml run --rm airflow-test
Airflow 2.10.5 | DAG: supply_chain_logistics_pipeline | Result: state=success, 0 retries

```
[2026-08-18T04:54:47.200+0000] {taskinstance.py:353} INFO - Marking task as SUCCESS. dag_id=supply_chain_logistics_pipeline, task_id=extract_sources, run_id=manual__2026-08-18T00:00:00+00:00, execution_date=20260818T000000, start_date=, end_date=20260818T045447
[2026-08-18T04:55:07.685+0000] {taskinstance.py:353} INFO - Marking task as SUCCESS. dag_id=supply_chain_logistics_pipeline, task_id=store_raw, run_id=manual__2026-08-18T00:00:00+00:00, execution_date=20260818T000000, start_date=, end_date=20260818T045507
[2026-08-18T04:55:16.449+0000] {taskinstance.py:353} INFO - Marking task as SUCCESS. dag_id=supply_chain_logistics_pipeline, task_id=clean_transform, run_id=manual__2026-08-18T00:00:00+00:00, execution_date=20260818T000000, start_date=, end_date=20260818T045516
[2026-08-18T04:55:19.749+0000] {taskinstance.py:353} INFO - Marking task as SUCCESS. dag_id=supply_chain_logistics_pipeline, task_id=engineer_features, run_id=manual__2026-08-18T00:00:00+00:00, execution_date=20260818T000000, start_date=, end_date=20260818T045519
[2026-08-18T04:55:37.771+0000] {taskinstance.py:353} INFO - Marking task as SUCCESS. dag_id=supply_chain_logistics_pipeline, task_id=validate_quality, run_id=manual__2026-08-18T00:00:00+00:00, execution_date=20260818T000000, start_date=, end_date=20260818T045537
[2026-08-18T04:56:19.549+0000] {taskinstance.py:353} INFO - Marking task as SUCCESS. dag_id=supply_chain_logistics_pipeline, task_id=spark_processing, run_id=manual__2026-08-18T00:00:00+00:00, execution_date=20260818T000000, start_date=, end_date=20260818T045619
[2026-08-18T04:56:28.493+0000] {taskinstance.py:353} INFO - Marking task as SUCCESS. dag_id=supply_chain_logistics_pipeline, task_id=generate_ml_ready_dataset, run_id=manual__2026-08-18T00:00:00+00:00, execution_date=20260818T000000, start_date=, end_date=20260818T045628
[2026-08-18T04:56:28.779+0000] {dagrun.py:905} INFO - DagRun Finished: dag_id=supply_chain_logistics_pipeline, execution_date=2026-08-18 00:00:00+00:00, run_id=manual__2026-08-18T00:00:00+00:00, run_start_date=2026-08-18 00:00:00+00:00, run_end_date=2026-08-18 04:56:28.778240+00:00, run_duration=17788.77824, state=success, external_trigger=False, run_type=manual, data_interval_start=2026-08-16 02:00:00+00:00, data_interval_end=2026-08-17 02:00:00+00:00, dag_hash=None
```
