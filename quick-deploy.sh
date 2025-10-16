#!/bin/bash

# Quick Deployment Script for Semantic Analysis Service
# This script automates the entire deployment process

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="charged-sum-438023-h2"
REGION="us-central1"
SERVICE_NAME="semantic-analysis-service"
API_KEY="Chy7k2_OTciwvcGY17aGxInOT6xedWAv3ywpBdRuuBg"
REDIS_AUTH="7dd4dd9b-4f59-4c81-b602-3248916b0519"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Series.so Semantic Analysis Service Deployment          ║${NC}"
echo -e "${BLUE}║   GPU-Powered Emotion & Sentiment Analysis                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Verify gcloud authentication
echo -e "${YELLOW}[1/8] Verifying Google Cloud authentication...${NC}"
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo -e "${RED}❌ Not authenticated. Please run: gcloud auth login${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Authenticated${NC}"
echo ""

# Step 2: Set project
echo -e "${YELLOW}[2/8] Setting project to ${PROJECT_ID}...${NC}"
gcloud config set project ${PROJECT_ID}
echo -e "${GREEN}✅ Project set${NC}"
echo ""

# Step 3: Create secrets
echo -e "${YELLOW}[3/8] Creating secrets in Google Cloud Secret Manager...${NC}"

# SEMANTIC_API_KEY
if gcloud secrets describe SEMANTIC_API_KEY --project=${PROJECT_ID} &> /dev/null; then
    echo "  • SEMANTIC_API_KEY already exists, updating..."
    echo -n "${API_KEY}" | gcloud secrets versions add SEMANTIC_API_KEY \
        --data-file=- \
        --project=${PROJECT_ID}
else
    echo "  • Creating SEMANTIC_API_KEY..."
    echo -n "${API_KEY}" | gcloud secrets create SEMANTIC_API_KEY \
        --data-file=- \
        --replication-policy="automatic" \
        --project=${PROJECT_ID}
fi

# REDIS_AUTH
if gcloud secrets describe REDIS_AUTH --project=${PROJECT_ID} &> /dev/null; then
    echo "  • REDIS_AUTH already exists, updating..."
    echo -n "${REDIS_AUTH}" | gcloud secrets versions add REDIS_AUTH \
        --data-file=- \
        --project=${PROJECT_ID}
else
    echo "  • Creating REDIS_AUTH..."
    echo -n "${REDIS_AUTH}" | gcloud secrets create REDIS_AUTH \
        --data-file=- \
        --replication-policy="automatic" \
        --project=${PROJECT_ID}
fi

echo -e "${GREEN}✅ Secrets created/updated${NC}"
echo ""

# Step 4: Create Artifact Registry
echo -e "${YELLOW}[4/8] Setting up Artifact Registry...${NC}"
if ! gcloud artifacts repositories describe semantic-analysis \
    --location=${REGION} \
    --project=${PROJECT_ID} &> /dev/null; then
    echo "  • Creating repository..."
    gcloud artifacts repositories create semantic-analysis \
        --repository-format=docker \
        --location=${REGION} \
        --description="Semantic Analysis Service GPU images" \
        --project=${PROJECT_ID}
    echo -e "${GREEN}✅ Repository created${NC}"
else
    echo -e "${GREEN}✅ Repository already exists${NC}"
fi
echo ""

# Step 5: Verify VPC Connector
echo -e "${YELLOW}[5/8] Verifying VPC Connector...${NC}"
if gcloud compute networks vpc-access connectors describe semantic-vpc-us-c1 \
    --region=${REGION} \
    --project=${PROJECT_ID} &> /dev/null; then
    echo -e "${GREEN}✅ VPC connector exists and is ready${NC}"
else
    echo -e "${RED}❌ VPC connector 'semantic-vpc-us-c1' not found${NC}"
    echo -e "${YELLOW}Creating VPC connector (requires vpcaccess.connectors.create permission)...${NC}"
    echo ""
    echo "Run this command manually if you have the required permissions:"
    echo "gcloud compute networks vpc-access connectors create semantic-vpc-us-c1 \\"
    echo "  --region=${REGION} \\"
    echo "  --network=default \\"
    echo "  --range=10.8.2.0/28 \\"
    echo "  --min-instances=2 \\"
    echo "  --max-instances=3 \\"
    echo "  --machine-type=e2-micro \\"
    echo "  --project=${PROJECT_ID}"
    exit 1
fi
echo ""

# Step 6: Build and Deploy
echo -e "${YELLOW}[6/8] Building and deploying service...${NC}"
echo "  • This will take 5-10 minutes (building ML models with GPU support)..."
gcloud builds submit \
    --config=cloudbuild.yaml \
    --project=${PROJECT_ID} \
    --region=${REGION}

echo -e "${GREEN}✅ Service deployed${NC}"
echo ""

# Step 7: Get service URL
echo -e "${YELLOW}[7/8] Retrieving service URL...${NC}"
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region=${REGION} \
    --project=${PROJECT_ID} \
    --format='value(status.url)')

echo -e "${GREEN}✅ Service URL: ${SERVICE_URL}${NC}"
echo ""

# Step 8: Test deployment
echo -e "${YELLOW}[8/8] Testing deployment...${NC}"
echo "  • Waiting for service to be ready..."
sleep 10

echo "  • Testing health endpoint..."
if curl -f "${SERVICE_URL}/health" &> /dev/null; then
    echo -e "${GREEN}  ✅ Health check passed${NC}"
else
    echo -e "${RED}  ❌ Health check failed${NC}"
fi

echo "  • Testing GPU availability..."
GPU_RESPONSE=$(curl -s "${SERVICE_URL}/api/v1/analysis/health")
echo "$GPU_RESPONSE" | jq '.' || echo "$GPU_RESPONSE"

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                   DEPLOYMENT COMPLETE!                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Service URL:${NC} ${SERVICE_URL}"
echo -e "${GREEN}API Key:${NC} ${API_KEY}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Update AnalyticsService environment variables:"
echo "   SEMANTIC_SERVICE_URL=${SERVICE_URL}"
echo "   SEMANTIC_SERVICE_API_KEY=${API_KEY}"
echo ""
echo "2. Run AnalyticsService migrations:"
echo "   cd ../AnalyticsService && alembic upgrade head"
echo ""
echo "3. Deploy updated AnalyticsService"
echo ""
echo -e "${YELLOW}Test the service:${NC}"
echo "curl -X POST '${SERVICE_URL}/api/v1/analysis/analyze' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -H 'X-API-Key: ${API_KEY}' \\"
echo "  -d '{\"conversation_id\": 1, \"messages\": [{\"content\": \"Hello!\"}]}'"
echo ""

