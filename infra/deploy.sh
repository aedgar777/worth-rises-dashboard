#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${1:?Usage: ./deploy.sh PROJECT_ID}"
REGION="${2:-us-central1}"
INSTANCE="worth-rises-db"

echo "==> Enabling APIs..."
gcloud services enable sqladmin.googleapis.com run.googleapis.com \
  artifactregistry.googleapis.com cloudbuild.googleapis.com \
  secretmanager.googleapis.com --project="$PROJECT_ID"

echo "==> Building backend..."
gcloud builds submit backend \
  --tag "${REGION}-docker.pkg.dev/${PROJECT_ID}/worth-rises/api:latest" \
  --project="$PROJECT_ID"

echo "==> Building frontend..."
gcloud builds submit frontend \
  --tag "${REGION}-docker.pkg.dev/${PROJECT_ID}/worth-rises/web:latest" \
  --project="$PROJECT_ID" \
  --substitutions=_VITE_API_URL="https://worth-rises-api-${REGION}.run.app"

echo "Deploy scripts prepared. See docs/GCP_DEPLOYMENT.md for full Cloud SQL + Cloud Run commands."
