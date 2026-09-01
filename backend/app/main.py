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


@app.post("/api/seed")
async def seed_database():
    """Seed the database with sample cases. Call once after deployment."""
    import json
    import uuid
    from pathlib import Path
    from app.models.base import SessionLocal, Base, engine
    from app.models.cases import Case, Feedback

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Load scenarios
    scenarios_path = Path(__file__).parent.parent / "data" / "output" / "all_scenarios.json"
    if not scenarios_path.exists():
        return {"error": "No scenario data found"}

    with open(scenarios_path) as f:
        scenarios = json.load(f)

    db = SessionLocal()

    try:
        # Check if already seeded
        existing = db.query(Case).count()
        if existing > 0:
            return {"status": "already_seeded", "cases": existing}

        case_count = 0

        for scenario in scenarios:
            scenario_type = scenario.get("scenario_type", "unknown")
            merchant = scenario.get("merchant", [{}])[0] if scenario.get("merchant") else {}
            merchant_id = merchant.get("merchant_id", "unknown")

            accounts = scenario.get("accounts", [])

            for account in accounts:
                account_id = account.get("account_id", "unknown")

                if scenario_type == "coordinated_ring":
                    risk_score = 0.85 + (hash(account_id) % 15) / 100
                    risk_level = "critical"
                    recommended_action = "hold_for_review"
                    status = "open"
                elif scenario_type == "single_abuse":
                    risk_score = 0.65 + (hash(account_id) % 20) / 100
                    risk_level = "high"
                    recommended_action = "manual_review"
                    status = "open"
                elif scenario_type == "shared_network":
                    risk_score = 0.35 + (hash(account_id) % 20) / 100
                    risk_level = "medium"
                    recommended_action = "monitor"
                    status = "investigating"
                elif scenario_type == "legitimate_refund":
                    risk_score = 0.1 + (hash(account_id) % 15) / 100
                    risk_level = "low"
                    recommended_action = "allow"
                    status = "resolved"
                else:
                    risk_score = 0.05 + (hash(account_id) % 10) / 100
                    risk_level = "low"
                    recommended_action = "allow"
                    status = "resolved"

                case = Case(
                    id=f"case_{uuid.uuid4().hex[:12]}",
                    merchant_id=merchant_id,
                    account_id=account_id,
                    risk_score=risk_score,
                    risk_level=risk_level,
                    status=status,
                    recommended_action=recommended_action,
                    evidence=json.dumps({"scenario_type": scenario_type}),
                    graph_evidence=json.dumps({"nodes": [], "edges": []}),
                    shap_values=json.dumps({
                        "refund_rate": 0.35,
                        "velocity_24h": 0.25,
                        "shared_devices": 0.20,
                        "shared_ips": 0.15,
                        "amount_pattern": 0.05,
                    }),
                    model_version="v5.0",
                )
                db.add(case)
                case_count += 1

        db.commit()
        return {"status": "seeded", "cases": case_count}

    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()
