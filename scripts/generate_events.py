"""
=============================================================================
Event Data Generator
=============================================================================
Generates realistic e-commerce event data for a cashback/shopping rewards
platform. Simulates user behavior with realistic temporal patterns,
behavioral segments, and proper funnel logic.

Usage:
    python scripts/generate_events.py --days 30 --users 1000
    python scripts/generate_events.py --start-date 2026-01-01 --end-date 2026-01-31
=============================================================================
"""

import os
import uuid
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import click
import pandas as pd
from faker import Faker
from loguru import logger

# =============================================================================
# Configuration
# =============================================================================

fake = Faker()
Faker.seed(42)
random.seed(42)

# Event types and their base probabilities (funnel order)
EVENT_TYPES = {
    "page_view": 0.40,
    "click": 0.25,
    "add_to_cart": 0.15,
    "purchase": 0.10,
    "cashback_earned": 0.07,
    "refund": 0.03,
}

# Product catalog
PRODUCT_CATEGORIES = [
    "Electronics", "Fashion", "Home & Living", "Beauty",
    "Food & Beverage", "Travel", "Health", "Sports",
]

PRODUCTS = [
    {"id": f"PROD_{i:04d}", "name": fake.catch_phrase(), "category": random.choice(PRODUCT_CATEGORIES),
     "price": round(random.uniform(5.0, 500.0), 2)}
    for i in range(1, 201)
]

# Device and browser distributions
DEVICES = ["mobile", "desktop", "tablet"]
DEVICE_WEIGHTS = [0.55, 0.35, 0.10]

BROWSERS = ["Chrome", "Safari", "Firefox", "Edge", "Samsung Internet"]
BROWSER_WEIGHTS = [0.50, 0.25, 0.10, 0.10, 0.05]

# Geographic distribution (Southeast Asia focus)
COUNTRIES = ["Singapore", "Malaysia", "Thailand", "Indonesia", "Philippines", "Vietnam", "Australia"]
COUNTRY_WEIGHTS = [0.20, 0.15, 0.15, 0.15, 0.10, 0.10, 0.15]

CITIES = {
    "Singapore": ["Singapore"],
    "Malaysia": ["Kuala Lumpur", "Penang", "Johor Bahru"],
    "Thailand": ["Bangkok", "Chiang Mai", "Phuket"],
    "Indonesia": ["Jakarta", "Surabaya", "Bandung"],
    "Philippines": ["Manila", "Cebu", "Davao"],
    "Vietnam": ["Ho Chi Minh City", "Hanoi", "Da Nang"],
    "Australia": ["Sydney", "Melbourne", "Brisbane"],
}

REFERRERS = [
    "google.com", "facebook.com", "instagram.com", "tiktok.com",
    "direct", "email", "youtube.com", "twitter.com", None,
]

# User segments define how actively a user engages
USER_SEGMENTS = {
    "power_user": {"events_per_day": (10, 30), "purchase_prob": 0.25, "weight": 0.10},
    "regular": {"events_per_day": (3, 10), "purchase_prob": 0.12, "weight": 0.30},
    "casual": {"events_per_day": (1, 5), "purchase_prob": 0.05, "weight": 0.40},
    "churned": {"events_per_day": (0, 1), "purchase_prob": 0.01, "weight": 0.20},
}


# =============================================================================
# User Profile Generation
# =============================================================================

def generate_user_profiles(num_users: int) -> list[dict]:
    """Generate user profiles with behavioral segments."""
    users = []
    segments = list(USER_SEGMENTS.keys())
    seg_weights = [USER_SEGMENTS[s]["weight"] for s in segments]

    for i in range(num_users):
        segment = random.choices(segments, weights=seg_weights, k=1)[0]
        country = random.choices(COUNTRIES, weights=COUNTRY_WEIGHTS, k=1)[0]
        city = random.choice(CITIES[country])

        users.append({
            "user_id": f"USR_{i:06d}",
            "segment": segment,
            "country": country,
            "city": city,
            "device": random.choices(DEVICES, weights=DEVICE_WEIGHTS, k=1)[0],
            "browser": random.choices(BROWSERS, weights=BROWSER_WEIGHTS, k=1)[0],
            "signup_date": fake.date_between(start_date="-365d", end_date="-1d"),
        })

    logger.info(f"Generated {num_users} user profiles across {len(set(u['segment'] for u in users))} segments")
    return users


# =============================================================================
# Event Generation
# =============================================================================

def get_hour_weight(hour: int) -> float:
    """
    Return a weight for a given hour to simulate realistic daily traffic patterns.
    Peak hours: 12-14 (lunch), 19-22 (evening).
    """
    if 0 <= hour < 6:
        return 0.05
    elif 6 <= hour < 9:
        return 0.15
    elif 9 <= hour < 12:
        return 0.25
    elif 12 <= hour < 14:
        return 0.35  # Lunch peak
    elif 14 <= hour < 17:
        return 0.20
    elif 17 <= hour < 19:
        return 0.30
    elif 19 <= hour < 22:
        return 0.40  # Evening peak
    else:
        return 0.10


def generate_event(
    user: dict,
    event_type: str,
    timestamp: datetime,
    session_id: str,
) -> dict:
    """Generate a single event record."""
    product = random.choice(PRODUCTS)

    # Calculate revenue and cashback based on event type
    revenue = 0.0
    cashback = 0.0
    quantity = 0

    if event_type == "purchase":
        quantity = random.randint(1, 5)
        revenue = round(product["price"] * quantity, 2)
        cashback = 0.0  # Cashback comes in a separate event
    elif event_type == "cashback_earned":
        # Cashback is typically 1-15% of purchase
        revenue = 0.0
        cashback = round(random.uniform(0.5, 50.0), 2)
    elif event_type == "refund":
        quantity = random.randint(1, 3)
        revenue = -round(product["price"] * quantity, 2)  # Negative revenue
        cashback = -round(abs(revenue) * random.uniform(0.01, 0.15), 2)
    elif event_type == "add_to_cart":
        quantity = random.randint(1, 5)

    # Build page URL based on event type
    page_urls = {
        "page_view": f"/category/{product['category'].lower().replace(' ', '-')}",
        "click": f"/product/{product['id']}",
        "add_to_cart": f"/product/{product['id']}",
        "purchase": "/checkout/confirmation",
        "cashback_earned": "/account/cashback",
        "refund": "/account/orders/refund",
    }

    return {
        "event_id": str(uuid.uuid4()),
        "user_id": user["user_id"],
        "event_type": event_type,
        "event_timestamp": timestamp.isoformat(),
        "event_date": timestamp.date().isoformat(),
        "page_url": page_urls.get(event_type, "/"),
        "product_id": product["id"],
        "product_name": product["name"],
        "product_category": product["category"],
        "product_price": product["price"],
        "quantity": quantity,
        "revenue": revenue,
        "cashback_amount": cashback,
        "device_type": user["device"],
        "browser": user["browser"],
        "country": user["country"],
        "city": user["city"],
        "session_id": session_id,
        "referrer": random.choice(REFERRERS),
    }


def generate_user_session_events(
    user: dict,
    date: datetime,
) -> list[dict]:
    """
    Generate a realistic session of events for a user on a given day.
    Follows funnel logic: page_view → click → add_to_cart → purchase → cashback.
    """
    segment_config = USER_SEGMENTS[user["segment"]]
    min_events, max_events = segment_config["events_per_day"]

    # Some days users don't show up (especially churned)
    if random.random() > (0.9 if user["segment"] == "power_user" else
                          0.6 if user["segment"] == "regular" else
                          0.3 if user["segment"] == "casual" else 0.05):
        return []

    num_events = random.randint(min_events, max_events)
    if num_events == 0:
        return []

    session_id = str(uuid.uuid4())[:8]
    events = []

    # Distribute events across the day with realistic hourly patterns
    hours = list(range(24))
    hour_weights = [get_hour_weight(h) for h in hours]

    # Generate funnel-based events
    funnel = ["page_view", "click", "add_to_cart", "purchase", "cashback_earned"]
    current_funnel_stage = 0

    for _ in range(num_events):
        hour = random.choices(hours, weights=hour_weights, k=1)[0]
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        timestamp = date.replace(hour=hour, minute=minute, second=second)

        # Determine event type using funnel logic
        if current_funnel_stage < len(funnel) - 1:
            # Progress through funnel with decreasing probability
            if random.random() < 0.6:  # 60% chance to stay at current level
                event_type = funnel[current_funnel_stage]
            else:
                current_funnel_stage += 1
                event_type = funnel[min(current_funnel_stage, len(funnel) - 1)]
        else:
            # At the end of funnel, generate random events
            event_type = random.choices(
                list(EVENT_TYPES.keys()),
                weights=list(EVENT_TYPES.values()),
                k=1,
            )[0]

        # Refund is a special case — only if there was a purchase
        if event_type == "refund" and random.random() > 0.15:
            event_type = "page_view"  # Most refund attempts don't happen

        events.append(generate_event(user, event_type, timestamp, session_id))

    # Sort events by timestamp within the session
    events.sort(key=lambda e: e["event_timestamp"])
    return events


def introduce_data_quality_issues(events: list[dict], error_rate: float = 0.02) -> list[dict]:
    """
    Introduce realistic data quality issues for testing the cleaning pipeline.
    This simulates real-world messiness in event data.
    """
    modified = []
    for event in events:
        e = event.copy()

        if random.random() < error_rate:
            issue = random.choice(["null_user", "future_date", "negative_price", "duplicate", "empty_type"])

            if issue == "null_user":
                e["user_id"] = None
            elif issue == "future_date":
                future = datetime.now() + timedelta(days=random.randint(1, 365))
                e["event_timestamp"] = future.isoformat()
                e["event_date"] = future.date().isoformat()
            elif issue == "negative_price":
                e["product_price"] = -abs(e["product_price"])
            elif issue == "duplicate":
                modified.append(e)  # Add duplicate
            elif issue == "empty_type":
                e["event_type"] = ""

        modified.append(e)

    logger.info(f"Introduced ~{error_rate*100:.1f}% data quality issues ({len(modified) - len(events)} extra rows)")
    return modified


# =============================================================================
# Main Generator
# =============================================================================

@click.command()
@click.option("--days", default=30, help="Number of days of data to generate")
@click.option("--users", default=1000, help="Number of unique users")
@click.option("--start-date", default=None, help="Start date (YYYY-MM-DD). If not set, uses today - days.")
@click.option("--end-date", default=None, help="End date (YYYY-MM-DD). If not set, uses today.")
@click.option("--output-dir", default=None, help="Output directory for CSV files")
@click.option("--error-rate", default=0.02, help="Rate of intentional data quality issues (0.0-1.0)")
@click.option("--seed", default=42, help="Random seed for reproducibility")
def generate(
    days: int,
    users: int,
    start_date: Optional[str],
    end_date: Optional[str],
    output_dir: Optional[str],
    error_rate: float,
    seed: int,
):
    """Generate realistic e-commerce event data for the analytics pipeline."""
    random.seed(seed)
    Faker.seed(seed)

    # Determine date range
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        end = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        start = end - timedelta(days=days - 1)

    # Determine output directory
    if output_dir is None:
        output_dir = os.environ.get("PIPELINE_DATA_DIR", "data")
    bronze_dir = Path(output_dir) / "bronze"
    bronze_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"🎲 Generating events: {users} users, {start.date()} → {end.date()}")
    logger.info(f"📁 Output: {bronze_dir}")

    # Generate user profiles
    user_profiles = generate_user_profiles(users)

    # Generate events day by day
    total_events = 0
    current_date = start

    while current_date <= end:
        daily_events = []

        # Weekend adjustment: slightly fewer events
        is_weekend = current_date.weekday() >= 5
        active_users = user_profiles if not is_weekend else random.sample(
            user_profiles, k=int(len(user_profiles) * 0.8)
        )

        for user in active_users:
            session_events = generate_user_session_events(user, current_date)
            daily_events.extend(session_events)

        # Introduce data quality issues
        if error_rate > 0:
            daily_events = introduce_data_quality_issues(daily_events, error_rate)

        # Save daily partition as CSV
        if daily_events:
            date_str = current_date.strftime("%Y-%m-%d")
            partition_dir = bronze_dir / f"event_date={date_str}"
            partition_dir.mkdir(parents=True, exist_ok=True)

            df = pd.DataFrame(daily_events)
            output_path = partition_dir / f"events_{date_str}.csv"
            df.to_csv(output_path, index=False)

            total_events += len(daily_events)
            logger.info(f"  📅 {date_str}: {len(daily_events):,} events → {output_path.name}")

        current_date += timedelta(days=1)

    logger.success(f"✅ Generation complete: {total_events:,} total events across {days} days")
    logger.info(f"📊 Average: {total_events / days:,.0f} events/day")

    return total_events


if __name__ == "__main__":
    generate()
