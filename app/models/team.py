import uuid
from datetime import datetime

from sqlalchemy import DateTime,String,Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

class Team(UUIDPrimaryKeyMixin,TimestampMixin, Base):
    __tablename__ = "teams"
    
    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True
    )
    
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    
    members: Mapped[list["TeamMember"]] = relationship(
        back_populates = "team",
        cascade="all, delete-orphan",
    )