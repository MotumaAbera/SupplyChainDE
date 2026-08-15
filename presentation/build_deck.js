const pptxgen = require("pptxgenjs");
const path = require("path");
const fs = require("fs");

const DOCS = path.join(__dirname, "..", "docs");

// ---- Ocean Gradient palette (logistics / global shipping theme) ----
const NAVY = "21295C";     // deep midnight - dark bg / accent
const DEEPBLUE = "065A82"; // primary
const TEAL = "1C7293";     // secondary
const ICE = "CFE8F3";      // light tint for cards on dark bg
const WHITE = "FFFFFF";
const INK = "16202A";
const MUTED = "5B6B76";
const AMBER = "E8A33D";    // sharp accent (used sparingly, e.g. warnings/highlights)
const GOOD = "1E8E5A";

let pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5 in

const FONT = "Calibri";
const HEAD = "Cambria";

function darkSlide() {
  const s = pres.addSlide();
  s.background = { color: NAVY };
  return s;
}
function lightSlide() {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  return s;
}
function kicker(s, text, opts = {}) {
  s.addText(text.toUpperCase(), {
    x: 0.6, y: opts.y ?? 0.45, w: 8, h: 0.35, fontFace: FONT, fontSize: 13, bold: true,
    color: opts.color ?? TEAL, charSpacing: 2,
  });
}
function title(s, text, opts = {}) {
  s.addText(text, {
    x: 0.6, y: opts.y ?? 0.78, w: opts.w ?? 12.1, h: opts.h ?? 0.9, fontFace: HEAD, fontSize: opts.size ?? 32,
    bold: true, color: opts.color ?? INK,
  });
}
function pageNum(s, n) {
  s.addText(String(n), { x: 12.6, y: 7.05, w: 0.5, h: 0.3, fontFace: FONT, fontSize: 10, color: MUTED, align: "right" });
}
function footerTag(s, dark = false) {
  s.addText("Assessment 2 · Supply Chain Logistics Pipeline", {
    x: 0.6, y: 7.05, w: 6, h: 0.3, fontFace: FONT, fontSize: 10, color: dark ? "8FA6B5" : MUTED,
  });
}
function circleLabel(s, x, y, d, label, opts = {}) {
  s.addShape("ellipse", { x, y, w: d, h: d, fill: { color: opts.fill ?? TEAL }, line: { type: "none" } });
  s.addText(label, {
    x, y, w: d, h: d, align: "center", valign: "middle", fontFace: HEAD, bold: true,
    fontSize: opts.fontSize ?? 20, color: opts.color ?? WHITE,
  });
}

// ============================== 1. TITLE ==============================
{
  const s = darkSlide();
  s.addShape("rect", { x: 0, y: 0, w: 13.33, h: 7.5, fill: { color: NAVY }, line: { type: "none" } });
  s.addShape("ellipse", { x: 9.6, y: -2.2, w: 7, h: 7, fill: { color: DEEPBLUE, transparency: 35 }, line: { type: "none" } });
  s.addShape("ellipse", { x: 11.6, y: 3.8, w: 4.2, h: 4.2, fill: { color: TEAL, transparency: 45 }, line: { type: "none" } });
  s.addText("ASSESSMENT 2  ·  TOPIC 9", { x: 0.8, y: 1.5, w: 9, h: 0.4, fontFace: FONT, fontSize: 14, bold: true, color: AMBER, charSpacing: 2 });
  s.addText("Supply Chain Logistics Pipeline", { x: 0.8, y: 2.0, w: 10.5, h: 1.3, fontFace: HEAD, fontSize: 44, bold: true, color: WHITE });
  s.addText("An End-to-End Data Engineering Pipeline for Delivery-Delay Prediction", {
    x: 0.8, y: 3.15, w: 10.5, h: 0.7, fontFace: FONT, fontSize: 19, italic: true, color: ICE,
  });
  s.addText("Motty  ·  DxValley", { x: 0.8, y: 6.15, w: 6, h: 0.4, fontFace: FONT, fontSize: 15, color: WHITE, bold: true });
  s.addText("August 2026", { x: 0.8, y: 6.55, w: 6, h: 0.35, fontFace: FONT, fontSize: 13, color: "8FA6B5" });
}

// ============================== 2. AGENDA ==============================
{
  const s = lightSlide();
  kicker(s, "Agenda");
  title(s, "From raw logistics data to an ML-ready dataset");
  const items = [
    ["01", "Problem & Objectives"], ["02", "Architecture"], ["03", "Ingestion & Storage"],
    ["04", "Cleaning & Feature Engineering"], ["05", "Data Quality & Orchestration"],
    ["06", "Versioning & Results"], ["07", "Findings, Challenges & Next Steps"],
  ];
  const colW = 3.9, rowH = 1.55, startX = 0.6, startY = 1.9, gapX = 0.25, gapY = 0.25;
  items.forEach((it, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = startX + col * (colW + gapX), y = startY + row * (rowH + gapY);
    s.addShape("roundRect", { x, y, w: colW, h: rowH, rectRadius: 0.08, fill: { color: "F2F7FA" }, line: { type: "none" },
      shadow: { type: "outer", color: "9AAAB5", opacity: 0.25, blur: 6, offset: 2, angle: 90 } });
    s.addText(it[0], { x: x + 0.25, y: y + 0.18, w: 1.2, h: 0.6, fontFace: HEAD, fontSize: 26, bold: true, color: TEAL });
    s.addText(it[1], { x: x + 0.25, y: y + 0.78, w: colW - 0.5, h: 0.65, fontFace: FONT, fontSize: 14, bold: true, color: INK, valign: "top" });
  });
  footerTag(s); pageNum(s, 2);
}

// ============================== 3. PROBLEM & OBJECTIVES ==============================
{
  const s = lightSlide();
  kicker(s, "Problem & Objectives");
  title(s, "Late deliveries are a data problem before they're a logistics problem");
  s.addText(
    "Raw order and carrier-tracking data is inconsistent, incomplete, and carries no engineered signal for delay risk. This project builds the full pipeline that turns it into a trustworthy, ML-ready dataset for predicting delivery delay.",
    { x: 0.6, y: 1.75, w: 6.1, h: 1.7, fontFace: FONT, fontSize: 14.5, color: INK, valign: "top", lineSpacingMultiple: 1.25 }
  );
  const objs = [
    "2+ ingestion sources (file + REST API)", "2+ storage formats (SQLite + Parquet)",
    "10+ engineered features", "Great Expectations quality gate",
    "PySpark aggregations & window functions", "Airflow orchestration, DVC versioning",
  ];
  objs.forEach((t, i) => {
    const y = 3.65 + i * 0.52;
    s.addShape("ellipse", { x: 0.6, y: y + 0.03, w: 0.18, h: 0.18, fill: { color: GOOD }, line: { type: "none" } });
    s.addText(t, { x: 0.95, y: y - 0.1, w: 5.8, h: 0.4, fontFace: FONT, fontSize: 13, color: INK });
  });
  // right column stat callout
  s.addShape("roundRect", { x: 7.1, y: 1.75, w: 5.6, h: 4.85, rectRadius: 0.1, fill: { color: NAVY }, line: { type: "none" } });
  s.addText("103,548", { x: 7.4, y: 2.15, w: 5, h: 1.0, fontFace: HEAD, fontSize: 46, bold: true, color: WHITE });
  s.addText("clean, feature-engineered orders (98.1% retention from 105,525 raw rows)", {
    x: 7.4, y: 3.05, w: 5, h: 0.7, fontFace: FONT, fontSize: 13, color: ICE,
  });
  s.addText("21 / 21", { x: 7.4, y: 3.9, w: 5, h: 0.8, fontFace: HEAD, fontSize: 38, bold: true, color: AMBER });
  s.addText("Great Expectations checks passing (100%)", { x: 7.4, y: 4.65, w: 5, h: 0.5, fontFace: FONT, fontSize: 13, color: ICE });
  s.addText("7-task DAG", { x: 7.4, y: 5.35, w: 5, h: 0.6, fontFace: HEAD, fontSize: 28, bold: true, color: WHITE });
  s.addText("executed end-to-end via Airflow — verified, not just authored", { x: 7.4, y: 6.0, w: 5, h: 0.5, fontFace: FONT, fontSize: 13, color: ICE });
  footerTag(s); pageNum(s, 3);
}

// ============================== 4. ARCHITECTURE ==============================
{
  const s = lightSlide();
  kicker(s, "Architecture");
  title(s, "Two sources in, one ML-ready dataset out");
  s.addImage({ path: path.join(DOCS, "diagrams", "architecture_diagram.png"), x: 3.05, y: 1.55, w: 7.2, h: 7.2 * (1580 / 1568) > 5.6 ? 5.6 : 7.2 * (1580/1568), sizing: { type: "contain", w: 7.2, h: 5.55 } });
  footerTag(s); pageNum(s, 4);
}

// ============================== 5. INGESTION & STORAGE ==============================
{
  const s = lightSlide();
  kicker(s, "Ingestion & Storage");
  title(s, "Two independent sources, two storage formats");
  const cardW = 5.85, cardH = 2.35, y1 = 1.85, y2 = 4.4;
  function card(x, y, h2, body) {
    s.addShape("roundRect", { x, y, w: cardW, h: cardH, rectRadius: 0.08, fill: { color: "F2F7FA" }, line: { type: "none" } });
    s.addText(h2, { x: x + 0.3, y: y + 0.2, w: cardW - 0.6, h: 0.45, fontFace: HEAD, fontSize: 16, bold: true, color: DEEPBLUE });
    s.addText(body, { x: x + 0.3, y: y + 0.68, w: cardW - 0.6, h: cardH - 0.9, fontFace: FONT, fontSize: 12.5, color: INK, valign: "top", lineSpacingMultiple: 1.2 });
  }
  card(0.6, y1, "Source 1 — Order CSV export", "kaggle_supply_chain_orders.csv\n105,525 rows · 25 columns\ncarrier, distance, cost, delivery windows, destination coordinates");
  card(6.85, y1, "Source 2 — Shipping-Carrier API", "Simulated Flask REST API\n188,299 tracking events, 6 carriers\nPaginated, rate-limited, retried on transient 503s");
  card(0.6, y2, "Storage format 1 — SQLite", "supply_chain_raw.db\nAd-hoc SQL queryability over the raw extract");
  card(6.85, y2, "Storage format 2 — Parquet", "data/raw/parquet/\nColumnar storage feeding Spark & Pandas downstream");
  footerTag(s); pageNum(s, 5);
}

// ============================== 6. CLEANING ==============================
{
  const s = lightSlide();
  kicker(s, "Cleaning & Transformation");
  title(s, "98.1% of records survive a real quality pass");
  const stats = [
    ["522", "duplicate rows removed"], ["317", "malformed dates dropped"],
    ["1,138", "invalid coordinates removed"], ["2,120", "missing delivery-days imputed"],
    ["1,053", "missing shipping-cost imputed"], ["103,548", "clean rows retained"],
  ];
  const colW = 3.9, rowH = 2.15, startX = 0.6, startY = 1.9, gapX = 0.25, gapY = 0.25;
  stats.forEach((it, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = startX + col * (colW + gapX), y = startY + row * (rowH + gapY);
    s.addShape("roundRect", { x, y, w: colW, h: rowH, rectRadius: 0.08,
      fill: { color: i === 5 ? DEEPBLUE : "F2F7FA" }, line: { type: "none" } });
    s.addText(it[0], { x: x + 0.25, y: y + 0.25, w: colW - 0.5, h: 0.9, fontFace: HEAD, fontSize: 30, bold: true, color: i === 5 ? WHITE : DEEPBLUE });
    s.addText(it[1], { x: x + 0.25, y: y + 1.15, w: colW - 0.5, h: 0.85, fontFace: FONT, fontSize: 13, color: i === 5 ? ICE : MUTED, valign: "top" });
  });
  footerTag(s); pageNum(s, 6);
}

// ============================== 7. FEATURE ENGINEERING ==============================
{
  const s = lightSlide();
  kicker(s, "Feature Engineering");
  title(s, "10 domain-relevant features, each with a rationale", { size: 28 });
  const feats = [
    "delivery_delay", "shipping_cost_per_unit", "route_efficiency_score", "carrier_performance_score",
    "seasonal_demand_index", "distance_category", "warehouse_utilization", "inventory_turnover",
    "reorder_risk_score", "shipment_size_category",
  ];
  const colW = 3.9, rowH = 0.85, startX = 0.6, startY = 1.75, gapX = 0.25, gapY = 0.18;
  feats.forEach((t, i) => {
    const col = Math.floor(i / 5), row = i % 5;
    const x = startX + col * (colW * 2.05 + gapX), y = startY + row * (rowH + gapY);
    // two wider columns of 5 each instead of 3x4 grid, for readability
  });
  // redo as 2 columns x 5 rows, full width cards
  const cW = 6.0, cH = 0.85;
  feats.forEach((t, i) => {
    const col = i < 5 ? 0 : 1, row = i % 5;
    const x = 0.6 + col * (cW + 0.35), y = 1.75 + row * (cH + 0.15);
    s.addShape("roundRect", { x, y, w: cW, h: cH, rectRadius: 0.06, fill: { color: "F2F7FA" }, line: { type: "none" } });
    circleLabel(s, x + 0.18, y + 0.18, 0.5, String(i + 1), { fill: TEAL, fontSize: 16 });
    s.addText(t, { x: x + 0.9, y: y, w: cW - 1.1, h: cH, align: "left", valign: "middle", fontFace: FONT, fontSize: 14.5, bold: true, color: INK });
  });
  footerTag(s); pageNum(s, 7);
}

// ============================== 8. DATA QUALITY ==============================
{
  const s = darkSlide();
  kicker(s, "Data Quality", { color: AMBER });
  title(s, "Great Expectations: 21/21 checks pass", { color: WHITE });
  s.addText(
    "Uniqueness & null checks, categorical set membership, numeric range checks (price, cost, coordinates, distance, delivery time), regex format validation, and range checks on every [0,1]-bounded engineered score.",
    { x: 0.6, y: 1.85, w: 6.6, h: 2.0, fontFace: FONT, fontSize: 14, color: ICE, valign: "top", lineSpacingMultiple: 1.3 }
  );
  s.addText("Cross-checked independently: carrier on-time ranking from the cleaned orders data agrees with the shipping API's own carrier-performance endpoint.", {
    x: 0.6, y: 4.1, w: 6.6, h: 1.3, fontFace: FONT, fontSize: 13, italic: true, color: "9FC3D6", valign: "top",
  });
  // donut-ish big stat
  s.addShape("ellipse", { x: 8.3, y: 1.85, w: 4.0, h: 4.0, fill: { color: DEEPBLUE }, line: { color: TEAL, width: 3 } });
  s.addText("100%", { x: 8.3, y: 3.15, w: 4.0, h: 1.0, align: "center", fontFace: HEAD, fontSize: 48, bold: true, color: WHITE });
  s.addText("suite pass rate", { x: 8.3, y: 4.15, w: 4.0, h: 0.5, align: "center", fontFace: FONT, fontSize: 14, color: ICE });
  footerTag(s, true); pageNum(s, 8);
}

// ============================== 9. ORCHESTRATION ==============================
{
  const s = lightSlide();
  kicker(s, "Orchestration");
  title(s, "One Airflow DAG, seven tasks, verified end-to-end");
  s.addShape("roundRect", { x: 0.6, y: 1.85, w: 12.1, h: 1.1, rectRadius: 0.08, fill: { color: "F2F7FA" }, line: { type: "none" } });
  s.addText("extract  →  store  →  clean  →  engineer  →  validate  →  spark  →  ml_ready", {
    x: 0.6, y: 1.85, w: 12.1, h: 1.1, align: "center", valign: "middle", fontFace: "Consolas", fontSize: 16, bold: true, color: DEEPBLUE,
  });
  const items = [
    ["Schedule", "Daily @ 02:00 UTC, catchup off, max 1 concurrent run"],
    ["Retries", "2x with exponential backoff (3–15 min)"],
    ["Quality gate", "Fails the run if <90% of GX checks pass"],
    ["Verified", "`airflow dags test` → DagRun Finished, state=success"],
  ];
  items.forEach((it, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.6 + col * 6.15, y = 3.35 + row * 1.7;
    s.addShape("roundRect", { x, y, w: 5.85, h: 1.45, rectRadius: 0.08, fill: { color: "F2F7FA" }, line: { type: "none" } });
    s.addText(it[0], { x: x + 0.3, y: y + 0.15, w: 5.3, h: 0.4, fontFace: FONT, fontSize: 14, bold: true, color: TEAL });
    s.addText(it[1], { x: x + 0.3, y: y + 0.55, w: 5.3, h: 0.8, fontFace: FONT, fontSize: 12.5, color: INK, valign: "top" });
  });
  footerTag(s); pageNum(s, 9);
}

// ============================== 10. VERSIONING ==============================
{
  const s = lightSlide();
  kicker(s, "Versioning & Reproducibility");
  title(s, "Every dataset is versioned, every step is reproducible");
  const left = [
    "DVC-tracked: raw CSV, SQLite DB, cleaned & feature-engineered Parquet, ML-ready train/test splits",
    "Local remote configured; `dvc push` / `dvc checkout` restore any historical version",
    "Two committed versions (v1, v2) across the git history",
  ];
  left.forEach((t, i) => {
    const y = 2.0 + i * 1.05;
    s.addShape("ellipse", { x: 0.6, y: y + 0.05, w: 0.18, h: 0.18, fill: { color: GOOD }, line: { type: "none" } });
    s.addText(t, { x: 0.95, y: y - 0.15, w: 5.9, h: 0.95, fontFace: FONT, fontSize: 13.5, color: INK, valign: "top" });
  });
  s.addShape("roundRect", { x: 7.1, y: 1.85, w: 5.6, h: 4.8, rectRadius: 0.1, fill: { color: "F2F7FA" }, line: { type: "none" } });
  s.addText("Full reproduction guide", { x: 7.4, y: 2.1, w: 5, h: 0.4, fontFace: FONT, fontSize: 14, bold: true, color: DEEPBLUE });
  s.addText(
    "python -m venv venv\npip install -r requirements.txt\npython -m src.ingestion.generate_seed_dataset\npython -m src.ingestion.shipping_api_server &\n... (full 7-stage pipeline)\nairflow dags test supply_chain_logistics_pipeline",
    { x: 7.4, y: 2.6, w: 5.0, h: 3.8, fontFace: "Consolas", fontSize: 11, color: INK, valign: "top", lineSpacingMultiple: 1.3 }
  );
  footerTag(s); pageNum(s, 10);
}

// ============================== 11. ML-READY DATASET (chart) ==============================
{
  const s = lightSlide();
  kicker(s, "Results");
  title(s, "An ML-ready dataset for delivery-delay prediction");
  s.addText("103,548 rows  ·  82,840 train / 20,708 test  ·  22 features  ·  2 targets", {
    x: 0.6, y: 1.7, w: 8, h: 0.4, fontFace: FONT, fontSize: 14, bold: true, color: MUTED,
  });
  s.addChart("pie", [{ name: "is_delayed", labels: ["On-time", "Delayed"], values: [71.1, 28.9] }], {
    x: 0.6, y: 2.2, w: 5.6, h: 4.5,
    showTitle: true, title: "Delay class balance (%)", titleFontSize: 14, titleColor: INK,
    showLegend: true, legendPos: "b", legendFontSize: 12,
    chartColors: [TEAL, AMBER], showValue: true, dataLabelColor: WHITE, dataLabelFontSize: 12,
    showPercent: false, dataLabelFormatCode: '0.0"%"',
  });
  s.addChart("bar", [{ name: "On-time %", labels: ["DHL Express", "FedEx", "UPS", "DB Schenker", "Maersk Line", "Local Courier Co"], values: [74.8, 74.1, 73.7, 71.1, 66.6, 62.7] }], {
    x: 6.6, y: 2.2, w: 6.1, h: 4.5, barDir: "bar",
    showTitle: true, title: "Carrier on-time rate (%)", titleFontSize: 14, titleColor: INK,
    showLegend: false, chartColors: [DEEPBLUE], showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 11,
    dataLabelFormatCode: "0.0",
    catAxisLabelFontSize: 11, valAxisLabelFontSize: 10, valAxisMaxVal: 100,
    catGridLine: { style: "none" }, valGridLine: { color: "E1E0D9", size: 0.5 },
  });
  footerTag(s); pageNum(s, 11);
}

// ============================== 12. KEY FINDINGS (chart) ==============================
{
  const s = lightSlide();
  kicker(s, "Key Findings");
  title(s, "Where delay risk actually concentrates", { size: 28 });
  s.addChart("bar", [{ name: "Delay rate %", labels: ["North America", "Europe", "Asia Pacific", "Latin America", "Africa"], values: [30.4, 29.9, 28.5, 27.9, 27.8] }], {
    x: 0.6, y: 1.8, w: 6.0, h: 4.5,
    showTitle: true, title: "Delay rate by region (%)", titleFontSize: 13, titleColor: INK,
    showLegend: false, chartColors: [TEAL], showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 10,
    dataLabelFormatCode: "0.0", valAxisMinVal: 26.5,
    catAxisLabelFontSize: 10, valAxisLabelFontSize: 10,
    catGridLine: { style: "none" }, valGridLine: { color: "E1E0D9", size: 0.5 },
  });
  s.addChart("bar", [{ name: "Avg delay (days)", labels: ["Local", "Regional", "Long-Haul", "International"], values: [0.417, 0.397, 0.392, 0.366] }], {
    x: 6.9, y: 1.8, w: 5.8, h: 4.5,
    showTitle: true, title: "Avg delay by distance category (days)", titleFontSize: 13, titleColor: INK,
    showLegend: false, chartColors: [AMBER], showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 10,
    dataLabelFormatCode: "0.000",
    catAxisLabelFontSize: 10, valAxisLabelFontSize: 10,
    catGridLine: { style: "none" }, valGridLine: { color: "E1E0D9", size: 0.5 },
  });
  s.addText("Counter-intuitively, Local shipments have the highest average delay — international shipments carry more schedule buffer that absorbs the same variability.", {
    x: 0.6, y: 6.45, w: 12.1, h: 0.6, fontFace: FONT, fontSize: 12, italic: true, color: MUTED,
  });
  footerTag(s); pageNum(s, 12);
}

// ============================== 13. DASHBOARD ==============================
{
  const s = lightSlide();
  kicker(s, "Analytics Dashboard");
  title(s, "A self-contained, interactive dashboard");
  s.addImage({ path: path.join(DOCS, "diagrams", "dashboard_screenshot.png"), x: 3.4, y: 1.55, sizing: { type: "contain", w: 6.5, h: 5.6 } });
  footerTag(s); pageNum(s, 13);
}

// ============================== 14. CHALLENGES ==============================
{
  const s = lightSlide();
  kicker(s, "Challenges");
  title(s, "What got in the way — and how it was resolved");
  const rows = [
    ["No live Kaggle API access in the build sandbox", "Generated a schema-faithful, seeded synthetic dataset; documented a one-file swap-in for real Kaggle data"],
    ["Flask/Airflow dependency conflict", "Pinned Flask to the version in Airflow's official constraints file"],
    ["Great Expectations 1.x Fluent API differs from older docs", "Built and tested against the actual installed 1.20 API"],
    ["PySpark 4.2 / pandas 3.x compatibility warning", "Verified correctness in testing; flagged for monitoring"],
  ];
  rows.forEach((r, i) => {
    const y = 1.85 + i * 1.2;
    s.addShape("roundRect", { x: 0.6, y, w: 12.1, h: 1.02, rectRadius: 0.06, fill: { color: "F2F7FA" }, line: { type: "none" } });
    s.addText(r[0], { x: 0.9, y: y, w: 5.4, h: 1.02, valign: "middle", fontFace: FONT, fontSize: 12.5, bold: true, color: INK });
    s.addShape("line", { x: 6.55, y: y + 0.12, w: 0, h: 0.78, line: { color: "D3DEE5", width: 1 } });
    s.addText(r[1], { x: 6.85, y: y, w: 5.7, h: 1.02, valign: "middle", fontFace: FONT, fontSize: 12, color: MUTED });
  });
  footerTag(s); pageNum(s, 14);
}

// ============================== 15. FUTURE WORK ==============================
{
  const s = darkSlide();
  kicker(s, "Future Work", { color: AMBER });
  title(s, "Where this goes next", { color: WHITE });
  const items = [
    "Swap in a real Kaggle/UCI/Zenodo dataset once credentials are available",
    "Train & evaluate delivery-delay models on the ML-ready dataset produced here",
    "Deploy to AWS/GCP/Azure (cloud bonus): managed Airflow, cloud DVC remote, warehouse-native analytics",
    "Replace the simulated carrier API with a real carrier/aggregator API",
    "Add data-drift monitoring alongside the existing Great Expectations checks",
  ];
  items.forEach((t, i) => {
    const y = 1.95 + i * 0.92;
    circleLabel(s, 0.6, y, 0.55, String(i + 1), { fill: DEEPBLUE, fontSize: 16 });
    s.addText(t, { x: 1.35, y: y - 0.05, w: 11.2, h: 0.75, valign: "middle", fontFace: FONT, fontSize: 14, color: ICE });
  });
  footerTag(s, true); pageNum(s, 15);
}

// ============================== 16. CONCLUSION ==============================
{
  const s = darkSlide();
  s.addShape("ellipse", { x: -2, y: 4.5, w: 7, h: 7, fill: { color: DEEPBLUE, transparency: 40 }, line: { type: "none" } });
  kicker(s, "Conclusion", { color: AMBER });
  title(s, "A complete, verified data engineering pipeline", { color: WHITE, size: 30 });
  const items = [
    "Every Core Requirement in the assessment brief implemented and tested, not scaffolded",
    "103,548-row ML-ready dataset, 100% data-quality pass rate, a working Airflow DAG, and DVC-versioned data",
    "Full documentation: architecture diagram, data dictionary, reproduction guide, and this report",
  ];
  items.forEach((t, i) => {
    const y = 2.3 + i * 0.95;
    s.addShape("ellipse", { x: 0.6, y: y + 0.05, w: 0.16, h: 0.16, fill: { color: AMBER }, line: { type: "none" } });
    s.addText(t, { x: 0.95, y: y - 0.15, w: 11.5, h: 0.85, fontFace: FONT, fontSize: 15, color: ICE, valign: "top" });
  });
  s.addText("Thank you — Questions?", { x: 0.6, y: 5.9, w: 8, h: 0.7, fontFace: HEAD, fontSize: 26, bold: true, color: WHITE });
  footerTag(s, true); pageNum(s, 16);
}

const outPath = path.join(__dirname, "Assessment2_Presentation.pptx");
pres.writeFile({ fileName: outPath }).then(() => console.log("Wrote " + outPath));
