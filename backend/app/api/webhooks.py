from fastapi import APIRouter, Request, HTTPException, Header
from sqlalchemy.orm import Session
from fastapi import Depends
from app.models.base import get_db
from app.services.webhook_service import process_webhook

router = APIRouter()


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(...),
    x_razorpay_event_id: str = Header(...),
    db: Session = Depends(get_db)
):
    """Handle incoming Razorpay webhook."""
    raw_body = await request.body()

    import json
    payload = json.loads(raw_body)
    merchant_id = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("notes", {}).get("merchant_id", "unknown")

    result = process_webhook(
        db=db,
        raw_body=raw_body,
        signature=x_razorpay_signature,
        event_id=x_razorpay_event_id,
        merchant_id=merchant_id
    )

    if result["status"] == "invalid_signature":
        raise HTTPException(status_code=400, detail="Invalid signature")

    return result
