# tests/test_price_tracker.py
import pytest
from unittest.mock import MagicMock
from datetime import datetime


def test_store_prices_writes_to_firestore(mock_firestore):
    from firestore_price_tracker import PriceTracker
    tracker = PriceTracker(mock_firestore)

    prices = [
        {"offer_id": "1", "price": 85000, "currency": "INR", "departure_date": "2026-06-01",
         "return_date": "2026-07-01", "airline": "EK", "stops": 1,
         "cabin_class": "PREMIUM_ECONOMY", "fare_family": "Basic", "duration_minutes": 750}
    ]

    tracker.store_prices("test-trip", "HYD-ARN", prices)

    mock_firestore.collection.assert_called_with("price_history")
    assert mock_firestore.collection().add.called


def test_get_rolling_average_calculates_from_last_7_scans(mock_firestore):
    # Mock query results - 7 price observations
    mock_docs = []
    for i, price in enumerate([80000, 82000, 85000, 83000, 81000, 84000, 86000]):
        doc = MagicMock()
        doc.to_dict.return_value = {"price": price}
        mock_docs.append(doc)

    mock_firestore.collection().where().where().where().order_by().limit().stream.return_value = mock_docs

    from firestore_price_tracker import PriceTracker
    tracker = PriceTracker(mock_firestore)

    avg = tracker.get_rolling_average("test-trip", "HYD-ARN", "PREMIUM_ECONOMY")

    assert avg == 83000  # (80000+82000+85000+83000+81000+84000+86000) / 7
