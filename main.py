# main.py
import functions_framework
from google.cloud import firestore, secretmanager
from datetime import datetime, timezone, timedelta

from amadeus_client import AmadeusClient
from firestore_price_tracker import PriceTracker
from slack_notifier import SlackNotifier


def get_secret(project_id: str, secret_id: str) -> str:
    """Fetch secret from Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


REQUIRED_TRIP_FIELDS = [
    "origins", "destinations", "airlines", "cabin_classes",
    "departure_date_range", "return_date_range", "min_trip_days",
    "max_trip_days", "scan_window", "scan_frequency_days",
    "alert_on_rolling_avg_drop_pct", "currency"
]


def validate_trip(trip: dict, trip_id: str) -> bool:
    """Validate trip has required fields. Returns False if invalid."""
    for field in REQUIRED_TRIP_FIELDS:
        if field not in trip:
            print(f"Skipping {trip_id}: missing required field '{field}'")
            return False
    return True


def should_scan(trip: dict) -> bool:
    """Check if trip should be scanned today."""
    today = datetime.now(timezone.utc).date()

    # Check scan window
    window_start = datetime.fromisoformat(trip["scan_window"]["start"]).date()
    window_end = datetime.fromisoformat(trip["scan_window"]["end"]).date()
    if not (window_start <= today <= window_end):
        return False

    # Check scan frequency
    last_scanned = trip.get("last_scanned")
    if last_scanned:
        if hasattr(last_scanned, 'date'):
            last_date = last_scanned.date()
        else:
            last_date = datetime.fromisoformat(str(last_scanned)).date()
        days_since = (today - last_date).days
        if days_since < trip["scan_frequency_days"]:
            return False

    return True


def generate_date_pairs(dep_range: list, ret_range: list, min_days: int, max_days: int, max_pairs: int = 5) -> list:
    """Generate departure/return date pairs within constraints."""
    dep_start = datetime.fromisoformat(dep_range[0]).date()
    dep_end = datetime.fromisoformat(dep_range[1]).date()
    ret_start = datetime.fromisoformat(ret_range[0]).date()
    ret_end = datetime.fromisoformat(ret_range[1]).date()

    pairs = []
    dep_date = dep_start
    while dep_date <= dep_end:
        ret_date = ret_start
        while ret_date <= ret_end:
            days = (ret_date - dep_date).days
            if min_days <= days <= max_days:
                pairs.append((dep_date.isoformat(), ret_date.isoformat()))
            ret_date += timedelta(days=2)  # Sample every 2 days
        dep_date += timedelta(days=2)  # Sample every 2 days

    # Return evenly spaced sample
    if len(pairs) <= max_pairs:
        return pairs
    step = len(pairs) // max_pairs
    return [pairs[i * step] for i in range(max_pairs)]


def calculate_drop_pct(price: float, rolling_avg: float | None, threshold_pct: int) -> int | None:
    """Calculate drop percentage if significant."""
    if rolling_avg is None:
        return None
    drop = ((rolling_avg - price) / rolling_avg) * 100
    return int(drop) if drop >= threshold_pct else None


@functions_framework.http
def check_flights(request):
    """Main Cloud Function entry point."""
    import os
    project_id = os.environ.get("GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")

    # Get secrets
    amadeus_key = get_secret(project_id, "amadeus-api-key")
    amadeus_secret = get_secret(project_id, "amadeus-api-secret")
    default_slack_webhook = get_secret(project_id, "slack-webhook-url")

    # Initialize clients
    db = firestore.Client()
    amadeus = AmadeusClient(amadeus_key, amadeus_secret)
    tracker = PriceTracker(db)

    # Get active trips
    trips = db.collection("trips").where("active", "==", True).stream()

    for trip_doc in trips:
        trip = trip_doc.to_dict()
        trip_id = trip_doc.id
        print(f"Processing trip: {trip_id} ({trip.get('label', 'no label')})")

        if not validate_trip(trip, trip_id):
            continue

        if not should_scan(trip):
            print(f"Skipping {trip_id}: should_scan=False")
            continue

        # Use trip-specific webhook if set, otherwise default
        webhook_url = trip.get("slack_webhook_url") or default_slack_webhook
        notifier = SlackNotifier(webhook_url)

        origin = trip["origins"][0]
        destination = trip["destinations"][0]
        route = f"{origin}-{destination}"

        # Generate date pairs to search
        date_pairs = generate_date_pairs(
            trip["departure_date_range"],
            trip["return_date_range"],
            trip["min_trip_days"],
            trip["max_trip_days"],
            max_pairs=5
        )

        all_results = {}

        for cabin_class in trip["cabin_classes"]:
            offers = []
            for dep_date, ret_date in date_pairs:
                try:
                    flight_offers = amadeus.get_flight_offers(
                        origin=origin,
                        destination=destination,
                        departure_date=dep_date,
                        return_date=ret_date,
                        cabin_class=cabin_class,
                        airlines=trip["airlines"],
                        max_stops=trip["max_stops"],
                        currency=trip["currency"]
                    )
                    offers.extend(flight_offers)
                except Exception as e:
                    # Log error type only, not full details (security)
                    print(f"Error fetching {dep_date}-{ret_date}: {type(e).__name__}")
                    continue

            # Store prices
            if offers:
                tracker.store_prices(trip_id, route, offers)

            # Calculate drops
            rolling_avg = tracker.get_rolling_average(trip_id, route, cabin_class)
            for offer in offers:
                offer["drop_pct"] = calculate_drop_pct(
                    offer["price"],
                    rolling_avg,
                    trip["alert_on_rolling_avg_drop_pct"]
                )

            all_results[cabin_class] = sorted(offers, key=lambda x: x["price"])
            print(f"  {cabin_class}: {len(offers)} offers found")

        # Send notification
        total_offers = sum(len(o) for o in all_results.values())
        print(f"Total offers: {total_offers}, always_notify: {trip.get('always_notify')}")

        if trip["always_notify"] or any(
            offer.get("drop_pct") for cabin_offers in all_results.values() for offer in cabin_offers
        ):
            message = notifier.format_message(
                trip["label"], origin, destination, all_results, trip["currency"],
                departure_range=tuple(trip["departure_date_range"]),
                return_range=tuple(trip["return_date_range"])
            )
            success = notifier.send(message)
            print(f"Slack notification sent: {success}")
        else:
            print("No notification: no drops and always_notify=False")

        # Update last_scanned
        db.collection("trips").document(trip_id).update({
            "last_scanned": datetime.now(timezone.utc)
        })

    return "OK"
