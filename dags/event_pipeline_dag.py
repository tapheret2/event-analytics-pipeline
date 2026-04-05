"""
=============================================================================
Event Analytics Pipeline - Airflow DAG
=============================================================================
Orchestrates the complete event analytics pipeline:
  1. Generate mock event data
  2. Ingest raw data → Bronze layer
  3. Clean & validate → Silver layer (PySpark)
  4. Transform & aggregate → Gold layer (dbt)
  5. Data quality checks

Schedule: Daily at 2:00 AM UTC
=============================================================================
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.task_group import TaskGroup

# =============================================================================
# DAG Configuration
# =============================================================================

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=1),
}

DAG_DESCRIPTION = """
### Event Analytics Pipeline 🚀

End-to-end data pipeline for e-commerce event analytics.

**Layers:**
- 🥉 **Bronze**: Raw event ingestion
- 🥈 **Silver**: PySpark cleaning & validation
- 🥇 **Gold**: dbt dimensional models & KPIs

**Schedule:** Daily at 2:00 AM UTC
"""


# =============================================================================
# Task Functions
# =============================================================================


def generate_events_task(**context):
    """Generate daily mock event data."""
    import sys
    sys.path.insert(0, "/opt/airflow/scripts")
    from generate_events import generate_user_profiles, generate_user_session_events
    from generate_events import introduce_data_quality_issues

    import pandas as pd
    from pathlib import Path
    from datetime import datetime
    from loguru import logger
    import os

    # Get execution date from Airflow context
    execution_date = context["ds"]
    data_dir = os.environ.get("PIPELINE_DATA_DIR", "/opt/airflow/data")
    bronze_dir = Path(data_dir) / "bronze" / f"event_date={execution_date}"
    bronze_dir.mkdir(parents=True, exist_ok=True)

    # Generate events for the execution date
    date = datetime.strptime(execution_date, "%Y-%m-%d")
    users = generate_user_profiles(num_users=1000)

    daily_events = []
    for user in users:
        events = generate_user_session_events(user, date)
        daily_events.extend(events)

    # Introduce realistic data quality issues
    daily_events = introduce_data_quality_issues(daily_events, error_rate=0.02)

    # Save to CSV
    if daily_events:
        df = pd.DataFrame(daily_events)
        output_path = bronze_dir / f"events_{execution_date}.csv"
        df.to_csv(output_path, index=False)
        logger.info(f"✅ Generated {len(daily_events)} events for {execution_date}")

    return len(daily_events)


def bronze_ingestion_task(**context):
    """Ingest raw CSV data into PostgreSQL Bronze layer."""
    import sys
    sys.path.insert(0, "/opt/airflow/scripts")
    from bronze_ingestion import ingest_partition, get_db_engine

    from pathlib import Path
    from datetime import datetime
    from loguru import logger
    import os

    execution_date = context["ds"]
    data_dir = os.environ.get("PIPELINE_DATA_DIR", "/opt/airflow/data")
    partition_dir = Path(data_dir) / "bronze" / f"event_date={execution_date}"

    engine = get_db_engine()
    batch_id = f"airflow_{execution_date}_{datetime.utcnow().strftime('%H%M%S')}"

    total_rows = 0
    csv_files = list(partition_dir.glob("*.csv"))

    for csv_file in csv_files:
        rows = ingest_partition(engine, csv_file, batch_id)
        total_rows += rows

    logger.info(f"✅ Bronze ingestion complete: {total_rows} rows for {execution_date}")
    return total_rows


def silver_transform_task(**context):
    """Run PySpark Silver transformation."""
    import sys
    sys.path.insert(0, "/opt/airflow/scripts")
    from silver_transform import create_spark_session, transform_bronze_to_silver
    from loguru import logger

    execution_date = context["ds"]

    spark = create_spark_session()
    try:
        rows = transform_bronze_to_silver(spark, date_filter=execution_date)
        logger.info(f"✅ Silver transform complete: {rows} rows for {execution_date}")
        return rows
    finally:
        spark.stop()


def data_quality_check_task(**context):
    """Run data quality checks on the Silver layer."""
    from sqlalchemy import create_engine, text
    from loguru import logger
    import os

    execution_date = context["ds"]

    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "pipeline")
    password = os.environ.get("POSTGRES_PASSWORD", "pipeline123")
    database = os.environ.get("POSTGRES_DB", "event_analytics")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    engine = create_engine(url)

    checks = {
        "row_count": f"""
            SELECT COUNT(*) as cnt
            FROM silver.cleaned_events
            WHERE event_date = '{execution_date}'
        """,
        "null_event_ids": f"""
            SELECT COUNT(*) as cnt
            FROM silver.cleaned_events
            WHERE event_date = '{execution_date}' AND event_id IS NULL
        """,
        "valid_ratio": f"""
            SELECT
                ROUND(
                    COUNT(*) FILTER (WHERE is_valid = true)::numeric /
                    NULLIF(COUNT(*), 0) * 100, 2
                ) as valid_pct
            FROM silver.cleaned_events
            WHERE event_date = '{execution_date}'
        """,
        "duplicate_check": f"""
            SELECT COUNT(*) - COUNT(DISTINCT event_id) as duplicates
            FROM silver.cleaned_events
            WHERE event_date = '{execution_date}'
        """,
    }

    results = {}
    with engine.connect() as conn:
        for check_name, query in checks.items():
            result = conn.execute(text(query)).scalar()
            results[check_name] = result
            logger.info(f"  📊 {check_name}: {result}")

    # Assert quality thresholds
    if results["row_count"] == 0:
        # Check if there's any data at all (manual trigger may use wrong date)
        with engine.connect() as conn:
            total = conn.execute(text("SELECT COUNT(*) FROM silver.cleaned_events")).scalar()
        if total > 0:
            logger.warning(
                f"⚠️  No rows found in Silver for {execution_date}, "
                f"but {total:,} total rows exist. Skipping DQ check (date mismatch)."
            )
            return results
        raise ValueError(f"❌ No rows found in Silver layer at all")
    if results["null_event_ids"] > 0:
        raise ValueError(f"❌ Found {results['null_event_ids']} null event_ids")
    if results["duplicate_check"] > 0:
        logger.warning(f"⚠️  Found {results['duplicate_check']} duplicates in Silver")

    logger.info(f"✅ All quality checks passed for {execution_date}")
    return results


# =============================================================================
# DAG Definition
# =============================================================================

with DAG(
    dag_id="event_analytics_pipeline",
    default_args=default_args,
    description="End-to-end event analytics: Bronze → Silver → Gold",
    schedule="0 2 * * *",  # Daily at 2:00 AM UTC
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["event-analytics", "medallion", "production"],
    doc_md=DAG_DESCRIPTION,
) as dag:

    # --- Start ---
    start = EmptyOperator(task_id="start")

    # --- Data Generation ---
    generate_events = PythonOperator(
        task_id="generate_events",
        python_callable=generate_events_task,
        doc_md="Generate realistic e-commerce event data for the execution date",
    )

    # --- Bronze Layer ---
    with TaskGroup("bronze_layer", tooltip="Raw data ingestion") as bronze_group:
        ingest = PythonOperator(
            task_id="bronze_ingestion",
            python_callable=bronze_ingestion_task,
            doc_md="Load raw CSV events into PostgreSQL Bronze schema",
        )

    # --- Silver Layer ---
    with TaskGroup("silver_layer", tooltip="PySpark cleaning & validation") as silver_group:
        transform = PythonOperator(
            task_id="silver_transform",
            python_callable=silver_transform_task,
            doc_md="Clean, validate, and deduplicate events using PySpark",
        )

    # --- Gold Layer (dbt) ---
    with TaskGroup("gold_layer", tooltip="dbt dimensional modeling") as gold_group:
        dbt_run = BashOperator(
            task_id="dbt_run",
            bash_command="cd /opt/airflow/dbt && dbt run --profiles-dir . --target prod",
            doc_md="Run dbt models to build Gold layer dimensional tables",
        )

        dbt_test = BashOperator(
            task_id="dbt_test",
            bash_command="cd /opt/airflow/dbt && dbt test --profiles-dir . --target prod",
            doc_md="Run dbt tests for data quality validation",
        )

        dbt_run >> dbt_test

    # --- Quality Checks (advisory — does not block Gold layer) ---
    quality_check = PythonOperator(
        task_id="data_quality_check",
        python_callable=data_quality_check_task,
        doc_md="Run quality assertions on Silver layer data (advisory)",
    )

    # --- End ---
    end = EmptyOperator(task_id="end", trigger_rule="none_failed_min_one_success")

    # --- Dependencies ---
    # Gold layer runs directly after Silver; DQ check is parallel / advisory
    start >> generate_events >> bronze_group >> silver_group
    silver_group >> gold_group >> end
    silver_group >> quality_check >> end

