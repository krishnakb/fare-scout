# Configuration Reference

## Trip Document Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `label` | string | Yes | Display name for Slack notifications |
| `active` | boolean | Yes | Set `false` to disable scanning |
| `origins` | string[] | Yes | Departure airports (IATA codes, e.g., `["JFK"]`) |
| `destinations` | string[] | Yes | Arrival airports (IATA codes, e.g., `["LHR"]`) |
| `airlines` | string[] | Yes | Preferred airlines - filters by **operating** carrier |
| `cabin_classes` | string[] | Yes | `ECONOMY`, `PREMIUM_ECONOMY`, `BUSINESS`, `FIRST` |
| `max_stops` | number | Yes | Maximum layovers (0 = direct only) |
| `departure_date_range` | string[] | Yes | `[start, end]` for outbound search (ISO format) |
| `return_date_range` | string[] | Yes | `[start, end]` for return search (ISO format) |
| `min_trip_days` | number | Yes | Minimum trip duration in days |
| `max_trip_days` | number | Yes | Maximum trip duration in days |
| `scan_window` | object | Yes | `{start, end}` - when to run scans |
| `scan_frequency_days` | number | Yes | Days between scans |
| `alert_on_rolling_avg_drop_pct` | number | Yes | Alert if price drops this % below average |
| `always_notify` | boolean | Yes | Send alerts even without price drops |
| `currency` | string | Yes | Price currency (USD, EUR, GBP, INR, etc.) |
| `slack_webhook_url` | string | No | Override default webhook for this trip |

## How Price Alerts Work

The tracker maintains a 7-day rolling average of prices for each route/cabin combination:

1. Each scan stores price observations in Firestore
2. Rolling average = mean of last 7 observations
3. If current price is X% below rolling average, alert triggers
4. Set `alert_on_rolling_avg_drop_pct: 10` to alert on 10%+ drops

**Tip**: Set `always_notify: true` initially to build baseline data, then switch to `false` to only get price drop alerts.

## API Limits & Polling Frequency

### Amadeus Free Tier (Test Environment)

- **2,000 API calls/month**
- Each scan makes ~10 API calls (5 date pairs × 2 cabin classes)
- With daily scans, one trip uses ~300 calls/month

### Recommended Settings

| Trips | `scan_frequency_days` | Monthly API Calls |
|-------|----------------------|-------------------|
| 1     | 1 (daily)            | ~300              |
| 2     | 1 (daily)            | ~600              |
| 5     | 2 (every other day)  | ~750              |
| 10    | 3 (twice weekly)     | ~1,000            |

### Tips to Reduce API Usage

- Start with `scan_frequency_days: 2` or `3`
- Narrow date ranges (fewer combinations searched)
- Use fewer cabin classes
- Set `always_notify: false` after building baseline

### Production API

For higher limits, apply for Amadeus production access. Update secrets with production credentials.

## Multiple Trips

Add multiple documents to the `trips` collection. Each trip:
- Runs independently
- Has its own scan schedule
- Can have different settings
- Can use a different Slack webhook (`slack_webhook_url` field)

## Example Configurations

### Weekend Getaway (Conservative)

```json
{
  "label": "Paris Weekend",
  "active": true,
  "origins": ["JFK"],
  "destinations": ["CDG"],
  "airlines": ["AF", "DL"],
  "cabin_classes": ["ECONOMY"],
  "max_stops": 0,
  "departure_date_range": ["2025-03-14", "2025-03-14"],
  "return_date_range": ["2025-03-16", "2025-03-16"],
  "min_trip_days": 2,
  "max_trip_days": 3,
  "scan_window": { "start": "2025-01-01", "end": "2025-03-01" },
  "scan_frequency_days": 3,
  "alert_on_rolling_avg_drop_pct": 15,
  "always_notify": false,
  "currency": "USD"
}
```

### Flexible Vacation (Comprehensive)

```json
{
  "label": "Japan Fall Trip",
  "active": true,
  "origins": ["LAX", "SFO"],
  "destinations": ["NRT", "HND"],
  "airlines": ["JL", "NH", "UA"],
  "cabin_classes": ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS"],
  "max_stops": 1,
  "departure_date_range": ["2025-10-01", "2025-10-15"],
  "return_date_range": ["2025-10-14", "2025-10-31"],
  "min_trip_days": 10,
  "max_trip_days": 21,
  "scan_window": { "start": "2025-04-01", "end": "2025-09-30" },
  "scan_frequency_days": 1,
  "alert_on_rolling_avg_drop_pct": 10,
  "always_notify": true,
  "currency": "USD"
}
```

## Slack Notification Format

```
✈️ *Europe Summer Trip*
📅 Jun 01-Jun 15 → Jun 20-Jul 05  •  Google Flights

*Economy*
`1` *$850* ECONOMY `BA` ⬇️12%
    JFK→LHR • 7h30m • Jun 05 18:00→06:30+1

*Premium Economy*
`1` *$1,450* PREMIUM `BA`
    JFK→LHR • 7h30m • Jun 05 18:00→06:30+1

💰 PE premium: $600 (+71%)
────────────────────────────────────
```

## Airline Codes

The `airlines` filter checks the **operating carrier**, not the marketing/codeshare carrier. Common codes:

| Code | Airline |
|------|---------|
| AA | American Airlines |
| BA | British Airways |
| DL | Delta |
| UA | United |
| LH | Lufthansa |
| AF | Air France |
| EK | Emirates |
| SQ | Singapore Airlines |
| JL | Japan Airlines |
| NH | ANA |

Full list: [IATA Airline Codes](https://www.iata.org/en/publications/directories/code-search/)
