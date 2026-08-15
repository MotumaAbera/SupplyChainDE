"""
Large-scale processing stage using PySpark (local mode).

Reads the feature-engineered Parquet dataset and produces analytics-ready
aggregate tables using Spark SQL window functions and groupBy aggregations:

  - carrier_monthly_performance : on-time rate, avg delay, avg cost per carrier/month
  - region_route_summary        : avg route efficiency, delay rate per destination region
  - rolling_delay_trend         : 7-order rolling average of delivery_delay per carrier
                                   (Spark window function over order_date)

Outputs are written to data/processed/analytics/ as Parquet.
"""
import os
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")
ANALYTICS_DIR = os.path.join(PROCESSED_DIR, "analytics")
os.makedirs(ANALYTICS_DIR, exist_ok=True)


def get_spark():
    return (
        SparkSession.builder
        .appName("SupplyChainLogisticsPipeline")
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.driver.memory", "2g")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )


def run():
    spark = get_spark()
    spark.sparkContext.setLogLevel("ERROR")

    df = spark.read.parquet(os.path.join(PROCESSED_DIR, "orders_featured.parquet"))
    df = df.withColumn("order_month", F.date_format("order_date", "yyyy-MM"))
    df.cache()
    n_rows = df.count()
    print(f"[spark] loaded {n_rows:,} rows into Spark DataFrame, {len(df.columns)} columns")

    # 1. Carrier x month performance aggregation
    carrier_monthly = (
        df.groupBy("carrier", "order_month")
        .agg(
            F.count("order_id").alias("order_count"),
            F.avg("is_delayed").alias("on_time_violation_rate"),
            F.avg("delivery_delay").alias("avg_delivery_delay_days"),
            F.avg("shipping_cost_per_unit").alias("avg_shipping_cost_per_unit"),
            F.avg("carrier_performance_score").alias("avg_carrier_performance_score"),
        )
        .orderBy("carrier", "order_month")
    )
    carrier_monthly.write.mode("overwrite").parquet(os.path.join(ANALYTICS_DIR, "carrier_monthly_performance.parquet"))
    print(f"[spark] wrote carrier_monthly_performance.parquet ({carrier_monthly.count():,} rows)")

    # 2. Region / route summary
    region_summary = (
        df.groupBy("destination_region", "distance_category")
        .agg(
            F.count("order_id").alias("order_count"),
            F.avg("route_efficiency_score").alias("avg_route_efficiency_score"),
            F.avg("is_delayed").alias("delay_rate"),
            F.avg("distance_km").alias("avg_distance_km"),
        )
        .orderBy("destination_region", "distance_category")
    )
    region_summary.write.mode("overwrite").parquet(os.path.join(ANALYTICS_DIR, "region_route_summary.parquet"))
    print(f"[spark] wrote region_route_summary.parquet ({region_summary.count():,} rows)")

    # 3. Rolling delay trend via window function (7-order trailing average per carrier)
    w = (
        Window.partitionBy("carrier")
        .orderBy("order_date")
        .rowsBetween(-6, 0)
    )
    rolling = (
        df.select("order_id", "carrier", "order_date", "delivery_delay")
        .withColumn("rolling_avg_delay_7orders", F.avg("delivery_delay").over(w))
    )
    rolling.write.mode("overwrite").parquet(os.path.join(ANALYTICS_DIR, "rolling_delay_trend.parquet"))
    print(f"[spark] wrote rolling_delay_trend.parquet ({rolling.count():,} rows, window function applied)")

    spark.stop()


if __name__ == "__main__":
    run()
