import pytest
from unittest.mock import MagicMock, patch


def _make_offer(
    offer_id="1",
    price="85000",
    currency="INR",
    outbound_duration="PT12H30M",
    outbound_segments=None,
    return_duration="PT13H00M",
    return_segments=None,
    cabin="PREMIUM_ECONOMY",
    branded_fare="BASIC",
    booking_class="R",
    baggage=None,
    seats=3,
):
    """Build a realistic Amadeus offer dict for testing."""
    if outbound_segments is None:
        outbound_segments = [
            {"carrierCode": "EK", "number": "528",
             "departure": {"iataCode": "HYD", "at": "2026-06-01T14:30:00"},
             "arrival": {"iataCode": "DXB", "at": "2026-06-01T17:00:00"}},
            {"carrierCode": "EK", "number": "157",
             "departure": {"iataCode": "DXB", "at": "2026-06-01T21:00:00"},
             "arrival": {"iataCode": "ARN", "at": "2026-06-02T03:00:00"}},
        ]
    if return_segments is None:
        return_segments = [
            {"carrierCode": "EK", "number": "158",
             "departure": {"iataCode": "ARN", "at": "2026-07-01T09:00:00"},
             "arrival": {"iataCode": "DXB", "at": "2026-07-01T18:00:00"}},
            {"carrierCode": "EK", "number": "529",
             "departure": {"iataCode": "DXB", "at": "2026-07-01T20:00:00"},
             "arrival": {"iataCode": "HYD", "at": "2026-07-01T23:30:00"}},
        ]
    if baggage is None:
        baggage = {"weight": 23, "weightUnit": "KG"}

    fare_detail = {
        "cabin": cabin,
        "brandedFare": branded_fare,
        "class": booking_class,
        "includedCheckedBags": baggage,
    }

    return {
        "id": offer_id,
        "price": {"total": price, "currency": currency},
        "numberOfBookableSeats": str(seats),
        "itineraries": [
            {"duration": outbound_duration, "segments": outbound_segments},
            {"duration": return_duration, "segments": return_segments},
        ],
        "travelerPricings": [{"fareDetailsBySegment": [fare_detail]}],
    }


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
    ek_offer = _make_offer(offer_id="1", price="85000")
    ai_offer = _make_offer(
        offer_id="2",
        price="95000",
        outbound_duration="PT15H",
        outbound_segments=[
            {"carrierCode": "AI", "number": "101",
             "departure": {"iataCode": "HYD", "at": "2026-06-01T10:00:00"},
             "arrival": {"iataCode": "DEL", "at": "2026-06-01T12:00:00"}},
            {"carrierCode": "AI", "number": "102",
             "departure": {"iataCode": "DEL", "at": "2026-06-01T14:00:00"},
             "arrival": {"iataCode": "FRA", "at": "2026-06-01T18:00:00"}},
            {"carrierCode": "AI", "number": "103",
             "departure": {"iataCode": "FRA", "at": "2026-06-01T20:00:00"},
             "arrival": {"iataCode": "ARN", "at": "2026-06-01T22:00:00"}},
        ],
        return_duration="PT14H",
        return_segments=[
            {"carrierCode": "AI", "number": "104",
             "departure": {"iataCode": "ARN", "at": "2026-07-01T08:00:00"},
             "arrival": {"iataCode": "DEL", "at": "2026-07-01T20:00:00"}},
            {"carrierCode": "AI", "number": "105",
             "departure": {"iataCode": "DEL", "at": "2026-07-01T22:00:00"},
             "arrival": {"iataCode": "HYD", "at": "2026-07-02T00:30:00"}},
        ],
        cabin="ECONOMY",
        branded_fare="LIGHT",
        booking_class="L",
        baggage={"quantity": 0},
    )

    mock_amadeus = MagicMock()
    mock_amadeus.shopping.flight_offers_search.get.return_value.data = [ek_offer, ai_offer]

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
    r = results[0]
    assert r["airlines"] == ["EK"]
    assert r["stops"] == 1
    assert r["layover_cities"] == ["DXB"]
    assert r["flight_numbers"] == ["EK 528", "EK 157"]
    assert "2026-06-01T14:30:00" in r["departure_time"]
    assert "2026-06-02T03:00:00" in r["arrival_time"]


def test_get_flight_offers_return_leg_fields():
    mock_amadeus = MagicMock()
    mock_amadeus.shopping.flight_offers_search.get.return_value.data = [_make_offer()]

    with patch('amadeus_client.Client', return_value=mock_amadeus):
        from amadeus_client import AmadeusClient
        client = AmadeusClient("key", "secret")
        results = client.get_flight_offers(
            origin="HYD", destination="ARN",
            departure_date="2026-06-01", return_date="2026-07-01",
            cabin_class="PREMIUM_ECONOMY", airlines=[], max_stops=2
        )

    r = results[0]
    assert r["return_airlines"] == ["EK"]
    assert r["return_stops"] == 1
    assert r["return_layover_cities"] == ["DXB"]
    assert r["return_flight_numbers"] == ["EK 158", "EK 529"]
    assert "2026-07-01T09:00:00" in r["return_departure_time"]
    assert "2026-07-01T23:30:00" in r["return_arrival_time"]
    assert r["return_duration_minutes"] == 780


def test_get_flight_offers_baggage_and_seats():
    mock_amadeus = MagicMock()
    mock_amadeus.shopping.flight_offers_search.get.return_value.data = [
        _make_offer(baggage={"weight": 23, "weightUnit": "KG"}, seats=3),
    ]

    with patch('amadeus_client.Client', return_value=mock_amadeus):
        from amadeus_client import AmadeusClient
        client = AmadeusClient("key", "secret")
        results = client.get_flight_offers(
            origin="HYD", destination="ARN",
            departure_date="2026-06-01", return_date="2026-07-01",
            cabin_class="PREMIUM_ECONOMY", airlines=[], max_stops=2
        )

    r = results[0]
    assert r["baggage"] == "23kg"
    assert r["booking_class"] == "R"
    assert r["seats_remaining"] == 3


def test_parse_baggage_quantity():
    mock_amadeus = MagicMock()
    mock_amadeus.shopping.flight_offers_search.get.return_value.data = [
        _make_offer(baggage={"quantity": 2}),
    ]

    with patch('amadeus_client.Client', return_value=mock_amadeus):
        from amadeus_client import AmadeusClient
        client = AmadeusClient("key", "secret")
        results = client.get_flight_offers(
            origin="HYD", destination="ARN",
            departure_date="2026-06-01", return_date="2026-07-01",
            cabin_class="PREMIUM_ECONOMY", airlines=[], max_stops=2
        )

    assert results[0]["baggage"] == "2PC"


def test_parse_baggage_quantity_and_weight():
    mock_amadeus = MagicMock()
    mock_amadeus.shopping.flight_offers_search.get.return_value.data = [
        _make_offer(baggage={"quantity": 2, "weight": 23, "weightUnit": "KG"}),
    ]

    with patch('amadeus_client.Client', return_value=mock_amadeus):
        from amadeus_client import AmadeusClient
        client = AmadeusClient("key", "secret")
        results = client.get_flight_offers(
            origin="HYD", destination="ARN",
            departure_date="2026-06-01", return_date="2026-07-01",
            cabin_class="PREMIUM_ECONOMY", airlines=[], max_stops=2
        )

    assert results[0]["baggage"] == "2×23kg"


def test_parse_baggage_empty():
    mock_amadeus = MagicMock()
    mock_amadeus.shopping.flight_offers_search.get.return_value.data = [
        _make_offer(baggage={}),
    ]

    with patch('amadeus_client.Client', return_value=mock_amadeus):
        from amadeus_client import AmadeusClient
        client = AmadeusClient("key", "secret")
        results = client.get_flight_offers(
            origin="HYD", destination="ARN",
            departure_date="2026-06-01", return_date="2026-07-01",
            cabin_class="PREMIUM_ECONOMY", airlines=[], max_stops=2
        )

    assert results[0]["baggage"] == ""
