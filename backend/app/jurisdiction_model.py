from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.jurisdictions_db import JurisdictionsBase


class Jurisdiction(JurisdictionsBase):
    """Reference jurisdictions to match (from Worth Rises assignment list)."""

    __tablename__ = "jurisdictions"
    __table_args__ = (
        UniqueConstraint("jurisdiction_type", "state", "county", name="uq_jurisdiction"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    jurisdiction_type: Mapped[str] = mapped_column(String(20), index=True)
    state: Mapped[str] = mapped_column(String(2), index=True)
    county = mapped_column(String(100), nullable=True)
