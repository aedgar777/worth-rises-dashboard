from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="processing")
    jurisdiction_count: Mapped[int] = mapped_column(Integer, default=0)
    matched_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MatchedRate(Base):
    __tablename__ = "matched_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    upload_id: Mapped[int] = mapped_column(Integer, index=True)
    jurisdiction_type: Mapped[str] = mapped_column(String(20))
    state: Mapped[str] = mapped_column(String(2), index=True)
    county: Mapped[str | None] = mapped_column(String(100), nullable=True)
    facility_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    in_state_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    out_of_state_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    match_status: Mapped[str] = mapped_column(String(50))
    match_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    facility_rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    place_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    place_description: Mapped[str | None] = mapped_column(Text, nullable=True)


class ProviderFacility(Base):
    __tablename__ = "provider_facilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    upload_id: Mapped[int] = mapped_column(Integer, index=True)
    state: Mapped[str] = mapped_column(String(2), index=True)
    county: Mapped[str | None] = mapped_column(String(100), nullable=True)
    facility_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    facility_name: Mapped[str] = mapped_column(String(255))
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    in_state_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    out_of_state_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    facility_address: Mapped[str | None] = mapped_column(Text, nullable=True)
