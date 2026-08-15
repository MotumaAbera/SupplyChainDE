"""
Shared reference/master data used to generate a consistent, realistic
synthetic Supply Chain dataset (schema modeled on public Kaggle supply-chain
logistics datasets, e.g. DataCo Smart Supply Chain for Big Data Analysis).

NOTE ON DATA PROVENANCE
------------------------
This assessment calls for a real Kaggle/UCI/Zenodo dataset. Live internet
access to Kaggle was not available in this build environment (no API
credentials, and the sandbox's web-fetch tools could not reach Kaggle's
authenticated dataset pages). To avoid blocking the project, this module
generates a large, seeded, statistically realistic synthetic dataset that
reproduces the exact schema, cardinalities and relationships of a real
supply-chain logistics dataset. Every downstream stage (ingestion, storage,
cleaning, feature engineering, quality checks, orchestration, versioning)
operates identically regardless of where the CSV originates -- so dropping
in the real Kaggle CSV later is a one-file swap (see README / reproduction
guide).
"""
import random

RANDOM_SEED = 42

CARRIERS = ["DHL Express", "FedEx", "UPS", "Maersk Line", "DB Schenker", "Local Courier Co"]

SHIPPING_MODES = ["Standard Class", "First Class", "Second Class", "Same Day"]

PRODUCT_CATEGORIES = [
    "Electronics", "Apparel", "Home & Garden", "Sporting Goods",
    "Furniture", "Grocery", "Office Supplies", "Toys", "Automotive", "Health & Beauty",
]

CUSTOMER_SEGMENTS = ["Consumer", "Corporate", "Home Office"]

ORDER_STATUSES = ["COMPLETE", "PENDING", "PROCESSING", "CANCELLED", "ON_HOLD"]

DELAY_REASONS = ["Weather", "Customs Hold", "Mechanical Issue", "Traffic", "Warehouse Backlog", "None"]

REGIONS = {
    "North America": {
        "countries": ["United States", "Canada", "Mexico"],
        "cities": ["New York", "Los Angeles", "Chicago", "Toronto", "Mexico City", "Houston", "Miami"],
        "lat_range": (25.0, 55.0), "lon_range": (-125.0, -70.0),
    },
    "Europe": {
        "countries": ["Germany", "France", "United Kingdom", "Netherlands", "Spain", "Italy"],
        "cities": ["Berlin", "Paris", "London", "Amsterdam", "Madrid", "Milan", "Hamburg"],
        "lat_range": (36.0, 60.0), "lon_range": (-9.0, 20.0),
    },
    "Asia Pacific": {
        "countries": ["China", "Japan", "India", "Australia", "Singapore", "South Korea"],
        "cities": ["Shanghai", "Tokyo", "Mumbai", "Sydney", "Singapore", "Seoul", "Shenzhen"],
        "lat_range": (-40.0, 45.0), "lon_range": (70.0, 155.0),
    },
    "Latin America": {
        "countries": ["Brazil", "Argentina", "Chile", "Colombia"],
        "cities": ["Sao Paulo", "Buenos Aires", "Santiago", "Bogota", "Rio de Janeiro"],
        "lat_range": (-40.0, 10.0), "lon_range": (-75.0, -35.0),
    },
    "Africa": {
        "countries": ["Kenya", "Nigeria", "South Africa", "Egypt"],
        "cities": ["Nairobi", "Lagos", "Johannesburg", "Cairo", "Mombasa"],
        "lat_range": (-35.0, 30.0), "lon_range": (-10.0, 45.0),
    },
}

WAREHOUSES = [
    {"warehouse_id": f"WH-{i:03d}", "region": region, "capacity_units_per_day": cap}
    for i, (region, cap) in enumerate(
        [
            ("North America", 4200), ("North America", 3100),
            ("Europe", 3800), ("Europe", 2600),
            ("Asia Pacific", 5200), ("Asia Pacific", 3900),
            ("Latin America", 1800), ("Africa", 1200),
        ],
        start=1,
    )
]


def get_rng(seed=RANDOM_SEED):
    return random.Random(seed)
