import pytest


def _make_offer(**overrides):
    """Build a complete offer dict with all fields for Slack tests."""
    base = {
        "price": 85000,
        "fare_family": "Basic",
        "departure_date": "2026-06-01",
        "return_date": "2026-07-01",
        "airlines": ["EK"],
        "stops": 1,
        "drop_pct": None,
        "layover_cities": ["DXB"],
        "flight_numbers": ["EK 528", "EK 157"],
        "departure_time": "2026-06-01T14:30:00",
        "arrival_time": "2026-06-02T03:00:00",
        "duration_minutes": 750,
        "return_layover_cities": ["DXB"],
        "return_flight_numbers": ["EK 158", "EK 529"],
        "return_departure_time": "2026-07-01T09:00:00",
        "return_arrival_time": "2026-07-01T23:30:00",
        "return_duration_minutes": 870,
        "baggage": "23kg",
        "booking_class": "R",
        "seats_remaining": 3,
    }
    base.update(overrides)
    return base


def test_format_message_includes_top_3_per_cabin():
    from slack_notifier import SlackNotifier
    notifier = SlackNotifier("https://hooks.slack.com/test")

    results = {
        "PREMIUM_ECONOMY": [
            _make_offer(price=85000, fare_family="Basic", drop_pct=12),
            _make_offer(price=92000, fare_family="Classic"),
            _make_offer(price=98000, fare_family="Flex"),
            _make_offer(price=105000, fare_family="Full"),
            _make_offer(price=110000, fare_family="Plus"),
            _make_offer(price=120000, fare_family="Max"),
        ],
        "ECONOMY": [
            _make_offer(price=52000, fare_family="Light"),
        ]
    }

    message = notifier.format_message("Sweden Summer 2026", "HYD", "ARN", results, "INR")

    assert "Sweden Summer 2026" in message
    assert "85,000" in message  # Top PE price formatted
    assert "12%" in message  # Drop indicator
    assert "110,000" in message  # 5th option included
    assert "120,000" not in message  # 6th option excluded
    assert "52,000" in message  # Economy price
    assert "PE premium" in message


def test_format_message_with_full_itinerary():
    from slack_notifier import SlackNotifier
    notifier = SlackNotifier("https://hooks.slack.com/test")

    results = {
        "ECONOMY": [
            _make_offer(
                price=58500, fare_family="ECOSAVER", drop_pct=8,
                departure_time="2026-05-22T14:30:00",
                arrival_time="2026-05-23T08:45:00",
                return_departure_time="2026-06-25T09:00:00",
                return_arrival_time="2026-06-25T23:30:00",
                return_duration_minutes=870,
                seats_remaining=3,
                baggage="23kg",
                booking_class="E",
            ),
        ]
    }

    message = notifier.format_message(
        "Sweden Summer 2026", "HYD", "ARN", results, "INR",
        departure_range=("2026-05-22", "2026-05-31"),
        return_range=("2026-06-25", "2026-07-10")
    )

    # Header
    assert "May 22-May 31" in message
    assert "Jun 25-Jul 10" in message
    assert "Google Flights" in message

    # Line 1: price, fare, airline, drop, seats
    assert "58,500" in message
    assert "ECOSAVER" in message
    assert "⬇️8%" in message
    assert "[3 seats]" in message

    # Line 2: outbound with ✈ prefix + flight numbers
    assert "✈ HYD→DXB→ARN" in message
    assert "12h30m" in message
    assert "EK 528/EK 157" in message
    assert "May 22 14:30→08:45+1" in message

    # Line 3: return with ↩ prefix
    assert "↩ ARN→DXB→HYD" in message
    assert "EK 158/EK 529" in message
    assert "Jun 25 09:00→23:30" in message

    # Line 4: fare details
    assert "🧳 23kg" in message
    assert "Class: E" in message


def test_format_message_handles_empty_cabin_offers():
    from slack_notifier import SlackNotifier
    notifier = SlackNotifier("https://hooks.slack.com/test")

    results = {
        "ECONOMY": [_make_offer(price=52000, fare_family="Light")],
        "PREMIUM_ECONOMY": [],
    }

    message = notifier.format_message("Sweden Summer 2026", "HYD", "ARN", results, "INR")

    assert "52,000" in message
    assert "PE premium" not in message


def test_format_message_missing_optional_fields():
    """Backward compat: offers without return/baggage/seats still render."""
    from slack_notifier import SlackNotifier
    notifier = SlackNotifier("https://hooks.slack.com/test")

    minimal_offer = {
        "price": 60000,
        "fare_family": "Light",
        "departure_date": "2026-06-01",
        "return_date": "2026-07-01",
        "airline": "EK",
        "stops": 1,
        "drop_pct": None,
    }

    results = {"ECONOMY": [minimal_offer]}
    message = notifier.format_message("Test Trip", "HYD", "ARN", results, "INR")

    assert "60,000" in message
    assert "Light" in message
    # No return leg or fare details lines
    assert "↩" not in message
    assert "🧳" not in message
    assert "[" not in message  # No seats bracket
