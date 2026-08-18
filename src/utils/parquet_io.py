"""Shared Parquet write helper.

Why this exists
---------------
Spark cannot read Parquet columns stored with nanosecond timestamp
precision. Reading such a file fails with:

    AnalysisException: [PARQUET_TYPE_ILLEGAL]
    Illegal Parquet type: INT64 (TIMESTAMP(NANOS,false))

pandas holds datetimes as ``datetime64[ns]`` by default, and recent PyArrow
versions default to the Parquet 2.6 format, which happily encodes that as
NANOS. Whether the pipeline produced a Spark-readable file therefore depended
on the exact pandas/PyArrow combination installed -- the same code produced a
readable file under pandas 3.x but an unreadable one under pandas 2.x, which
made the Spark stage fail only inside the Airflow container.

``write_parquet`` pins the precision to microseconds so the output is
Spark-readable regardless of which versions are installed. Microsecond
precision is far finer than this dataset's daily granularity, so nothing of
value is lost.
"""
import pandas as pd

# Parquet/Spark-safe timestamp precision.
_TIMESTAMP_UNIT = "us"


def coerce_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with all datetime columns downcast to microseconds."""
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].astype(f"datetime64[{_TIMESTAMP_UNIT}]")
    return out


def write_parquet(df: pd.DataFrame, path: str, **kwargs) -> None:
    """Write ``df`` to ``path`` as Spark-readable Parquet.

    Accepts the same keyword arguments as ``DataFrame.to_parquet``.
    """
    kwargs.setdefault("index", False)
    coerce_timestamps(df).to_parquet(
        path,
        coerce_timestamps=_TIMESTAMP_UNIT,
        allow_truncated_timestamps=True,
        **kwargs,
    )
