"""Inbound webhooks — Google Calendar booking sync."""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db, Prospect
from app.services.calendar_service import sync_booked_attendees
from app.services.slack_service import notify_booked

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/gcal/sync")
async def gcal_sync(since_minutes: int = 20, db: AsyncSession = Depends(get_db)):
    """
    Called by n8n every 15 minutes (or manually).
    Scans Google Calendar for new/updated events and marks matching prospects as booked.
    """
    bookings = sync_booked_attendees(since_minutes=since_minutes)

    booked = []
    for booking in bookings:
        email = booking["email"]
        prospect = (
            await db.execute(select(Prospect).where(Prospect.email == email))
        ).scalar_one_or_none()

        if not prospect:
            continue
        if prospect.status == "booked":
            continue

        prospect.status = "booked"
        prospect.calendly_event_url = booking["event_link"]

        if booking["start_time"]:
            try:
                prospect.booked_at = datetime.fromisoformat(
                    booking["start_time"].rstrip("Z")
                )
            except ValueError:
                prospect.booked_at = datetime.utcnow()
        else:
            prospect.booked_at = datetime.utcnow()

        notify_booked(
            prospect_name=f"{prospect.first_name} {prospect.last_name}",
            company=prospect.company,
            email=prospect.email,
        )

        booked.append({
            "prospect_id": prospect.id,
            "email": email,
            "meeting": booking["event_name"],
            "start_time": booking["start_time"],
        })

    await db.commit()
    return {"synced": len(bookings), "newly_booked": len(booked), "details": booked}
