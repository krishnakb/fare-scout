#!/bin/bash
# deploy.sh - Deploy flight tracker to GCP
#
# Usage: ./deploy.sh PROJECT_ID [REGION] [TIMEZONE]
#
# Arguments:
#   PROJECT_ID  Your GCP project ID (required)
#   REGION      GCP region for deployment (default: europe-west1)
#               Examples: us-central1, us-east1, europe-west1, asia-south1
#               Full list: https://cloud.google.com/functions/docs/locations
#   TIMEZONE    Timezone for scheduler (default: UTC)
#               Examples: America/New_York, Europe/London, Asia/Tokyo
#               Full list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

set -e

PROJECT_ID="${1:?Usage: ./deploy.sh PROJECT_ID [REGION] [TIMEZONE]}"
REGION="${2:-europe-west1}"
TIMEZONE="${3:-UTC}"

echo "Deploying to project: $PROJECT_ID"

# Enable APIs
gcloud services enable \
  cloudfunctions.googleapis.com \
  cloudscheduler.googleapis.com \
  firestore.googleapis.com \
  secretmanager.googleapis.com \
  --project=$PROJECT_ID

# Deploy Cloud Function
gcloud functions deploy flight-price-tracker \
  --gen2 \
  --runtime=python312 \
  --region=$REGION \
  --trigger-http \
  --no-allow-unauthenticated \
  --entry-point=check_flights \
  --memory=256MB \
  --timeout=300s \
  --project=$PROJECT_ID

# Get function URL
FUNCTION_URL=$(gcloud functions describe flight-price-tracker \
  --region=$REGION \
  --format='value(serviceConfig.uri)' \
  --project=$PROJECT_ID)

echo "Function deployed at: $FUNCTION_URL"

# Create/update scheduler job
gcloud scheduler jobs delete flight-scanner-daily \
  --location=$REGION \
  --project=$PROJECT_ID \
  --quiet 2>/dev/null || true

gcloud scheduler jobs create http flight-scanner-daily \
  --location=$REGION \
  --schedule="0 8 * * *" \
  --time-zone="$TIMEZONE" \
  --uri="$FUNCTION_URL" \
  --oidc-service-account-email="${PROJECT_ID}@appspot.gserviceaccount.com" \
  --project=$PROJECT_ID

echo "Scheduler job created: daily at 8am IST"
echo "Done!"
