import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.models.base import get_db
from app.models.cases import Case

router = APIRouter()


@router.get("/")
async def list_cases(
    merchant_id: Optional[str] = None,
    status: Optional[str] = None,
    risk_level: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List cases with optional filters."""
    query = db.query(Case)

    if merchant_id:
        query = query.filter(Case.merchant_id == merchant_id)
    if status:
        query = query.filter(Case.status == status)
    if risk_level:
        query = query.filter(Case.risk_level == risk_level)

    cases = query.order_by(Case.created_at.desc()).offset(offset).limit(limit).all()
    total = query.count()

    return {
        "cases": [
            {
                "id": c.id,
                "merchant_id": c.merchant_id,
                "account_id": c.account_id,
                "risk_score": c.risk_score,
                "risk_level": c.risk_level,
                "status": c.status,
                "recommended_action": c.recommended_action,
                "created_at": c.created_at.isoformat()
            }
            for c in cases
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/{case_id}")
async def get_case(case_id: str, db: Session = Depends(get_db)):
    """Get case details with evidence."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    def _parse_json(val):
        if val is None:
            return {}
        if isinstance(val, str):
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return {}
        return val

    return {
        "id": case.id,
        "merchant_id": case.merchant_id,
        "account_id": case.account_id,
        "risk_score": case.risk_score,
        "risk_level": case.risk_level,
        "status": case.status,
        "recommended_action": case.recommended_action,
        "evidence": _parse_json(case.evidence),
        "graph_evidence": _parse_json(case.graph_evidence),
        "shap_values": _parse_json(case.shap_values),
        "model_version": case.model_version or "v5.0",
        "llm_summary": case.llm_summary,
        "created_at": case.created_at.isoformat() if case.created_at else "",
        "updated_at": case.updated_at.isoformat() if case.updated_at else ""
    }
