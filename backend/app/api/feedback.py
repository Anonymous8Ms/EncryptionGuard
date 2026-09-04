from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.models.base import get_db
from app.models.cases import Feedback, Case

router = APIRouter()


class FeedbackRequest(BaseModel):
    case_id: str
    feedback: str  # confirm_abuse, legitimate, need_more_evidence
    analyst_notes: Optional[str] = None


@router.post("/")
async def submit_feedback(
    req: FeedbackRequest,
    db: Session = Depends(get_db)
):
    """Submit analyst feedback for a case."""
    case = db.query(Case).filter(Case.id == req.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    db_feedback = Feedback(
        case_id=req.case_id,
        disposition=req.feedback,
        analyst_id="analyst",
        model_version=case.model_version,
        notes=req.analyst_notes
    )
    db.add(db_feedback)
    db.commit()

    return {"status": "recorded", "feedback_id": db_feedback.id}
