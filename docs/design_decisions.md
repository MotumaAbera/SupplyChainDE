# Design Decisions

Why the pipeline is built the way it is. Each entry states the decision, the
alternatives considered, and the reasoning — including the places where a
constraint forced a compromise.

---

## 1. Two ingestion sources: flat file + live REST API

**Decision.** Source #1 is an order-level CSV. Source #2 is a Flask service
(`src/ingestion/shipping_api_server.py`) that serves shipment tracking events
over HTTP.

**Alternatives.** Two CSVs, or a CSV plus a second database table. Both would
satisfy "≥2 sources" literally.

**Reasoning.** Reading two files exercises the same code path twice and proves
nothing about integration. The simulated carrier API deliberately reproduces
the failure modes of a real third-party vendor:

- **pagination** — 500 rows/page, so the extractor must loop (377 pages)
- **transient 503s** — 1% of requests fail, forcing retry-with-backoff
- **rate-limit headers** — `X-RateLimit-Remaining` on every response

`extract_shipping_api.py` therefore has to implement real integration logic
(`_get_with_retry`, page accumulation against `total_rows`) rather than a
single `read_csv`. That is the part of ingestion worth demonstrating.

---

## 2. Storage: SQLite *and* Parquet, not one or the other

**Decision.** Raw data lands in both (`src/storage/raw_storage.py`).

**Reasoning.** They answer different questions, and using both shows why the
choice matters:

| | SQLite | Parquet |
|---|---|---|
| Access | ad-hoc SQL, row lookups | columnar scans |
| Consumer | the cleaning stage's `read_sql` | Spark, Polars |
| Strength | joins, indexing, single-file | compression, column pruning |

The cleaning stage reads from SQLite (it needs relational access across
orders and events); Spark reads Parquet (it needs efficient columnar scans of
103k rows). Neither format is decorative.

---

## 3. Timestamps pinned to microseconds

**Decision.** All Parquet writes go through
`src/utils/parquet_io.write_parquet`, which coerces datetimes to microsecond
precision.

**Reasoning.** This one was found the hard way. Spark cannot read Parquet
columns encoded as `TIMESTAMP(NANOS)` — it raises
`PARQUET_TYPE_ILLEGAL`. pandas holds datetimes as `datetime64[ns]`, and
whether PyArrow encodes that as NANOS depends on the installed versions:
pandas 3.x defaults to microseconds, pandas 2.x to nanoseconds. The result was
a pipeline that passed on the development machine and failed inside the
Airflow container **with identical code**.

Rather than pin pandas and hope, the write path now guarantees the precision.
Microseconds are far finer than the dataset's daily granularity, so nothing is
lost. The lesson: "works on my machine" bugs in a data pipeline usually live
in the serialisation layer.

---

## 4. Deterministic split via md5, not `hash()`

**Decision.** The train/test split keys on
`md5(order_id)` (`src/ml_ready/build_ml_dataset.py`).

**Reasoning.** The original implementation used Python's built-in `hash()`,
which is **salted per interpreter process** (`PYTHONHASHSEED`). The split was
documented as deterministic but silently produced different train/test sizes
on every run — 82,745 rows one run, 82,747 the next. `hashlib.md5` is stable
across processes and machines, so a given `order_id` always lands in the same
side of the split. Verified: two consecutive runs now both yield
82,851 / 20,697.

Hash-based splitting was chosen over `train_test_split(random_state=...)`
because it is stable under *data growth*: adding new orders does not reshuffle
the existing ones between train and test, which matters for a pipeline
designed to run daily.

---

## 5. Ephemeral GX context for validation, file-backed only for Data Docs

**Decision.** `gx_validation.py` uses `mode="ephemeral"`; a separate
`build_data_docs.py` uses a file-backed context.

**Reasoning.** The validation stage runs inside an Airflow task on every DAG
run. An ephemeral context needs no on-disk GX project, no migration, and
cannot be corrupted by concurrent runs — it validates and returns. Its outputs
are the machine-readable `data_quality_report.json` (which the DAG's quality
gate reads) and the human-readable Markdown.

Data Docs, however, *require* persistence. Keeping them in a separate script
means the browsable HTML report is available on demand without making the
orchestrated path depend on on-disk GX state.

---

## 6. A quality gate that can fail the DAG

**Decision.** `validate_quality` raises if fewer than 90% of expectations
pass, halting the run before Spark and the ML-ready build.

**Reasoning.** Validation that only logs is decoration. The point of a quality
suite in a pipeline is to *stop bad data from propagating* — the gate makes
the guarantee enforceable. 90% rather than 100% leaves headroom for a single
non-critical expectation drifting on new data without blocking the pipeline;
the report always records exactly what failed.

Similarly, `extract_sources` aborts on a zero-row extract and `clean_transform`
aborts if cleaning removes every row. Both are cheap guards against silently
producing an empty dataset.

---

## 7. Spark in local mode, despite a 103k-row dataset

**Decision.** PySpark runs `local[*]` over data that fits comfortably in
pandas.

**Reasoning.** Honest framing: at this size Spark is *slower* than pandas —
JVM startup alone costs more than the whole computation. It is used because
the aggregations written here (`groupBy` rollups, and a 7-order rolling
average per carrier via `Window.partitionBy(...).rowsBetween(...)`) are the
ones that would not change shape at 100× the data. The code is the
deliverable, not the runtime.

Polars covers the case where speed at this scale genuinely matters — it writes
the ~100k-row flat CSV export several times faster than pandas.

---

## 8. Airflow in Docker rather than natively

**Decision.** Orchestration runs via `docker/docker-compose.yml`.

**Reasoning.** Not a preference — a constraint. Airflow depends on the
POSIX-only `pwd` and `fcntl` modules and cannot be pip-installed on native
Windows, which is the development platform. The container image adds OpenJDK
17 on top of `apache/airflow:2.10.5` because the `spark_processing` task needs
a JVM and the base image ships without one.

The repo is bind-mounted at `/opt/project`, so the DAG executes the *same*
`src/` modules as a native run and writes outputs back to the host. There is
no duplicated pipeline logic between the two paths — the DAG tasks are thin
wrappers that call each stage's `main()`.

---

## 9. Idempotent stages, file-based handoff

**Decision.** Every stage reads from disk, writes to disk, and can be re-run
safely. Tasks pass data through Parquet files rather than Airflow XCom.

**Reasoning.** XCom is designed for small metadata, not 100k-row frames;
pushing dataframes through it would serialise them into the metadata database.
File handoff keeps each stage independently runnable — essential for
debugging, and what makes Airflow's automatic retries safe. A retried task
recomputes from its inputs and overwrites its outputs, so a partial failure
never leaves a half-written state that the next attempt would compound.

---

## 10. Real Kaggle data, with four derived columns

**Decision.** Source #1 is the **DataCo Smart Supply Chain** dataset from
Kaggle (`shashwatwork/dataco-smart-supply-chain-for-big-data-analysis`) —
**180,519 rows × 53 columns**, fetched by `src/ingestion/download_kaggle.py`.

**Provenance of every field.** 21 of the 25 schema columns map directly from
the source:

| Schema column | Source column |
|---|---|
| `order_date` | `order date (DateOrders)` |
| `promised_delivery_days` | `Days for shipment (scheduled)` |
| `actual_delivery_days` | `Days for shipping (real)` |
| `product_category` | `Category Name` |
| `quantity` | `Order Item Quantity` |
| `unit_price` | `Product Price` |
| `discount_rate` | `Order Item Discount Rate` |
| `destination_latitude/longitude` | `Latitude` / `Longitude` |
| `destination_city/country/region` | `Order City` / `Order Country` / `Order Region` |
| `shipping_mode` | `Shipping Mode` |
| `order_status` | `Order Status` |
| `delay_reason` | `Delivery Status` |
| `customer_id`, `customer_segment` | `Customer Id`, `Customer Segment` |
| `product_id` | `Product Card Id` |
| `origin_warehouse_id`, `origin_region` | `Department Id`, `Market` |

Critically, **the target is real**: `delivery_delay = actual − promised` comes
from two genuine source columns, giving a real class balance of **57.3%
delayed** rather than an invented one. The geospatial columns are real too,
which matters for Topic 9's route/coordinate requirements.

**Four columns are derived, not real,** because the source does not carry
them — this is stated plainly rather than buried:

- `weight_kg` — derived from quantity
- `distance_km` — synthesised
- `shipping_cost` — derived from distance and weight
- `carrier` — synthesised from the six-carrier value set

The dataset has `Shipping Mode` but no carrier field. Features that depend on
these four (`shipping_cost_per_unit`, `route_efficiency_score`,
`carrier_performance_score`) are therefore computed over partly-derived
inputs. Everything driven by delivery days, dates, categories, geography and
price is real.

**`order_id` is renumbered.** The source is order-*item* level, so `Order Id`
repeats across line items (114,767 duplicates). Since the expectation suite
requires a unique key matching `^ORD-\d+$`, rows are renumbered sequentially.

**Source #2 is regenerated from Source #1.** The simulated carrier API serves
events joined on `order_id`, so events built against the old synthetic ids
would join to nothing. `generate_seed_dataset.py --events-only` rebuilds them
from whichever orders file is in place — verified at a **100% join rate**
(60,000/60,000 sampled orders).

**The synthetic generator is retained as a fallback** for anyone without a
Kaggle token. It is seeded (`seed=42`) and schema-faithful, so the pipeline
runs identically either way and no downstream stage changes.

**Expectation adjusted for real data.** The suite originally required
`promised_delivery_days >= 1`. Real data legitimately contains 0 — the
"Same Day" shipping mode. The bound was relaxed to 0 rather than clipping the
data, because the data is correct and the assumption was wrong.
