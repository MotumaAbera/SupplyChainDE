"""Build Great Expectations Data Docs -- the browsable HTML UI for the
validation suite.

The main validation stage (gx_validation.py) deliberately uses an *ephemeral*
context: it needs no on-disk GX project and emits the Markdown/JSON reports the
assessment asks for. Ephemeral contexts cannot persist Data Docs, though, so
this script re-runs the same suite against a *file-backed* context and renders
the Data Docs site.

Run:    python -m src.quality.build_data_docs
        python -m src.quality.build_data_docs --open   (also opens a browser)

Output: gx/uncommitted/data_docs/local_site/index.html
"""
import os
import sys
import webbrowser

import pandas as pd
import great_expectations as gx
from great_expectations.checkpoint import UpdateDataDocsAction

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.quality.gx_validation import build_suite

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")

SUITE_NAME = "supply_chain_orders_suite"
VALIDATION_NAME = "orders_featured_validation"
CHECKPOINT_NAME = "supply_chain_data_docs_checkpoint"


def _replace(collection, name, obj):
    """Add obj to a GX store, replacing any existing entry with that name.

    Makes the script idempotent -- re-running it must not fail on
    'already exists'.
    """
    try:
        collection.delete(name)
    except Exception:
        pass
    return collection.add(obj)


def main():
    df = pd.read_parquet(os.path.join(PROCESSED_DIR, "orders_featured.parquet"))

    # A file-backed context persists to great_expectations/ so Data Docs
    # have somewhere to live.
    context = gx.get_context(mode="file", project_root_dir=PROJECT_ROOT)

    data_source = context.data_sources.add_or_update_pandas("pandas_supply_chain")

    try:
        asset = data_source.get_asset("orders_featured")
    except (LookupError, KeyError, ValueError):
        asset = data_source.add_dataframe_asset(name="orders_featured")

    try:
        batch_definition = asset.get_batch_definition("full_table")
    except (LookupError, KeyError, ValueError):
        batch_definition = asset.add_batch_definition_whole_dataframe("full_table")

    suite = _replace(context.suites, SUITE_NAME, build_suite())

    validation_definition = _replace(
        context.validation_definitions, VALIDATION_NAME,
        gx.ValidationDefinition(name=VALIDATION_NAME, data=batch_definition, suite=suite),
    )

    checkpoint = _replace(
        context.checkpoints, CHECKPOINT_NAME,
        gx.Checkpoint(
            name=CHECKPOINT_NAME,
            validation_definitions=[validation_definition],
            actions=[UpdateDataDocsAction(name="update_data_docs")],
            result_format="SUMMARY",
        ),
    )

    result = checkpoint.run(batch_parameters={"dataframe": df})
    print(f"[data_docs] validation success: {result.success}")

    context.build_data_docs()
    sites = context.get_docs_sites_urls()
    for site in sites:
        print(f"[data_docs] {site['site_name']}: {site['site_url']}")
    return sites


if __name__ == "__main__":
    sites = main()
    if "--open" in sys.argv and sites:
        webbrowser.open(sites[0]["site_url"])
