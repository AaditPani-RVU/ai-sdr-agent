from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

from app.db import get_db, Campaign, Prospect
from app.schemas import CampaignCreate, CampaignOut

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("/", response_model=CampaignOut)
async def create_campaign(data: CampaignCreate, db: AsyncSession = Depends(get_db)):
    campaign = Campaign(**data.model_dump())
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return CampaignOut(**data.model_dump(), id=campaign.id)


@router.get("/", response_model=list[CampaignOut])
async def list_campaigns(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign))
    campaigns = result.scalars().all()
    out = []
    for c in campaigns:
        counts = await db.execute(
            select(
                func.count(Prospect.id),
                func.sum(case((Prospect.status == "sent", 1), else_=0)),
                func.sum(case((Prospect.status == "replied", 1), else_=0)),
                func.sum(case((Prospect.status == "booked", 1), else_=0)),
            ).where(Prospect.campaign_id == c.id)
        )
        total, sent, replied, booked = counts.one()
        out.append(CampaignOut(
            id=c.id, name=c.name, description=c.description,
            sender_name=c.sender_name, sender_email=c.sender_email,
            total_prospects=total or 0, sent=sent or 0,
            replied=replied or 0, booked=booked or 0,
        ))
    return out


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign
