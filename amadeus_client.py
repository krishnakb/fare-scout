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
            outbound = offer["itineraries"][0]
            segments = outbound["segments"]
            stops = len(segments) - 1

            # Get all unique carriers - check OPERATING carrier (actual plane)
            # Falls back to marketing carrier if no operating info
            def get_operating_carrier(seg):
                op = seg.get("operating", {}).get("carrierCode")
                return op if op else seg["carrierCode"]

            operating_carriers = list(dict.fromkeys(
                get_operating_carrier(seg) for seg in segments
            ))
            marketing_carriers = list(dict.fromkeys(
                seg["carrierCode"] for seg in segments
            ))

            # Filter: ALL operating carriers must be in allowed list
            if airlines and not all(c in airlines for c in operating_carriers):
                continue
            if stops > max_stops:
                continue

            fare_info = offer["travelerPricings"][0]["fareDetailsBySegment"][0]

            # Extract route details
            layover_cities = [seg["arrival"]["iataCode"] for seg in segments[:-1]]
            flight_numbers = [
                f"{seg['carrierCode']} {seg.get('number', '')}"
                for seg in segments
            ]
            dep_time = segments[0]["departure"]["at"]
            arr_time = segments[-1]["arrival"]["at"]

            results.append({
                "offer_id": offer["id"],
                "price": float(offer["price"]["total"]),
                "currency": offer["price"]["currency"],
                "departure_date": departure_date,
                "return_date": return_date,
                "airlines": operating_carriers,
                "stops": stops,
                "cabin_class": fare_info["cabin"],
                "fare_family": fare_info.get("brandedFare", "Standard"),
                "duration_minutes": self._parse_duration(outbound["duration"]),
                "layover_cities": layover_cities,
                "flight_numbers": flight_numbers,
                "departure_time": dep_time,
                "arrival_time": arr_time,
            })

        return sorted(results, key=lambda x: x["price"])

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
