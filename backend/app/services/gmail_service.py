"""Gmail integration via Google API. Requires OAuth2 credentials (Week 3)."""
import os
import base64
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def _get_service():
    token_path = os.getenv("GMAIL_TOKEN_PATH", "token.json")
    creds = Credentials.from_authorized_user_file(token_path)
    return build("gmail", "v1", credentials=creds)


def send_email(to: str, subject: str, body: str, sender: str) -> str:
    """Send an email and return the message id."""
    service = _get_service()
    message = MIMEText(body)
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return sent["id"]


def list_replies(query: str = "in:inbox is:unread") -> list[dict]:
    """Fetch unread inbox messages matching query."""
    service = _get_service()
    result = service.users().messages().list(userId="me", q=query).execute()
    messages = result.get("messages", [])
    full = []
    for msg in messages[:20]:
        detail = service.users().messages().get(userId="me", id=msg["id"], format="full").execute()
        headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
        snippet = detail.get("snippet", "")
        full.append({"id": msg["id"], "from": headers.get("From", ""), "subject": headers.get("Subject", ""), "snippet": snippet})
    return full
