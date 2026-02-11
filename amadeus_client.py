import re
from amadeus import Client


def _validate_iata(code: str, field_name: str) -> None:
    """Validate IATA airport code (3 uppercase letters)."""
    if not re.match(r'^[A-Z]{3}$', code):
        raise ValueError(f"Invalid {field_name}: {code!r} (expected 3-letter IATA code)")


class AmadeusClient:
    def __init__(self, api_key: str, api_secret: str):
        self.client = Client(client_id=api_key, client_secret=api_secret)

    def get_cheapest_dates(
        self,
        origin: str,
        destination: str,
        departure_range: tuple[str, str],
        return_range: tuple[str, str]
    ) -> list[dict]:
        """Get cheapest flight dates for route."""
        _validate_iata(origin, "origin")
        _validate_iata(destination, "destination")
        response = self.client.shopping.flight_dates.get(
            origin=origin,
            destination=destination,
            departureDate=departure_range[0],
            oneWay=False
        )

        results = []
        for item in response.data:
            results.append({
                "departure_date": item["departureDate"],
                "return_date": item["returnDate"],
                "price": float(item["price"]["total"])
            })

        return sorted(results, key=lambda x: x["price"])

    def get_flight_offers(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
        cabin_class: str,
        airlines: list[str],
        max_stops: int,
        currency: str = "EUR"
    ) -> list[dict]:
        """Get detailed flight offers for specific dates."""
        _validate_iata(origin, "origin")
        _validate_iata(destination, "destination")
        response = self.client.shopping.flight_offers_search.get(
            originLocationCode=origin,
            destinationLocationCode=destination,
            departureDate=departure_date,
            returnDate=return_date,
            adults=1,
            travelClass=cabin_class,
            currencyCode=currency,
            max=20
        )

        results = []
        for offer in response.data:
            outbound = self._parse_itinerary(offer["itineraries"][0])

            # Filter: ALL operating carriers must be in allowed list
            if airlines and not all(c in airlines for c in outbound["airlines"]):
                continue
            if outbound["stops"] > max_stops:
                continue

            fare_segments = offer["travelerPricings"][0]["fareDetailsBySegment"]
            fare_info = fare_segments[0]

            result = {
                "offer_id": offer["id"],
                "price": float(offer["price"]["total"]),
                "currency": offer["price"]["currency"],
                "departure_date": departure_date,
                "return_date": return_date,
                "airlines": outbound["airlines"],
                "stops": outbound["stops"],
                "cabin_class": fare_info["cabin"],
                "fare_family": fare_info.get("brandedFare", "Standard"),
                "duration_minutes": outbound["duration_minutes"],
                "layover_cities": outbound["layover_cities"],
                "flight_numbers": outbound["flight_numbers"],
                "departure_time": outbound["departure_time"],
                "arrival_time": outbound["arrival_time"],
                "booking_class": fare_info.get("class", ""),
                "baggage": self._parse_baggage(fare_info),
                "seats_remaining": int(offer.get("numberOfBookableSeats", 0)),
            }

            # Return leg (round-trip)
            if len(offer["itineraries"]) > 1:
                ret = self._parse_itinerary(offer["itineraries"][1])
                result["return_airlines"] = ret["airlines"]
                result["return_stops"] = ret["stops"]
                result["return_duration_minutes"] = ret["duration_minutes"]
                result["return_layover_cities"] = ret["layover_cities"]
                result["return_flight_numbers"] = ret["flight_numbers"]
                result["return_departure_time"] = ret["departure_time"]
                result["return_arrival_time"] = ret["arrival_time"]

            results.append(result)

        return sorted(results, key=lambda x: x["price"])

    def _parse_itinerary(self, itinerary: dict) -> dict:
        """Parse a single itinerary into structured fields."""
        segments = itinerary["segments"]
        operating_carriers = list(dict.fromkeys(
            self._get_operating_carrier(seg) for seg in segments
        ))
        return {
            "airlines": operating_carriers,
            "stops": len(segments) - 1,
            "layover_cities": [seg["arrival"]["iataCode"] for seg in segments[:-1]],
            "flight_numbers": [
                f"{seg['carrierCode']} {seg.get('number', '')}"
                for seg in segments
            ],
            "departure_time": segments[0]["departure"]["at"],
            "arrival_time": segments[-1]["arrival"]["at"],
            "duration_minutes": self._parse_duration(itinerary["duration"]),
        }

    def _get_operating_carrier(self, seg: dict) -> str:
        """Get operating carrier, falling back to marketing carrier."""
        op = seg.get("operating", {}).get("carrierCode")
        return op if op else seg["carrierCode"]

    def _parse_baggage(self, fare_info: dict) -> str:
        """Parse baggage allowance: '2×23kg', '23kg', '2PC', or ''."""
        bags = fare_info.get("includedCheckedBags", {})
        weight = bags.get("weight")
        unit = bags.get("weightUnit", "KG").lower()
        qty = bags.get("quantity")
        if qty and weight:
            return f"{qty}×{weight}{unit}"
        if weight:
            return f"{weight}{unit}"
        if qty:
            return f"{qty}PC"
        return ""

    def _parse_duration(self, duration: str) -> int:
        """Parse ISO 8601 duration to minutes. PT12H30M -> 750"""
        hours = re.search(r'(\d+)H', duration)
        minutes = re.search(r'(\d+)M', duration)
        total = 0
        if hours:
            total += int(hours.group(1)) * 60
        if minutes:
            total += int(minutes.group(1))
        return total
