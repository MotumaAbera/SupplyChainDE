# Data Dictionary — Supply Chain Logistics Pipeline

## 1. Raw source columns (`data/raw/kaggle_supply_chain_orders.csv`, Source #1)

| Column | Type | Description |
|---|---|---|
| `order_id` | string | Unique order identifier (`ORD-######`) |
| `order_date` | date | Date the order was placed |
| `customer_id` | string | Unique customer identifier |
| `customer_segment` | categorical | Consumer / Corporate / Home Office |
| `product_id` | string | Product SKU identifier |
| `product_category` | categorical | One of 10 categories (raw data has inconsistent casing, standardized in cleaning) |
| `quantity` | integer | Units ordered |
| `unit_price` | float | Price per unit (USD) |
| `discount_rate` | float | Discount applied (0.0–0.25) |
| `weight_kg` | float | Shipment weight |
| `origin_warehouse_id` | string | Fulfilling warehouse (`WH-###`) |
| `origin_region` | categorical | Region of the origin warehouse |
| `destination_city` / `destination_country` / `destination_region` | string/categorical | Delivery destination |
| `destination_latitude` / `destination_longitude` | float | Destination coordinates (raw data contains ~1% out-of-range values, removed in cleaning) |
| `distance_km` | float | Shipping distance |
| `carrier` | categorical | One of 6 carriers |
| `shipping_mode` | categorical | Standard / First / Second Class / Same Day |
| `promised_delivery_days` | integer | SLA delivery time |
| `actual_delivery_days` | integer | Actual delivery time (raw data has ~2% missing, imputed in cleaning) |
| `shipping_cost` | float | Total shipping cost for the order (raw data has ~1% missing, imputed) |
| `order_status` | categorical | COMPLETE / PENDING / PROCESSING / CANCELLED / ON_HOLD |
| `delay_reason` | categorical | Weather / Customs Hold / Mechanical Issue / Traffic / Warehouse Backlog / None |

## 2. Raw source: shipping tracking events (`shipping_events_raw`, Source #2 — simulated shipping-carrier API)

| Column | Type | Description |
|---|---|---|
| `order_id` | string | Foreign key to orders |
| `carrier` | categorical | Carrier handling the shipment |
| `event_timestamp` | datetime | Timestamp of the tracking scan |
| `event_type` | categorical | PICKED_UP / IN_TRANSIT / CUSTOMS / OUT_FOR_DELIVERY / DELAYED / DELIVERED |
| `location` | string | Scan location (destination city) |
| `delay_reason` | categorical | Populated only for DELAYED events |

## 3. Engineered features (`data/processed/orders_featured.parquet`)

| Feature | Type | Formula / Rationale |
|---|---|---|
| `delivery_delay` | integer (days) | `actual_delivery_days - promised_delivery_days`. Core delay signal; also the regression target. |
| `is_delayed` | binary | `1` if `delivery_delay > 0`. Classification target. |
| `shipping_cost_per_unit` | float | `shipping_cost / quantity`. Normalizes cost across order sizes. |
| `route_efficiency_score` | float [0,1] | `distance_km / actual_delivery_days`, min-max normalized within `destination_region` so routes are compared against similarly-distanced peers. |
| `carrier_performance_score` | float [0,1] | `1 - mean(is_delayed)` per carrier — historical on-time rate. Cross-checked against the shipping API's independently-computed carrier on-time rate in the data-quality report. |
| `seasonal_demand_index` | float | Monthly order count relative to the dataset's average monthly count — captures peak-season strain (e.g. Nov/Dec). |
| `distance_category` | categorical | Binned `distance_km`: Local (<500km), Regional (500–2000km), Long-Haul (2000–6000km), International (>6000km). |
| `warehouse_utilization` | float | Daily units shipped from a warehouse ÷ that warehouse's stated daily capacity. Proxy for operational strain. |
| `inventory_turnover` | float | Daily units shipped for a product category ÷ (category's average daily demand × 30). Proxy metric — no live inventory table exists in the source data. |
| `reorder_risk_score` | float [0,1] | `0.65 × delay_rate(carrier, category) + 0.35 × normalized demand volatility(category)`. Composite disruption-risk indicator. |
| `shipment_size_category` | categorical | Binned `weight_kg × quantity`: Small (<5), Medium (5–25), Large (25–100), Bulk (>100). |

## 4. ML-ready dataset (`data/ml_ready/{train,test}.parquet`, `supply_chain_ml_ready.csv`)

- **Grain:** one row per order.
- **Split:** deterministic 80/20 train/test split via a stable hash of `order_id` (reproducible without relying on random seed state), stratified approximately by `is_delayed` (~29% positive rate preserved in both splits).
- **Targets:** `is_delayed` (binary classification), `delivery_delay` (regression, days).
- **Features:** 22 columns — 14 numeric/engineered + 8 categorical (see `FEATURE_COLUMNS` in `src/ml_ready/build_ml_dataset.py`). Categorical columns are left un-encoded so downstream users can choose their own encoding (one-hot, target, embeddings).
- **ID columns retained for traceability:** `order_id`, `customer_id`, `order_date` (excluded from modeling).

## 5. Analytics tables (`data/processed/analytics/`, produced by PySpark)

| Table | Grain | Contents |
|---|---|---|
| `carrier_monthly_performance.parquet` | carrier × month | order count, delay violation rate, avg delay days, avg cost/unit, avg carrier score |
| `region_route_summary.parquet` | region × distance category | order count, avg route efficiency, delay rate, avg distance |
| `rolling_delay_trend.parquet` | order (ordered by date, per carrier) | 7-order trailing average of `delivery_delay`, computed via a Spark window function |
