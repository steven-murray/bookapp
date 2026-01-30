# Simplified Google Cloud Run Deployment Script
# Run this after you've enabled billing and set up permissions

# Configuration
$PROJECT_ID = "bookapp-for-kids"
$SERVICE_NAME = "bookapp"
$REGION = "us-central1"
$IMAGE_NAME = "gcr.io/$PROJECT_ID/$SERVICE_NAME"

# Generate a secure secret key
$SECRET_KEY = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object {[char]$_})

# Supabase connection string
$DATABASE_URL = "postgresql://postgres:1C1UfWgAViKjxScW@db.wwwelxzsgmrjxzciyvnu.supabase.co:5432/postgres"

Write-Host "=== Deploying Flask Book Tracker to Cloud Run ===" -ForegroundColor Cyan
Write-Host "Project: $PROJECT_ID"
Write-Host "Service: $SERVICE_NAME"
Write-Host ""

# Set the project
gcloud config set project $PROJECT_ID

# Build the container image
Write-Host "Building container image..." -ForegroundColor Yellow
gcloud builds submit --tag $IMAGE_NAME

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed! Check errors above." -ForegroundColor Red
    exit 1
}

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

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=== Deployment Complete! ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Get your service URL:" -ForegroundColor Cyan
    Write-Host "gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)'"
} else {
    Write-Host ""
    Write-Host "Deployment failed! Check errors above." -ForegroundColor Red
}
