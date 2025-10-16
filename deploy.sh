#!/bin/bash

# Deployment script for Semantic Analysis Service
# This script deploys to Cloud Run with GPU support in us-central1

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="charged-sum-438023-h2"
REGION="us-central1"
SERVICE_NAME="semantic-analysis-service"
REPOSITORY="semantic-analysis"
VPC_CONNECTOR="semantic-vpc-us-c1"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    exit 1
fi

# Check if logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo -e "${RED}Error: Not logged in to gcloud${NC}"
    echo "Run: gcloud auth login"
    exit 1
fi

# Set project
echo -e "${YELLOW}Setting project to ${PROJECT_ID}...${NC}"
gcloud config set project ${PROJECT_ID}

# Ensure Artifact Registry repository exists
echo -e "${YELLOW}Checking Artifact Registry repository...${NC}"
if ! gcloud artifacts repositories describe ${REPOSITORY} --location=${REGION} &> /dev/null; then
    echo -e "${YELLOW}Creating Artifact Registry repository...${NC}"
    gcloud artifacts repositories create ${REPOSITORY} \
        --repository-format=docker \
        --location=${REGION} \
        --description="Semantic Analysis Service GPU images"
fi

# Ensure VPC Connector exists for cross-region communication
# Using 10.8.2.0/28 to avoid conflict with stargate-redis-connector (10.8.0.0/28)
echo -e "${YELLOW}Checking VPC Connector...${NC}"
if ! gcloud compute networks vpc-access connectors describe ${VPC_CONNECTOR} --region=${REGION} &> /dev/null; then
    echo -e "${YELLOW}Creating VPC Connector for service-to-service communication...${NC}"
    gcloud compute networks vpc-access connectors create ${VPC_CONNECTOR} \
        --region=${REGION} \
        --network=default \
        --range=10.8.2.0/28 \
        --min-instances=2 \
        --max-instances=3 \
        --machine-type=e2-micro
    
    echo -e "${GREEN}VPC Connector created successfully${NC}"
else
    echo -e "${GREEN}VPC Connector already exists${NC}"
fi

# Submit build
echo -e "${YELLOW}Submitting Cloud Build...${NC}"
gcloud builds submit \
    --config=cloudbuild.yaml \
    --substitutions=_API_KEY="${SEMANTIC_API_KEY:-placeholder-key}" \
    --region=${REGION}

# Get service URL
echo -e "${GREEN}Deployment complete!${NC}"
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region=${REGION} \
    --format='value(status.url)')

echo -e "${GREEN}Service URL: ${SERVICE_URL}${NC}"

# Test health endpoint
echo -e "${YELLOW}Testing health endpoint...${NC}"
sleep 5
if curl -f "${SERVICE_URL}/health" > /dev/null 2>&1; then
    echo -e "${GREEN}Health check passed!${NC}"
else
    echo -e "${RED}Health check failed!${NC}"
    exit 1
fi

# Display GPU info
echo -e "${YELLOW}Testing GPU availability...${NC}"
curl -s "${SERVICE_URL}/api/v1/analysis/health" | jq '.'

echo -e "${GREEN}Deployment successful!${NC}"
echo ""
echo "Next steps:"
echo "1. Update AnalyticsService SEMANTIC_SERVICE_URL to: ${SERVICE_URL}"
echo "2. Update AnalyticsService SEMANTIC_SERVICE_API_KEY"
echo "3. Deploy AnalyticsService with updated configuration"

