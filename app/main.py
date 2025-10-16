"""Main application entry point."""

import logging
import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.v1 import analysis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# Log startup environment
logger.info("=" * 80)
logger.info("SEMANTIC ANALYSIS SERVICE STARTING")
logger.info("=" * 80)
logger.info(f"Python version: {sys.version}")
logger.info(f"PORT environment variable: {os.environ.get('PORT', 'NOT SET')}")
logger.info(f"Working directory: {os.getcwd()}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("=" * 80)
    logger.info("LIFESPAN STARTUP BEGIN")
    logger.info("=" * 80)
    
    try:
        settings = get_settings()
        logger.info(f"✓ Settings loaded successfully")
        logger.info(f"  - Log level: {settings.log_level}")
        logger.info(f"  - Debug mode: {settings.debug}")
        logger.info(f"  - Port: {settings.port}")
        logger.info(f"  - Batch size: {settings.batch_size}")
        logger.info(f"  - Redis enabled: {settings.redis_enabled}")
        
        # Check for CUDA availability
        try:
            import torch
            cuda_available = torch.cuda.is_available()
            logger.info(f"  - CUDA available: {cuda_available}")
            if cuda_available:
                logger.info(f"  - GPU: {torch.cuda.get_device_name(0)}")
        except Exception as e:
            logger.warning(f"  - Could not check CUDA: {e}")
        
        # Skip model preloading to ensure fast startup
        # Models will be loaded lazily on first request
        logger.info("✓ Models will be loaded on first request (lazy loading)")
        logger.info("=" * 80)
        logger.info("SERVICE READY TO ACCEPT REQUESTS")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"✗ STARTUP FAILED: {e}", exc_info=True)
        raise
    
    yield
    
    # Shutdown
    logger.info("=" * 80)
    logger.info("SHUTTING DOWN SEMANTIC ANALYSIS SERVICE")
    logger.info("=" * 80)


# Create FastAPI application
app = FastAPI(
    title="Series.so Semantic Analysis Service",
    description="GPU-powered emotion and sentiment analysis for conversations",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to AnalyticsService URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    analysis.router,
    prefix="/api/v1/analysis",
    tags=["analysis"]
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Series.so Semantic Analysis Service",
        "version": "1.0.0",
        "status": "operational"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.debug
    )

