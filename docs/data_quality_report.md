# Data Quality Report — Great Expectations

Run at: 2026-08-18T12:04:47.853772+00:00

- Dataset: `orders_featured.parquet` (292,867 rows, 37 columns)
- Expectations run: **21**
- Passed: **19**  |  Failed: **2**
- Success rate: **90.48%**
- Overall suite result: **FAIL**

## Failed expectations

- `expect_column_values_to_be_in_set` on {'column': 'distance_category', 'value_set': ['Local', 'Regional', 'Long-Haul', 'International']} — 26 unexpected values (0.008877749968415697%)
- `expect_column_values_to_be_in_set` on {'column': 'shipment_size_category', 'value_set': ['Small', 'Medium', 'Large', 'Bulk']} — 8 unexpected values (0.002731615374897138%)
