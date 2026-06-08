"""
Sender Agent — Week 3.

Schedules and sends emails via Gmail API with rate limiting and tracking.
"""
import asyncio
from app.schemas import EmailDraft, ProspectCreate
from app.services.gmail_service import send_email

SEND_DELAY_SECONDS = 90  # ~40 emails/hour to avoid spam filters


async def send_sequence(prospect: ProspectCreate, draft: EmailDraft, sender_email: str) -> dict:
    """Send initial email. Follow-ups are triggered by n8n on a schedule."""
    msg_id = send_email(
        to=prospect.email,
        subject=draft.subject,
        body=draft.body,
        sender=sender_email,
    )
    await asyncio.sleep(SEND_DELAY_SECONDS)
    return {"message_id": msg_id, "status": "sent"}
