from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.models.team import Team
from app.models.team_member import TeamMember
from app.models.user import User, UserRole


class TeamService:
    async def list_teams_for_user(
        self,
        db: AsyncSession,
        *,
        user: User,
    ) -> list[Team]:
        if user.role == UserRole.ADMIN:
            return await self.list_teams(db)

        result = await db.execute(
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

    async def create_team(
        self,
        db: AsyncSession,
        *,
        name: str,
        description: str | None,
    ) -> Team:
        result = await db.execute(select(Team).where(Team.name == name))

        if result.scalar_one_or_none() is not None:
            raise ValueError("A team with this name already exists")

        team = Team(
            name=name,
            description=description,
        )

        db.add(team)
        await db.commit()
        await db.refresh(team)

        return team

    async def get_team(
        self,
        db: AsyncSession,
        *,
        team_id: UUID,
    ) -> Team | None:
        result = await db.execute(select(Team).where(Team.id == team_id))

        return result.scalar_one_or_none()

    async def list_teams(
        self,
        db: AsyncSession,
    ) -> list[Team]:
        result = await db.execute(select(Team).order_by(Team.name))

        return list(result.scalars().all())

    async def update_team(
        self,
        db: AsyncSession,
        *,
        team: Team,
        name: str | None,
        description: str | None,
    ) -> Team:
        if name is not None and name != team.name:
            result = await db.execute(
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

        await db.commit()
        await db.refresh(team)

        return team

    async def delete_team(
        self,
        db: AsyncSession,
        *,
        team: Team,
    ) -> None:
        result = await db.execute(
            select(Task.id)
            .where(
                Task.team_id == team.id,
            )
            .limit(1)
        )

        if result.scalar_one_or_none() is not None:
            raise ValueError("A team cannot be deleted while it contains tasks")

        await db.delete(team)
        await db.commit()

    async def add_member(
        self,
        db: AsyncSession,
        *,
        team_id: UUID,
        user_id: UUID,
    ) -> TeamMember:
        user_result = await db.execute(
            select(User).where(
                User.id == user_id,
                User.is_active.is_(True),
            )
        )

        user = user_result.scalar_one_or_none()

        if user is None:
            raise ValueError("User not found")

        existing_result = await db.execute(
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
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise ValueError("Unable to add user to team") from None

        await db.refresh(membership)

        return membership

    async def remove_member(
        self,
        db: AsyncSession,
        *,
        team_id: UUID,
        user_id: UUID,
    ) -> bool:
        result = await db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user_id,
            )
        )

        membership = result.scalar_one_or_none()

        if membership is None:
            return False

        await db.delete(membership)
        await db.commit()

        return True

    async def list_members(
        self,
        db: AsyncSession,
        *,
        team_id: UUID,
    ) -> list[TeamMember]:
        result = await db.execute(
            select(TeamMember)
            .where(TeamMember.team_id == team_id)
            .order_by(TeamMember.joined_at)
        )

        return list(result.scalars().all())


team_service = TeamService()
