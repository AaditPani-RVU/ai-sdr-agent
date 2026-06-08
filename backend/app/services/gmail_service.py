"""Gmail integration via Google API.

Set DRY_RUN=true in .env to log emails without sending — useful for testing
before completing OAuth setup.
"""
import os
import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"


def _get_service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    token_path = os.getenv("GMAIL_TOKEN_PATH", "token.json")
    if not os.path.exists(token_path):
        raise FileNotFoundError(
            f"Gmail token not found at {token_path}. Run `python auth_gmail.py` first."
        )
    creds = Credentials.from_authorized_user_file(token_path)
    return build("gmail", "v1", credentials=creds)


def send_email(to: str, subject: str, body: str, sender: str, thread_id: str | None = None) -> str:
    """Send an email. Returns message id (or 'dry-run' if DRY_RUN=true)."""
    if DRY_RUN:
        logger.info(f"[DRY RUN] To: {to} | Subject: {subject}\n{body}")
        return "dry-run"

    service = _get_service()
    message = MIMEText(body, "plain")
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject

    payload: dict = {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode()}
    if thread_id:
        payload["threadId"] = thread_id

    sent = service.users().messages().send(userId="me", body=payload).execute()
    return sent["id"]


def list_unread_replies(max_results: int = 20) -> list[dict]:
    """Fetch unread inbox messages. Returns list of dicts with id, from, subject, body, thread_id."""
    if DRY_RUN:
        logger.info("[DRY RUN] list_unread_replies called — returning empty list")
        return []

    service = _get_service()
    result = service.users().messages().list(
        userId="me", q="in:inbox is:unread", maxResults=max_results
    ).execute()

    messages = result.get("messages", [])
    full = []
    for msg in messages:
        detail = service.users().messages().get(userId="me", id=msg["id"], format="full").execute()
        headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
        body = _extract_body(detail["payload"])
        full.append({
            "id": msg["id"],
            "thread_id": detail.get("threadId", ""),
            "from": headers.get("From", ""),
            "subject": headers.get("Subject", ""),
            "snippet": detail.get("snippet", ""),
            "body": body,
        })
    return full


def mark_as_read(message_id: str) -> None:
    if DRY_RUN:
        return
    service = _get_service()
    service.users().messages().modify(
        userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
    ).execute()


def _extract_body(payload: dict) -> str:
    """Recursively extract plain text body from a Gmail message payload."""
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")

    for part in payload.get("parts", []):
        text = _extract_body(part)
        if text:
            return text

    return payload.get("snippet", "")
