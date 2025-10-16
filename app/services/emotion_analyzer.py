"""Emotion and sentiment analysis service."""

import numpy as np
from typing import Dict, List, Any
from app.models.ml_models import EmotionSentimentModels
import logging

logger = logging.getLogger(__name__)


class EmotionAnalyzer:
    """Analyzes emotions and sentiment in conversations."""
    
    def __init__(self):
        """Initialize with ML models."""
        self.models = EmotionSentimentModels()
    
    def analyze_conversation(self, messages: List[Dict]) -> Dict:
        """
        Analyze a full conversation for emotions and sentiment.
        
        Args:
            messages: List of message dicts with 'content' field
            
        Returns:
            Comprehensive analysis including emotion distribution, sentiment, and quality metrics
        """
        texts = [msg.get("content", "") for msg in messages if msg.get("content", "").strip()]
        
        if not texts:
            return self._empty_analysis()
        
        try:
            # Run batch analysis on GPU
            emotion_results = self.models.analyze_emotions_batch(texts)
            sentiment_results = self.models.analyze_sentiment_batch(texts)
            
            # Process message-level results
            message_analyses = []
            for i, (emotions, sentiment) in enumerate(zip(emotion_results, sentiment_results)):
                emotion_scores = {e["label"]: e["score"] for e in emotions}
                dominant_emotion = max(emotion_scores, key=emotion_scores.get)
                
                message_analyses.append({
                    "message_index": i,
                    "emotion": dominant_emotion,
                    "emotion_confidence": emotion_scores[dominant_emotion],
                    "emotion_scores": emotion_scores,
                    "sentiment": sentiment["label"],
                    "sentiment_score": self._normalize_sentiment(sentiment),
                    "valence": self._calculate_valence(emotion_scores),
                    "arousal": self._calculate_arousal(emotion_scores)
                })
            
            # Aggregate conversation-level analysis
            return self._aggregate_analysis(message_analyses, texts)
            
        except Exception as e:
            logger.error(f"Error analyzing conversation: {e}")
            return self._error_analysis(str(e))
    
    def _calculate_valence(self, emotion_scores: Dict) -> float:
        """
        Calculate valence (pleasantness) from -1 (negative) to +1 (positive).
        
        Based on Russell's circumplex model of affect.
        """
        valence_map = {
            "joy": 0.8,
            "surprise": 0.3,
            "neutral": 0.0,
            "fear": -0.5,
            "sadness": -0.7,
            "anger": -0.8,
            "disgust": -0.6
        }
        return sum(score * valence_map.get(emotion, 0) 
                  for emotion, score in emotion_scores.items())
    
    def _calculate_arousal(self, emotion_scores: Dict) -> float:
        """
        Calculate arousal (activation) from 0 (calm) to 1 (excited).
        
        Based on Russell's circumplex model of affect.
        """
        arousal_map = {
            "joy": 0.7,
            "surprise": 0.9,
            "neutral": 0.1,
            "fear": 0.8,
            "sadness": 0.3,
            "anger": 0.9,
            "disgust": 0.6
        }
        return sum(score * arousal_map.get(emotion, 0)
                  for emotion, score in emotion_scores.items())
    
    def _normalize_sentiment(self, sentiment: Dict) -> float:
        """
        Convert sentiment label to normalized score from -1 to +1.
        
        Args:
            sentiment: {"label": "positive", "score": 0.9}
            
        Returns:
            Float from -1 (negative) to +1 (positive)
        """
        label = sentiment["label"].lower()
        score = sentiment["score"]
        
        if label == "positive":
            return score
        elif label == "negative":
            return -score
        else:  # neutral
            return 0.0
    
    def _aggregate_analysis(self, message_analyses: List[Dict], texts: List[str]) -> Dict:
        """Aggregate message-level analyses into conversation-level metrics."""
        
        # Extract arrays for statistics
        valences = [m["valence"] for m in message_analyses]
        arousals = [m["arousal"] for m in message_analyses]
        sentiment_scores = [m["sentiment_score"] for m in message_analyses]
        
        # Aggregate emotion distribution
        all_emotions = {}
        for msg in message_analyses:
            for emotion, score in msg["emotion_scores"].items():
                all_emotions[emotion] = all_emotions.get(emotion, 0) + score
        
        # Normalize emotion distribution
        total = sum(all_emotions.values())
        emotion_distribution = {k: v / total for k, v in all_emotions.items()}
        dominant_emotion = max(emotion_distribution, key=emotion_distribution.get)
        
        # Calculate emotional volatility (standard deviation of valence)
        emotional_volatility = float(np.std(valences)) if len(valences) > 1 else 0.0
        
        # Determine sentiment polarity
        avg_sentiment = float(np.mean(sentiment_scores))
        if avg_sentiment > 0.2:
            sentiment_polarity = "positive"
        elif avg_sentiment < -0.2:
            sentiment_polarity = "negative"
        else:
            sentiment_polarity = "neutral"
        
        # Calculate quality metrics
        conversation_quality_score = self._calculate_quality_score(
            avg_sentiment, emotional_volatility, emotion_distribution
        )
        
        return {
            "emotion": {
                "dominant_emotion": dominant_emotion,
                "emotion_confidence": emotion_distribution[dominant_emotion],
                "emotion_distribution": emotion_distribution,
                "average_valence": float(np.mean(valences)),
                "average_arousal": float(np.mean(arousals)),
                "emotional_volatility": emotional_volatility
            },
            "sentiment": {
                "sentiment_polarity": sentiment_polarity,
                "sentiment_score": avg_sentiment,
                "positive_ratio": sum(1 for s in sentiment_scores if s > 0.2) / len(sentiment_scores),
                "negative_ratio": sum(1 for s in sentiment_scores if s < -0.2) / len(sentiment_scores)
            },
            "quality": {
                "conversation_quality_score": conversation_quality_score,
                "message_count": len(message_analyses),
                "engagement_level": self._calculate_engagement(arousals),
                "emotional_consistency": 1.0 - min(emotional_volatility / 2.0, 1.0)
            },
            "message_level_analysis": message_analyses
        }
    
    def _calculate_quality_score(
        self, 
        avg_sentiment: float, 
        volatility: float,
        emotion_distribution: Dict
    ) -> float:
        """
        Calculate overall conversation quality score (0-1).
        
        Higher scores indicate positive, stable, emotionally rich conversations.
        """
        # Positive sentiment contributes positively
        sentiment_component = (avg_sentiment + 1) / 2  # Convert -1,1 to 0,1
        
        # Moderate volatility is good (shows engagement), extreme is bad
        volatility_component = 1.0 - min(volatility / 1.5, 1.0)
        
        # Emotional diversity (entropy) - richer conversations have more varied emotions
        entropy = -sum(p * np.log(p + 1e-10) for p in emotion_distribution.values())
        max_entropy = np.log(len(emotion_distribution))
        diversity_component = entropy / max_entropy if max_entropy > 0 else 0
        
        # Weighted combination
        quality = (
            0.4 * sentiment_component +
            0.3 * volatility_component +
            0.3 * diversity_component
        )
        
        return float(np.clip(quality, 0, 1))
    
    def _calculate_engagement(self, arousals: List[float]) -> str:
        """Classify engagement level based on arousal."""
        avg_arousal = float(np.mean(arousals))
        
        if avg_arousal > 0.6:
            return "high"
        elif avg_arousal > 0.3:
            return "medium"
        else:
            return "low"
    
    def _empty_analysis(self) -> Dict:
        """Return empty analysis structure for conversations with no content."""
        return {
            "emotion": {
                "dominant_emotion": "neutral",
                "emotion_confidence": 0.0,
                "emotion_distribution": {"neutral": 1.0},
                "average_valence": 0.0,
                "average_arousal": 0.0,
                "emotional_volatility": 0.0
            },
            "sentiment": {
                "sentiment_polarity": "neutral",
                "sentiment_score": 0.0,
                "positive_ratio": 0.0,
                "negative_ratio": 0.0
            },
            "quality": {
                "conversation_quality_score": 0.0,
                "message_count": 0,
                "engagement_level": "low",
                "emotional_consistency": 0.0
            },
            "message_level_analysis": []
        }
    
    def _error_analysis(self, error_msg: str) -> Dict:
        """Return error analysis structure."""
        result = self._empty_analysis()
        result["error"] = error_msg
        return result

