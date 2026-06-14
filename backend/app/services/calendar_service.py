"""Google Calendar integration — creates booking events and syncs incoming bookings."""
import logging
import os
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
]


def _get_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    token_path = os.getenv("GMAIL_TOKEN_PATH", "token.json")
    if not os.path.exists(token_path):
        raise FileNotFoundError(
            f"Token not found at {token_path}. Run `python auth_gmail.py` first."
        )
    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("calendar", "v3", credentials=creds)


def sync_booked_attendees(since_minutes: int = 20) -> list[dict]:
    """
    Scan Google Calendar for events created/updated in the last N minutes.
    Returns list of {email, event_name, start_time, end_time, event_link} for
    each external attendee found — caller matches these against prospects.
    """
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    if dry_run:
        logger.info("[DRY RUN] sync_booked_attendees called — returning empty list")
        return []

    try:
        service = _get_service()
    except Exception as e:
        logger.warning(f"Calendar service unavailable: {e}")
        return []

    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
    now = datetime.now(timezone.utc)
    updated_min = (now - timedelta(minutes=since_minutes)).isoformat()

    try:
        result = service.events().list(
            calendarId=calendar_id,
            updatedMin=updated_min,
            singleEvents=True,
            orderBy="updated",
            maxResults=50,
        ).execute()
    except Exception as e:
        logger.error(f"Failed to list calendar events: {e}")
        return []

    bookings = []
    for event in result.get("items", []):
        if event.get("status") == "cancelled":
            continue
        attendees = event.get("attendees", [])
        start = event.get("start", {}).get("dateTime", event.get("start", {}).get("date", ""))
        end = event.get("end", {}).get("dateTime", event.get("end", {}).get("date", ""))
        for att in attendees:
            if att.get("self"):
                continue
            email = att.get("email", "").lower()
            if not email:
                continue
            bookings.append({
                "email": email,
                "event_name": event.get("summary", ""),
                "start_time": start,
                "end_time": end,
                "event_link": event.get("htmlLink", ""),
                "event_id": event.get("id", ""),
            })

    return bookings


def create_booking_event(
    prospect_name: str,
    prospect_email: str,
    company: str,
    start_time: str,
    end_time: str,
    gcal_event_link: str | None = None,
) -> str | None:
    """Create a Google Calendar event when a booking is detected. Returns the event HTML link."""
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"

    if dry_run:
        logger.info(f"[DRY RUN] Would create calendar event: {prospect_name} ({company}) at {start_time}")
        return None

    try:
        service = _get_service()
    except Exception as e:
        logger.warning(f"Calendar service unavailable: {e}")
        return None

    description_parts = [
        f"Prospect: {prospect_name} ({company})",
        f"Email: {prospect_email}",
    ]
    if gcal_event_link:
        description_parts.append(f"Event: {gcal_event_link}")

    event = {
        "summary": f"Meeting: {prospect_name} — {company}",
        "description": "\n".join(description_parts),
        "start": {"dateTime": _ensure_rfc3339(start_time), "timeZone": "UTC"},
        "end": {"dateTime": _ensure_rfc3339(end_time), "timeZone": "UTC"},
        "attendees": [{"email": prospect_email}],
        "reminders": {"useDefault": False, "overrides": [{"method": "email", "minutes": 60}]},
    }

    try:
        created = service.events().insert(calendarId=calendar_id, body=event).execute()
        return created.get("htmlLink")
    except Exception as e:
        logger.error(f"Failed to create calendar event: {e}")
        return None


def _ensure_rfc3339(dt_str: str) -> str:
    if not dt_str:
        return dt_str
    dt_str = dt_str.rstrip("Z")
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return dt_str + "Z"
