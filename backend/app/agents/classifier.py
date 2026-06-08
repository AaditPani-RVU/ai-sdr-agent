"""
Reply Classifier Agent — Week 3.

Classifies inbound email replies into actionable categories.
"""
import json
from app.schemas import ReplyIn, ReplyOut, ReplyCategory
from app.services.groq_client import chat

CLASSIFIER_SYSTEM_PROMPT = """Classify this cold email reply into one category and suggest the next action.

Categories:
- interested: they want to learn more or have questions
- not_now: timing issue, come back later
- out_of_office: auto-reply or OOO message
- unsubscribe: they explicitly want to stop receiving emails
- other: anything else

Respond with JSON only:
{
  "category": "interested|not_now|out_of_office|unsubscribe|other",
  "summary": "one sentence summary of their reply",
  "suggested_action": "specific next step"
}"""


async def classify_reply(reply: ReplyIn) -> ReplyOut:
    messages = [
        {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
        {"role": "user", "content": f"Classify this reply:\n\n{reply.email_body}"},
    ]
    # Use Scout (fast + cheap) for classification
    clean, _ = await chat(messages, model="llama-3.3-70b-versatile", temperature=0.1, max_tokens=256)

    try:
        data = json.loads(clean)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        data = json.loads(match.group()) if match else {}

    return ReplyOut(
        prospect_id=reply.prospect_id,
        category=ReplyCategory(data.get("category", "other")),
        summary=data.get("summary", ""),
        suggested_action=data.get("suggested_action", ""),
    )
