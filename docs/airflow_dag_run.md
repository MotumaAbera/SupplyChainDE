# Airflow DAG run evidence

Command: `docker compose -f docker/docker-compose.yml run --rm airflow-test`

- Airflow 2.10.5 (Docker), SequentialExecutor
- DAG: `supply_chain_logistics_pipeline`
- Data: two real Kaggle datasets unioned — DataCo (180,519) + Olist (112,650) = 293,169 rows
- Source #2: 446,937 real delivery milestones pulled over 894 API pages
- Result: **state=success**, all 7 tasks, 0 retries, 0 lock errors

```
[2026-08-18T11:55:34.680+0000] {taskinstance.py:353} INFO - Marking task as SUCCESS. dag_id=supply_chain_logistics_pipeline, task_id=extract_sources, run_id=manual__2026-08-18T00:00:00+00:00, execution_date=20260818T000000, start_date=, end_date=20260818T115534
[2026-08-18T11:59:30.120+0000] {taskinstance.py:353} INFO - Marking task as SUCCESS. dag_id=supply_chain_logistics_pipeline, task_id=store_raw, run_id=manual__2026-08-18T00:00:00+00:00, execution_date=20260818T000000, start_date=, end_date=20260818T115930
[2026-08-18T12:02:53.868+0000] {taskinstance.py:353} INFO - Marking task as SUCCESS. dag_id=supply_chain_logistics_pipeline, task_id=clean_transform, run_id=manual__2026-08-18T00:00:00+00:00, execution_date=20260818T000000, start_date=, end_date=20260818T120253
[2026-08-18T12:03:31.547+0000] {taskinstance.py:353} INFO - Marking task as SUCCESS. dag_id=supply_chain_logistics_pipeline, task_id=engineer_features, run_id=manual__2026-08-18T00:00:00+00:00, execution_date=20260818T000000, start_date=, end_date=20260818T120331
[2026-08-18T12:04:49.516+0000] {taskinstance.py:353} INFO - Marking task as SUCCESS. dag_id=supply_chain_logistics_pipeline, task_id=validate_quality, run_id=manual__2026-08-18T00:00:00+00:00, execution_date=20260818T000000, start_date=, end_date=20260818T120449
[2026-08-18T12:08:08.011+0000] {taskinstance.py:353} INFO - Marking task as SUCCESS. dag_id=supply_chain_logistics_pipeline, task_id=spark_processing, run_id=manual__2026-08-18T00:00:00+00:00, execution_date=20260818T000000, start_date=, end_date=20260818T120808
[2026-08-18T12:09:52.550+0000] {taskinstance.py:353} INFO - Marking task as SUCCESS. dag_id=supply_chain_logistics_pipeline, task_id=generate_ml_ready_dataset, run_id=manual__2026-08-18T00:00:00+00:00, execution_date=20260818T000000, start_date=, end_date=20260818T120952
[2026-08-18T12:09:53.509+0000] {dagrun.py:905} INFO - DagRun Finished: dag_id=supply_chain_logistics_pipeline, execution_date=2026-08-18 00:00:00+00:00, run_id=manual__2026-08-18T00:00:00+00:00, run_start_date=2026-08-18 00:00:00+00:00, run_end_date=2026-08-18 12:09:53.501610+00:00, run_duration=43793.50161, state=success, external_trigger=False, run_type=manual, data_interval_start=2026-08-16 02:00:00+00:00, data_interval_end=2026-08-17 02:00:00+00:00, dag_hash=None
```
