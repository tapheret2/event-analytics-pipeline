"""
=============================================================================
Tests: Event Data Generator
=============================================================================
Unit tests for the mock event data generator.
=============================================================================
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from generate_events import (
    generate_user_profiles,
    generate_user_session_events,
    generate_event,
    introduce_data_quality_issues,
    get_hour_weight,
    EVENT_TYPES,
)


# =============================================================================
# User Profile Tests
# =============================================================================


class TestUserProfiles:
    """Tests for user profile generation."""

    def test_generates_correct_number_of_users(self):
        users = generate_user_profiles(100)
        assert len(users) == 100

    def test_user_has_required_fields(self):
        users = generate_user_profiles(1)
        user = users[0]
        required_fields = [
            "user_id", "segment", "country", "city",
            "device", "browser", "signup_date",
        ]
        for field in required_fields:
            assert field in user, f"Missing field: {field}"

    def test_user_id_format(self):
        users = generate_user_profiles(5)
        for user in users:
            assert user["user_id"].startswith("USR_")

    def test_segments_are_valid(self):
        users = generate_user_profiles(100)
        valid_segments = {"power_user", "regular", "casual", "churned"}
        for user in users:
            assert user["segment"] in valid_segments

    def test_devices_are_valid(self):
        users = generate_user_profiles(100)
        valid_devices = {"mobile", "desktop", "tablet"}
        for user in users:
            assert user["device"] in valid_devices


# =============================================================================
# Event Generation Tests
# =============================================================================


class TestEventGeneration:
    """Tests for event generation logic."""

    @pytest.fixture
    def sample_user(self):
        return {
            "user_id": "USR_000001",
            "segment": "regular",
            "country": "Singapore",
            "city": "Singapore",
            "device": "mobile",
            "browser": "Chrome",
            "signup_date": datetime(2025, 6, 1).date(),
        }

    def test_event_has_required_fields(self, sample_user):
        event = generate_event(
            sample_user, "page_view",
            datetime(2026, 1, 15, 10, 30, 0), "sess123",
        )
        required_fields = [
            "event_id", "user_id", "event_type", "event_timestamp",
            "event_date", "product_id", "device_type", "session_id",
        ]
        for field in required_fields:
            assert field in event, f"Missing field: {field}"

    def test_event_types_are_valid(self, sample_user):
        for event_type in EVENT_TYPES:
            event = generate_event(
                sample_user, event_type,
                datetime(2026, 1, 15, 10, 30, 0), "sess123",
            )
            assert event["event_type"] == event_type

    def test_purchase_has_positive_revenue(self, sample_user):
        event = generate_event(
            sample_user, "purchase",
            datetime(2026, 1, 15, 10, 30, 0), "sess123",
        )
        assert event["revenue"] > 0
        assert event["quantity"] > 0

    def test_refund_has_negative_revenue(self, sample_user):
        event = generate_event(
            sample_user, "refund",
            datetime(2026, 1, 15, 10, 30, 0), "sess123",
        )
        assert event["revenue"] < 0

    def test_cashback_event_has_cashback(self, sample_user):
        event = generate_event(
            sample_user, "cashback_earned",
            datetime(2026, 1, 15, 10, 30, 0), "sess123",
        )
        assert event["cashback_amount"] > 0

    def test_session_events_sorted_by_time(self, sample_user):
        events = generate_user_session_events(
            sample_user, datetime(2026, 1, 15),
        )
        if len(events) > 1:
            for i in range(len(events) - 1):
                assert events[i]["event_timestamp"] <= events[i+1]["event_timestamp"]

    def test_event_id_is_unique(self, sample_user):
        events = generate_user_session_events(
            sample_user, datetime(2026, 1, 15),
        )
        event_ids = [e["event_id"] for e in events]
        assert len(event_ids) == len(set(event_ids))


# =============================================================================
# Data Quality Tests
# =============================================================================


class TestDataQuality:
    """Tests for intentional data quality issue injection."""

    def test_introduces_issues(self):
        events = [
            {
                "event_id": f"test_{i}",
                "user_id": f"USR_{i}",
                "event_type": "page_view",
                "event_timestamp": "2026-01-15T10:00:00",
                "event_date": "2026-01-15",
                "product_price": 10.0,
            }
            for i in range(1000)
        ]

        # With 100% error rate, all events should be affected
        modified = introduce_data_quality_issues(events, error_rate=1.0)
        assert len(modified) >= len(events)  # May have duplicates

    def test_no_issues_at_zero_rate(self):
        events = [
            {
                "event_id": f"test_{i}",
                "user_id": f"USR_{i}",
                "event_type": "page_view",
                "event_timestamp": "2026-01-15T10:00:00",
                "event_date": "2026-01-15",
                "product_price": 10.0,
            }
            for i in range(100)
        ]

        modified = introduce_data_quality_issues(events, error_rate=0.0)
        assert len(modified) == len(events)


# =============================================================================
# Hour Weight Tests
# =============================================================================


class TestHourWeights:
    """Tests for temporal traffic patterns."""

    def test_peak_hours_have_higher_weight(self):
        # Evening peak (19-22) should be higher than early morning (0-6)
        assert get_hour_weight(20) > get_hour_weight(3)

    def test_lunch_peak(self):
        assert get_hour_weight(13) > get_hour_weight(10)

    def test_all_hours_positive(self):
        for hour in range(24):
            assert get_hour_weight(hour) > 0
