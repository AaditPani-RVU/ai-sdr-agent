from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import csv
import io
import json

from app.db import get_db, Prospect, Research, EmailDraftModel
from app.schemas import ProspectCreate, ProspectOut, ResearchResult, EmailDraft
from app.agents.researcher import research_prospect
from app.agents.writer import write_email

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
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
    created = []
    for row in reader:
        existing = await db.execute(select(Prospect).where(Prospect.email == row["email"]))
        if existing.scalar_one_or_none():
            continue
        prospect = Prospect(campaign_id=campaign_id, **{k: v for k, v in row.items() if k in ProspectCreate.model_fields})
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
