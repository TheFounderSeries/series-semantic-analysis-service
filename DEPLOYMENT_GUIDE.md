# Semantic Analysis Service - Deployment Guide

## Prerequisites

1. Google Cloud SDK installed and authenticated
2. Project: `charged-sum-438023-h2`
3. Region: `us-central1` (GPU-enabled)

## Step 1: Authenticate with Google Cloud

```bash
# Login to Google Cloud
gcloud auth login

# Set the project
gcloud config set project charged-sum-438023-h2

# Verify authentication
gcloud auth list
```

## Step 2: Create Secrets in Google Cloud Secret Manager

```bash
# Create SEMANTIC_API_KEY secret
echo -n "Chy7k2_OTciwvcGY17aGxInOT6xedWAv3ywpBdRuuBg" | gcloud secrets create SEMANTIC_API_KEY \
  --data-file=- \
  --replication-policy="automatic" \
  --project=charged-sum-438023-h2

# If secret already exists, update it:
echo -n "Chy7k2_OTciwvcGY17aGxInOT6xedWAv3ywpBdRuuBg" | gcloud secrets versions add SEMANTIC_API_KEY \
  --data-file=- \
  --project=charged-sum-438023-h2

# Create REDIS_AUTH secret
echo -n "7dd4dd9b-4f59-4c81-b602-3248916b0519" | gcloud secrets create REDIS_AUTH \
  --data-file=- \
  --replication-policy="automatic" \
  --project=charged-sum-438023-h2

# Or update if exists:
echo -n "7dd4dd9b-4f59-4c81-b602-3248916b0519" | gcloud secrets versions add REDIS_AUTH \
  --data-file=- \
  --project=charged-sum-438023-h2

# Verify secrets created
gcloud secrets list --project=charged-sum-438023-h2
```

## Step 3: Grant Secret Access to Service Account

```bash
# Grant the service account access to secrets
gcloud secrets add-iam-policy-binding SEMANTIC_API_KEY \
  --member="serviceAccount:gh-actions-deployer@charged-sum-438023-h2.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=charged-sum-438023-h2

gcloud secrets add-iam-policy-binding REDIS_AUTH \
  --member="serviceAccount:gh-actions-deployer@charged-sum-438023-h2.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=charged-sum-438023-h2
```

## Step 4: Create Artifact Registry Repository

```bash
# Create repository if it doesn't exist
gcloud artifacts repositories create semantic-analysis \
  --repository-format=docker \
  --location=us-central1 \
  --description="Semantic Analysis Service GPU images" \
  --project=charged-sum-438023-h2

# Configure Docker authentication
gcloud auth configure-docker us-central1-docker.pkg.dev
```

## Step 5: Create VPC Connector

```bash
# Create VPC connector for private networking
# Using 10.8.2.0/28 to avoid conflict with stargate-redis-connector (10.8.0.0/28)
gcloud compute networks vpc-access connectors create semantic-vpc-connector-us-central1 \
  --region=us-central1 \
  --network=default \
  --range=10.8.2.0/28 \
  --min-instances=2 \
  --max-instances=3 \
  --machine-type=e2-micro \
  --project=charged-sum-438023-h2

# Verify connector created
gcloud compute networks vpc-access connectors describe semantic-vpc-connector-us-central1 \
  --region=us-central1 \
  --project=charged-sum-438023-h2
```

## Step 6: Deploy via Cloud Build

### Option A: Using Cloud Build (Recommended)

```bash
# Navigate to service directory
cd /Users/sethvin-nanayakkara/Series/semantic-analysis-service

# Deploy using Cloud Build
gcloud builds submit \
  --config=cloudbuild.yaml \
  --project=charged-sum-438023-h2 \
  --region=us-central1

# Monitor deployment
gcloud builds list --project=charged-sum-438023-h2 --limit=5
```

### Option B: Using Deployment Script

```bash
# Make script executable
chmod +x deploy.sh

# Run deployment script
./deploy.sh
```

## Step 7: Verify Deployment

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe semantic-analysis-service \
  --region=us-central1 \
  --project=charged-sum-438023-h2 \
  --format='value(status.url)')

echo "Service URL: $SERVICE_URL"

# Test health endpoint
curl "$SERVICE_URL/health"

# Test GPU availability
curl "$SERVICE_URL/api/v1/analysis/health"

# Expected response:
# {
#   "status": "healthy",
#   "gpu_available": true,
#   "gpu_info": {
#     "gpu_name": "NVIDIA L4",
#     "gpu_memory_total": "22.17 GB",
#     "gpu_memory_allocated": "..."
#   }
# }
```

## Step 8: Test Analysis Endpoint

```bash
# Test with sample conversation
curl -X POST "$SERVICE_URL/api/v1/analysis/analyze" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: Chy7k2_OTciwvcGY17aGxInOT6xedWAv3ywpBdRuuBg" \
  -d '{
    "conversation_id": 1,
    "messages": [
      {"content": "Hi! Nice to meet you!"},
      {"content": "Great to connect with you too!"},
      {"content": "I heard you are working on an interesting startup."}
    ]
  }'

# Expected: JSON response with emotion and sentiment analysis
```

## Step 9: Update AnalyticsService Configuration

After successful deployment, update AnalyticsService with the service URL:

```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe semantic-analysis-service \
  --region=us-central1 \
  --project=charged-sum-438023-h2 \
  --format='value(status.url)')

echo "Add this to AnalyticsService environment variables:"
echo "SEMANTIC_SERVICE_URL=$SERVICE_URL"
echo "SEMANTIC_SERVICE_API_KEY=Chy7k2_OTciwvcGY17aGxInOT6xedWAv3ywpBdRuuBg"
```

Update files:
- `AnalyticsService/env.production`
- `AnalyticsService/env.staging`
- `AnalyticsService/env.development`

## Step 10: Deploy AnalyticsService

```bash
# Navigate to AnalyticsService
cd /Users/sethvin-nanayakkara/Series/AnalyticsService

# Run database migrations
alembic upgrade head

# Deploy updated service
gcloud builds submit \
  --config=cloudbuild.yaml \
  --project=charged-sum-438023-h2
```

## Troubleshooting

### GPU Not Available

```bash
# Check service logs
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=semantic-analysis-service" \
  --limit=50 \
  --project=charged-sum-438023-h2

# Check GPU quota
gcloud compute project-info describe --project=charged-sum-438023-h2 | grep -i gpu
```

### VPC Connector Issues

```bash
# Check connector status
gcloud compute networks vpc-access connectors describe semantic-vpc-connector-us-central1 \
  --region=us-central1 \
  --project=charged-sum-438023-h2

# Expected state: READY
```

### Service Not Responding

```bash
# Check service status
gcloud run services describe semantic-analysis-service \
  --region=us-central1 \
  --project=charged-sum-438023-h2

# View recent logs
gcloud logging tail "resource.type=cloud_run_revision" --project=charged-sum-438023-h2
```

## Configuration Summary

| Setting | Value |
|---------|-------|
| **Project** | charged-sum-438023-h2 |
| **Region** | us-central1 |
| **Service Name** | semantic-analysis-service |
| **GPU** | NVIDIA L4 (1x) |
| **Memory** | 8Gi |
| **CPU** | 4 |
| **Min Instances** | 1 (keep warm) |
| **Max Instances** | 3 |
| **VPC Connector** | semantic-vpc-connector-us-central1 |
| **VPC Subnet** | 10.8.2.0/28 |
| **API Key** | Chy7k2_OTciwvcGY17aGxInOT6xedWAv3ywpBdRuuBg |
| **Redis Host** | 10.52.158.91 |
| **Redis Port** | 6379 |
| **Redis Auth** | 7dd4dd9b-4f59-4c81-b602-3248916b0519 |

## Estimated Costs

- **GPU Service**: ~$12-15/day (1 min instance always running)
- **VPC Connector**: ~$0.05/hour (~$36/month)
- **Artifact Registry Storage**: ~$0.10/GB/month
- **Total**: ~$400-500/month for moderate usage

## Next Steps

1. ✅ Deploy semantic-analysis-service
2. ⏳ Update AnalyticsService environment variables
3. ⏳ Run AnalyticsService migrations
4. ⏳ Deploy updated AnalyticsService
5. ⏳ Test end-to-end conversation analysis
6. ⏳ Implement frontend UI components
7. ⏳ Monitor performance and GPU utilization

## Support

For issues or questions:
- Check logs: `gcloud logging read ...`
- View service status: `gcloud run services describe ...`
- Refer to: `VPC_SETUP.md`, `README.md`, `SEMANTIC_ANALYSIS_IMPLEMENTATION.md`

