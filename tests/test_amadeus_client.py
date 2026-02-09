import pytest
from unittest.mock import MagicMock, patch


def test_get_cheapest_dates_returns_sorted_prices():
    mock_amadeus = MagicMock()
    mock_amadeus.shopping.flight_dates.get.return_value.data = [
        {"departureDate": "2026-06-01", "returnDate": "2026-07-01", "price": {"total": "85000"}},
        {"departureDate": "2026-06-03", "returnDate": "2026-07-02", "price": {"total": "82000"}},
        {"departureDate": "2026-06-05", "returnDate": "2026-07-03", "price": {"total": "90000"}},
    ]

    with patch('amadeus_client.Client', return_value=mock_amadeus):
        from amadeus_client import AmadeusClient
        client = AmadeusClient("key", "secret")
        results = client.get_cheapest_dates(
            origin="HYD",
            destination="ARN",
            departure_range=("2026-05-25", "2026-06-07"),
            return_range=("2026-06-25", "2026-07-07")
        )

    assert len(results) == 3
    assert results[0]["price"] == 82000  # Sorted by price
    assert results[0]["departure_date"] == "2026-06-03"


def test_get_flight_offers_filters_by_airlines_and_stops():
    mock_amadeus = MagicMock()
    mock_amadeus.shopping.flight_offers_search.get.return_value.data = [
        {
            "id": "1",
            "price": {"total": "85000", "currency": "INR"},
            "itineraries": [
                {"duration": "PT12H30M", "segments": [
                    {"carrierCode": "EK", "number": "528",
                     "departure": {"iataCode": "HYD", "at": "2026-06-01T14:30:00"},
                     "arrival": {"iataCode": "DXB", "at": "2026-06-01T17:00:00"}},
                    {"carrierCode": "EK", "number": "157",
                     "departure": {"iataCode": "DXB", "at": "2026-06-01T21:00:00"},
                     "arrival": {"iataCode": "ARN", "at": "2026-06-02T03:00:00"}}
                ]},
                {"duration": "PT13H", "segments": [{"carrierCode": "EK"}]}
            ],
            "travelerPricings": [{"fareDetailsBySegment": [{"cabin": "PREMIUM_ECONOMY", "brandedFare": "BASIC"}]}]
        },
        {
            "id": "2",
            "price": {"total": "95000", "currency": "INR"},
            "itineraries": [
                {"duration": "PT15H", "segments": [
                    {"carrierCode": "AI", "number": "101",
                     "departure": {"iataCode": "HYD", "at": "2026-06-01T10:00:00"},
                     "arrival": {"iataCode": "DEL", "at": "2026-06-01T12:00:00"}},
                    {"carrierCode": "AI", "number": "102",
                     "departure": {"iataCode": "DEL", "at": "2026-06-01T14:00:00"},
                     "arrival": {"iataCode": "FRA", "at": "2026-06-01T18:00:00"}},
                    {"carrierCode": "AI", "number": "103",
                     "departure": {"iataCode": "FRA", "at": "2026-06-01T20:00:00"},
                     "arrival": {"iataCode": "ARN", "at": "2026-06-01T22:00:00"}}
                ]},
                {"duration": "PT14H", "segments": [{"carrierCode": "AI"}]}
            ],
            "travelerPricings": [{"fareDetailsBySegment": [{"cabin": "ECONOMY", "brandedFare": "LIGHT"}]}]
        }
    ]

    with patch('amadeus_client.Client', return_value=mock_amadeus):
        from amadeus_client import AmadeusClient
        client = AmadeusClient("key", "secret")
        results = client.get_flight_offers(
            origin="HYD",
            destination="ARN",
            departure_date="2026-06-01",
            return_date="2026-07-01",
            cabin_class="PREMIUM_ECONOMY",
            airlines=["EK", "LH", "KL"],
            max_stops=1
        )

    assert len(results) == 1  # AI filtered out, 3-stop filtered out
    assert results[0]["airlines"] == ["EK"]
    assert results[0]["stops"] == 1
    assert results[0]["layover_cities"] == ["DXB"]
    assert results[0]["flight_numbers"] == ["EK 528", "EK 157"]
    assert "2026-06-01T14:30:00" in results[0]["departure_time"]
    assert "2026-06-02T03:00:00" in results[0]["arrival_time"]