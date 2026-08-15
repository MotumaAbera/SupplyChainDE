const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow,
  TableCell, WidthType, ShadingType, BorderStyle, ImageRun, PageBreak, TableOfContents,
  LevelFormat, VerticalAlign, Footer, PageNumber, NumberFormat,
  PositionalTab, PositionalTabAlignment, PositionalTabLeader, PositionalTabRelativeTo,
} = require("docx");

const ROOT = path.join(__dirname, "..");
const DOCS = path.join(ROOT, "docs");
const PAGE_W = 12240, PAGE_H = 15840; // US Letter (DXA)

const FONT = "Calibri";
const MONO = "Consolas";
const SECONDARY = "52514E";
const GRID = "E1E0D9";

function H1(text) { return new Paragraph({ text, heading: HeadingLevel.HEADING_1, spacing: { before: 320, after: 160 } }); }
function H2(text) { return new Paragraph({ text, heading: HeadingLevel.HEADING_2, spacing: { before: 240, after: 120 } }); }
function P(text, opts = {}) {
  return new Paragraph({ spacing: { after: 160, line: 276 }, children: [new TextRun({ text, font: FONT, size: 22, ...opts })] });
}
function Bullet(text) {
  return new Paragraph({
    numbering: { reference: "bullet-list", level: 0 },
    spacing: { after: 80 },
    children: [new TextRun({ text, font: FONT, size: 22 })],
  });
}
function Code(lines) {
  return new Paragraph({
    shading: { type: ShadingType.CLEAR, fill: "F4F3EF" },
    border: {
      top: { style: BorderStyle.SINGLE, size: 2, color: GRID }, bottom: { style: BorderStyle.SINGLE, size: 2, color: GRID },
      left: { style: BorderStyle.SINGLE, size: 2, color: GRID }, right: { style: BorderStyle.SINGLE, size: 2, color: GRID },
    },
    spacing: { before: 120, after: 200 },
    children: lines.flatMap((l, i) => [new TextRun({ text: l || " ", font: MONO, size: 18, break: i === 0 ? 0 : 1 })]),
  });
}
function cell(text, opts = {}) {
  return new TableCell({
    width: { size: opts.width || 2000, type: WidthType.DXA },
    shading: opts.header ? { type: ShadingType.CLEAR, fill: "EAF1FB" } : undefined,
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: [new TextRun({ text: String(text), font: FONT, size: 20, bold: !!opts.header })] })],
  });
}
function simpleTable(headers, rows, widths) {
  const total = widths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: widths,
    rows: [
      new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, { header: true, width: widths[i] })) }),
      ...rows.map(r => new TableRow({ children: r.map((c, i) => cell(c, { width: widths[i] })) })),
    ],
  });
}
function image(filePath, width, height) {
  const data = fs.readFileSync(filePath);
  return new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { before: 160, after: 160 },
    children: [new ImageRun({ data, type: "png", transformation: { width, height } })],
  });
}
function caption(text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { after: 240 },
    children: [new TextRun({ text, italics: true, font: FONT, size: 18, color: SECONDARY })],
  });
}
function pageBreak() { return new Paragraph({ children: [new PageBreak()] }); }
const TOC_TAB_POS = 9360; // right text margin on US Letter w/ 1in margins (12240 - 2*1440)
function tocLine(text, pg, bold = false, indent = 0) {
  return new Paragraph({
    spacing: { after: 100 },
    indent: indent ? { left: indent } : undefined,
    tabStops: [{ type: "right", position: TOC_TAB_POS, leader: "dot" }],
    children: [
      new TextRun({ text: text + "\t" + String(pg), font: FONT, size: 22, bold }),
    ],
  });
}

const S = [];

// ============================== TITLE PAGE ==============================
S.push(
  new Paragraph({ spacing: { before: 2400 }, children: [] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
    children: [new TextRun({ text: "Assessment 2", font: FONT, size: 28, color: SECONDARY })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 },
    children: [new TextRun({ text: "End-to-End Data Engineering Project:\nA Supply Chain Logistics Pipeline for Delivery-Delay Prediction", font: FONT, size: 40, bold: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
    children: [new TextRun({ text: "Topic 9 — Supply Chain Logistics Pipeline", font: FONT, size: 24, italics: true, color: SECONDARY })] }),
  new Paragraph({ spacing: { before: 1600 }, children: [] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [new TextRun({ text: "Prepared by: Motty", font: FONT, size: 24 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [new TextRun({ text: "Organization: DxValley", font: FONT, size: 24 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [new TextRun({ text: "Student ID: [Student ID]", font: FONT, size: 24, color: SECONDARY })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [new TextRun({ text: "Course: [Course Name]", font: FONT, size: 24, color: SECONDARY })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [new TextRun({ text: "Instructor: [Instructor Name]", font: FONT, size: 24, color: SECONDARY })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [new TextRun({ text: "Date: August 15, 2026  |  Submission Deadline: August 28, 2026", font: FONT, size: 22 })] }),
  pageBreak(),
);

// ============================== EXECUTIVE SUMMARY ==============================
S.push(
  H1("Executive Summary"),
  P("This report documents the design, implementation, and evaluation of an end-to-end data engineering pipeline for the Supply Chain Logistics Pipeline track (Topic 9) of Assessment 2. The pipeline ingests order-level logistics data from two independent sources, cleans and validates it, engineers ten domain-relevant features, processes it at scale with PySpark, orchestrates the full workflow with Apache Airflow, versions every dataset with DVC, and produces an ML-ready dataset for delivery-delay prediction alongside an interactive analytics dashboard."),
  new Paragraph({ children: [new TextRun({ text: "Overview. ", bold: true, font: FONT, size: 22 }),
    new TextRun({ text: "The project targets the core business problem behind Topic 9: predicting whether a shipment will arrive late (binary) and by how many days (regression), using operational signals available at order time — carrier, shipping mode, distance, product category, warehouse load, and seasonal demand. All ten Core Requirements and every phase of the Common Pipeline Phases table in the assessment brief are implemented and independently verified, not merely scaffolded.", font: FONT, size: 22 })],
    spacing: { after: 160, line: 276 } }),
  new Paragraph({ children: [new TextRun({ text: "Tools used. ", bold: true, font: FONT, size: 22 }),
    new TextRun({ text: "Python 3.11, Pandas/NumPy, Polars/PyArrow, PySpark 4.2 (local mode), SQLite, Apache Parquet, Great Expectations 1.20, Apache Airflow 2.9.3, DVC 3.x, Flask (simulated carrier API), and Plotly for the dashboard. Exact versions are pinned in requirements.txt (Appendix E).", font: FONT, size: 22 })],
    spacing: { after: 160, line: 276 } }),
  P("Key outcomes:"),
  Bullet("105,525 raw orders ingested from two sources; 103,548 rows survive cleaning (98.1% retention) after removing 522 duplicates, 317 malformed dates, and 1,138 invalid coordinates, and imputing 2,120 missing delivery-time and 1,053 missing shipping-cost values."),
  Bullet("10 engineered features (11 including the binary delay flag), each with a documented rationale (Section 6, Appendix D)."),
  Bullet("A 21-check Great Expectations suite passes at 100% on the cleaned, feature-engineered dataset."),
  Bullet("An Apache Airflow DAG (extract → store → clean → engineer → validate → Spark-process → ML-ready) executed end-to-end via \"airflow dags test\" with a successful DagRun — proven to run, not just authored."),
  Bullet("All raw, processed, and ML-ready datasets are tracked with DVC against a local remote, with two committed versions (v1, v2) in git history."),
  Bullet("A final ML-ready dataset of 103,548 rows (82,840 train / 20,708 test, ~71%/29% class balance) plus a self-contained interactive analytics dashboard."),
  new Paragraph({ children: [new TextRun({ text: "Architecture at a glance. ", bold: true, font: FONT, size: 22 }),
    new TextRun({ text: "Two ingestion connectors feed a dual-format raw store (SQLite + Parquet); a cleaning stage and a feature-engineering stage transform the data; a Great Expectations gate validates it; PySpark computes carrier/region aggregates and a rolling-delay window metric; a final stage assembles the ML-ready split and dashboard. Apache Airflow orchestrates all seven stages with retries and a data-quality gate; DVC versions every dataset produced along the way. See Section 2 for the full architecture diagram.", font: FONT, size: 22 })],
    spacing: { after: 160, line: 276 } }),
  pageBreak(),
);

// ============================== TOC ==============================
const SUB = 360; // sub-heading indent (twips)
S.push(
  H1("Table of Contents"),
  tocLine("Executive Summary", 2, true),
  tocLine("1. Introduction", 5, true),
  tocLine("1.1 Background", 5, false, SUB),
  tocLine("1.2 Problem Statement", 5, false, SUB),
  tocLine("1.3 Objectives", 5, false, SUB),
  tocLine("1.4 Scope", 5, false, SUB),
  tocLine("2. Pipeline Architecture", 6, true),
  tocLine("2.1 Components", 6, false, SUB),
  tocLine("2.2 Key Design Decisions", 7, false, SUB),
  tocLine("3. Data Sources & Ingestion", 8, true),
  tocLine("3.1 Datasets", 8, false, SUB),
  tocLine("3.2 Ingestion Methods", 8, false, SUB),
  tocLine("3.3 Challenges", 8, false, SUB),
  tocLine("4. Processing & Feature Engineering", 10, true),
  tocLine("4.1 Cleaning", 10, false, SUB),
  tocLine("4.2 Feature Engineering", 10, false, SUB),
  tocLine("4.3 Code Snippet — Carrier Performance & Route Efficiency", 10, false, SUB),
  tocLine("4.4 PySpark Processing", 11, false, SUB),
  tocLine("5. Data Quality", 12, true),
  tocLine("6. Orchestration", 13, true),
  tocLine("6.1 Scheduling & Error Handling", 13, false, SUB),
  tocLine("6.2 Verification", 13, false, SUB),
  tocLine("7. Versioning & Reproducibility", 14, true),
  tocLine("7.1 DVC Setup", 14, false, SUB),
  tocLine("7.2 Reproducibility", 14, false, SUB),
  tocLine("8. Results & Outputs", 15, true),
  tocLine("8.1 ML-Ready Dataset", 15, false, SUB),
  tocLine("8.2 Key Findings", 15, false, SUB),
  tocLine("8.3 Analytics Dashboard", 15, false, SUB),
  tocLine("9. Challenges & Future Work", 17, true),
  tocLine("9.1 Challenges Encountered", 17, false, SUB),
  tocLine("9.2 Future Work", 17, false, SUB),
  tocLine("10. References", 18, true),
  tocLine("Appendix", 19, true),
  tocLine("A. Code Structure", 19, false, SUB),
  tocLine("B. Airflow DAG (excerpt)", 19, false, SUB),
  tocLine("C. Great Expectations Suite (expectation list)", 19, false, SUB),
  tocLine("D. DVC Configuration", 19, false, SUB),
  tocLine("E. Environment Setup (requirements.txt)", 20, false, SUB),
  tocLine("F. Data Dictionary (summary)", 20, false, SUB),
  tocLine("G. Reproduction Guide (summary)", 20, false, SUB),
  tocLine("H. Sample ML-Ready Output (first rows)", 21, false, SUB),
  pageBreak(),
);

// ============================== 1. INTRODUCTION ==============================
S.push(
  H1("1. Introduction"),
  H2("1.1 Background"),
  P("Modern e-commerce and logistics operations depend on accurate, timely visibility into where shipments are and whether they will arrive on schedule. Late deliveries drive customer-service costs, erode trust, and cascade into inventory and warehouse-planning problems. Predicting delivery delay before or shortly after an order is placed lets a business proactively re-route shipments, adjust customer expectations, or renegotiate carrier contracts. Doing this well requires clean, feature-rich, well-governed data — the data-engineering problem this assessment targets."),
  H2("1.2 Problem Statement"),
  P("Raw logistics data is rarely analysis-ready: it arrives from multiple systems (order-management exports, carrier tracking APIs) in inconsistent formats, with missing values, invalid geospatial data, and no engineered signal for delay risk. Assessment 2 asks for a complete pipeline — ingestion through orchestration and versioning — that turns this raw data into a trustworthy, ML-ready dataset. This project implements that pipeline for Topic 9: Supply Chain Logistics."),
  H2("1.3 Objectives"),
  Bullet("Ingest logistics data from at least two independent sources (a file-based export and a REST API)."),
  Bullet("Persist raw data in at least two storage formats (SQLite and Parquet)."),
  Bullet("Clean and standardize the data: handle missing values, standardize categorical fields, validate dates and coordinates, and remove duplicates."),
  Bullet("Engineer at least ten domain-relevant features with documented rationale."),
  Bullet("Validate data quality with Great Expectations and publish a data-quality report."),
  Bullet("Process the data at scale with PySpark (aggregations and window functions)."),
  Bullet("Orchestrate the full pipeline with an Apache Airflow DAG, including retries and failure handling."),
  Bullet("Version every dataset produced with DVC."),
  Bullet("Produce an ML-ready dataset for delivery-delay prediction (binary and regression targets) and a supply-chain analytics dashboard."),
  Bullet("Document the architecture, data dictionary, and a step-by-step reproduction guide."),
  H2("1.4 Scope"),
  P("In scope: the full data pipeline from raw ingestion to an ML-ready dataset, including orchestration, quality gating, versioning, and analytics visualization. Out of scope: training and evaluating a predictive model on the ML-ready dataset (the brief scopes this project as a data-engineering deliverable that feeds, but does not itself include, a downstream modeling exercise), and production cloud deployment (addressed only as optional future work, matching the assessment's own bonus framing of cloud deployment as optional)."),
  pageBreak(),
);

// ============================== 2. ARCHITECTURE ==============================
S.push(
  H1("2. Pipeline Architecture"),
  P("Figure 1 shows the full pipeline: two ingestion connectors feed a dual-format raw store, followed by cleaning, feature engineering, quality validation, PySpark processing, and ML-ready dataset generation — all orchestrated by an Airflow DAG and versioned by DVC."),
  image(path.join(DOCS, "diagrams", "architecture_diagram.png"), 500, 504),
  caption("Figure 1. End-to-end pipeline architecture."),
  H2("2.1 Components"),
  simpleTable(
    ["Component", "Implementation"],
    [
      ["Ingestion", "extract_csv.py (file source); extract_shipping_api.py + shipping_api_server.py (simulated carrier REST API with pagination and retry logic)"],
      ["Raw storage", "SQLite (supply_chain_raw.db) and Parquet (data/raw/parquet/)"],
      ["Transformation", "clean.py — missing-value imputation, categorical standardization, date/coordinate validation, deduplication"],
      ["Feature engineering", "engineer.py — 10 engineered features (Section 6)"],
      ["Data quality", "gx_validation.py — 21-expectation Great Expectations suite"],
      ["Large-scale processing", "spark_processing.py — PySpark local-mode aggregations and window functions"],
      ["Orchestration", "dags/supply_chain_dag.py — 7-task Airflow DAG"],
      ["Versioning", "DVC-tracked datasets against a local remote"],
      ["Output", "build_ml_dataset.py (train/test split) + build_dashboard.py (Plotly dashboard)"],
    ],
    [2600, 7600],
  ),
  H2("2.2 Key Design Decisions"),
  Bullet("Pandas + PySpark, not PySpark-only: interactive cleaning/feature steps use Pandas for iteration speed and readability; the aggregation-heavy processing stage uses PySpark specifically to exercise groupBy aggregations and window functions at scale, per the assessment's \"Use PySpark (local) or Pandas/Polars\" requirement."),
  Bullet("SQLite + Parquet as the two raw formats: SQLite gives ad-hoc SQL queryability over the raw extract; Parquet gives columnar, compressed storage suited to the downstream Spark and Pandas processing."),
  Bullet("A real, running simulated API rather than a mocked function: the shipping-carrier API is an actual Flask server queried over HTTP with pagination, a rate-limit header, and a simulated transient-503 rate, so the ingestion code handles the same failure modes a real vendor integration would."),
  Bullet("A deterministic hash-based train/test split (on order_id) rather than a random seed: keeps the split perfectly reproducible across pipeline re-runs without depending on RNG state."),
  Bullet("A data-quality gate inside the DAG: the validate_quality task fails the DAG run if fewer than 90% of Great Expectations checks pass, so a data-quality regression stops the pipeline rather than silently propagating downstream."),
  pageBreak(),
);

// ============================== 3. DATA SOURCES & INGESTION ==============================
S.push(
  H1("3. Data Sources & Ingestion"),
  H2("3.1 Datasets"),
  P("The pipeline models a supply-chain logistics dataset in the style of the assessment's suggested source (\"Supply Chain Analytics, Kaggle, ~100,000+ rows\"), combined with a simulated shipping-carrier API as the second required source (files + API)."),
  new Paragraph({ children: [new TextRun({ text: "Data provenance note: ", bold: true, font: FONT, size: 22 }),
    new TextRun({ text: "the build environment for this project did not have live Kaggle API access (no credentials, and the sandbox's web tools could not reach Kaggle's authenticated dataset pages). To avoid blocking delivery, a large (105,525-row), seeded, statistically realistic synthetic dataset was generated that reproduces the exact schema, cardinalities, and relationships of a real Kaggle supply-chain logistics export (see src/utils/reference_data.py and Appendix A). Every pipeline stage operates identically regardless of the CSV's origin; Appendix G / docs/reproduction_guide.md documents the one-file swap-in procedure to substitute a real Kaggle CSV.", font: FONT, size: 22, italics: true, color: SECONDARY })],
    spacing: { after: 200, line: 276 } }),
  simpleTable(
    ["Source", "Type", "Volume", "Key fields"],
    [
      ["kaggle_supply_chain_orders.csv", "File (CSV)", "105,525 rows, 25 columns", "order_id, carrier, shipping_mode, distance_km, promised/actual_delivery_days, shipping_cost, destination coordinates"],
      ["Shipping-carrier API (Flask, simulated)", "REST API (JSON, paginated)", "188,299 tracking events across 6 carriers", "order_id, event_type (PICKED_UP/IN_TRANSIT/CUSTOMS/DELAYED/DELIVERED), event_timestamp, delay_reason"],
    ],
    [3200, 2000, 2200, 2800],
  ),
  H2("3.2 Ingestion Methods"),
  P("extract_csv.py reads the file source directly with Pandas. extract_shipping_api.py queries the Flask API's paginated /shipments/events endpoint (500 rows/page) and its /carriers/performance endpoint, retrying up to 4 times with backoff on the simulated transient 503. Both raw extracts are then persisted in two formats — SQLite and Parquet — by raw_storage.py."),
  Code([
    "def _get_with_retry(url, params=None):",
    "    for attempt in range(MAX_RETRIES):",
    "        resp = requests.get(url, params=params, timeout=10)",
    "        if resp.status_code == 200:",
    "            return resp.json()",
    "        time.sleep(0.2 * (attempt + 1))",
    "    raise RuntimeError(f\"Failed to fetch {url} after {MAX_RETRIES} retries\")",
  ]),
  H2("3.3 Challenges"),
  Bullet("Kaggle access unavailable in the sandbox — addressed by generating a schema-faithful synthetic dataset with full transparency (Section 3.1) and a documented swap-in path."),
  Bullet("Simulating realistic API failure modes (pagination, rate limits, transient 503s) so the retry logic in extract_shipping_api.py is genuinely exercised rather than trivially always succeeding."),
  Bullet("Coordinate validity: ~1.5% of generated destination coordinates are deliberately out-of-range to require real validation logic downstream (Section 4)."),
  pageBreak(),
);

// ============================== 4. PROCESSING & FEATURE ENGINEERING ==============================
S.push(
  H1("4. Processing & Feature Engineering"),
  H2("4.1 Cleaning"),
  P("clean.py applies, in order: exact-duplicate removal, date validation (invalid order_date strings coerced to NaT and dropped), categorical standardization (casing/whitespace on product_category, carrier, order_status), coordinate-range validation (latitude in [-90, 90], longitude in [-180, 180]), missing-value imputation (actual_delivery_days and shipping_cost imputed by carrier/shipping-mode group median), and type conversion."),
  simpleTable(
    ["Metric", "Value"],
    [
      ["Input rows", "105,525"],
      ["Duplicates removed", "522"],
      ["Invalid dates dropped", "317"],
      ["Invalid coordinates removed", "1,138"],
      ["Missing actual_delivery_days imputed", "2,120"],
      ["Missing shipping_cost imputed", "1,053"],
      ["Output rows", "103,548 (98.1% retention)"],
    ],
    [5200, 4400],
  ),
  H2("4.2 Feature Engineering"),
  P("Ten domain-relevant features (plus a binary delay-flag helper) are engineered in engineer.py, each with a documented rationale:"),
  simpleTable(
    ["#", "Feature", "Rationale (abridged)"],
    [
      ["1", "delivery_delay", "actual − promised delivery days; core delay signal and regression target"],
      ["2", "shipping_cost_per_unit", "shipping_cost / quantity — normalizes cost across order sizes"],
      ["3", "route_efficiency_score", "distance/time, min-max normalized within destination region"],
      ["4", "carrier_performance_score", "historical on-time rate per carrier"],
      ["5", "seasonal_demand_index", "monthly order volume vs. yearly average (captures peak season)"],
      ["6", "distance_category", "binned distance: Local / Regional / Long-Haul / International"],
      ["7", "warehouse_utilization", "daily warehouse order load vs. stated capacity"],
      ["8", "inventory_turnover", "proxy: category units/day vs. category average"],
      ["9", "reorder_risk_score", "composite of carrier×category delay rate and demand volatility"],
      ["10", "shipment_size_category", "binned weight × quantity: Small/Medium/Large/Bulk"],
    ],
    [500, 2800, 6300],
  ),
  P("Full formulas and rationale are in the project data dictionary (Appendix D)."),
  H2("4.3 Code Snippet — Carrier Performance & Route Efficiency"),
  Code([
    "carrier_rate = 1 - df.groupby('carrier')['is_delayed'].transform('mean')",
    "df['carrier_performance_score'] = carrier_rate.round(4)",
    "",
    "speed = df['distance_km'] / df['actual_delivery_days'].replace(0, np.nan)",
    "df['route_efficiency_score'] = (",
    "    df.groupby('destination_region')['_speed_km_per_day']",
    "      .transform(_minmax_norm).round(4)",
    ")",
  ]),
  H2("4.4 PySpark Processing"),
  P("spark_processing.py loads the feature-engineered Parquet dataset into a local-mode Spark session and computes three analytics tables: carrier_monthly_performance (groupBy carrier × month), region_route_summary (groupBy region × distance category), and rolling_delay_trend — a 7-order trailing average of delivery_delay computed with a Spark window function partitioned by carrier and ordered by order date. All three ran successfully against the full 103,548-row dataset."),
  pageBreak(),
);

// ============================== 5. DATA QUALITY ==============================
S.push(
  H1("5. Data Quality"),
  P("Data quality is enforced with a Great Expectations 1.20 suite (gx_validation.py) built on the Fluent API, running 21 expectations against the cleaned, feature-engineered dataset: uniqueness and non-null checks on order_id, categorical set membership for carrier/shipping_mode/distance_category/shipment_size_category, numeric range checks on quantity, price, cost, coordinates, distance, and delivery-time columns, a regex format check on order_id, and range checks on the three [0,1]-bounded engineered scores."),
  simpleTable(
    ["Metric", "Value"],
    [
      ["Dataset validated", "orders_featured.parquet (103,548 rows, 36 columns)"],
      ["Expectations run", "21"],
      ["Passed", "21"],
      ["Failed", "0"],
      ["Success rate", "100.0%"],
      ["Overall suite result", "PASS"],
    ],
    [4200, 5400],
  ),
  P("The full machine-readable report is published to docs/data_quality_report.json / .md and is regenerated on every pipeline run. As an independent cross-check, the carrier on-time rate computed from the cleaned orders data was compared against the shipping-carrier API's own independently-computed carrier performance endpoint; both sources agree on carrier ranking (DHL Express best, Local Courier Co worst), corroborating the feature's validity."),
  pageBreak(),
);

// ============================== 6. ORCHESTRATION ==============================
S.push(
  H1("6. Orchestration"),
  P("The full pipeline is orchestrated by a single Apache Airflow DAG, supply_chain_logistics_pipeline (dags/supply_chain_dag.py), with seven tasks in a linear dependency chain:"),
  Code([
    "extract_sources >> store_raw >> clean_transform >> engineer_features",
    "  >> validate_quality >> spark_processing >> generate_ml_ready_dataset",
  ]),
  H2("6.1 Scheduling & Error Handling"),
  Bullet("Schedule: daily at 02:00 UTC (cron \"0 2 * * *\"), catchup disabled, max 1 concurrent run."),
  Bullet("Retries: 2 retries per task with exponential backoff (starting at 3 minutes, capped at 15 minutes)."),
  Bullet("Timeouts: a 30-minute execution timeout per task."),
  Bullet("Data-quality gate: validate_quality raises (failing the run) if the Great Expectations pass rate drops below 90%."),
  Bullet("Failure alerting hook: an on_failure_callback logs the failing task, DAG run, and exception for downstream alerting (Slack/email/PagerDuty in a production deployment)."),
  H2("6.2 Verification"),
  P("The DAG was not just authored but executed end-to-end in this environment: `airflow db migrate` initialized the metadata store, `airflow dags list-import-errors` confirmed zero import errors, and `airflow dags test supply_chain_logistics_pipeline <date>` ran all seven tasks to completion, ending with \"DagRun Finished ... state=success\" in the Airflow logs. Each task's own stdout (row counts, validation results, Spark aggregation counts) is visible in that run and reproduced in the sections above."),
  pageBreak(),
);

// ============================== 7. VERSIONING & REPRODUCIBILITY ==============================
S.push(
  H1("7. Versioning & Reproducibility"),
  H2("7.1 DVC Setup"),
  P("DVC is initialized in the project root with a local remote. The following datasets are tracked as DVC pointers (.dvc files) rather than committed directly to git, keeping the git history lightweight while giving every dataset a content-addressed, retrievable version:"),
  Bullet("data/raw/kaggle_supply_chain_orders.csv, data/raw/supply_chain_raw.db"),
  Bullet("data/processed/orders_clean.parquet, data/processed/orders_featured.parquet"),
  Bullet("data/ml_ready/train.parquet, data/ml_ready/test.parquet"),
  P("Two versions have been committed (v1: initial pipeline + raw/processed data; v2: documentation, dashboard, and refreshed feature data), each pushed to the local DVC remote with `dvc push`. A historical version can be restored at any time with `git checkout <commit> && dvc checkout`."),
  H2("7.2 Reproducibility"),
  P("A complete, tested step-by-step reproduction guide is provided in docs/reproduction_guide.md (reproduced in Appendix G), covering environment setup, dataset generation, starting the simulated API, running each stage manually, running the full DAG via Airflow, and restoring DVC-tracked data versions. Every command in that guide was executed against this exact codebase while preparing this report."),
  pageBreak(),
);

// ============================== 8. RESULTS & OUTPUTS ==============================
S.push(
  H1("8. Results & Outputs"),
  H2("8.1 ML-Ready Dataset"),
  simpleTable(
    ["Metric", "Value"],
    [
      ["Total rows", "103,548"],
      ["Train / test split", "82,840 / 20,708 (80/20, deterministic hash split on order_id)"],
      ["Feature columns", "22 (14 numeric/engineered, 8 categorical, left un-encoded)"],
      ["Targets", "is_delayed (binary), delivery_delay (regression, days)"],
      ["Class balance (is_delayed)", "71.1% on-time (0) / 28.9% delayed (1)"],
    ],
    [3600, 6000],
  ),
  H2("8.2 Key Findings"),
  Bullet("Carrier performance varies meaningfully: DHL Express has the best on-time rate (74.8%) and Local Courier Co the worst (62.7%) — a >12-point spread that makes carrier_performance_score a strong candidate predictive feature."),
  Bullet("Regional delay rates cluster fairly tightly (27.8%–30.4%) but North America has the highest delay rate (30.4%) despite not being the most distant region on average — suggesting warehouse/demand strain (captured by warehouse_utilization and seasonal_demand_index) matters as much as raw distance."),
  Bullet("Counter-intuitively, average delivery_delay is highest for Local shipments (0.417 days) and lowest for International shipments (0.366 days) — plausibly because international shipments carry more schedule buffer (longer promised_delivery_days) that absorbs the same absolute variability, whereas local \"same/next-day\" promises leave little slack. This is exactly the kind of relationship distance_category and route_efficiency_score are engineered to expose."),
  Bullet("Order volume peaks sharply in November (seasonal_demand_index ≈ 1.45) and December (≈ 1.55), consistent with holiday-season demand; this seasonal strain is precisely what warehouse_utilization and reorder_risk_score are designed to capture for delay prediction."),
  H2("8.3 Analytics Dashboard"),
  P("A self-contained (offline-capable) Plotly dashboard summarizes these results interactively: KPI tiles (total orders, on-time rate, average delay, total shipping cost), monthly order volume, carrier on-time rate, regional delay rate, delay by distance category, and order volume by product category. See Figure 2 and the delivered file docs/dashboard/supply_chain_dashboard.html."),
  image(path.join(__dirname, "..", "docs", "diagrams", "dashboard_screenshot.png"), 460, 662),
  caption("Figure 2. Supply chain analytics dashboard (excerpt)."),
  pageBreak(),
);

// ============================== 9. CHALLENGES & FUTURE WORK ==============================
S.push(
  H1("9. Challenges & Future Work"),
  H2("9.1 Challenges Encountered"),
  Bullet("No live Kaggle API access in the build sandbox — resolved by generating a schema-faithful synthetic dataset with full transparency and a documented real-data swap-in path (Section 3.1, Appendix G)."),
  Bullet("Dependency conflicts between Airflow's Flask-AppBuilder (requires Flask 2.2.5) and a newer Flask installed for the simulated API server — resolved by pinning Flask to the version in Airflow's official constraints file."),
  Bullet("Great Expectations 1.x's Fluent API differs substantially from the older 0.18 class-based API referenced in general documentation — the validation suite was built and tested against the actual installed 1.20 API."),
  Bullet("PySpark 4.2 emits a compatibility warning against pandas ≥ 3.0 (not yet officially supported by the PySpark maintainers at time of writing); this did not affect correctness in testing but is worth monitoring."),
  H2("9.2 Future Work"),
  Bullet("Swap in a real Kaggle/UCI/Zenodo supply-chain dataset once API credentials are available (one-file swap per Appendix G) and re-validate all downstream metrics."),
  Bullet("Train and evaluate delivery-delay models (e.g. gradient-boosted trees for classification, and regression for delay-days) on the ML-ready dataset produced here."),
  Bullet("Deploy to a cloud environment (AWS/GCP/Azure) per the assessment's optional cloud bonus, e.g. S3/Blob-backed DVC remote, a managed Airflow (MWAA/Cloud Composer), and BigQuery/Redshift for the analytics tables."),
  Bullet("Replace the simulated shipping-carrier API with a real carrier or aggregator API (e.g. EasyPost, Shippo) for live tracking data."),
  Bullet("Add data-drift monitoring (e.g. Evidently AI) alongside the existing Great Expectations checks to catch distribution shifts between pipeline runs."),
  pageBreak(),
);

// ============================== 10. REFERENCES ==============================
S.push(
  H1("10. References"),
  P("[1] Apache Airflow, \"Apache Airflow Documentation,\" Apache Software Foundation, 2026. [Online]. Available: https://airflow.apache.org/docs/"),
  P("[2] Great Expectations, \"Great Expectations Documentation,\" Great Expectations, Inc., 2026. [Online]. Available: https://docs.greatexpectations.io/"),
  P("[3] DVC, \"Data Version Control Documentation,\" Iterative, Inc., 2026. [Online]. Available: https://dvc.org/doc"),
  P("[4] Apache Spark, \"PySpark Documentation,\" Apache Software Foundation, 2026. [Online]. Available: https://spark.apache.org/docs/latest/api/python/"),
  P("[5] The Apache Software Foundation, \"Apache Parquet Format,\" 2026. [Online]. Available: https://parquet.apache.org/"),
  P("[6] SQLite Consortium, \"SQLite Documentation,\" 2026. [Online]. Available: https://www.sqlite.org/docs.html"),
  P("[7] Plotly Technologies Inc., \"Plotly.js Documentation,\" 2026. [Online]. Available: https://plotly.com/javascript/"),
  P("[8] Pallets Projects, \"Flask Documentation,\" 2026. [Online]. Available: https://flask.palletsprojects.com/"),
  P("[9] Kaggle, \"Supply Chain Analytics Datasets,\" Kaggle Inc. [Online]. Available: https://www.kaggle.com/datasets (dataset access unavailable in the build environment; see Section 3.1)."),
  P("[10] W. McKinney, \"Data Structures for Statistical Computing in Python,\" in Proc. 9th Python in Science Conf., 2010, pp. 56–61."),
  pageBreak(),
);

// ============================== APPENDIX ==============================
S.push(
  H1("Appendix"),
  H2("A. Code Structure"),
  Code([
    "src/",
    "  ingestion/    extract_csv.py, extract_shipping_api.py,",
    "                shipping_api_server.py, generate_seed_dataset.py",
    "  storage/      raw_storage.py",
    "  transformation/ clean.py",
    "  features/     engineer.py",
    "  quality/      gx_validation.py",
    "  processing/   spark_processing.py",
    "  ml_ready/     build_ml_dataset.py",
    "  dashboard/    build_dashboard.py",
    "  utils/        reference_data.py",
    "dags/           supply_chain_dag.py",
    "docs/           architecture_diagram.*, data_dictionary.md,",
    "                reproduction_guide.md, data_quality_report.*,",
    "                summary_statistics.json, dashboard/",
    "data/           raw/, processed/, ml_ready/  (DVC-tracked)",
    "reports/        Assessment2_Report.docx (this document)",
  ]),
  P("Full source code is included with this submission's GitHub repository (see README.md)."),

  H2("B. Airflow DAG (excerpt)"),
  Code([
    "default_args = {",
    "    'owner': 'data-engineering', 'retries': 2,",
    "    'retry_delay': timedelta(minutes=3), 'retry_exponential_backoff': True,",
    "    'max_retry_delay': timedelta(minutes=15),",
    "    'execution_timeout': timedelta(minutes=30),",
    "}",
    "",
    "with DAG(dag_id='supply_chain_logistics_pipeline', schedule='0 2 * * *',",
    "         default_args=default_args, catchup=False, max_active_runs=1,",
    "         on_failure_callback=on_failure_callback) as dag:",
    "    extract >> store >> clean >> engineer >> validate >> spark_process >> ml_ready",
  ]),

  H2("C. Great Expectations Suite (expectation list)"),
  Code([
    "ExpectColumnValuesToBeUnique(column='order_id')",
    "ExpectColumnValuesToNotBeNull(column='order_id' | 'order_date' | 'carrier')",
    "ExpectColumnValuesToBeInSet(column='carrier', value_set=[...6 carriers...])",
    "ExpectColumnValuesToBeInSet(column='shipping_mode', value_set=[...4 modes...])",
    "ExpectColumnValuesToBeBetween(quantity, unit_price, shipping_cost,",
    "    destination_latitude, destination_longitude, distance_km,",
    "    promised_delivery_days, actual_delivery_days)",
    "ExpectColumnValuesToMatchRegex(column='order_id', regex=r'^ORD-\\d+$')",
    "ExpectColumnValuesToBeBetween(carrier_performance_score, route_efficiency_score,",
    "    reorder_risk_score, min=0, max=1)",
    "ExpectColumnValuesToBeInSet(distance_category, shipment_size_category)",
    "ExpectColumnMeanToBeBetween(column='is_delayed', min=0.0, max=0.6)",
    "# 21 expectations total; 21/21 passed (see docs/data_quality_report.json)",
  ]),

  H2("D. DVC Configuration"),
  Code([
    "[core]",
    "    remote = localremote",
    "['remote \"localremote\"']",
    "    url = /home/claude/dvc_remote_storage",
    "",
    "# Tracked datasets (.dvc pointer files committed to git):",
    "data/raw/kaggle_supply_chain_orders.csv.dvc",
    "data/raw/supply_chain_raw.db.dvc",
    "data/processed/orders_clean.parquet.dvc",
    "data/processed/orders_featured.parquet.dvc",
    "data/ml_ready/train.parquet.dvc",
    "data/ml_ready/test.parquet.dvc",
  ]),

  H2("E. Environment Setup (requirements.txt)"),
  Code(fs.readFileSync(path.join(ROOT, "requirements.txt"), "utf8").split("\n").filter(l => l.trim() && !l.startsWith("#"))),

  H2("F. Data Dictionary (summary)"),
  P("Full field-by-field data dictionary (raw columns, both sources, all 10 engineered features with formulas, and the ML-ready schema) is in docs/data_dictionary.md, reproduced in full alongside this report."),
  simpleTable(
    ["Feature", "Formula"],
    [
      ["delivery_delay", "actual_delivery_days − promised_delivery_days"],
      ["shipping_cost_per_unit", "shipping_cost / quantity"],
      ["route_efficiency_score", "min-max norm. of (distance_km / actual_delivery_days) within region"],
      ["carrier_performance_score", "1 − mean(is_delayed) per carrier"],
      ["seasonal_demand_index", "monthly order count / average monthly order count"],
      ["distance_category", "binned distance_km (Local/Regional/Long-Haul/International)"],
      ["warehouse_utilization", "daily warehouse units shipped / warehouse daily capacity"],
      ["inventory_turnover", "daily category units shipped / (category avg daily demand × 30)"],
      ["reorder_risk_score", "0.65×delay_rate(carrier,category) + 0.35×norm. demand volatility(category)"],
      ["shipment_size_category", "binned weight_kg × quantity (Small/Medium/Large/Bulk)"],
    ],
    [2600, 6600],
  ),

  H2("G. Reproduction Guide (summary)"),
  P("See docs/reproduction_guide.md for the complete, tested step-by-step guide. In brief:"),
  Code([
    "python3 -m venv venv && source venv/bin/activate",
    "pip install -r requirements.txt",
    "python -m src.ingestion.generate_seed_dataset",
    "python -m src.ingestion.shipping_api_server &",
    "python -m src.storage.raw_storage",
    "python -m src.transformation.clean",
    "python -m src.features.engineer",
    "python -m src.quality.gx_validation",
    "python -m src.processing.spark_processing",
    "python -m src.ml_ready.build_ml_dataset",
    "python -m src.dashboard.build_dashboard",
    "",
    "# Orchestrated end-to-end via Airflow:",
    "export AIRFLOW_HOME=$(pwd)/.airflow",
    "airflow db migrate",
    "airflow dags test supply_chain_logistics_pipeline $(date +%F)",
  ]),

  H2("H. Sample ML-Ready Output (first rows)"),
  simpleTable(
    ["order_id", "carrier", "distance_category", "shipping_cost_per_unit", "carrier_perf_score", "is_delayed", "delivery_delay"],
    [
      ["ORD-187901", "UPS", "Long-Haul", "43.91", "0.7372", "1", "5"],
      ["ORD-123846", "Local Courier Co", "Local", "3.38", "0.6274", "0", "0"],
      ["ORD-170473", "FedEx", "Local", "0.39", "0.7412", "0", "0"],
      ["ORD-201316", "UPS", "International", "212.52", "0.7372", "1", "1"],
      ["ORD-192315", "DB Schenker", "Local", "4.13", "0.7106", "1", "4"],
    ],
    [1300, 1500, 1300, 1500, 1400, 900, 1300],
  ),
);

// ============================== ASSEMBLE ==============================
const doc = new Document({
  numbering: {
    config: [{
      reference: "bullet-list",
      levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 480, hanging: 260 } } } }],
    }],
  },
  styles: {
    default: {
      document: { run: { font: FONT, size: 22 } },
      heading1: { run: { font: FONT, size: 30, bold: true, color: "0B0B0B" }, paragraph: { spacing: { before: 320, after: 160 } } },
      heading2: { run: { font: FONT, size: 25, bold: true, color: "0B0B0B" }, paragraph: { spacing: { before: 240, after: 120 } } },
    },
  },
  sections: [{
    properties: {
      page: { size: { width: PAGE_W, height: PAGE_H }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } },
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18, color: SECONDARY })],
        })],
      }),
    },
    children: S,
  }],
});

Packer.toBuffer(doc).then(buf => {
  const out = path.join(__dirname, "Assessment2_Report.docx");
  fs.writeFileSync(out, buf);
  console.log("Wrote " + out);
});
