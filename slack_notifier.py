import requests
from datetime import datetime
from urllib.parse import urlencode


class SlackNotifier:
    CURRENCY_SYMBOLS = {"INR": "₹", "SEK": "kr", "USD": "$", "EUR": "€"}

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def format_message(
        self,
        trip_label: str,
        origin: str,
        destination: str,
        results: dict[str, list[dict]],
        currency: str,
        departure_range: tuple[str, str] | None = None,
        return_range: tuple[str, str] | None = None
    ) -> str:
        """Format flight results for Slack."""
        lines = [f"✈️ *{trip_label}*"]

        # Search context header
        if departure_range and return_range:
            dep_str = f"{self._format_date_short(departure_range[0])}-{self._format_date_short(departure_range[1])}"
            ret_str = f"{self._format_date_short(return_range[0])}-{self._format_date_short(return_range[1])}"
            gf_url = self._google_flights_url(origin, destination, departure_range[0], return_range[0])
            lines.append(f"📅 {dep_str} → {ret_str}  •  <{gf_url}|Google Flights>")

        lines.append("")

        pe_best = results.get("PREMIUM_ECONOMY", [{}])[0].get("price")
        eco_best = results.get("ECONOMY", [{}])[0].get("price")

        for cabin, offers in results.items():
            if not offers:
                continue

            cabin_label = "Premium Economy" if cabin == "PREMIUM_ECONOMY" else "Economy"
            lines.append(f"*{cabin_label}*")

            for i, offer in enumerate(offers[:3], 1):
                offer_currency = offer.get("currency", currency)
                offer_symbol = self.CURRENCY_SYMBOLS.get(offer_currency, offer_currency + " ")
                price_str = f"{offer_symbol}{offer['price']:,.0f}"
                drop = offer.get("drop_pct")
                drop_str = f" ⬇️{drop}%" if drop else ""

                # Route with layovers
                route = self._format_route(origin, destination, offer.get("layover_cities", []))

                # Duration
                duration = self._format_duration(offer.get("duration_minutes", 0))

                # Times (compact)
                times = self._format_times_compact(offer.get("departure_time"), offer.get("arrival_time"))

                # Airlines (show all carriers)
                carriers = offer.get("airlines", [offer.get("airline", "")])
                if isinstance(carriers, str):
                    carriers = [carriers]
                airline_str = "/".join(carriers) if carriers else ""

                # Line 1: price, fare, [airlines], drop
                lines.append(f"`{i}` *{price_str}* {offer['fare_family']} `{airline_str}`{drop_str}")

                # Line 2: route • duration • times
                details = [route]
                if duration:
                    details.append(duration)
                if times:
                    details.append(times)
                lines.append(f"    {' • '.join(details)}")

            lines.append("")

        if pe_best and eco_best:
            eco_currency = results.get("ECONOMY", [{}])[0].get("currency", currency)
            eco_symbol = self.CURRENCY_SYMBOLS.get(eco_currency, eco_currency + " ")
            premium = pe_best - eco_best
            pct = (premium / eco_best) * 100
            lines.append(f"💰 PE premium: {eco_symbol}{premium:,.0f} (+{pct:.0f}%)")

        lines.append("─" * 36)

        return "\n".join(lines)

    def _format_route(self, origin: str, dest: str, layovers: list[str]) -> str:
        """Format route with layover cities: JFK → LHR → CDG"""
        parts = [origin] + layovers + [dest]
        return "→".join(parts)

    def _format_duration(self, minutes: int) -> str:
        """Format duration: 750 -> 12h30m"""
        if not minutes:
            return ""
        h, m = divmod(minutes, 60)
        return f"{h}h{m:02d}m"

    def _format_times_compact(self, dep: str | None, arr: str | None) -> str:
        """Format times compactly: May 22 14:30→08:45+1"""
        if not dep or not arr:
            return ""
        try:
            dep_dt = datetime.fromisoformat(dep.replace("Z", "+00:00"))
            arr_dt = datetime.fromisoformat(arr.replace("Z", "+00:00"))
            dep_str = dep_dt.strftime("%b %d %H:%M")
            arr_str = arr_dt.strftime("%H:%M")
            day_diff = (arr_dt.date() - dep_dt.date()).days
            if day_diff > 0:
                arr_str += f"+{day_diff}"
            return f"{dep_str}→{arr_str}"
        except (ValueError, AttributeError):
            return ""

    def _format_date_short(self, date_str: str) -> str:
        """Format date: 2025-06-15 -> Jun 15"""
        try:
            dt = datetime.fromisoformat(date_str)
            return dt.strftime("%b %d")
        except ValueError:
            return date_str

    def _google_flights_url(self, origin: str, dest: str, dep_date: str, ret_date: str) -> str:
        """Generate Google Flights search URL."""
        base = "https://www.google.com/travel/flights"
        params = {
            "q": f"flights from {origin} to {dest} on {dep_date} return {ret_date}"
        }
        return f"{base}?{urlencode(params)}"

    def send(self, message: str) -> bool:
        """Send message to Slack webhook."""
        response = requests.post(
            self.webhook_url,
            json={"text": message, "mrkdwn": True},
            timeout=10
        )
        return response.status_code == 200
