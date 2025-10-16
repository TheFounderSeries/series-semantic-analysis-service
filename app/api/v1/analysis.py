"""Analysis API endpoints."""

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from app.services.emotion_analyzer import EmotionAnalyzer
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize analyzer once at module level
analyzer = None


def get_analyzer() -> EmotionAnalyzer:
    """Get or create emotion analyzer instance."""
    global analyzer
    if analyzer is None:
        analyzer = EmotionAnalyzer()
    return analyzer


async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify API key from header."""
    settings = get_settings()
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True


class AnalysisRequest(BaseModel):
    """Request model for conversation analysis."""
    conversation_id: int
    messages: List[Dict]


class AnalysisResponse(BaseModel):
    """Response model for conversation analysis."""
    conversation_id: int
    analysis: Dict
    status: str
    models_info: Dict = Field(alias="model_info")


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_conversation(
    request: AnalysisRequest,
    _: bool = Depends(verify_api_key),
    emotion_analyzer: EmotionAnalyzer = Depends(get_analyzer)
):
    """
    Analyze a conversation for emotions and sentiment.
    
    This endpoint performs GPU-accelerated analysis using RoBERTa-based models.
    
    Args:
        request: Conversation ID and messages
        
    Returns:
        Comprehensive emotion and sentiment analysis
    """
    try:
        logger.info(f"Analyzing conversation {request.conversation_id} with {len(request.messages)} messages")
        
        # Perform analysis
        analysis = emotion_analyzer.analyze_conversation(request.messages)
        
        # Check for errors in analysis
        if "error" in analysis:
            raise HTTPException(status_code=500, detail=f"Analysis error: {analysis['error']}")
        
        # Import torch only when needed
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "unknown"
        
        return {
            "conversation_id": request.conversation_id,
            "analysis": analysis,
            "status": "success",
            "model_info": {
                "emotion_model": "j-hartmann/emotion-english-distilroberta-base",
                "sentiment_model": "cardiffnlp/twitter-roberta-base-sentiment-latest",
                "device": device
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing conversation {request.conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns system status including GPU availability.
    """
    # Import torch only when checking health (lazy)
    try:
        import torch
        gpu_available = torch.cuda.is_available()
        gpu_info = {}
        
        if gpu_available:
            gpu_info = {
                "gpu_name": torch.cuda.get_device_name(0),
                "gpu_memory_total": f"{torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB",
                "gpu_memory_allocated": f"{torch.cuda.memory_allocated(0) / 1e9:.2f} GB"
            }
    except ImportError:
        gpu_available = False
        gpu_info = None
    
    return {
        "status": "healthy",
        "gpu_available": gpu_available,
        "gpu_info": gpu_info if gpu_available else None,
        "models_loaded": analyzer is not None
    }


@router.get("/warmup")
async def warmup(
    _: bool = Depends(verify_api_key),
    emotion_analyzer: EmotionAnalyzer = Depends(get_analyzer)
):
    """
    Warmup endpoint to initialize models.
    
    This loads models into memory and performs a test inference.
    Useful for ensuring models are ready before serving traffic.
    """
    try:
        # Test with a simple message
        test_messages = [{"content": "This is a test message to warm up the models."}]
        analysis = emotion_analyzer.analyze_conversation(test_messages)
        
        return {
            "status": "warmed_up",
            "models_ready": True,
            "test_analysis_completed": "error" not in analysis
        }
    except Exception as e:
        logger.error(f"Warmup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Warmup failed: {str(e)}")

