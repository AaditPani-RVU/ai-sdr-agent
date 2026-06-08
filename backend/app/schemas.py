from pydantic import BaseModel, HttpUrl
from typing import Optional
from enum import Enum


class ProspectStatus(str, Enum):
    PENDING = "pending"
    RESEARCHED = "researched"
    EMAIL_DRAFTED = "email_drafted"
    SENT = "sent"
    REPLIED = "replied"
    BOOKED = "booked"
    UNSUBSCRIBED = "unsubscribed"


class ReplyCategory(str, Enum):
    INTERESTED = "interested"
    NOT_NOW = "not_now"
    OUT_OF_OFFICE = "out_of_office"
    UNSUBSCRIBE = "unsubscribe"
    OTHER = "other"


class ProspectCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    role: str
    company: str
    website_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    campaign_id: Optional[int] = None


class ProspectOut(ProspectCreate):
    id: int
    status: ProspectStatus = ProspectStatus.PENDING

    class Config:
        from_attributes = True


class ResearchResult(BaseModel):
    prospect_id: int
    company_summary: str
    pain_points: list[str]
    personalization_hooks: list[str]
    recommended_angle: str
    thinking_trace: Optional[str] = None
    confidence_score: float


class EmailDraft(BaseModel):
    prospect_id: int
    subject: str
    body: str
    follow_up_1: str
    follow_up_2: str


class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None
    sender_name: str
    sender_email: str


class CampaignOut(CampaignCreate):
    id: int
    total_prospects: int = 0
    sent: int = 0
    replied: int = 0
    booked: int = 0

    class Config:
        from_attributes = True


class ReplyIn(BaseModel):
    prospect_id: int
    email_body: str


class ReplyOut(BaseModel):
    prospect_id: int
    category: ReplyCategory
    summary: str
    suggested_action: str
