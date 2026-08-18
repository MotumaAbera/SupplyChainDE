# Airflow DAG run evidence

Command: `docker compose -f docker/docker-compose.yml run --rm airflow-test`

- Airflow 2.10.5 (Docker), SequentialExecutor
- DAG: `supply_chain_logistics_pipeline`
- Data: real Kaggle DataCo Smart Supply Chain, 180,519 rows
- Result: **state=success**, all 7 tasks, 0 retries

```
[2026-08-18T08:11:40.889+0000] {taskinstance.py:353} INFO - Marking task as SUCCESS. dag_id=supply_chain_logistics_pipeline, task_id=extract_sources, run_id=manual__2026-08-18T00:00:00+00:00, execution_date=20260818T000000, start_date=, end_date=20260818T081140
[2026-08-18T08:12:17.748+0000] {taskinstance.py:353} INFO - Marking task as SUCCESS. dag_id=supply_chain_logistics_pipeline, task_id=store_raw, run_id=manual__2026-08-18T00:00:00+00:00, execution_date=20260818T000000, start_date=, end_date=20260818T081217
[2026-08-18T08:12:42.369+0000] {taskinstance.py:353} INFO - Marking task as SUCCESS. dag_id=supply_chain_logistics_pipeline, task_id=clean_transform, run_id=manual__2026-08-18T00:00:00+00:00, execution_date=20260818T000000, start_date=, end_date=20260818T081242
[2026-08-18T08:12:45.250+0000] {taskinstance.py:353} INFO - Marking task as SUCCESS. dag_id=supply_chain_logistics_pipeline, task_id=engineer_features, run_id=manual__2026-08-18T00:00:00+00:00, execution_date=20260818T000000, start_date=, end_date=20260818T081245
[2026-08-18T08:12:58.204+0000] {taskinstance.py:353} INFO - Marking task as SUCCESS. dag_id=supply_chain_logistics_pipeline, task_id=validate_quality, run_id=manual__2026-08-18T00:00:00+00:00, execution_date=20260818T000000, start_date=, end_date=20260818T081258
[2026-08-18T08:13:53.525+0000] {taskinstance.py:353} INFO - Marking task as SUCCESS. dag_id=supply_chain_logistics_pipeline, task_id=spark_processing, run_id=manual__2026-08-18T00:00:00+00:00, execution_date=20260818T000000, start_date=, end_date=20260818T081353
[2026-08-18T08:14:06.961+0000] {taskinstance.py:353} INFO - Marking task as SUCCESS. dag_id=supply_chain_logistics_pipeline, task_id=generate_ml_ready_dataset, run_id=manual__2026-08-18T00:00:00+00:00, execution_date=20260818T000000, start_date=, end_date=20260818T081406
[2026-08-18T08:14:07.361+0000] {dagrun.py:905} INFO - DagRun Finished: dag_id=supply_chain_logistics_pipeline, execution_date=2026-08-18 00:00:00+00:00, run_id=manual__2026-08-18T00:00:00+00:00, run_start_date=2026-08-18 00:00:00+00:00, run_end_date=2026-08-18 08:14:07.358567+00:00, run_duration=29647.358567, state=success, external_trigger=False, run_type=manual, data_interval_start=2026-08-16 02:00:00+00:00, data_interval_end=2026-08-17 02:00:00+00:00, dag_hash=None
```
