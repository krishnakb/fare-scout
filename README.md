# Fare Scout

Automated flight price tracker that monitors Amadeus for cheap fares and sends Slack alerts.

## Features

- Searches multiple date combinations within your travel window
- Tracks Economy and Premium Economy fares
- Filters by preferred airlines (checks actual operating carrier, not just codeshares)
- Alerts on price drops vs 7-day rolling average
- Rich Slack notifications with route, duration, times, and airlines
- Runs on GCP Cloud Functions with Cloud Scheduler

## Quick Start

### 1. Get API credentials

- **Amadeus**: Sign up at [developers.amadeus.com](https://developers.amadeus.com), create an app, get API key & secret
- **Slack**: Create an [incoming webhook](https://api.slack.com/messaging/webhooks) for your channel

### 2. Store secrets in GCP

```bash
PROJECT_ID="your-project-id"

echo -n "your-amadeus-key" | gcloud secrets create amadeus-api-key --data-file=- --project=$PROJECT_ID
echo -n "your-amadeus-secret" | gcloud secrets create amadeus-api-secret --data-file=- --project=$PROJECT_ID
echo -n "https://hooks.slack.com/..." | gcloud secrets create slack-webhook-url --data-file=- --project=$PROJECT_ID
```

### 3. Create Firestore database

```bash
gcloud firestore databases create --location=nam5 --project=$PROJECT_ID
```

### 4. Add a trip

In [Firestore console](https://console.cloud.google.com/firestore), create `trips` collection with a document:

```json
{
  "label": "Europe Summer Trip",
  "active": true,
  "origins": ["JFK"],
  "destinations": ["LHR"],
  "airlines": ["BA", "AA", "VS"],
  "cabin_classes": ["ECONOMY", "PREMIUM_ECONOMY"],
  "max_stops": 1,
  "departure_date_range": ["2025-06-01", "2025-06-15"],
  "return_date_range": ["2025-06-20", "2025-07-05"],
  "min_trip_days": 14,
  "max_trip_days": 30,
  "scan_window": { "start": "2025-01-01", "end": "2025-05-31" },
  "scan_frequency_days": 1,
  "alert_on_rolling_avg_drop_pct": 10,
  "always_notify": true,
  "currency": "USD"
}
```

### 5. Deploy

```bash
./deploy.sh your-project-id us-central1 America/New_York
```

### 6. Test

```bash
gcloud scheduler jobs run flight-scanner-daily --location=us-central1
```

## Documentation

- [Configuration Reference](docs/CONFIGURATION.md) - All trip fields, API limits, polling recommendations
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and fixes

## Cost

Likely free tier eligible:
- **Amadeus**: 2,000 API calls/month (free test environment)
- **GCP**: Cloud Functions, Firestore, Scheduler all have generous free tiers

