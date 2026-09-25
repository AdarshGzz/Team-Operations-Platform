from sqlalchemy import Column, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Team(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "teams"

    name = Column(
        String(150),
        nullable=False,
        unique=True,
    )

    description = Column(
        Text,
        nullable=True,
    )

    members = relationship(
        "TeamMember",
        back_populates="team",
        cascade="all, delete-orphan",
    )

    tasks = relationship(
        "Task",
        back_populates="team",
    )
