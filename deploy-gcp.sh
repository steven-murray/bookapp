#!/bin/bash

# Google Cloud Run Deployment Script
# Prerequisites: gcloud CLI installed and authenticated

# Configuration
PROJECT_ID="YOUR_PROJECT_ID"  # Replace with your GCP project ID
SERVICE_NAME="bookapp"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Generate a secure secret key (or use your own)
SECRET_KEY=$(openssl rand -base64 32)

# Supabase connection string - Replace with your actual Supabase database URL
# Get this from: Supabase Dashboard -> Project Settings -> Database -> Connection string (URI)
# Example: postgresql://postgres.xxxxx:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres
DATABASE_URL="postgresql://postgres.xxxxx:YOUR_PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres"

echo "=== Building and Deploying Flask Book Tracker to Cloud Run ==="
echo "Project ID: $PROJECT_ID"
echo "Service Name: $SERVICE_NAME"
echo "Region: $REGION"
echo ""

# Set the project
echo "Setting GCP project..."
gcloud config set project $PROJECT_ID

# Build the container image
echo ""
echo "Building container image..."
gcloud builds submit --tag $IMAGE_NAME

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

# Using Supabase Postgres (free tier available)
# Get your connection string from: https://supabase.com/dashboard -> Your Project -> Settings -> Database
# Connection string format: postgresql://postgres.xxxxx:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres

echo ""
echo "=== Deployment Complete ==="
echo "Your app should be available at the URL shown above."
echo ""
echo "To use Cloud SQL (recommended for production):"
echo "1. Create a Cloud SQL Postgres instance"
echo "2. Update the DATABASE_URL in the deploy command"
echo "3. Add --add-cloudsql-instances flag"
echo ""
echo "To update environment variables later:"
echo "gcloud run services update $SERVICE_NAME --region $REGION --set-env-vars KEY=VALUE"
