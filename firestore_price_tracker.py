# price_tracker.py
from datetime import datetime, timezone


class PriceTracker:
    def __init__(self, firestore_client):
        self.db = firestore_client

    def store_prices(self, trip_id: str, route: str, prices: list[dict]) -> None:
        """Store price observations in Firestore."""
        collection = self.db.collection("price_history")
        scanned_at = datetime.now(timezone.utc)

        for price in prices:
            doc = {
                "trip_id": trip_id,
                "scanned_at": scanned_at,
                "route": route,
                **price
            }
            collection.add(doc)

    def get_rolling_average(self, trip_id: str, route: str, cabin_class: str) -> float | None:
        """Calculate rolling average from last 7 scans."""
        query = (
            self.db.collection("price_history")
            .where("trip_id", "==", trip_id)
            .where("route", "==", route)
            .where("cabin_class", "==", cabin_class)
            .order_by("scanned_at", direction="DESCENDING")
            .limit(7)
        )

        prices = [doc.to_dict()["price"] for doc in query.stream()]

        if not prices:
            return None

        return sum(prices) / len(prices)
