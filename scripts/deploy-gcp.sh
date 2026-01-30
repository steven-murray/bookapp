#!/bin/bash

# Simplified Google Cloud Run Deployment Script
# Run this after you've enabled billing and set up permissions

# Configuration
PROJECT_ID="bookapp-for-kids"
SERVICE_NAME="bookapp"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Generate a secure secret key
SECRET_KEY=$(openssl rand -base64 32)

# Supabase connection string
DATABASE_URL="postgresql://postgres:1C1UfWgAViKjxScW@db.wwwelxzsgmrjxzciyvnu.supabase.co:5432/postgres"

echo "=== Deploying Flask Book Tracker to Cloud Run ==="
echo "Project: $PROJECT_ID"
echo "Service: $SERVICE_NAME"
echo ""

# Set the project
gcloud config set project $PROJECT_ID

# Build the container image
echo ""
echo "Building container image..."
gcloud builds submit --tag $IMAGE_NAME

if [ $? -ne 0 ]; then
    echo "Build failed! Check errors above."
    exit 1
fi

# Deploy to Cloud Run
echo ""
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --set-env-vars "SECRET_KEY=${SECRET_KEY}" \
  --set-env-vars "DATABASE_URL=${DATABASE_URL}"

if [ $? -eq 0 ]; then
    echo ""
    echo "=== Deployment Complete! ==="
    echo ""
    echo "Get your service URL:"
    echo "gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)'"
else
    echo ""
    echo "Deployment failed! Check errors above."
fi
