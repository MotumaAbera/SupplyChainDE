"""
Builds a self-contained HTML analytics dashboard (Plotly, via CDN) summarizing
the Supply Chain Logistics pipeline output: KPIs, seasonal demand, carrier
performance, regional delay rates, and distance/shipment-size breakdowns.
"""
import json
import os
import pandas as pd

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "docs")
DASHBOARD_DIR = os.path.join(DOCS_DIR, "dashboard")
os.makedirs(DASHBOARD_DIR, exist_ok=True)

# Fixed-order categorical palette (validated, see dataviz skill references/palette.md)
CAT_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
SURFACE = "#fcfcfb"
GOOD = "#0ca30c"
CRITICAL = "#d03b3b"


def main():
    df = pd.read_parquet(os.path.join(PROCESSED_DIR, "orders_featured.parquet"))
    with open(os.path.join(DOCS_DIR, "summary_statistics.json")) as f:
        summary = json.load(f)

    # KPIs
    total_orders = len(df)
    on_time_rate = round(100 * (1 - df["is_delayed"].mean()), 1)
    avg_delay = round(df["delivery_delay"].mean(), 2)
    total_cost = df["shipping_cost"].sum()

    # Monthly volume + seasonal index
    monthly = (
        df.assign(month=df["order_date"].dt.to_period("M").astype(str))
        .groupby("month")
        .agg(orders=("order_id", "count"), avg_delay=("delivery_delay", "mean"))
        .reset_index()
        .sort_values("month")
    )

    # Carrier performance (sorted worst->best delay rate for readability)
    carrier = (
        df.groupby("carrier")
        .agg(on_time_rate=("is_delayed", lambda s: round(100 * (1 - s.mean()), 1)),
             avg_cost_per_unit=("shipping_cost_per_unit", "mean"),
             orders=("order_id", "count"))
        .reset_index()
        .sort_values("on_time_rate")
    )

    # Region delay rate
    region = (
        df.groupby("destination_region")
        .agg(delay_rate=("is_delayed", lambda s: round(100 * s.mean(), 1)),
             orders=("order_id", "count"))
        .reset_index()
        .sort_values("delay_rate", ascending=False)
    )

    # Distance category avg delay
    dist_order = ["Local", "Regional", "Long-Haul", "International"]
    distcat = (
        df.groupby("distance_category")["delivery_delay"].mean().reindex(dist_order).round(2).reset_index()
    )

    # Top product categories by order volume (top 7 + Other)
    cat_counts = df["product_category"].value_counts()
    top_cats = cat_counts.head(7)
    other_sum = cat_counts.iloc[7:].sum()
    cat_labels = list(top_cats.index) + (["Other"] if other_sum > 0 else [])
    cat_values = list(top_cats.values) + ([other_sum] if other_sum > 0 else [])

    data = {
        "kpis": {
            "total_orders": f"{total_orders:,}",
            "on_time_rate": f"{on_time_rate}%",
            "avg_delay": f"{avg_delay} days",
            "total_cost": f"${total_cost:,.0f}",
        },
        "monthly": {"x": monthly["month"].tolist(), "orders": monthly["orders"].tolist(),
                     "avg_delay": monthly["avg_delay"].round(2).tolist()},
        "carrier": {"x": carrier["carrier"].tolist(), "on_time": carrier["on_time_rate"].tolist(),
                     "cost": carrier["avg_cost_per_unit"].round(2).tolist()},
        "region": {"x": region["destination_region"].tolist(), "delay_rate": region["delay_rate"].tolist()},
        "distcat": {"x": distcat["distance_category"].tolist(), "avg_delay": distcat["delivery_delay"].tolist()},
        "category": {"x": cat_labels, "y": [int(v) for v in cat_values]},
    }

    html = _render_html(data)
    out_path = os.path.join(DASHBOARD_DIR, "supply_chain_dashboard.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[dashboard] wrote {out_path}")
    return out_path


def _plotly_js_tag() -> str:
    """Inline the Plotly.js bundle shipped with the plotly Python package so the
    dashboard is fully self-contained and works offline / without CDN access."""
    import plotly
    js_path = os.path.join(os.path.dirname(plotly.__file__), "package_data", "plotly.min.js")
    with open(js_path, "r", encoding="utf-8") as f:
        js = f.read()
    return f"<script>{js}</script>"


def _render_html(data: dict) -> str:
    data_json = json.dumps(data)
    plotly_tag = _plotly_js_tag()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Supply Chain Logistics — Analytics Dashboard</title>
{plotly_tag}
<style>
  :root {{
    --surface-1: {SURFACE};
    --page: #f9f9f7;
    --text-primary: {INK_PRIMARY};
    --text-secondary: {INK_SECONDARY};
    --text-muted: {INK_MUTED};
    --gridline: {GRIDLINE};
    --good: {GOOD};
    --critical: {CRITICAL};
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 32px; background: var(--page);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    color: var(--text-primary);
  }}
  h1 {{ font-size: 22px; margin: 0 0 4px 0; }}
  .subtitle {{ color: var(--text-secondary); font-size: 14px; margin-bottom: 24px; }}
  .kpi-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }}
  .kpi-tile {{
    background: var(--surface-1); border: 1px solid var(--gridline); border-radius: 10px;
    padding: 18px 20px;
  }}
  .kpi-label {{ font-size: 12px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: .03em; }}
  .kpi-value {{ font-size: 28px; font-weight: 600; margin-top: 6px; }}
  .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }}
  .card {{
    background: var(--surface-1); border: 1px solid var(--gridline); border-radius: 10px;
    padding: 16px;
  }}
  .card h2 {{ font-size: 14px; margin: 0 0 8px 4px; color: var(--text-primary); }}
  footer {{ color: var(--text-muted); font-size: 12px; margin-top: 24px; }}
</style>
</head>
<body>
  <h1>Supply Chain Logistics Pipeline — Analytics Dashboard</h1>
  <div class="subtitle">Assessment 2: End-to-End Data Engineering Project · Topic 9 · ML-ready delivery-delay dataset</div>

  <div class="kpi-row">
    <div class="kpi-tile"><div class="kpi-label">Total Orders</div><div class="kpi-value" id="kpi-orders"></div></div>
    <div class="kpi-tile"><div class="kpi-label">On-Time Rate</div><div class="kpi-value" id="kpi-ontime"></div></div>
    <div class="kpi-tile"><div class="kpi-label">Avg Delivery Delay</div><div class="kpi-value" id="kpi-delay"></div></div>
    <div class="kpi-tile"><div class="kpi-label">Total Shipping Cost</div><div class="kpi-value" id="kpi-cost"></div></div>
  </div>

  <div class="grid">
    <div class="card"><h2>Monthly Order Volume &amp; Avg Delay</h2><div id="chart-monthly"></div></div>
    <div class="card"><h2>Carrier On-Time Rate (%)</h2><div id="chart-carrier"></div></div>
    <div class="card"><h2>Delay Rate by Destination Region (%)</h2><div id="chart-region"></div></div>
    <div class="card"><h2>Avg Delivery Delay by Distance Category (days)</h2><div id="chart-distcat"></div></div>
    <div class="card" style="grid-column: 1 / -1;"><h2>Order Volume by Product Category</h2><div id="chart-category"></div></div>
  </div>

  <footer>Generated from the cleaned, feature-engineered dataset (data/processed/orders_featured.parquet). Colors follow a fixed, CVD-validated categorical order.</footer>

<script>
const DATA = {data_json};
const CAT_COLORS = {json.dumps(CAT_COLORS)};
const INK_SECONDARY = "{INK_SECONDARY}";
const GRIDLINE = "{GRIDLINE}";
const SURFACE = "{SURFACE}";

document.getElementById('kpi-orders').textContent = DATA.kpis.total_orders;
document.getElementById('kpi-ontime').textContent = DATA.kpis.on_time_rate;
document.getElementById('kpi-delay').textContent = DATA.kpis.avg_delay;
document.getElementById('kpi-cost').textContent = DATA.kpis.total_cost;

const baseLayout = {{
  paper_bgcolor: SURFACE, plot_bgcolor: SURFACE,
  font: {{ family: 'system-ui, -apple-system, "Segoe UI", sans-serif', color: '#0b0b0b', size: 12 }},
  margin: {{ t: 10, r: 20, l: 50, b: 40 }},
  xaxis: {{ gridcolor: GRIDLINE, zeroline: false, linecolor: GRIDLINE, automargin: true }},
  yaxis: {{ gridcolor: GRIDLINE, zeroline: false, linecolor: GRIDLINE, automargin: true }},
  hoverlabel: {{ bgcolor: '#ffffff', bordercolor: GRIDLINE, font: {{ color: '#0b0b0b' }} }},
}};
const config = {{ responsive: true, displayModeBar: false }};

// Monthly order volume (bar). Avg delay is reported via tooltip rather than a
// second y-scale, to avoid a dual-axis chart (see dataviz anti-patterns: never
// two y-scales on one plot).
Plotly.newPlot('chart-monthly', [
  {{ x: DATA.monthly.x, y: DATA.monthly.orders, type: 'bar', name: 'Orders', marker: {{ color: CAT_COLORS[0] }},
     customdata: DATA.monthly.avg_delay,
     hovertemplate: '%{{x}}<br>%{{y:,}} orders<br>avg delay: %{{customdata}} days<extra></extra>' }}
], {{ ...baseLayout, xaxis: {{ ...baseLayout.xaxis, type: 'date' }},
     yaxis: {{ ...baseLayout.yaxis, type: 'linear', title: 'Orders' }} }}, config);

Plotly.newPlot('chart-carrier', [
  {{ y: DATA.carrier.x, x: DATA.carrier.on_time, type: 'bar', orientation: 'h',
     marker: {{ color: CAT_COLORS[0] }},
     hovertemplate: '%{{y}}: %{{x}}% on-time<extra></extra>' }}
], {{ ...baseLayout, xaxis: {{ ...baseLayout.xaxis, type: 'linear', title: '% on-time', range: [0, 100] }},
     yaxis: {{ ...baseLayout.yaxis, type: 'category' }} }}, config);

Plotly.newPlot('chart-region', [
  {{ x: DATA.region.x, y: DATA.region.delay_rate, type: 'bar', marker: {{ color: CAT_COLORS[1] }},
     hovertemplate: '%{{x}}: %{{y}}% delayed<extra></extra>' }}
], {{ ...baseLayout, xaxis: {{ ...baseLayout.xaxis, type: 'category' }},
     yaxis: {{ ...baseLayout.yaxis, type: 'linear', title: '% delayed' }} }}, config);

Plotly.newPlot('chart-distcat', [
  {{ x: DATA.distcat.x, y: DATA.distcat.avg_delay, type: 'bar', marker: {{ color: CAT_COLORS[2] }},
     hovertemplate: '%{{x}}: %{{y}} days avg delay<extra></extra>' }}
], {{ ...baseLayout, xaxis: {{ ...baseLayout.xaxis, type: 'category' }},
     yaxis: {{ ...baseLayout.yaxis, type: 'linear', title: 'Avg delay (days)' }} }}, config);

Plotly.newPlot('chart-category', [
  {{ x: DATA.category.x, y: DATA.category.y, type: 'bar', marker: {{ color: CAT_COLORS[3] }},
     hovertemplate: '%{{x}}: %{{y:,}} orders<extra></extra>' }}
], {{ ...baseLayout, xaxis: {{ ...baseLayout.xaxis, type: 'category' }},
     yaxis: {{ ...baseLayout.yaxis, type: 'linear', title: 'Orders' }} }}, config);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
