"""
=============================================================================
Tests: Data Transformations
=============================================================================
Unit tests for data transformation logic used in Bronze and Silver layers.
Tests use Pandas for simplicity (no Spark dependency needed for unit tests).
=============================================================================
"""

import pandas as pd
import pytest
from datetime import datetime


# =============================================================================
# Bronze Ingestion Tests
# =============================================================================


class TestBronzeTransformations:
    """Tests for Bronze layer data handling."""

    @pytest.fixture
    def sample_raw_data(self):
        """Create sample raw event data."""
        return pd.DataFrame({
            "event_id": ["e1", "e2", "e3", "e4", "e5"],
            "user_id": ["u1", "u2", "u3", "u1", "u2"],
            "event_type": ["page_view", "click", "purchase", "add_to_cart", "page_view"],
            "event_timestamp": [
                "2026-01-15T10:00:00",
                "2026-01-15T11:00:00",
                "2026-01-15T12:00:00",
                "2026-01-15T13:00:00",
                "2026-01-15T14:00:00",
            ],
            "event_date": ["2026-01-15"] * 5,
            "product_price": ["10.99", "20.50", "99.99", "15.00", "5.99"],
            "quantity": ["0", "0", "2", "1", "0"],
            "revenue": ["0", "0", "199.98", "0", "0"],
            "cashback_amount": ["0", "0", "0", "0", "0"],
        })

    def test_numeric_columns_convert_correctly(self, sample_raw_data):
        """Verify numeric type casting."""
        df = sample_raw_data.copy()
        numeric_cols = ["product_price", "quantity", "revenue", "cashback_amount"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        assert df["product_price"].dtype in ["float64", "int64"]
        assert df["revenue"].iloc[2] == 199.98

    def test_timestamp_parsing(self, sample_raw_data):
        """Verify timestamp parsing."""
        df = sample_raw_data.copy()
        df["event_timestamp"] = pd.to_datetime(df["event_timestamp"])
        assert df["event_timestamp"].dtype == "datetime64[ns]"

    def test_metadata_columns_added(self, sample_raw_data):
        """Verify metadata columns can be added."""
        df = sample_raw_data.copy()
        df["ingested_at"] = datetime.utcnow().isoformat()
        df["source_file"] = "test_events.csv"
        df["batch_id"] = "batch_001"

        assert "ingested_at" in df.columns
        assert "source_file" in df.columns
        assert "batch_id" in df.columns


# =============================================================================
# Silver Transformation Tests
# =============================================================================


class TestSilverTransformations:
    """Tests for Silver layer cleaning and validation logic."""

    @pytest.fixture
    def sample_events(self):
        """Create sample events with various quality issues."""
        return pd.DataFrame({
            "event_id": ["e1", "e2", "e3", "e4", "e5", "e1"],  # e1 is duplicated
            "user_id": ["u1", "u2", None, "u4", "u5", "u1"],   # u3 is null
            "event_type": ["page_view", "click", "purchase", "", "page_view", "page_view"],
            "event_timestamp": pd.to_datetime([
                "2026-01-15T10:00:00",
                "2026-01-15T11:00:00",
                "2026-01-15T12:00:00",
                "2026-01-15T13:00:00",
                "2027-06-15T14:00:00",  # Future date
                "2026-01-15T10:00:00",  # Duplicate
            ]),
            "event_date": pd.to_datetime([
                "2026-01-15", "2026-01-15", "2026-01-15",
                "2026-01-15", "2027-06-15", "2026-01-15",
            ]).date,
            "product_price": [10.99, 20.50, 99.99, -15.00, 5.99, 10.99],
            "quantity": [0, 0, 2, 1, 0, 0],
            "revenue": [0, 0, 199.98, 0, 0, 0],
            "device_type": ["mobile", "desktop", None, "mobile", "tablet", "mobile"],
        })

    def test_deduplication(self, sample_events):
        """Verify duplicate removal by event_id."""
        df = sample_events.drop_duplicates(subset=["event_id"])
        assert len(df) == 5  # e1 was duplicated

    def test_null_detection(self, sample_events):
        """Verify null user_ids are detected."""
        null_count = sample_events["user_id"].isna().sum()
        assert null_count == 1

    def test_invalid_event_type_detection(self, sample_events):
        """Verify empty event types are detected."""
        valid_types = {"page_view", "click", "add_to_cart", "purchase", "cashback_earned", "refund"}
        invalid = sample_events[~sample_events["event_type"].isin(valid_types)]
        assert len(invalid) >= 1  # The empty event type

    def test_future_date_detection(self, sample_events):
        """Verify future timestamps are detected."""
        now = datetime.utcnow()
        future = sample_events[sample_events["event_timestamp"] > now]
        assert len(future) >= 1

    def test_negative_price_correction(self, sample_events):
        """Verify negative prices are corrected."""
        df = sample_events.copy()
        # Correct negative prices (except refunds)
        mask = (df["product_price"] < 0) & (df["event_type"] != "refund")
        df.loc[mask, "product_price"] = df.loc[mask, "product_price"].abs()

        assert (df[df["event_type"] != "refund"]["product_price"] >= 0).all()

    def test_default_fill_for_nulls(self, sample_events):
        """Verify null device types are filled with defaults."""
        df = sample_events.copy()
        df["device_type"] = df["device_type"].fillna("unknown")
        assert (df["device_type"] != "").all()
        assert df["device_type"].isna().sum() == 0


# =============================================================================
# KPI Calculation Tests
# =============================================================================


class TestKPICalculations:
    """Tests for KPI calculation logic."""

    @pytest.fixture
    def daily_events(self):
        """Create sample daily events for KPI testing."""
        return pd.DataFrame({
            "event_id": [f"e{i}" for i in range(10)],
            "user_id": ["u1", "u1", "u2", "u2", "u3", "u3", "u4", "u4", "u5", "u5"],
            "event_type": [
                "page_view", "purchase",
                "page_view", "click",
                "page_view", "add_to_cart",
                "page_view", "purchase",
                "page_view", "page_view",
            ],
            "event_date": ["2026-01-15"] * 10,
            "revenue": [0, 50.0, 0, 0, 0, 0, 0, 75.0, 0, 0],
            "cashback_amount": [0, 5.0, 0, 0, 0, 0, 0, 7.5, 0, 0],
        })

    def test_dau_calculation(self, daily_events):
        """Verify DAU counts unique users."""
        dau = daily_events["user_id"].nunique()
        assert dau == 5

    def test_revenue_sum(self, daily_events):
        """Verify revenue aggregation."""
        total_revenue = daily_events[daily_events["event_type"] == "purchase"]["revenue"].sum()
        assert total_revenue == 125.0

    def test_cashback_sum(self, daily_events):
        """Verify cashback aggregation."""
        total_cashback = daily_events["cashback_amount"].sum()
        assert total_cashback == 12.5

    def test_conversion_rate(self, daily_events):
        """Verify conversion rate calculation."""
        page_views = len(daily_events[daily_events["event_type"] == "page_view"])
        purchases = len(daily_events[daily_events["event_type"] == "purchase"])
        conversion = (purchases / page_views * 100) if page_views > 0 else 0

        assert page_views == 5
        assert purchases == 2
        assert conversion == 40.0

    def test_event_type_counts(self, daily_events):
        """Verify event type counting."""
        counts = daily_events["event_type"].value_counts()
        assert counts["page_view"] == 5
        assert counts["purchase"] == 2
        assert counts["click"] == 1
        assert counts["add_to_cart"] == 1
