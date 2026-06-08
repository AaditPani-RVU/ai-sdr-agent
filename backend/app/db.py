from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Float, Text, ForeignKey, Enum as SAEnum
from typing import Optional
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./sdr.db")

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sender_name: Mapped[str] = mapped_column(String(255))
    sender_email: Mapped[str] = mapped_column(String(255))
    prospects: Mapped[list["Prospect"]] = relationship(back_populates="campaign")


class Prospect(Base):
    __tablename__ = "prospects"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(255))
    company: Mapped[str] = mapped_column(String(255))
    website_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    campaign_id: Mapped[Optional[int]] = mapped_column(ForeignKey("campaigns.id"), nullable=True)
    campaign: Mapped[Optional["Campaign"]] = relationship(back_populates="prospects")
    research: Mapped[Optional["Research"]] = relationship(back_populates="prospect", uselist=False)
    email_draft: Mapped[Optional["EmailDraftModel"]] = relationship(back_populates="prospect", uselist=False)


class Research(Base):
    __tablename__ = "research"

    id: Mapped[int] = mapped_column(primary_key=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospects.id"), unique=True)
    company_summary: Mapped[str] = mapped_column(Text)
    pain_points: Mapped[str] = mapped_column(Text)        # JSON array stored as string
    personalization_hooks: Mapped[str] = mapped_column(Text)  # JSON array stored as string
    recommended_angle: Mapped[str] = mapped_column(Text)
    thinking_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    prospect: Mapped["Prospect"] = relationship(back_populates="research")


class EmailDraftModel(Base):
    __tablename__ = "email_drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospects.id"), unique=True)
    subject: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    follow_up_1: Mapped[str] = mapped_column(Text)
    follow_up_2: Mapped[str] = mapped_column(Text)
    prospect: Mapped["Prospect"] = relationship(back_populates="email_draft")


async def get_db():
    async with SessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
