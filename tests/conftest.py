import os
import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_firestore():
    return MagicMock()

@pytest.fixture
def mock_amadeus():
    return MagicMock()

@pytest.fixture
def sample_trip_config():
    return {
        "trip_id": "test-trip",
        "label": "Test Trip",
        "type": "round_trip",
        "origins": ["HYD"],
        "destinations": ["ARN"],
        "airlines": ["LH", "EK", "KL"],
        "cabin_classes": ["ECONOMY", "PREMIUM_ECONOMY"],
        "max_stops": 1,
        "departure_date_range": ["2026-05-25", "2026-06-07"],
        "return_date_range": ["2026-06-25", "2026-07-10"],
        "min_trip_days": 25,
        "max_trip_days": 30,
        "scan_frequency_days": 1,
        "last_scanned": None,
        "price_threshold": None,
        "alert_on_rolling_avg_drop_pct": 10,
        "always_notify": True,
        "currency": "INR",
        "slack_webhook_url": None,
        "active": True
    }

@pytest.fixture
def integration_env():
    """Set up environment for local integration testing."""
    return {
        "AMADEUS_API_KEY": os.environ.get("AMADEUS_API_KEY"),
        "AMADEUS_API_SECRET": os.environ.get("AMADEUS_API_SECRET"),
        "SLACK_WEBHOOK_URL": os.environ.get("SLACK_WEBHOOK_URL"),
    }
