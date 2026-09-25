from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.authorization import require_roles
from app.core.database import get_db_session
from app.core.team_authorization import (
    require_team_access,
    require_team_manager_access,
)
from app.models.team import Team
from app.models.user import User, UserRole
from app.schemas.team import (
    TeamCreateRequest,
    TeamMemberResponse,
    TeamResponse,
    TeamUpdateRequest,
)
from app.services.team import team_service

router = APIRouter(
    prefix="/teams",
    tags=["Teams"],
)


@router.post(
    "",
    response_model=TeamResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_team(
    request: TeamCreateRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db_session),
) -> TeamResponse:
    try:
        team = team_service.create_team(
            db,
            name=request.name,
            description=request.description,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return TeamResponse.model_validate(team)


@router.get(
    "",
    response_model=list[TeamResponse],
)
def list_teams(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[TeamResponse]:
    teams = team_service.list_teams_for_user(
        db,
        user=current_user,
    )

    return [TeamResponse.model_validate(team) for team in teams]


@router.get(
    "/{team_id}",
    response_model=TeamResponse,
)
def get_team(
    team: Team = Depends(require_team_access),
) -> TeamResponse:
    return TeamResponse.model_validate(team)


@router.patch(
    "/{team_id}",
    response_model=TeamResponse,
)
def update_team(
    request: TeamUpdateRequest,
    team_id: UUID,
    current_user: User = Depends(require_team_manager_access),
    db: Session = Depends(get_db_session),
) -> TeamResponse:
    team = team_service.get_team(
        db,
        team_id=team_id,
    )

    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    try:
        team = team_service.update_team(
            db,
            team=team,
            name=request.name,
            description=request.description,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return TeamResponse.model_validate(team)


@router.delete(
    "/{team_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_team(
    team_id: UUID,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db_session),
) -> None:
    team = team_service.get_team(
        db,
        team_id=team_id,
    )

    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    try:
        team_service.delete_team(
            db,
            team=team,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post(
    "/{team_id}/members/{user_id}",
    response_model=TeamMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_team_member(
    team_id: UUID,
    user_id: UUID,
    current_user: User = Depends(require_team_manager_access),
    db: Session = Depends(get_db_session),
) -> TeamMemberResponse:
    team = team_service.get_team(
        db,
        team_id=team_id,
    )

    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    try:
        membership = team_service.add_member(
            db,
            team_id=team_id,
            user_id=user_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return TeamMemberResponse.model_validate(membership)


@router.delete(
    "/{team_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_team_member(
    team_id: UUID,
    user_id: UUID,
    current_user: User = Depends(require_team_manager_access),
    db: Session = Depends(get_db_session),
) -> None:
    removed = team_service.remove_member(
        db,
        team_id=team_id,
        user_id=user_id,
    )

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team membership not found",
        )


@router.get(
    "/{team_id}/members",
    response_model=list[TeamMemberResponse],
)
def list_team_members(
    team_id: UUID,
    current_user: User = Depends(require_team_access),
    db: Session = Depends(get_db_session),
) -> list[TeamMemberResponse]:
    members = team_service.list_members(
        db,
        team_id=team_id,
    )

    return [TeamMemberResponse.model_validate(member) for member in members]
