"""
=============================================================================
Silver Layer Transformation (PySpark)
=============================================================================
Reads raw event data from the Bronze layer in PostgreSQL, applies cleaning,
validation, deduplication, and schema enforcement using PySpark, then loads
the cleaned data into the Silver layer.

Usage:
    python scripts/silver_transform.py
    python scripts/silver_transform.py --date 2026-01-15
=============================================================================
"""

import os
from datetime import datetime
from typing import Optional

import click
from loguru import logger
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, TimestampType, DateType,
    DecimalType, IntegerType, BooleanType,
)

# =============================================================================
# Spark Session Setup
# =============================================================================


def create_spark_session() -> SparkSession:
    """Create a configured SparkSession for local processing."""
    spark = (
        SparkSession.builder
        .appName("EventAnalytics-SilverTransform")
        .master("local[*]")
        .config("spark.driver.memory", "2g")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.jars", "/opt/airflow/jars/postgresql-42.7.3.jar")
        .config("spark.driver.extraClassPath", "/opt/airflow/jars/postgresql-42.7.3.jar")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    logger.info("✅ SparkSession created successfully")
    return spark


# =============================================================================
# Database Helpers
# =============================================================================


def get_jdbc_properties() -> dict:
    """Get JDBC connection properties from environment."""
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "pipeline")
    password = os.environ.get("POSTGRES_PASSWORD", "pipeline123")
    database = os.environ.get("POSTGRES_DB", "event_analytics")

    return {
        "url": f"jdbc:postgresql://{host}:{port}/{database}",
        "user": user,
        "password": password,
        "driver": "org.postgresql.Driver",
    }


def read_bronze_data(spark: SparkSession, date_filter: Optional[str] = None) -> DataFrame:
    """Read raw events from the Bronze layer in PostgreSQL."""
    jdbc = get_jdbc_properties()

    # Build query with optional date filter
    if date_filter:
        query = f"(SELECT * FROM bronze.raw_events WHERE event_date = '{date_filter}') AS bronze"
    else:
        query = "(SELECT * FROM bronze.raw_events) AS bronze"

    df = (
        spark.read
        .format("jdbc")
        .option("url", jdbc["url"])
        .option("dbtable", query)
        .option("user", jdbc["user"])
        .option("password", jdbc["password"])
        .option("driver", jdbc["driver"])
        .load()
    )

    logger.info(f"📥 Read {df.count():,} rows from Bronze layer")
    return df


def write_silver_data(df: DataFrame) -> int:
    """Write cleaned data to the Silver layer in PostgreSQL."""
    jdbc = get_jdbc_properties()
    row_count = df.count()

    (
        df.write
        .format("jdbc")
        .option("url", jdbc["url"])
        .option("dbtable", "silver.cleaned_events")
        .option("user", jdbc["user"])
        .option("password", jdbc["password"])
        .option("driver", jdbc["driver"])
        .mode("append")
        .save()
    )

    logger.info(f"📤 Wrote {row_count:,} rows to Silver layer")
    return row_count


# =============================================================================
# Data Cleaning & Validation
# =============================================================================

# Valid event types
VALID_EVENT_TYPES = [
    "page_view", "click", "add_to_cart", "purchase", "cashback_earned", "refund"
]


def remove_duplicates(df: DataFrame) -> DataFrame:
    """Remove exact duplicate events based on event_id."""
    before = df.count()
    df_deduped = df.dropDuplicates(["event_id"])
    after = df_deduped.count()
    removed = before - after
    if removed > 0:
        logger.info(f"  🔄 Removed {removed:,} duplicate events")
    return df_deduped


def validate_not_null(df: DataFrame) -> DataFrame:
    """Flag records with null critical fields instead of dropping them."""
    critical_fields = ["event_id", "user_id", "event_type", "event_timestamp"]

    # Build quality flags
    df = df.withColumn(
        "quality_flags",
        F.concat_ws(
            ",",
            *[
                F.when(F.col(field).isNull(), F.lit(f"null_{field}"))
                for field in critical_fields
            ],
        ),
    )

    # Mark validity
    df = df.withColumn(
        "is_valid",
        F.when(
            F.col("event_id").isNotNull()
            & F.col("user_id").isNotNull()
            & F.col("event_type").isNotNull()
            & F.col("event_timestamp").isNotNull(),
            F.lit(True),
        ).otherwise(F.lit(False)),
    )

    invalid_count = df.filter(~F.col("is_valid")).count()
    if invalid_count > 0:
        logger.warning(f"  ⚠️  {invalid_count:,} records flagged as invalid (null critical fields)")

    return df


def validate_event_types(df: DataFrame) -> DataFrame:
    """Validate event_type values against the known set."""
    df = df.withColumn(
        "is_valid",
        F.when(
            F.col("event_type").isin(VALID_EVENT_TYPES) & F.col("is_valid"),
            F.lit(True),
        ).otherwise(F.lit(False)),
    )

    # Update quality flags for invalid event types
    df = df.withColumn(
        "quality_flags",
        F.when(
            ~F.col("event_type").isin(VALID_EVENT_TYPES),
            F.concat_ws(",", F.col("quality_flags"), F.lit("invalid_event_type")),
        ).otherwise(F.col("quality_flags")),
    )

    return df


def validate_timestamps(df: DataFrame) -> DataFrame:
    """Validate that timestamps are not in the future and are reasonable."""
    now = datetime.utcnow()
    min_date = datetime(2020, 1, 1)  # Reasonable minimum date

    df = df.withColumn(
        "is_valid",
        F.when(
            (F.col("event_timestamp") > F.lit(now))
            | (F.col("event_timestamp") < F.lit(min_date)),
            F.lit(False),
        ).otherwise(F.col("is_valid")),
    )

    df = df.withColumn(
        "quality_flags",
        F.when(
            F.col("event_timestamp") > F.lit(now),
            F.concat_ws(",", F.col("quality_flags"), F.lit("future_timestamp")),
        ).otherwise(F.col("quality_flags")),
    )

    return df


def validate_prices(df: DataFrame) -> DataFrame:
    """Validate that product prices are non-negative (except refunds)."""
    df = df.withColumn(
        "product_price",
        F.when(
            (F.col("product_price") < 0) & (F.col("event_type") != "refund"),
            F.abs(F.col("product_price")),  # Fix: take absolute value
        ).otherwise(F.col("product_price")),
    )
    return df


def fill_defaults(df: DataFrame) -> DataFrame:
    """Fill null values with sensible defaults."""
    defaults = {
        "product_price": 0.0,
        "quantity": 0,
        "revenue": 0.0,
        "cashback_amount": 0.0,
        "device_type": "unknown",
        "browser": "unknown",
        "country": "unknown",
        "city": "unknown",
    }

    for col_name, default_val in defaults.items():
        if col_name in df.columns:
            df = df.withColumn(
                col_name,
                F.coalesce(F.col(col_name), F.lit(default_val)),
            )

    return df


def add_derived_columns(df: DataFrame) -> DataFrame:
    """Add derived columns useful for downstream analytics."""
    df = df.withColumn("event_hour", F.hour(F.col("event_timestamp")))
    df = df.withColumn("cleaned_at", F.current_timestamp())
    return df


# =============================================================================
# Main Transformation Pipeline
# =============================================================================


def transform_bronze_to_silver(
    spark: SparkSession,
    date_filter: Optional[str] = None,
) -> int:
    """
    Execute the full Bronze → Silver transformation pipeline.

    Steps:
        1. Read raw data from Bronze
        2. Remove duplicates
        3. Validate critical fields
        4. Validate event types
        5. Validate timestamps
        6. Validate prices
        7. Fill defaults
        8. Add derived columns
        9. Write to Silver layer

    Returns:
        Number of rows written to Silver
    """
    logger.info("🥈 Starting Silver Transformation Pipeline")
    logger.info("=" * 60)

    # Step 1: Read Bronze data
    df = read_bronze_data(spark, date_filter)
    if df.count() == 0:
        logger.warning("⚠️  No data found in Bronze layer")
        return 0

    # Step 2: Remove duplicates
    logger.info("Step 2: Deduplication")
    df = remove_duplicates(df)

    # Step 3: Validate critical fields
    logger.info("Step 3: Null validation")
    df = validate_not_null(df)

    # Step 4: Validate event types
    logger.info("Step 4: Event type validation")
    df = validate_event_types(df)

    # Step 5: Validate timestamps
    logger.info("Step 5: Timestamp validation")
    df = validate_timestamps(df)

    # Step 6: Validate prices
    logger.info("Step 6: Price validation")
    df = validate_prices(df)

    # Step 7: Fill defaults
    logger.info("Step 7: Fill defaults")
    df = fill_defaults(df)

    # Step 8: Add derived columns
    logger.info("Step 8: Derived columns")
    df = add_derived_columns(df)

    # Step 9: Select final columns and write
    logger.info("Step 9: Writing to Silver layer")
    silver_columns = [
        "event_id", "user_id", "event_type", "event_timestamp", "event_date",
        "event_hour", "page_url", "product_id", "product_name", "product_category",
        "product_price", "quantity", "revenue", "cashback_amount", "device_type",
        "browser", "country", "city", "session_id", "referrer",
        "is_valid", "quality_flags", "cleaned_at",
    ]

    # Only select columns that exist in the DataFrame
    available_cols = [c for c in silver_columns if c in df.columns]
    df_final = df.select(available_cols)

    # Filter to only valid records for Silver
    df_valid = df_final.filter(F.col("is_valid") == True)  # noqa: E712
    df_invalid = df_final.filter(F.col("is_valid") == False)  # noqa: E712

    valid_count = df_valid.count()
    invalid_count = df_invalid.count()

    logger.info(f"  ✅ Valid records:   {valid_count:,}")
    logger.info(f"  ❌ Invalid records: {invalid_count:,}")

    # Write valid records to Silver
    rows_written = write_silver_data(df_valid)

    logger.success(f"🥈 Silver transformation complete: {rows_written:,} rows written")
    return rows_written


# =============================================================================
# CLI Entry Point
# =============================================================================


@click.command()
@click.option("--date", default=None, help="Process specific date (YYYY-MM-DD)")
def main(date: Optional[str]):
    """Run the Silver transformation pipeline."""
    spark = create_spark_session()
    try:
        transform_bronze_to_silver(spark, date)
    finally:
        spark.stop()
        logger.info("SparkSession stopped")


if __name__ == "__main__":
    main()
