# tests/test_main.py
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


def test_check_flights_processes_active_trips(sample_trip_config):
    # Add scan_window to config (not in original fixture)
    sample_trip_config["scan_window"] = {
        "start": "2026-01-01",
        "end": "2026-12-31"
    }

    mock_firestore = MagicMock()
    mock_trip_doc = MagicMock()
    mock_trip_doc.to_dict.return_value = sample_trip_config
    mock_trip_doc.id = "test-trip"
    mock_firestore.collection().where().stream.return_value = [mock_trip_doc]

    mock_amadeus_client = MagicMock()
    mock_amadeus_client.get_cheapest_dates.return_value = [
        {"departure_date": "2026-06-01", "return_date": "2026-07-01", "price": 85000}
    ]
    mock_amadeus_client.get_flight_offers.return_value = [
        {"offer_id": "1", "price": 85000, "currency": "INR", "departure_date": "2026-06-01",
         "return_date": "2026-07-01", "airline": "EK", "stops": 1,
         "cabin_class": "PREMIUM_ECONOMY", "fare_family": "Basic", "duration_minutes": 750}
    ]

    mock_notifier = MagicMock()
    mock_tracker = MagicMock()
    mock_tracker.get_rolling_average.return_value = 95000

    with patch('main.firestore.Client', return_value=mock_firestore), \
         patch('main.AmadeusClient', return_value=mock_amadeus_client), \
         patch('main.SlackNotifier', return_value=mock_notifier), \
         patch('main.PriceTracker', return_value=mock_tracker), \
         patch('main.get_secret', side_effect=["key", "secret", "webhook"]):

        from main import check_flights
        request = MagicMock()
        response = check_flights(request)

    assert response == "OK"
    assert mock_notifier.send.called
