"""Fuel endpoints."""

from datetime import date

from fastapi import APIRouter, Query

from app.shared.api.deps import CurrentUserDep, DBDep
from app.schemas import (
    FuelAnalytics,
    FuelEntryCreate,
    FuelEntryResponse,
    FuelEntryUpdate,
)
from app.services import fuel_service

router = APIRouter()


@router.get("", response_model=list[FuelEntryResponse])
def list_fuel_entries(
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
    vehicle_id: str | None = None,
    employee_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[FuelEntryResponse]:
    """List fuel entries with optional filters."""
    if vehicle_id:
        entries = fuel_service.get_entries_by_vehicle(
            db, vehicle_id, organization_id=current_user.organization_id, skip=skip, limit=limit
        )
    elif employee_id:
        entries = fuel_service.get_entries_by_employee(
            db, employee_id, organization_id=current_user.organization_id, skip=skip, limit=limit
        )
    elif start_date and end_date:
        entries = fuel_service.get_entries_by_date_range(
            db,
            organization_id=current_user.organization_id,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit,
        )
    else:
        entries = fuel_service.get_multi(
            db,
            skip=skip,
            limit=limit,
            organization_id=current_user.organization_id,
        )
    return [FuelEntryResponse.model_validate(e) for e in entries]


@router.post("", response_model=FuelEntryResponse, status_code=201)
def create_fuel_entry(
    entry_in: FuelEntryCreate,
    db: DBDep,
    current_user: CurrentUserDep,
) -> FuelEntryResponse:
    """Create a new fuel entry."""
    entry_data = entry_in.model_copy(update={"organization_id": current_user.organization_id})
    entry = fuel_service.create(db, obj_in=entry_data)
    return FuelEntryResponse.model_validate(entry)


@router.get("/analytics", response_model=FuelAnalytics)
def get_fuel_analytics(
    db: DBDep,
    current_user: CurrentUserDep,
    start_date: date = Query(..., description="Start date for analytics"),
    end_date: date = Query(..., description="End date for analytics"),
) -> FuelAnalytics:
    """Get fuel analytics for a date range."""
    return fuel_service.get_analytics(
        db,
        organization_id=current_user.organization_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/vehicle/{vehicle_id}", response_model=list[FuelEntryResponse])
def list_fuel_entries_by_vehicle(
    vehicle_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
) -> list[FuelEntryResponse]:
    """List fuel entries for a specific vehicle."""
    entries = fuel_service.get_entries_by_vehicle(
        db, vehicle_id, skip=skip, limit=limit
    )
    return [FuelEntryResponse.model_validate(e) for e in entries]


@router.get("/employee/{employee_id}", response_model=list[FuelEntryResponse])
def list_fuel_entries_by_employee(
    employee_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
) -> list[FuelEntryResponse]:
    """List fuel entries for a specific employee."""
    entries = fuel_service.get_entries_by_employee(
        db, employee_id, skip=skip, limit=limit
    )
    return [FuelEntryResponse.model_validate(e) for e in entries]


@router.get("/{entry_id}", response_model=FuelEntryResponse)
def get_fuel_entry(
    entry_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> FuelEntryResponse:
    """Get a fuel entry by ID."""
    entry = fuel_service.get_or_404(db, entry_id, organization_id=current_user.organization_id)
    return FuelEntryResponse.model_validate(entry)


@router.patch("/{entry_id}", response_model=FuelEntryResponse)
def update_fuel_entry(
    entry_id: str,
    entry_in: FuelEntryUpdate,
    db: DBDep,
    current_user: CurrentUserDep,
) -> FuelEntryResponse:
    """Update a fuel entry."""
    entry = fuel_service.get_or_404(db, entry_id, organization_id=current_user.organization_id)
    updated = fuel_service.update(db, db_obj=entry, obj_in=entry_in)
    return FuelEntryResponse.model_validate(updated)


@router.delete("/{entry_id}", status_code=204)
def delete_fuel_entry(
    entry_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> None:
    """Delete a fuel entry."""
    fuel_service.delete(db, entry_id, organization_id=current_user.organization_id)
