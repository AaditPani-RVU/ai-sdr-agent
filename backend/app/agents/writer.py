"""
Writer Agent — Week 2.

Takes ResearchResult + prospect info → personalized cold email + 2 follow-ups.
"""
import json
from app.schemas import ResearchResult, ProspectCreate, EmailDraft
from app.services.groq_client import chat

WRITER_SYSTEM_PROMPT = """You are an expert cold email copywriter. You write short, highly personalized B2B cold emails that get replies.

Rules:
- Subject line: curiosity-driven, under 8 words, no spam words
- Opening line: hyper-specific to their company/role (never generic)
- Value proposition: one clear sentence, tied to a pain point
- CTA: one soft question, not "hop on a call"
- Total body: under 120 words
- Follow-ups: shorter, different angle, add value not just "bumping this"

Respond with JSON only:
{
  "subject": "...",
  "body": "...",
  "follow_up_1": "...",
  "follow_up_2": "..."
}"""


async def write_email(prospect: ProspectCreate, research: ResearchResult, prospect_id: int) -> EmailDraft:
    context = f"""
Prospect: {prospect.first_name} {prospect.last_name}, {prospect.role} at {prospect.company}
Company summary: {research.company_summary}
Pain points: {', '.join(research.pain_points)}
Personalization hooks: {', '.join(research.personalization_hooks)}
Recommended angle: {research.recommended_angle}
"""
    messages = [
        {"role": "system", "content": WRITER_SYSTEM_PROMPT},
        {"role": "user", "content": f"Write a cold email sequence for this prospect:\n{context}"},
    ]
    clean, _ = await chat(messages, model="llama3-70b-8192", temperature=0.7)

    try:
        data = json.loads(clean)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        data = json.loads(match.group()) if match else {}

    return EmailDraft(
        prospect_id=prospect_id,
        subject=data.get("subject", ""),
        body=data.get("body", ""),
        follow_up_1=data.get("follow_up_1", ""),
        follow_up_2=data.get("follow_up_2", ""),
    )
