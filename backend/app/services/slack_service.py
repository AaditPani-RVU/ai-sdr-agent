import os
import logging
import httpx

logger = logging.getLogger(__name__)
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")


def notify_booked(prospect_name: str, company: str, email: str) -> None:
    msg = f":calendar: *Meeting booked!* {prospect_name} from {company} ({email}) replied as interested."
    if not SLACK_WEBHOOK_URL:
        logger.info(f"[SLACK disabled] {msg}")
        return
    try:
        httpx.post(SLACK_WEBHOOK_URL, json={"text": msg}, timeout=5)
    except Exception as exc:
        logger.warning(f"Slack notification failed: {exc}")
