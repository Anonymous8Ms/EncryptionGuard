import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

try:
    from app.api import webhooks, cases, feedback
    logger.info("Routers imported successfully")
except Exception as e:
    logger.error("Failed to import routers: %s", e, exc_info=True)
    raise

app = FastAPI(
    title="EncryptionGuard API",
    version="5.0.0",
    description="Coordinated refund abuse detection system"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(cases.router, prefix="/api/cases", tags=["cases"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["feedback"])


@app.on_event("startup")
async def startup():
    from app.models.base import DATABASE_URL, engine
    logger.info("DATABASE_URL: %s", DATABASE_URL[:30] + "..." if len(DATABASE_URL) > 30 else DATABASE_URL)
    try:
        with engine.connect() as conn:
            logger.info("Database connection OK")
    except Exception as e:
        logger.error("Database connection FAILED: %s", e)


@app.get("/")
async def root():
    return {"status": "ok", "version": "5.0.0", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "5.0.0"}
