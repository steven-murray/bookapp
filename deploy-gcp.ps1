# Google Cloud Run Deployment Script for Windows PowerShell
# Prerequisites: gcloud CLI installed and authenticated

# Configuration
$PROJECT_ID = "bookapp-for-kids"  # Replace with your GCP project ID
$SERVICE_NAME = "bookapp"
$REGION = "us-central1"
$IMAGE_NAME = "gcr.io/$PROJECT_ID/$SERVICE_NAME"

# Generate a secure secret key (or use your own)
$SECRET_KEY = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object {[char]$_})

# Supabase connection string - Replace with your actual Supabase database URL
# Get this from: Supabase Dashboard -> Project Settings -> Database -> Connection string (URI)
# Example: postgresql://postgres.xxxxx:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres
$DATABASE_URL = "postgresql://postgres:1C1UfWgAViKjxScW@db.wwwelxzsgmrjxzciyvnu.supabase.co:5432/postgres"

Write-Host "=== Building and Deploying Flask Book Tracker to Cloud Run ===" -ForegroundColor Cyan
Write-Host "Project ID: $PROJECT_ID"
Write-Host "Service Name: $SERVICE_NAME"
Write-Host "Region: $REGION"
Write-Host ""

# Set the project
Write-Host "Setting GCP project..." -ForegroundColor Yellow
gcloud config set project $PROJECT_ID

# Enable required APIs
Write-Host ""
Write-Host "Enabling required APIs..." -ForegroundColor Yellow
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Grant Cloud Build service account permissions
# Grant permissions to your user account and Cloud Build service account
Write-Host ""
Write-Host "Setting up permissions..." -ForegroundColor Yellow
$USER_EMAIL = (gcloud config get-value account)
$PROJECT_NUMBER = (gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Grant your user the Cloud Build Editor role
Write-Host "Granting permissions to $USER_EMAIL..." -ForegroundColor Yellow
gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member="user:$USER_EMAIL" `
  --role="roles/cloudbuild.builds.editor"

# Grant your user Storage Admin role for Container Registry
gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member="user:$USER_EMAIL" `
  --role="roles/storage.admin"

# Grant Cloud Build service account permissions
gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member="serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com" `
  --role="roles/storage.admin"

Write-Host "Permissions granted. Waiting 10 seconds for changes to propagate..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Build the container image
Write-Host ""
Write-Host "Building container image..." -ForegroundColor Yellow
gcloud builds submit --tag $IMAGE_NAME

# Deploy to Cloud Run
Write-Host ""
Write-Host "Deploying to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $SERVICE_NAME `
  --image $IMAGE_NAME `
  --platform managed `
  --region $REGION `
  --allow-unauthenticated `
  --memory 512Mi `
  --cpu 1 `
  --timeout 300 `
  --set-env-vars "SECRET_KEY=$SECRET_KEY" `
  --set-env-vars "DATABASE_URL=$DATABASE_URL"

# Using Supabase Postgres (free tier available)
# Get your connection string from: https://supabase.com/dashboard -> Your Project -> Settings -> Database
# Connection string format: postgresql://postgres.xxxxx:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres

Write-Host ""
Write-Host "=== Deployment Complete ===" -ForegroundColor Green
Write-Host "Your app should be available at the URL shown above."
Write-Host ""
Write-Host "Note: Make sure you've set up your Supabase database and updated the DATABASE_URL in this script!" -ForegroundColor Yellow
Write-Host "1. Create a Cloud SQL Postgres instance"
Write-Host "2. Update the DATABASE_URL in the deploy command"
Write-Host "3. Add --add-cloudsql-instances flag"
Write-Host ""
Write-Host "To update environment variables later:" -ForegroundColor Cyan
Write-Host "gcloud run services update $SERVICE_NAME --region $REGION --set-env-vars KEY=VALUE"
