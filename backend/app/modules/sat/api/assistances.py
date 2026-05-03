"""SAT assistance endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.shared.api.deps import CurrentUserDep, DBDep, SatManagerDep
from app.shared.models.enums import AssistancePriority, AssistanceStatus
from app.modules.sat.schemas import (
    SatAssistanceCreate,
    SatAssistanceResponse,
    SatAssistanceStatusUpdate,
    SatAssistanceUpdate,
)
from app.modules.sat.services import sat_assistance_service

router = APIRouter()


@router.get("", response_model=list[SatAssistanceResponse])
def list_assistances(
    db: DBDep,
    current_user: CurrentUserDep,
    status: AssistanceStatus | None = None,
    priority: AssistancePriority | None = None,
    customer_id: str | None = None,
    technician_id: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[SatAssistanceResponse]:
    """List SAT assistances with optional filters."""
    assistances = sat_assistance_service.search(
        db,
        organization_id=current_user.organization_id,
        status=status,
        priority=priority,
        customer_id=customer_id,
        technician_id=technician_id,
        skip=skip,
        limit=limit,
    )
    return [SatAssistanceResponse.model_validate(a) for a in assistances]


@router.post("", response_model=SatAssistanceResponse, status_code=201)
def create_assistance(
    assistance_in: SatAssistanceCreate,
    db: DBDep,
    current_user: SatManagerDep,
) -> SatAssistanceResponse:
    """Create a new SAT assistance."""
    assistance_data = assistance_in.model_copy(
        update={"organization_id": current_user.organization_id}
    )
    assistance = sat_assistance_service.create(db, obj_in=assistance_data)
    return SatAssistanceResponse.model_validate(assistance)


@router.get("/{assistance_id}", response_model=SatAssistanceResponse)
def get_assistance(
    assistance_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> SatAssistanceResponse:
    """Get a SAT assistance by ID with eagerly loaded relationships."""
    assistance = sat_assistance_service.get_detail(db, assistance_id, organization_id=current_user.organization_id)
    if assistance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SatAssistance with id '{assistance_id}' not found",
        )
    return SatAssistanceResponse.model_validate(assistance)


@router.patch("/{assistance_id}", response_model=SatAssistanceResponse)
def update_assistance(
    assistance_id: str,
    assistance_in: SatAssistanceUpdate,
    db: DBDep,
    current_user: SatManagerDep,
) -> SatAssistanceResponse:
    """Update a SAT assistance."""
    assistance = sat_assistance_service.get_or_404(db, assistance_id, organization_id=current_user.organization_id)
    updated = sat_assistance_service.update(db, db_obj=assistance, obj_in=assistance_in)
    return SatAssistanceResponse.model_validate(updated)


@router.delete("/{assistance_id}", status_code=204)
def delete_assistance(
    assistance_id: str,
    db: DBDep,
    current_user: SatManagerDep,
) -> None:
    """Delete a SAT assistance."""
    sat_assistance_service.delete(db, assistance_id, organization_id=current_user.organization_id)


@router.patch("/{assistance_id}/status", response_model=SatAssistanceResponse)
def update_assistance_status(
    assistance_id: str,
    status_in: SatAssistanceStatusUpdate,
    db: DBDep,
    current_user: SatManagerDep,
) -> SatAssistanceResponse:
    """Update the status of a SAT assistance."""
    assistance = sat_assistance_service.get_or_404(db, assistance_id, organization_id=current_user.organization_id)
    updated = sat_assistance_service.update(db, db_obj=assistance, obj_in=status_in)
    return SatAssistanceResponse.model_validate(updated)
