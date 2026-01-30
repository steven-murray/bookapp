# Google Cloud / Firebase Deployment Guide

## Prerequisites

1. **Google Cloud CLI** - Install from https://cloud.google.com/sdk/docs/install
2. **Google Cloud Project** - Create at https://console.cloud.google.com
3. **Enable APIs**:
   ```bash
   gcloud services enable run.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   ```

## Quick Deploy

### Option 1: Using the deployment script (Linux/Mac/Git Bash)

```bash
# Edit scripts/deploy-gcp.sh and set your PROJECT_ID
chmod +x scripts/deploy-gcp.sh
./scripts/deploy-gcp.sh
```

### Option 2: Using PowerShell (Windows)

```powershell
# Edit scripts/deploy-gcp.ps1 and set your PROJECT_ID
.\scripts\deploy-gcp.ps1
```

### Option 3: Manual deployment

```bash
# Set your project
gcloud config set project YOUR_PROJECT_ID

# Build the container
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/bookapp

# Deploy to Cloud Run (SQLite in /tmp - simple but ephemeral)
gcloud run deploy bookapp \
  --image gcr.io/YOUR_PROJECT_ID/bookapp \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --set-env-vars "SECRET_KEY=$(openssl rand -base64 32)" \
  --set-env-vars "DATABASE_URL=sqlite:////tmp/bookapp.db"
```

## Database Options

### Option A: SQLite (Ephemeral - Good for testing)
- **Pros**: Simple, no extra cost
- **Cons**: Data resets on each deployment
- Already configured in the deployment scripts above

### Option B: Supabase Postgres (Recommended - Free tier available)

1. **Create Supabase project**:
   - Go to https://supabase.com
   - Click "Start your project"
   - Create a new organization and project
   - Choose a region close to your Cloud Run region (e.g., us-east-1)

2. **Get connection string**:
   - In Supabase dashboard, go to **Project Settings** → **Database**
   - Find **Connection string** section
   - Copy the **URI** connection string (starts with `postgresql://`)
   - Replace `[YOUR-PASSWORD]` with your database password
   - Example: `postgresql://postgres.xxxxx:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres`

3. **Deploy with Supabase**:
   ```bash
   gcloud run deploy bookapp \
     --image gcr.io/YOUR_PROJECT_ID/bookapp \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars "SECRET_KEY=$(openssl rand -base64 32)" \
     --set-env-vars "DATABASE_URL=postgresql://postgres.xxxxx:YOUR_PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
   ```

4. **Supabase advantages**:
   - ✅ **Free tier**: 500MB database, unlimited API requests
   - ✅ **No cold starts**: Database stays warm
   - ✅ **Built-in dashboard**: Browse tables, run SQL queries
   - ✅ **Automatic backups**: Daily backups included
   - ✅ **Pooling**: Connection pooler included (use port 6543)
   - ✅ **No extra GCP costs**: Database hosted separately

## Environment Variables

Update environment variables without redeploying:

```bash
gcloud run services update bookapp \
  --region us-central1 \
  --set-env-vars "SECRET_KEY=new-secret-key"
```

View current configuration:

```bash
gcloud run services describe bookapp --region us-central1
```

## Costs (as of 2025)

- **Cloud Run**: Free tier includes 2M requests/month, then ~$0.00002400/request
- **Supabase Free Tier**: 500MB database, unlimited API requests (recommended)
- **Container Registry**: First 0.5GB free, then $0.026/GB/month

**Total estimated cost with Supabase free tier**: ~$0/month for low-traffic apps

## Monitoring

View logs:
```bash
gcloud logs read --service=bookapp --limit=50
```

View in Cloud Console:
```
https://console.cloud.google.com/run?project=YOUR_PROJECT_ID
```

## Create Admin User

After first deployment, create an admin user:

```bash
# Get your service URL
SERVICE_URL=$(gcloud run services describe bookapp --region us-central1 --format="value(status.url)")

# SSH into a Cloud Run container (or use Cloud Shell)
gcloud run services proxy bookapp --region us-central1

# In another terminal/tab:
curl http://localhost:8080  # verify it's running

# Then you can manually register an admin user through the web UI
# Or add a CLI command to create admin users
```

## Troubleshooting

**Build fails**: Check that all files are present and Docker is working locally
```bash
docker build -t test-bookapp .
docker run -p 8080:8080 test-bookapp
```

**App crashes on startup**: Check logs
```bash
gcloud logs tail --service=bookapp
```

**Database connection issues**: 
- Verify Supabase connection string format (should use pooler port 6543)
- Check that password is correctly URL-encoded if it contains special characters
- Ensure Supabase project is not paused (free tier pauses after 1 week of inactivity)

**Permission issues**: Ensure Cloud Run and Cloud SQL APIs are enabled

## Next Steps

- Set up custom domain: https://cloud.google.com/run/docs/mapping-custom-domains
- Explore Supabase Auth as alternative to Flask-Login: https://supabase.com/docs/guides/auth
- Add CI/CD with Cloud Build triggers
- Monitor database usage in Supabase dashboard
- Upgrade to Supabase Pro ($25/month) when you exceed 500MB or need more features
