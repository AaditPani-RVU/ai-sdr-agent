import re as _re
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db, Prospect
from app.schemas import ReplyIn, ReplyOut, InboxItem
from app.agents.classifier import classify_reply
from app.services.gmail_service import list_unread_replies, mark_as_read
from app.services.slack_service import notify_booked

router = APIRouter(prefix="/replies", tags=["replies"])

STATUS_MAP = {
    "interested": "replied",
    "not_now": "replied",
    "unsubscribe": "unsubscribed",
    "out_of_office": None,   # don't change status
    "other": "replied",
}


@router.post("/classify", response_model=ReplyOut)
async def classify(data: ReplyIn, db: AsyncSession = Depends(get_db)):
    return await classify_reply(data)


@router.get("/inbox", response_model=list[InboxItem])
async def poll_inbox(db: AsyncSession = Depends(get_db)):
    """Fetch unread Gmail replies, classify each one, update prospect statuses."""
    messages = list_unread_replies()
    results: list[InboxItem] = []

    for msg in messages:
        from_email = _extract_email_addr(msg["from"])
        prospect = (
            await db.execute(select(Prospect).where(Prospect.email == from_email))
        ).scalar_one_or_none()

        item = InboxItem(
            gmail_message_id=msg["id"],
            from_email=from_email,
            subject=msg["subject"],
            body_snippet=msg["snippet"],
            prospect_id=prospect.id if prospect else None,
            prospect_name=f"{prospect.first_name} {prospect.last_name}" if prospect else None,
        )

        if prospect:
            reply_data = ReplyIn(
                prospect_id=prospect.id,
                email_body=msg["body"] or msg["snippet"],
            )
            classification = await classify_reply(reply_data)
            item.category = classification.category.value
            item.suggested_action = classification.suggested_action

            new_status = STATUS_MAP.get(classification.category.value)
            if new_status and prospect.status not in ("booked", "unsubscribed"):
                prospect.status = new_status
                if classification.category.value == "interested":
                    prospect.status = "booked"
                    notify_booked(
                        prospect_name=f"{prospect.first_name} {prospect.last_name}",
                        company=prospect.company,
                        email=prospect.email,
                    )

        mark_as_read(msg["id"])
        results.append(item)

    await db.commit()
    return results


def _extract_email_addr(raw: str) -> str:
    """Extract plain email from 'Name <email@domain.com>' format."""
    match = _re.search(r"<(.+?)>", raw)
    return match.group(1).lower() if match else raw.strip().lower()
