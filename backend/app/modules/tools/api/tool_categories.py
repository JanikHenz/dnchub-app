"""Tool category endpoints."""

from fastapi import APIRouter

from app.shared.api.deps import CurrentUserDep, DBDep, FleetManagerDep
from app.schemas import (
    ToolCategoryCreate,
    ToolCategoryResponse,
    ToolCategoryUpdate,
)
from app.services import tool_category_service

router = APIRouter()


@router.get("", response_model=list[ToolCategoryResponse])
def list_tool_categories(
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
) -> list[ToolCategoryResponse]:
    """List tool categories in the organization."""
    categories = tool_category_service.get_multi(
        db,
        skip=skip,
        limit=limit,
        organization_id=current_user.organization_id,
    )
    return [ToolCategoryResponse.model_validate(c) for c in categories]


@router.post("", response_model=ToolCategoryResponse, status_code=201)
def create_tool_category(
    category_in: ToolCategoryCreate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> ToolCategoryResponse:
    """Create a new tool category."""
    category_data = category_in.model_copy(
        update={"organization_id": current_user.organization_id}
    )
    category = tool_category_service.create(db, obj_in=category_data)
    return ToolCategoryResponse.model_validate(category)


@router.get("/{category_id}", response_model=ToolCategoryResponse)
def get_tool_category(
    category_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> ToolCategoryResponse:
    """Get a tool category by ID."""
    category = tool_category_service.get_or_404(db, category_id, organization_id=current_user.organization_id)
    return ToolCategoryResponse.model_validate(category)


@router.put("/{category_id}", response_model=ToolCategoryResponse)
def update_tool_category(
    category_id: str,
    category_in: ToolCategoryUpdate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> ToolCategoryResponse:
    """Update a tool category."""
    category = tool_category_service.get_or_404(db, category_id, organization_id=current_user.organization_id)
    updated = tool_category_service.update(db, db_obj=category, obj_in=category_in)
    return ToolCategoryResponse.model_validate(updated)


@router.delete("/{category_id}", status_code=204)
def delete_tool_category(
    category_id: str,
    db: DBDep,
    current_user: FleetManagerDep,
) -> None:
    """Delete a tool category (soft delete)."""
    tool_category_service.delete(db, category_id, organization_id=current_user.organization_id)
