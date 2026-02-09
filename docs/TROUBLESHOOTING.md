# Troubleshooting

## Manual Run Skipped

**Symptom**: Logs show `Skipping trip-id: should_scan=False`

**Cause**: The trip was already scanned today (respects `scan_frequency_days`).

**Fix**: Reset `last_scanned` in Firestore:
1. Go to [Firestore console](https://console.cloud.google.com/firestore)
2. Navigate to `trips` > your trip document
3. Delete the `last_scanned` field or set it to yesterday

## No Slack Notification

**Check 1**: View function logs
```bash
gcloud functions logs read flight-price-tracker --region=REGION --limit=30
```

Look for:
- `Slack notification sent: True/False`
- Any error messages

**Check 2**: Verify `always_notify`

If `always_notify: false`, notifications only send on price drops. Set to `true` for testing.

**Check 3**: Webhook URL

Verify the webhook URL in Secret Manager:
```bash
gcloud secrets versions access latest --secret=slack-webhook-url --project=PROJECT_ID
```

**Check 4**: Trip is active

Ensure `active: true` in your trip document.

## No Flights Found

**Check 1**: Airline codes

The filter uses **operating carriers**, not codeshares. A flight marketed as "LH" might be operated by a partner airline.

Add more airlines to your list or temporarily remove the filter by setting `airlines: []`.

**Check 2**: Max stops

Setting `max_stops: 0` (direct only) significantly limits results. Try `max_stops: 1`.

**Check 3**: Date ranges

Ensure dates are in the future and within a bookable window (typically 330 days).

**Check 4**: IATA codes

Airport codes must be exactly 3 uppercase letters. Verify codes at [IATA Search](https://www.iata.org/en/publications/directories/code-search/).

## Function Timeout

**Symptom**: Function exceeds 300s timeout.

**Fixes**:
- Narrow date ranges (fewer combinations)
- Reduce cabin classes
- Split into multiple trip documents
- Increase timeout in `deploy.sh` (max 540s for gen2)

## Amadeus API Errors

**401 Unauthorized**: Check API credentials in Secret Manager.

**429 Too Many Requests**: You've hit the rate limit. Increase `scan_frequency_days`.

**500 Server Error**: Amadeus temporary issue. Will retry on next scheduled run.

## Cloud Function Not Triggering

**Check scheduler job**:
```bash
gcloud scheduler jobs describe flight-scanner-daily --location=REGION
```

**Check job history**:
```bash
gcloud scheduler jobs list --location=REGION
```

**Manual trigger**:
```bash
gcloud scheduler jobs run flight-scanner-daily --location=REGION
```

## Missing Required Fields

**Symptom**: Logs show `Skipping trip-id: missing required field 'X'`

**Fix**: Ensure your trip document has all required fields. See [Configuration Reference](CONFIGURATION.md).

## Price History Not Building

Check Firestore `price_history` collection for documents. Each scan should add entries.

If empty:
1. Check logs for API errors
2. Verify the scan is running (not skipped)
3. Confirm flights are found (not filtered out)

## Pause Scanning

Temporarily stop all scans:
```bash
gcloud scheduler jobs pause flight-scanner-daily --location=REGION
```

Resume:
```bash
gcloud scheduler jobs resume flight-scanner-daily --location=REGION
```

Or set `active: false` on individual trips in Firestore.

## View All Logs

```bash
# Recent logs
gcloud functions logs read flight-price-tracker --region=REGION --limit=50

# Logs from specific time
gcloud functions logs read flight-price-tracker --region=REGION --start-time="2025-01-15T00:00:00Z"

# Follow live logs
gcloud functions logs read flight-price-tracker --region=REGION --limit=10 --follow
```

## Delete Price History

To reset rolling averages, delete documents from `price_history` collection in Firestore console.

**Warning**: This resets all baseline data. Price drop alerts won't work until new data accumulates.
