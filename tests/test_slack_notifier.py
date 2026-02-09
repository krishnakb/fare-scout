import pytest


def test_format_message_includes_top_3_per_cabin():
    from slack_notifier import SlackNotifier
    notifier = SlackNotifier("https://hooks.slack.com/test")

    results = {
        "PREMIUM_ECONOMY": [
            {"price": 85000, "fare_family": "Basic", "departure_date": "2026-06-01",
             "return_date": "2026-07-01", "airline": "EK", "stops": 1, "drop_pct": 12},
            {"price": 92000, "fare_family": "Classic", "departure_date": "2026-06-02",
             "return_date": "2026-07-02", "airline": "LH", "stops": 1, "drop_pct": None},
            {"price": 98000, "fare_family": "Flex", "departure_date": "2026-06-03",
             "return_date": "2026-07-03", "airline": "KL", "stops": 1, "drop_pct": None},
            {"price": 105000, "fare_family": "Full", "departure_date": "2026-06-04",
             "return_date": "2026-07-04", "airline": "EK", "stops": 1, "drop_pct": None},
        ],
        "ECONOMY": [
            {"price": 52000, "fare_family": "Light", "departure_date": "2026-06-01",
             "return_date": "2026-07-01", "airline": "EK", "stops": 1, "drop_pct": None},
        ]
    }

    message = notifier.format_message("Sweden Summer 2026", "HYD", "ARN", results, "INR")

    assert "Sweden Summer 2026" in message
    assert "85,000" in message  # Top PE price formatted
    assert "12%" in message  # Drop indicator
    assert "105,000" not in message  # 4th option excluded
    assert "52,000" in message  # Economy price
    assert "PE premium" in message


def test_format_message_with_date_ranges_and_route_details():
    from slack_notifier import SlackNotifier
    notifier = SlackNotifier("https://hooks.slack.com/test")

    results = {
        "ECONOMY": [
            {
                "price": 58500, "fare_family": "ECOSAVER", "departure_date": "2026-05-22",
                "return_date": "2026-06-25", "airline": "EK", "stops": 1, "drop_pct": 8,
                "layover_cities": ["DXB"],
                "flight_numbers": ["EK 528", "EK 157"],
                "departure_time": "2026-05-22T14:30:00",
                "arrival_time": "2026-05-23T08:45:00",
                "duration_minutes": 750
            },
        ]
    }

    message = notifier.format_message(
        "Sweden Summer 2026", "HYD", "ARN", results, "INR",
        departure_range=("2026-05-22", "2026-05-31"),
        return_range=("2026-06-25", "2026-07-10")
    )

    assert "May 22-May 31" in message  # Departure range
    assert "Jun 25-Jul 10" in message  # Return range
    assert "HYD→DXB→ARN" in message  # Route with layover (compact)
    assert "12h30m" in message  # Duration (compact)
    assert "May 22 14:30→08:45+1" in message  # Times with +1 day
    assert "Google Flights" in message  # GF link text
    assert "google.com/travel/flights" in message  # GF link URL
