"""Seed the database with generated scenario data."""
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.models.base import engine, SessionLocal, Base
from app.models.cases import Case, Feedback


def seed_database():
    """Load generated scenarios into the database."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Load scenarios
    scenarios_path = Path(__file__).parent / "data" / "output" / "all_scenarios.json"
    if not scenarios_path.exists():
        print("No scenario data found. Run 'python -m data.generator' first.")
        return
    
    with open(scenarios_path) as f:
        scenarios = json.load(f)
    
    db = SessionLocal()
    
    try:
        # Clear existing cases
        db.query(Feedback).delete()
        db.query(Case).delete()
        db.commit()
        
        case_count = 0
        
        for scenario in scenarios:
            scenario_type = scenario.get("scenario_type", "unknown")
            scenario_id = scenario.get("scenario_id", "unknown")
            merchant = scenario.get("merchant", [{}])[0] if scenario.get("merchant") else {}
            merchant_id = merchant.get("merchant_id", "unknown")
            
            # Get accounts from scenario
            accounts = scenario.get("accounts", [])
            
            for account in accounts:
                account_id = account.get("account_id", "unknown")
                
                # Determine risk level based on scenario type
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
                    status = "closed"
                else:  # normal
                    risk_score = 0.05 + (hash(account_id) % 10) / 100
                    risk_level = "low"
                    recommended_action = "allow"
                    status = "closed"
                
                # Create case
                case = Case(
                    id=f"case_{uuid.uuid4().hex[:12]}",
                    merchant_id=merchant_id,
                    account_id=account_id,
                    risk_score=risk_score,
                    risk_level=risk_level,
                    status=status,
                    recommended_action=recommended_action,
                    evidence=json.dumps({
                        "scenario_type": scenario_type,
                        "scenario_id": scenario_id,
                    }),
                    graph_evidence=json.dumps({
                        "nodes": [],
                        "edges": [],
                    }),
                    shap_values=json.dumps({
                        "refund_rate": 0.35,
                        "velocity_24h": 0.25,
                        "shared_devices": 0.20,
                        "shared_ips": 0.15,
                        "amount_pattern": 0.05,
                    }),
                    model_version="v5.0",
                    llm_summary=None,
                )
                db.add(case)
                case_count += 1
        
        db.commit()
        print(f"Seeded {case_count} cases into the database.")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
