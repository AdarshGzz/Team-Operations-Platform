from sqlalchemy import Column, DateTime, ForeignKey, Uuid, func
from sqlalchemy.orm import relationship

from app.models.base import Base


class TeamMember(Base):
    __tablename__ = "team_members"

    team_id = Column(
        Uuid,
        ForeignKey("teams.id", ondelete="CASCADE"),
        primary_key=True,
    )

    user_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    joined_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    team = relationship(
        "Team",
        back_populates="members",
    )

    user = relationship(
        "User",
        back_populates="team_memberships",
    )
