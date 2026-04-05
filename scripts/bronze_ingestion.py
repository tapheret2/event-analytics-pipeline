"""
=============================================================================
Bronze Layer Ingestion
=============================================================================
Loads raw CSV event data from the filesystem into the PostgreSQL Bronze layer.
Handles partitioned data (event_date=YYYY-MM-DD directories), adds metadata
columns, and supports incremental loading.

Usage:
    python scripts/bronze_ingestion.py --data-dir data/bronze
    python scripts/bronze_ingestion.py --date 2026-01-15
=============================================================================
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
import pandas as pd
from loguru import logger
from sqlalchemy import create_engine, text

# =============================================================================
# Database Configuration
# =============================================================================


def get_db_engine():
    """Create a SQLAlchemy engine from environment variables."""
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "pipeline")
    password = os.environ.get("POSTGRES_PASSWORD", "pipeline123")
    database = os.environ.get("POSTGRES_DB", "event_analytics")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    return create_engine(url, pool_pre_ping=True)


# =============================================================================
# Ingestion Logic
# =============================================================================


def ingest_partition(
    engine,
    csv_path: Path,
    batch_id: str,
) -> int:
    """
    Ingest a single CSV partition into the bronze.raw_events table.

    Args:
        engine: SQLAlchemy engine
        csv_path: Path to the CSV file
        batch_id: Unique identifier for this ingestion batch

    Returns:
        Number of rows ingested
    """
    logger.info(f"  📥 Reading: {csv_path}")

    try:
        df = pd.read_csv(csv_path, dtype=str)  # Read all as strings initially
    except Exception as e:
        logger.error(f"  ❌ Failed to read {csv_path}: {e}")
        return 0

    if df.empty:
        logger.warning(f"  ⚠️  Empty file: {csv_path}")
        return 0

    # Add ingestion metadata
    df["ingested_at"] = datetime.utcnow().isoformat()
    df["source_file"] = csv_path.name
    df["batch_id"] = batch_id

    # Type casting for numeric columns
    numeric_cols = ["product_price", "quantity", "revenue", "cashback_amount"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Convert timestamps
    if "event_timestamp" in df.columns:
        df["event_timestamp"] = pd.to_datetime(df["event_timestamp"], errors="coerce")
    if "event_date" in df.columns:
        df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce").dt.date

    # Drop rows that violate NOT NULL constraints (from intentional DQ issues)
    required_cols = ["event_id", "user_id", "event_type", "event_timestamp", "event_date"]
    existing_required = [c for c in required_cols if c in df.columns]
    before_count = len(df)
    df = df.dropna(subset=existing_required)
    # Also drop rows with empty strings in required text columns
    for col in ["event_id", "user_id", "event_type"]:
        if col in df.columns:
            df = df[df[col].astype(str).str.strip() != ""]
    dropped = before_count - len(df)
    if dropped > 0:
        logger.warning(f"  ⚠️  Filtered out {dropped} rows with NULL/empty required fields")

    # Load into PostgreSQL bronze schema
    try:
        rows = df.to_sql(
            name="raw_events",
            schema="bronze",
            con=engine,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=5000,
        )
        row_count = len(df)
        logger.info(f"  ✅ Loaded {row_count:,} rows from {csv_path.name}")
        return row_count
    except Exception as e:
        logger.error(f"  ❌ Failed to load {csv_path.name}: {e}")
        return 0


def check_already_ingested(engine, source_file: str) -> bool:
    """Check if a source file has already been ingested (idempotency)."""
    query = text("SELECT COUNT(*) FROM bronze.raw_events WHERE source_file = :file")
    with engine.connect() as conn:
        result = conn.execute(query, {"file": source_file}).scalar()
    return result > 0


# =============================================================================
# Main Ingestion
# =============================================================================


@click.command()
@click.option("--data-dir", default=None, help="Path to bronze data directory")
@click.option("--date", default=None, help="Specific date to ingest (YYYY-MM-DD)")
@click.option("--force", is_flag=True, help="Force re-ingestion even if already loaded")
def ingest(data_dir: Optional[str], date: Optional[str], force: bool):
    """Ingest raw CSV event data into the Bronze PostgreSQL layer."""
    if data_dir is None:
        data_dir = os.path.join(
            os.environ.get("PIPELINE_DATA_DIR", "data"), "bronze"
        )

    bronze_path = Path(data_dir)
    if not bronze_path.exists():
        logger.error(f"❌ Bronze directory not found: {bronze_path}")
        return

    engine = get_db_engine()
    batch_id = f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    logger.info(f"🥉 Bronze Ingestion - Batch: {batch_id}")
    logger.info(f"📁 Source: {bronze_path}")

    # Find partitions to ingest
    if date:
        partitions = [bronze_path / f"event_date={date}"]
    else:
        partitions = sorted(bronze_path.glob("event_date=*"))

    if not partitions:
        logger.warning("⚠️  No partitions found to ingest")
        return

    total_rows = 0
    total_files = 0

    for partition in partitions:
        if not partition.is_dir():
            continue

        csv_files = list(partition.glob("*.csv"))
        for csv_file in csv_files:
            # Idempotency check
            if not force and check_already_ingested(engine, csv_file.name):
                logger.info(f"  ⏭️  Skipping (already ingested): {csv_file.name}")
                continue

            rows = ingest_partition(engine, csv_file, batch_id)
            total_rows += rows
            total_files += 1

    logger.success(f"✅ Ingestion complete: {total_rows:,} rows from {total_files} files")


if __name__ == "__main__":
    ingest()
