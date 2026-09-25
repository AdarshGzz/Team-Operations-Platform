from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.user import User, UserRole


class TeamService:
    def list_teams_for_user(
        self,
        db: Session,
        *,
        user: User,
    ) -> list[Team]:
        if user.role == UserRole.ADMIN:
            return self.list_teams(db)

        result = db.execute(
            select(Team)
            .join(
                TeamMember,
                TeamMember.team_id == Team.id,
            )
            .where(
                TeamMember.user_id == user.id,
            )
            .order_by(Team.name)
        )

        return list(result.scalars().unique().all())

    def create_team(
        self,
        db: Session,
        *,
        name: str,
        description: str | None,
    ) -> Team:
        result = db.execute(select(Team).where(Team.name == name))

        if result.scalar_one_or_none() is not None:
            raise ValueError("A team with this name already exists")

        team = Team(
            name=name,
            description=description,
        )

        db.add(team)
        db.commit()
        db.refresh(team)

        return team

    def get_team(
        self,
        db: Session,
        *,
        team_id: UUID,
    ) -> Team | None:
        result = db.execute(select(Team).where(Team.id == team_id))

        return result.scalar_one_or_none()

    def list_teams(
        self,
        db: Session,
    ) -> list[Team]:
        result = db.execute(select(Team).order_by(Team.name))

        return list(result.scalars().all())

    def update_team(
        self,
        db: Session,
        *,
        team: Team,
        name: str | None,
        description: str | None,
    ) -> Team:
        if name is not None and name != team.name:
            result = db.execute(
                select(Team).where(
                    Team.name == name,
                    Team.id != team.id,
                )
            )

            if result.scalar_one_or_none() is not None:
                raise ValueError("A team with this name already exists")

            team.name = name

        if description is not None:
            team.description = description

        db.commit()
        db.refresh(team)

        return team

    def delete_team(
        self,
        db: Session,
        *,
        team: Team,
    ) -> None:
        result = db.execute(
            select(Task.id)
            .where(
                Task.team_id == team.id,
            )
            .limit(1)
        )

        if result.scalar_one_or_none() is not None:
            raise ValueError("A team cannot be deleted while it contains tasks")

        db.delete(team)
        db.commit()

    def add_member(
        self,
        db: Session,
        *,
        team_id: UUID,
        user_id: UUID,
    ) -> TeamMember:
        user_result = db.execute(
            select(User).where(
                User.id == user_id,
                User.is_active.is_(True),
            )
        )

        user = user_result.scalar_one_or_none()

        if user is None:
            raise ValueError("User not found")

        existing_result = db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
            )
        )

        if existing_result.scalar_one_or_none() is not None:
            raise ValueError("User is already a team member")

        membership = TeamMember(
            team_id=team_id,
            user_id=user_id,
        )

        db.add(membership)

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise ValueError("Unable to add user to team") from None

        db.refresh(membership)

        return membership

    def remove_member(
        self,
        db: Session,
        *,
        team_id: UUID,
        user_id: UUID,
    ) -> bool:
        result = db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
            )
        )

        membership = result.scalar_one_or_none()

        if membership is None:
            return False

        db.delete(membership)
        db.commit()

        return True

    def list_members(
        self,
        db: Session,
        *,
        team_id: UUID,
    ) -> list[TeamMember]:
        result = db.execute(
            select(TeamMember)
            .where(TeamMember.team_id == team_id)
            .order_by(TeamMember.joined_at)
        )

        return list(result.scalars().all())


team_service = TeamService()
