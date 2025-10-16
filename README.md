# Series.so Semantic Analysis Service

GPU-powered emotion and sentiment analysis service for conversation insights.

## Features

- **Emotion Detection**: 7 emotion categories using j-hartmann/emotion-english-distilroberta-base
- **Sentiment Analysis**: Positive/negative/neutral using cardiffnlp/twitter-roberta-base-sentiment-latest
- **GPU Acceleration**: Optimized for NVIDIA L4 GPUs on Cloud Run
- **Batch Processing**: Efficient batch inference for conversation-level analysis
- **Valence/Arousal**: Dimensional emotion representation

## Architecture

- **Framework**: FastAPI
- **ML Backend**: HuggingFace Transformers + PyTorch
- **Deployment**: Google Cloud Run with GPU support (us-central1)
- **Authentication**: API key-based

## API Endpoints

### POST /api/v1/analysis/analyze
Analyze a conversation for emotions and sentiment.

**Request:**
```json
{
  "conversation_id": 123,
  "messages": [
    {"content": "Hello, nice to meet you!"},
    {"content": "Great to connect with you too!"}
  ]
}
```

**Response:**
```json
{
  "conversation_id": 123,
  "analysis": {
    "emotion": {
      "dominant_emotion": "joy",
      "emotion_confidence": 0.85,
      "emotion_distribution": {...},
      "average_valence": 0.7,
      "average_arousal": 0.6
    },
    "sentiment": {
      "sentiment_polarity": "positive",
      "sentiment_score": 0.75
    },
    "quality": {
      "conversation_quality_score": 0.82,
      "engagement_level": "high"
    }
  },
  "status": "success"
}
```

### GET /api/v1/analysis/health
Health check with GPU status.

### GET /api/v1/analysis/warmup
Warmup endpoint to preload models.

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (CPU mode)
uvicorn app.main:app --reload --port 8000
```

## Deployment

Deploy to Cloud Run with GPU:

```bash
# Build and push image
gcloud builds submit --tag us-central1-docker.pkg.dev/PROJECT_ID/semantic-analysis/service:latest

# Deploy with GPU
gcloud run deploy semantic-analysis-service \
  --image us-central1-docker.pkg.dev/PROJECT_ID/semantic-analysis/service:latest \
  --platform managed \
  --region us-central1 \
  --gpu 1 \
  --gpu-type nvidia-l4 \
  --memory 8Gi \
  --cpu 4 \
  --max-instances 3 \
  --min-instances 1 \
  --timeout 60 \
  --set-env-vars API_KEY=your-api-key
```

## Performance

- **Inference Time**: 50-100ms per conversation (GPU)
- **Batch Size**: 16 messages per batch
- **GPU Memory**: ~2-3 GB with models loaded
- **Cold Start**: ~30-45 seconds (model loading)

## Models

1. **Emotion**: [j-hartmann/emotion-english-distilroberta-base](https://huggingface.co/j-hartmann/emotion-english-distilroberta-base)
   - 7 emotions: anger, disgust, fear, joy, neutral, sadness, surprise
   
2. **Sentiment**: [cardiffnlp/twitter-roberta-base-sentiment-latest](https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest)
   - 3 classes: positive, neutral, negative

