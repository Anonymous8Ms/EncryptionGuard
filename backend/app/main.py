import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

from app.api import webhooks, cases, feedback
from app.models.base import Base, engine

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
def startup():
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured")

    # Auto-seed if empty
    from app.models.base import SessionLocal
    from app.models.cases import Case
    db = SessionLocal()
    try:
        count = db.query(Case).count()
        if count == 0:
            logger.info("No cases found, seeding...")
            _seed(db)
        else:
            logger.info("Database has %d cases", count)
    finally:
        db.close()


def _seed(db):
    import json, uuid
    from app.models.cases import Case
    scenarios = [
        ("coordinated_ring", "critical", 0.92, "hold_for_review", "open"),
        ("coordinated_ring", "critical", 0.88, "hold_for_review", "open"),
        ("single_abuse", "high", 0.71, "manual_review", "open"),
        ("single_abuse", "high", 0.68, "manual_review", "investigating"),
        ("shared_network", "medium", 0.42, "monitor", "investigating"),
        ("shared_network", "medium", 0.38, "monitor", "open"),
        ("legitimate_refund", "low", 0.15, "allow", "resolved"),
        ("legitimate_refund", "low", 0.12, "allow", "resolved"),
        ("normal", "low", 0.08, "allow", "resolved"),
        ("normal", "low", 0.05, "allow", "resolved"),
    ]
    merchants = ["merch_electronics_001", "merch_fashion_002", "merch_digital_003"]
    shap_values = json.dumps({
        "refund_rate": 0.35, "velocity_24h": 0.25,
        "shared_devices": 0.20, "shared_ips": 0.15, "amount_pattern": 0.05,
    })

    for i, (stype, risk_level, risk_score, action, status) in enumerate(scenarios):
        for j in range(3):  # 3 accounts per scenario
            case = Case(
                id=f"case_{uuid.uuid4().hex[:12]}",
                merchant_id=merchants[i % len(merchants)],
                account_id=f"acc_{uuid.uuid4().hex[:8]}",
                risk_score=risk_score,
                risk_level=risk_level,
                status=status,
                recommended_action=action,
                evidence=json.dumps({"scenario_type": stype}),
                graph_evidence=json.dumps({"nodes": [], "edges": []}),
                shap_values=shap_values,
                model_version="v5.0",
            )
            db.add(case)
    db.commit()
    logger.info("Seeded %d cases", len(scenarios) * 3)


@app.get("/")
async def root():
    return {"status": "ok", "version": "5.0.0", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "5.0.0"}
