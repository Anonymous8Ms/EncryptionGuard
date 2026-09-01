from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.models.base import get_db
from app.models.cases import Feedback, Case

router = APIRouter()


class FeedbackRequest(BaseModel):
    case_id: str
    event_id: str
    label: str  # confirmed_abuse, legitimate, needs_more_evidence, unknown
    analyst: str


@router.post("/")
async def submit_feedback(
    feedback: FeedbackRequest,
    db: Session = Depends(get_db)
):
    """Submit analyst feedback for a case."""
    case = db.query(Case).filter(Case.id == feedback.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    db_feedback = Feedback(
        case_id=feedback.case_id,
        event_id=feedback.event_id,
        label=feedback.label,
        analyst=feedback.analyst,
        model_version=case.model_version
    )
    db.add(db_feedback)
    db.commit()

    return {"status": "recorded", "feedback_id": db_feedback.id}
