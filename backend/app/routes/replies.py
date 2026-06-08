from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas import ReplyIn, ReplyOut
from app.agents.classifier import classify_reply

router = APIRouter(prefix="/replies", tags=["replies"])


@router.post("/classify", response_model=ReplyOut)
async def classify(data: ReplyIn, db: AsyncSession = Depends(get_db)):
    return await classify_reply(data)
