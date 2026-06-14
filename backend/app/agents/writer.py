"""
Writer Agent — Week 2.

Three-email sequence: PAS cold email → value-add follow-up → break-up.
Tone is calibrated by prospect seniority (C-level vs VP vs Manager).
"""
import json
import os
import re
from app.schemas import ResearchResult, ProspectCreate, EmailDraft
from app.services.groq_client import chat


def _seniority_tone(role: str) -> str:
    role_lower = role.lower()
    if any(t in role_lower for t in ("ceo", "cto", "cfo", "coo", "founder", "owner", "president", "partner")):
        return (
            "This is a C-level executive. Be peer-to-peer, extremely brief (under 80 words for Email 1). "
            "No buzzwords. Focus only on revenue impact or existential risk. They have zero patience for fluff."
        )
    if any(t in role_lower for t in ("vp", "vice president", "director", "head of", "chief")):
        return (
            "This is a VP/Director. They care about team outcomes and hitting targets. "
            "Be results-focused. Reference metrics if possible. Under 100 words for Email 1."
        )
    return (
        "This is a Manager or IC. They care about making their job easier and looking good to their boss. "
        "Can be slightly more tactical. Under 110 words for Email 1."
    )


WRITER_SYSTEM_PROMPT = """\
You are a top-tier B2B cold email copywriter. You write sequences with 35%+ reply rates.

NON-NEGOTIABLE RULES:
- NEVER open with: "I hope", "My name is", "I wanted to reach out", "I came across your profile", "We help companies like yours"
- Email 1 MUST open with a hyper-specific observation about their company (from the research hooks)
- Subject lines: max 6 words, sentence case, no exclamation marks, no spam words (free, guarantee, exclusive, opportunity, limited)
- CTAs: ONE soft question per email. Never "hop on a 15-minute call". Never "Does this resonate?"
- Never mention features. Only problems solved and outcomes delivered.
- Follow-ups get SHORTER, not longer. Email 2 = 50-65 words. Email 3 = 30-40 words.

EMAIL 1 FRAMEWORK (PAS — Problem, Agitate, Solution):
Line 1: Specific observation tied to a research hook (what you noticed about them)
Line 2-3: The downstream problem this creates for someone in their role
Line 4-5: One sentence on how you solve it + one credibility signal (result/client/stat if you have context)
Line 6: Soft question CTA (e.g. "Would it make sense to explore if we can do the same for [Company]?")

EMAIL 2 FRAMEWORK (Value-Add, send Day 3 — no reply assumed):
Lead with a genuinely useful insight, stat, or observation relevant to their business — NOT a follow-up to email 1.
End with: "Happy to share more on this if useful."
MAX 60 words. No hard ask.

EMAIL 3 FRAMEWORK (Break-up, send Day 7 — no reply assumed):
Acknowledge you've reached out a couple of times.
One final value statement in one sentence.
Easy binary CTA: "If the timing is off, just let me know — otherwise, would love to connect."
MAX 40 words. After this email, stop.

SUBJECT LINE RULES:
- subject: question or curiosity-gap format (e.g. "How [Company] handles X?")
- subject_alt: outcome/benefit format (e.g. "Cutting [pain point] by 30%")
Both max 6 words.

Respond with VALID JSON ONLY — no markdown fences, no extra text:
{
  "subject": "...",
  "subject_alt": "...",
  "body": "...",
  "follow_up_1": "...",
  "follow_up_2": "..."
}"""


WRITER_USER_TEMPLATE = """\
Write a 3-email cold sequence for this prospect.

Prospect: {first_name} {last_name}, {role} at {company}
Seniority guidance: {tone_guidance}

Research context:
Company summary: {company_summary}
Pain points: {pain_points}
Personalization hooks (USE THESE in Email 1): {personalization_hooks}
Recommended angle: {recommended_angle}

Remember:
- Email 1 MUST open with one of the personalization hooks above — be specific, not generic
- Follow-ups must feel like new messages, not reminders
- subject_alt must be meaningfully different from subject (different format/angle)

Return JSON only."""


def _booking_footer() -> str:
    link = os.getenv("BOOKING_LINK", "").strip()
    if not link:
        return ""
    return f"\n\nP.S. If you'd like to grab time directly: {link}"


async def write_email(prospect: ProspectCreate, research: ResearchResult, prospect_id: int) -> EmailDraft:
    tone = _seniority_tone(prospect.role)

    messages = [
        {"role": "system", "content": WRITER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": WRITER_USER_TEMPLATE.format(
                first_name=prospect.first_name,
                last_name=prospect.last_name,
                role=prospect.role,
                company=prospect.company,
                tone_guidance=tone,
                company_summary=research.company_summary,
                pain_points=", ".join(research.pain_points),
                personalization_hooks=", ".join(research.personalization_hooks),
                recommended_angle=research.recommended_angle,
            ),
        },
    ]

    clean, _ = await chat(messages, model="llama-3.3-70b-versatile", temperature=0.65, max_tokens=1500)
    data = _parse_json(clean)

    footer = _booking_footer()
    return EmailDraft(
        prospect_id=prospect_id,
        subject=data.get("subject", ""),
        subject_alt=data.get("subject_alt", ""),
        body=data.get("body", "") + footer,
        follow_up_1=data.get("follow_up_1", "") + footer,
        follow_up_2=data.get("follow_up_2", ""),
    )


def _parse_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {}
