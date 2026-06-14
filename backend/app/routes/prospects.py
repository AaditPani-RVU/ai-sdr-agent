from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import csv
import io
import json
import os
from datetime import datetime, timedelta, timezone

from app.db import get_db, Prospect, Research, EmailDraftModel, Campaign
from app.schemas import ProspectCreate, ProspectOut, ResearchResult, EmailDraft, SendResult, ContactFinderRequest, ContactCandidate
from app.agents.researcher import research_prospect
from app.agents.writer import write_email
from app.agents.contact_finder import find_contacts
from app.services.gmail_service import send_email

router = APIRouter(prefix="/prospects", tags=["prospects"])


@router.post("/", response_model=ProspectOut)
async def create_prospect(data: ProspectCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Prospect).where(Prospect.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Prospect with this email already exists")
    prospect = Prospect(**data.model_dump())
    db.add(prospect)
    await db.commit()
    await db.refresh(prospect)
    return prospect


@router.post("/bulk", response_model=list[ProspectOut])
async def bulk_upload(campaign_id: int, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Upload a CSV with columns: first_name, last_name, email, role, company, website_url, linkedin_url"""
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    created = []
    for row in reader:
        clean = {k.strip(): (v.strip() if v else None) for k, v in row.items()}
        if not clean.get("email"):
            continue
        existing = await db.execute(select(Prospect).where(Prospect.email == clean["email"]))
        if existing.scalar_one_or_none():
            continue
        prospect = Prospect(campaign_id=campaign_id, **{k: v for k, v in clean.items() if k in ProspectCreate.model_fields})
        db.add(prospect)
        await db.flush()
        created.append(prospect)
    await db.commit()
    return created


@router.get("/", response_model=list[ProspectOut])
async def list_prospects(campaign_id: int | None = None, db: AsyncSession = Depends(get_db)):
    q = select(Prospect)
    if campaign_id:
        q = q.where(Prospect.campaign_id == campaign_id)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/{prospect_id}/research", response_model=ResearchResult)
async def run_research(prospect_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prospect).where(Prospect.id == prospect_id))
    prospect = result.scalar_one_or_none()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    prospect_data = ProspectCreate(
        first_name=prospect.first_name,
        last_name=prospect.last_name,
        email=prospect.email,
        role=prospect.role,
        company=prospect.company,
        website_url=prospect.website_url,
        linkedin_url=prospect.linkedin_url,
    )
    research_result = await research_prospect(prospect_data, prospect_id)

    research_row = Research(
        prospect_id=prospect_id,
        company_summary=research_result.company_summary,
        pain_points=json.dumps(research_result.pain_points),
        personalization_hooks=json.dumps(research_result.personalization_hooks),
        recommended_angle=research_result.recommended_angle,
        thinking_trace=research_result.thinking_trace,
        confidence_score=research_result.confidence_score,
    )
    db.add(research_row)
    prospect.status = "researched"
    await db.commit()

    return research_result


@router.post("/{prospect_id}/draft", response_model=EmailDraft)
async def run_writer(prospect_id: int, db: AsyncSession = Depends(get_db)):
    prospect_row = (await db.execute(select(Prospect).where(Prospect.id == prospect_id))).scalar_one_or_none()
    if not prospect_row:
        raise HTTPException(status_code=404, detail="Prospect not found")

    research_row = (await db.execute(select(Research).where(Research.prospect_id == prospect_id))).scalar_one_or_none()
    if not research_row:
        raise HTTPException(status_code=400, detail="Run /research first before drafting")

    prospect_data = ProspectCreate(
        first_name=prospect_row.first_name,
        last_name=prospect_row.last_name,
        email=prospect_row.email,
        role=prospect_row.role,
        company=prospect_row.company,
        website_url=prospect_row.website_url,
        linkedin_url=prospect_row.linkedin_url,
    )
    research_data = ResearchResult(
        prospect_id=prospect_id,
        company_summary=research_row.company_summary,
        pain_points=json.loads(research_row.pain_points),
        personalization_hooks=json.loads(research_row.personalization_hooks),
        recommended_angle=research_row.recommended_angle,
        confidence_score=research_row.confidence_score,
    )

    draft = await write_email(prospect_data, research_data, prospect_id)

    existing = (await db.execute(select(EmailDraftModel).where(EmailDraftModel.prospect_id == prospect_id))).scalar_one_or_none()
    if existing:
        existing.subject = draft.subject
        existing.subject_alt = draft.subject_alt
        existing.body = draft.body
        existing.follow_up_1 = draft.follow_up_1
        existing.follow_up_2 = draft.follow_up_2
    else:
        db.add(EmailDraftModel(
            prospect_id=prospect_id,
            subject=draft.subject,
            subject_alt=draft.subject_alt,
            body=draft.body,
            follow_up_1=draft.follow_up_1,
            follow_up_2=draft.follow_up_2,
        ))

    prospect_row.status = "email_drafted"
    await db.commit()
    return draft


@router.get("/{prospect_id}/draft", response_model=EmailDraft)
async def get_draft(prospect_id: int, db: AsyncSession = Depends(get_db)):
    draft = (await db.execute(select(EmailDraftModel).where(EmailDraftModel.prospect_id == prospect_id))).scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="No draft found — run POST /draft first")
    return EmailDraft(
        prospect_id=prospect_id,
        subject=draft.subject,
        subject_alt=draft.subject_alt,
        body=draft.body,
        follow_up_1=draft.follow_up_1,
        follow_up_2=draft.follow_up_2,
    )


@router.post("/{prospect_id}/send", response_model=SendResult)
async def send_initial(prospect_id: int, db: AsyncSession = Depends(get_db)):
    prospect = (await db.execute(
        select(Prospect).options(selectinload(Prospect.campaign)).where(Prospect.id == prospect_id)
    )).scalar_one_or_none()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    if prospect.status != "email_drafted":
        raise HTTPException(status_code=400, detail=f"Expected status 'email_drafted', got '{prospect.status}'")

    draft = (await db.execute(select(EmailDraftModel).where(EmailDraftModel.prospect_id == prospect_id))).scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=400, detail="No draft found — run POST /draft first")

    sender_email = _resolve_sender(prospect)

    msg_id = send_email(
        to=prospect.email,
        subject=draft.subject,
        body=draft.body,
        sender=sender_email,
    )

    prospect.status = "sent"
    prospect.sent_at = datetime.utcnow()
    prospect.gmail_thread_id = msg_id
    await db.commit()

    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    return SendResult(prospect_id=prospect_id, status="sent", message_id=msg_id, dry_run=dry_run)


@router.post("/{prospect_id}/send-followup", response_model=SendResult)
async def send_followup(prospect_id: int, db: AsyncSession = Depends(get_db)):
    prospect = (await db.execute(
        select(Prospect).options(selectinload(Prospect.campaign)).where(Prospect.id == prospect_id)
    )).scalar_one_or_none()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    if prospect.status not in ("sent", "replied"):
        raise HTTPException(status_code=400, detail="Prospect must be in 'sent' status to follow up")
    if prospect.followups_sent >= 2:
        raise HTTPException(status_code=400, detail="All follow-ups already sent for this prospect")

    draft = (await db.execute(select(EmailDraftModel).where(EmailDraftModel.prospect_id == prospect_id))).scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=400, detail="No draft found")

    body = draft.follow_up_1 if prospect.followups_sent == 0 else draft.follow_up_2
    subject = f"Re: {draft.subject}"
    sender_email = _resolve_sender(prospect)

    msg_id = send_email(
        to=prospect.email,
        subject=subject,
        body=body,
        sender=sender_email,
        thread_id=prospect.gmail_thread_id,
    )

    prospect.followups_sent += 1
    await db.commit()

    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    return SendResult(
        prospect_id=prospect_id,
        status=f"followup_{prospect.followups_sent}_sent",
        message_id=msg_id,
        dry_run=dry_run,
    )


@router.post("/trigger-followups")
async def trigger_followups(db: AsyncSession = Depends(get_db)):
    """Called by n8n daily: send follow-up 1 at day 3 and follow-up 2 at day 7."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    day3 = now - timedelta(days=3)
    day7 = now - timedelta(days=7)

    result = await db.execute(
        select(Prospect)
        .options(selectinload(Prospect.campaign))
        .where(
            Prospect.status == "sent",
            Prospect.sent_at.isnot(None),
            Prospect.followups_sent < 2,
        )
    )
    prospects = result.scalars().all()

    triggered = []
    for prospect in prospects:
        draft = (await db.execute(
            select(EmailDraftModel).where(EmailDraftModel.prospect_id == prospect.id)
        )).scalar_one_or_none()
        if not draft:
            continue

        if prospect.followups_sent == 0 and prospect.sent_at <= day3:
            body = draft.follow_up_1
            followup_num = 1
        elif prospect.followups_sent == 1 and prospect.sent_at <= day7:
            body = draft.follow_up_2
            followup_num = 2
        else:
            continue

        try:
            sender_email = _resolve_sender(prospect)
            send_email(
                to=prospect.email,
                subject=f"Re: {draft.subject}",
                body=body,
                sender=sender_email,
                thread_id=prospect.gmail_thread_id,
            )
            prospect.followups_sent = followup_num
            triggered.append({"prospect_id": prospect.id, "followup": followup_num})
        except Exception:
            continue

    await db.commit()
    return {"triggered": len(triggered), "details": triggered}


@router.post("/find-contacts", response_model=list[ContactCandidate])
async def find_company_contacts(request: ContactFinderRequest):
    """Use web search to find key contacts at a company. Returns candidates — not saved yet."""
    return await find_contacts(request)


@router.post("/confirm-contacts", response_model=list[ProspectOut])
async def confirm_contacts(
    contacts: list[ProspectCreate],
    db: AsyncSession = Depends(get_db),
):
    """Save a user-selected subset of found contacts as prospects."""
    created = []
    for data in contacts:
        existing = await db.execute(select(Prospect).where(Prospect.email == data.email))
        if existing.scalar_one_or_none():
            continue
        prospect = Prospect(**data.model_dump())
        db.add(prospect)
        await db.flush()
        created.append(prospect)
    await db.commit()
    return created


@router.get("/stats")
async def get_stats(campaign_id: int | None = None, db: AsyncSession = Depends(get_db)):
    """Return prospect counts grouped by status."""
    q = select(Prospect)
    if campaign_id:
        q = q.where(Prospect.campaign_id == campaign_id)
    result = await db.execute(q)
    prospects = result.scalars().all()
    counts: dict[str, int] = {}
    for p in prospects:
        counts[p.status] = counts.get(p.status, 0) + 1
    return counts


def _resolve_sender(prospect: Prospect) -> str:
    """Get sender email from campaign, or fall back to SENDER_EMAIL env var."""
    if prospect.campaign and prospect.campaign.sender_email:
        return prospect.campaign.sender_email
    fallback = os.getenv("SENDER_EMAIL", "")
    if not fallback:
        raise HTTPException(status_code=400, detail="No sender email — attach prospect to a campaign or set SENDER_EMAIL in .env")
    return fallback
