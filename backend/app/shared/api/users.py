"""User endpoints."""

from fastapi import APIRouter

from app.shared.api.deps import AdminUserDep, CurrentUserDep, DBDep
from app.schemas import (
    UserCreate,
    UserPasswordUpdate,
    UserResponse,
    UserUpdate,
)
from app.services import user_service

router = APIRouter()


@router.get("", response_model=list[UserResponse])
def list_users(
    db: DBDep,
    current_user: AdminUserDep,
    skip: int = 0,
    limit: int = 100,
) -> list[UserResponse]:
    """List users in the current organization."""
    users = user_service.get_users_by_organization(
        db,
        organization_id=current_user.organization_id,
        skip=skip,
        limit=limit,
    )
    return [UserResponse.model_validate(user) for user in users]


@router.post("", response_model=UserResponse, status_code=201)
def create_user(
    user_in: UserCreate,
    db: DBDep,
    current_user: AdminUserDep,
) -> UserResponse:
    """Create a new user (admin only)."""
    # Ensure user is created in the same organization
    user_data = user_in.model_copy(update={"organization_id": current_user.organization_id})
    user = user_service.create(db, obj_in=user_data)
    return UserResponse.model_validate(user)


@router.get("/me", response_model=UserResponse)
def get_current_user_endpoint(
    db: DBDep,
    current_user: CurrentUserDep,
) -> UserResponse:
    """Get the current authenticated user."""
    from app.models import User

    user = db.get(User, current_user.id)
    if user:
        return UserResponse.model_validate(user)

    return UserResponse(
        id=current_user.id,
        organization_id=current_user.organization_id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        role=current_user.role,
        is_active=True,
    )


@router.patch("/me", response_model=UserResponse)
def update_current_user(
    user_in: UserUpdate,
    db: DBDep,
    current_user: CurrentUserDep,
) -> UserResponse:
    """Update the current user's profile."""
    from app.models import User
    from app.core.exceptions import NotFoundError

    user = db.get(User, current_user.id)
    if not user:
        raise NotFoundError(message="User not found")

    # Users cannot change their own role or is_active status
    update_data = user_in.model_dump(exclude_unset=True, exclude={"role", "is_active"})
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    db: DBDep,
    current_user: AdminUserDep,
) -> UserResponse:
    """Get a user by ID."""
    user = user_service.get_or_404(db, user_id, organization_id=current_user.organization_id)
    return UserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    user_in: UserUpdate,
    db: DBDep,
    current_user: AdminUserDep,
) -> UserResponse:
    """Update a user (admin only)."""
    user = user_service.get_or_404(db, user_id, organization_id=current_user.organization_id)
    updated = user_service.update(db, db_obj=user, obj_in=user_in)
    return UserResponse.model_validate(updated)


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: str,
    db: DBDep,
    current_user: AdminUserDep,
) -> None:
    """Delete a user (admin only)."""
    user_service.delete(db, user_id, organization_id=current_user.organization_id)


@router.post("/me/password", response_model=UserResponse)
def update_password(
    password_update: UserPasswordUpdate,
    db: DBDep,
    current_user: CurrentUserDep,
) -> UserResponse:
    """Update the current user's password."""
    from app.models import User
    from app.core.exceptions import NotFoundError

    user = db.get(User, current_user.user_id)
    if not user:
        raise NotFoundError(message="User not found")

    updated = user_service.update_password(
        db, user=user, password_update=password_update
    )
    return UserResponse.model_validate(updated)
