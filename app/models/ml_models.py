"""Core ML models for emotion and sentiment analysis."""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class EmotionSentimentModels:
    """Manages emotion and sentiment classification models with lazy loading."""
    
    def __init__(self):
        """Initialize with lazy loading - models loaded on first use."""
        self._emotion_classifier = None
        self._sentiment_classifier = None
        self._initialized = False
        logger.info("EmotionSentimentModels created (models will load on first use)")
    
    def _ensure_models_loaded(self):
        """Lazy load models on first use to avoid startup timeout."""
        if self._initialized:
            return
            
        logger.info("=" * 80)
        logger.info("LOADING ML MODELS (First request - this may take 30-60 seconds)")
        logger.info("=" * 80)
        
        try:
            # Import here to avoid loading at module import time
            from transformers import pipeline
            import torch
            from app.core.config import get_settings
            
            settings = get_settings()
            device = 0 if torch.cuda.is_available() else -1
            logger.info(f"Device: {'GPU (CUDA)' if device == 0 else 'CPU'}")
            
            # Initialize emotion classifier (j-hartmann/emotion-english-distilroberta-base)
            # Detects: anger, disgust, fear, joy, neutral, sadness, surprise
            logger.info("Loading emotion classifier...")
            self._emotion_classifier = pipeline(
                "text-classification",
                model="j-hartmann/emotion-english-distilroberta-base",
                device=device,
                batch_size=settings.batch_size,
                top_k=None  # Return all emotion scores
            )
            logger.info("✓ Emotion classifier loaded")
            
            # Initialize sentiment classifier (cardiffnlp/twitter-roberta-base-sentiment-latest)
            # Detects: negative, neutral, positive
            logger.info("Loading sentiment classifier...")
            self._sentiment_classifier = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                device=device,
                batch_size=settings.batch_size
            )
            logger.info("✓ Sentiment classifier loaded")
            
            if torch.cuda.is_available():
                logger.info(f"GPU device: {torch.cuda.get_device_name(0)}")
                logger.info(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
            
            self._initialized = True
            logger.info("=" * 80)
            logger.info("ALL MODELS LOADED SUCCESSFULLY")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"Failed to load models: {e}", exc_info=True)
            raise
    
    def analyze_emotions_batch(self, texts: List[str]) -> List[List[Dict]]:
        """
        Analyze emotions for a batch of texts.
        
        Returns list of emotion scores for each text:
        [[{"label": "joy", "score": 0.8}, {"label": "neutral", "score": 0.1}, ...], ...]
        """
        if not texts:
            return []
        
        # Lazy load models on first use
        self._ensure_models_loaded()
        return self._emotion_classifier(texts)
    
    def analyze_sentiment_batch(self, texts: List[str]) -> List[Dict]:
        """
        Analyze sentiment for a batch of texts.
        
        Returns list of sentiment labels with scores:
        [{"label": "positive", "score": 0.9}, ...]
        """
        if not texts:
            return []
        
        # Lazy load models on first use
        self._ensure_models_loaded()
        return self._sentiment_classifier(texts)

