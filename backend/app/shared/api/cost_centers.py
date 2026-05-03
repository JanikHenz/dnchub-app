"""Cost center endpoints."""

from datetime import date

from fastapi import APIRouter, Query

from app.shared.api.deps import CurrentUserDep, DBDep, FleetManagerDep
from app.models.enums import CostType
from app.schemas import (
    CostAllocationCreate,
    CostAllocationResponse,
    CostAllocationUpdate,
    CostCenterCreate,
    CostCenterResponse,
    CostCenterUpdate,
)
from app.services import cost_allocation_service, cost_center_service

router = APIRouter()


# Cost Center endpoints
@router.get("", response_model=list[CostCenterResponse])
def list_cost_centers(
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
) -> list[CostCenterResponse]:
    """List cost centers."""
    if active_only:
        cost_centers = cost_center_service.get_active_cost_centers(
            db, organization_id=current_user.organization_id
        )
    else:
        cost_centers = cost_center_service.get_multi(
            db,
            skip=skip,
            limit=limit,
            organization_id=current_user.organization_id,
        )
    return [CostCenterResponse.model_validate(cc) for cc in cost_centers]


@router.post("", response_model=CostCenterResponse, status_code=201)
def create_cost_center(
    cost_center_in: CostCenterCreate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> CostCenterResponse:
    """Create a cost center."""
    cost_center_data = cost_center_in.model_copy(update={"organization_id": current_user.organization_id})
    cost_center = cost_center_service.create(db, obj_in=cost_center_data)
    return CostCenterResponse.model_validate(cost_center)


@router.get("/{cost_center_id}", response_model=CostCenterResponse)
def get_cost_center(
    cost_center_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> CostCenterResponse:
    """Get a cost center by ID."""
    cost_center = cost_center_service.get_or_404(db, cost_center_id, organization_id=current_user.organization_id)
    return CostCenterResponse.model_validate(cost_center)


@router.patch("/{cost_center_id}", response_model=CostCenterResponse)
def update_cost_center(
    cost_center_id: str,
    cost_center_in: CostCenterUpdate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> CostCenterResponse:
    """Update a cost center."""
    cost_center = cost_center_service.get_or_404(db, cost_center_id, organization_id=current_user.organization_id)
    updated = cost_center_service.update(
        db, db_obj=cost_center, obj_in=cost_center_in
    )
    return CostCenterResponse.model_validate(updated)


@router.delete("/{cost_center_id}", status_code=204)
def delete_cost_center(
    cost_center_id: str,
    db: DBDep,
    current_user: FleetManagerDep,
) -> None:
    """Delete a cost center."""
    cost_center_service.delete(db, cost_center_id, organization_id=current_user.organization_id)


@router.get("/{cost_center_id}/summary")
def get_cost_center_summary(
    cost_center_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
    start_date: date = Query(...),
    end_date: date = Query(...),
) -> dict:
    """Get cost summary for a cost center."""
    return cost_center_service.get_cost_summary(
        db,
        cost_center_id=cost_center_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/{cost_center_id}/budget-status")
def get_budget_status(
    cost_center_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
    start_date: date = Query(...),
    end_date: date = Query(...),
) -> dict:
    """Get budget status for a cost center."""
    cost_center = cost_center_service.get_or_404(db, cost_center_id, organization_id=current_user.organization_id)
    return cost_center_service.check_budget(
        db,
        cost_center=cost_center,
        start_date=start_date,
        end_date=end_date,
    )


# Cost Allocation endpoints
@router.get("/allocations", response_model=list[CostAllocationResponse])
def list_cost_allocations(
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
    cost_center_id: str | None = None,
    vehicle_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    cost_type: CostType | None = None,
) -> list[CostAllocationResponse]:
    """List cost allocations with filters."""
    if cost_center_id:
        allocations = cost_allocation_service.get_allocations_by_cost_center(
            db, cost_center_id, skip=skip, limit=limit
        )
    elif vehicle_id:
        allocations = cost_allocation_service.get_allocations_by_vehicle(
            db, vehicle_id, skip=skip, limit=limit
        )
    elif start_date and end_date:
        allocations = cost_allocation_service.get_allocations_by_date_range(
            db,
            organization_id=current_user.organization_id,
            start_date=start_date,
            end_date=end_date,
            cost_type=cost_type,
            skip=skip,
            limit=limit,
        )
    else:
        allocations = cost_allocation_service.get_multi(
            db,
            skip=skip,
            limit=limit,
            organization_id=current_user.organization_id,
        )
    return [CostAllocationResponse.model_validate(a) for a in allocations]


@router.post("/allocations", response_model=CostAllocationResponse, status_code=201)
def create_cost_allocation(
    allocation_in: CostAllocationCreate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> CostAllocationResponse:
    """Create a cost allocation."""
    allocation_data = allocation_in.model_copy(update={"organization_id": current_user.organization_id})
    allocation = cost_allocation_service.create(db, obj_in=allocation_data)
    return CostAllocationResponse.model_validate(allocation)


@router.get("/allocations/breakdown")
def get_cost_breakdown(
    db: DBDep,
    current_user: CurrentUserDep,
    start_date: date = Query(...),
    end_date: date = Query(...),
) -> list[dict]:
    """Get cost breakdown by type."""
    return cost_allocation_service.get_cost_breakdown_by_type(
        db,
        organization_id=current_user.organization_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/allocations/{allocation_id}", response_model=CostAllocationResponse)
def get_cost_allocation(
    allocation_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> CostAllocationResponse:
    """Get a cost allocation by ID."""
    allocation = cost_allocation_service.get_or_404(db, allocation_id, organization_id=current_user.organization_id)
    return CostAllocationResponse.model_validate(allocation)


@router.patch("/allocations/{allocation_id}", response_model=CostAllocationResponse)
def update_cost_allocation(
    allocation_id: str,
    allocation_in: CostAllocationUpdate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> CostAllocationResponse:
    """Update a cost allocation."""
    allocation = cost_allocation_service.get_or_404(db, allocation_id, organization_id=current_user.organization_id)
    updated = cost_allocation_service.update(
        db, db_obj=allocation, obj_in=allocation_in
    )
    return CostAllocationResponse.model_validate(updated)


@router.delete("/allocations/{allocation_id}", status_code=204)
def delete_cost_allocation(
    allocation_id: str,
    db: DBDep,
    current_user: FleetManagerDep,
) -> None:
    """Delete a cost allocation."""
    cost_allocation_service.delete(db, allocation_id, organization_id=current_user.organization_id)
