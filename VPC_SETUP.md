# VPC Networking Setup for Cross-Region Communication

This document explains the VPC networking setup for communication between `semantic-analysis-service` (us-central1) and `AnalyticsService` (us-east1).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     GCP Project: charged-sum-438023-h2                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────┐      ┌──────────────────────┐   │
│  │  AnalyticsService    │      │  semantic-analysis   │   │
│  │  (us-east1)          │◄────►│  -service            │   │
│  │  Cloud Run           │      │  (us-central1)       │   │
│  │                      │      │  Cloud Run + GPU     │   │
│  └──────────────────────┘      └──────────────────────┘   │
│           │                              │                 │
│           │                              │                 │
│  ┌────────▼──────────────────────────────▼────────────┐   │
│  │         VPC Network (default)                       │   │
│  │                                                      │   │
│  │  ┌──────────────────┐    ┌──────────────────────┐  │   │
│  │  │ VPC Connector    │    │ VPC Connector        │  │   │
│  │  │ us-east1         │    │ us-central1          │  │   │
│  │  │ 10.8.1.0/28      │    │ 10.8.0.0/28          │  │   │
│  │  └──────────────────┘    └──────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## VPC Connectors

### Existing Connectors
- **stargate-redis-connector**: `10.8.0.0/28` (Reserved for Redis access)

### us-central1 (GPU Region - Semantic Analysis Service)
- **Name**: `semantic-vpc-connector-us-central1`
- **CIDR Range**: `10.8.2.0/28` (16 IP addresses)
- **Machine Type**: `e2-micro`
- **Min Instances**: 2
- **Max Instances**: 3

### us-east1 (AnalyticsService Region)
- **Name**: `analytics-vpc-connector-us-east1`
- **CIDR Range**: `10.8.1.0/28` (16 IP addresses)
- **Machine Type**: `e2-micro`
- **Min Instances**: 2
- **Max Instances**: 3

**Note:** The semantic analysis service also uses `stargate-redis-connector` to access Redis at `10.52.158.91`

## Setup Commands

### Create VPC Connector in us-central1 (GPU region)

```bash
# Using 10.8.2.0/28 to avoid conflict with stargate-redis-connector
gcloud compute networks vpc-access connectors create semantic-vpc-connector-us-central1 \
  --region=us-central1 \
  --network=default \
  --range=10.8.2.0/28 \
  --min-instances=2 \
  --max-instances=3 \
  --machine-type=e2-micro \
  --project=charged-sum-438023-h2
```

### Create VPC Connector in us-east1 (AnalyticsService region)

```bash
gcloud compute networks vpc-access connectors create analytics-vpc-connector-us-east1 \
  --region=us-east1 \
  --network=default \
  --range=10.8.1.0/28 \
  --min-instances=2 \
  --max-instances=3 \
  --machine-type=e2-micro \
  --project=charged-sum-438023-h2
```

### Redis Access

The semantic-analysis-service also accesses Redis via VPC:
- **Redis Host**: `10.52.158.91` (internal VPC IP)
- **Redis Port**: `6379`
- **Authentication**: Password-based
- **VPC Access**: Via `stargate-redis-connector` or `semantic-vpc-connector-us-central1`

## Cloud Run Configuration

### semantic-analysis-service (us-central1)

```bash
gcloud run deploy semantic-analysis-service \
  --region=us-central1 \
  --vpc-connector=semantic-vpc-connector-us-central1 \
  --vpc-egress=private-ranges-only
```

This connector provides access to:
- AnalyticsService (us-east1) via Google's private network
- Redis (10.52.158.91) for caching

### AnalyticsService (us-east1)

```bash
gcloud run deploy analytics-service \
  --region=us-east1 \
  --vpc-connector=analytics-vpc-connector-us-east1 \
  --vpc-egress=private-ranges-only
```

## Communication Flow

1. **AnalyticsService** (us-east1) makes HTTPS request to **semantic-analysis-service** (us-central1)
2. Request goes through VPC connector in us-east1
3. Traffic routes through Google's private network (not public internet)
4. Request arrives at semantic-analysis-service via VPC connector in us-central1
5. Response follows the same path in reverse

## Benefits

- **Lower Latency**: ~20-30ms cross-region latency vs 50-100ms public internet
- **Security**: Traffic stays within Google's private network
- **Cost**: No egress charges for VPC traffic within same project
- **Reliability**: More reliable than public internet routing

## Authentication

In addition to VPC networking, services use API key authentication:

```bash
# Set in semantic-analysis-service
X-API-Key: <SEMANTIC_API_KEY>

# Used by AnalyticsService when calling semantic-analysis-service
```

## Monitoring

### Check VPC Connector Status

```bash
# us-central1
gcloud compute networks vpc-access connectors describe series-vpc-connector-us-central1 \
  --region=us-central1

# us-east1
gcloud compute networks vpc-access connectors describe series-vpc-connector-us-east1 \
  --region=us-east1
```

### View Connector Logs

```bash
gcloud logging read "resource.type=vpc_access_connector" \
  --limit=50 \
  --format=json
```

## Costs

- **VPC Connector**: ~$0.05/hour per connector (~$72/month for 2 connectors)
- **Traffic**: No egress charges for VPC traffic within same project
- **Total**: ~$144/month for VPC infrastructure

## Troubleshooting

### Test Connectivity

From AnalyticsService container:

```bash
curl https://semantic-analysis-service-<hash>-uc.a.run.app/health
```

### Check VPC Connector Health

```bash
gcloud compute networks vpc-access connectors describe <connector-name> \
  --region=<region> \
  --format="value(state)"
```

Should return `READY`.

### Common Issues

1. **503 errors**: VPC connector not ready or wrong egress setting
2. **Timeout**: Check firewall rules and connector configuration
3. **Connection refused**: Service not deployed or wrong URL

## Alternative: Public HTTPS with API Key

If VPC setup has issues, services can communicate via public HTTPS with API key authentication:

```bash
# semantic-analysis-service
gcloud run deploy semantic-analysis-service \
  --allow-unauthenticated \
  --no-vpc-connector

# AnalyticsService calls public URL with API key header
```

This is simpler but uses public internet (slightly higher latency, egress costs apply).

