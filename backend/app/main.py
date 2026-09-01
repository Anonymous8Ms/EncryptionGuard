from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import webhooks, cases, feedback
from app.config import get_settings

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


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "5.0.0"}
