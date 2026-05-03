"""Tool location endpoints."""

from fastapi import APIRouter

from app.shared.api.deps import CurrentUserDep, DBDep, FleetManagerDep
from app.schemas import (
    ToolLocationCreate,
    ToolLocationResponse,
    ToolLocationUpdate,
)
from app.services import tool_location_service

router = APIRouter()


@router.get("", response_model=list[ToolLocationResponse])
def list_tool_locations(
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
) -> list[ToolLocationResponse]:
    """List tool locations in the organization."""
    locations = tool_location_service.get_multi(
        db,
        skip=skip,
        limit=limit,
        organization_id=current_user.organization_id,
    )
    return [ToolLocationResponse.model_validate(loc) for loc in locations]


@router.post("", response_model=ToolLocationResponse, status_code=201)
def create_tool_location(
    location_in: ToolLocationCreate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> ToolLocationResponse:
    """Create a new tool location."""
    location_data = location_in.model_copy(
        update={"organization_id": current_user.organization_id}
    )
    location = tool_location_service.create(db, obj_in=location_data)
    return ToolLocationResponse.model_validate(location)


@router.get("/{location_id}", response_model=ToolLocationResponse)
def get_tool_location(
    location_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> ToolLocationResponse:
    """Get a tool location by ID."""
    location = tool_location_service.get_or_404(db, location_id, organization_id=current_user.organization_id)
    return ToolLocationResponse.model_validate(location)


@router.put("/{location_id}", response_model=ToolLocationResponse)
def update_tool_location(
    location_id: str,
    location_in: ToolLocationUpdate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> ToolLocationResponse:
    """Update a tool location."""
    location = tool_location_service.get_or_404(db, location_id, organization_id=current_user.organization_id)
    updated = tool_location_service.update(db, db_obj=location, obj_in=location_in)
    return ToolLocationResponse.model_validate(updated)


@router.delete("/{location_id}", status_code=204)
def delete_tool_location(
    location_id: str,
    db: DBDep,
    current_user: FleetManagerDep,
) -> None:
    """Delete a tool location (soft delete)."""
    tool_location_service.delete(db, location_id, organization_id=current_user.organization_id)
