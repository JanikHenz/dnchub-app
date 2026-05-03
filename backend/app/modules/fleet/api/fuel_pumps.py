"""Fuel pump endpoints."""

from decimal import Decimal

from fastapi import APIRouter

from app.shared.api.deps import CurrentUserDep, DBDep
from app.models.enums import FuelType
from app.schemas import (
    FuelPumpCreate,
    FuelPumpLevelAdjustment,
    FuelPumpResponse,
    FuelPumpUpdate,
)
from app.services import fuel_pump_service

router = APIRouter()


@router.get("", response_model=list[FuelPumpResponse])
def list_fuel_pumps(
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
) -> list[FuelPumpResponse]:
    """List all fuel pumps for the organization."""
    pumps = fuel_pump_service.get_multi(
        db,
        skip=skip,
        limit=limit,
        organization_id=current_user.organization_id,
    )
    return [FuelPumpResponse.model_validate(p) for p in pumps]


@router.post("", response_model=FuelPumpResponse, status_code=201)
def create_fuel_pump(
    pump_in: FuelPumpCreate,
    db: DBDep,
    current_user: CurrentUserDep,
) -> FuelPumpResponse:
    """Create a new fuel pump."""
    pump_data = pump_in.model_copy(
        update={"organization_id": current_user.organization_id}
    )
    pump = fuel_pump_service.create(db, obj_in=pump_data)
    return FuelPumpResponse.model_validate(pump)


@router.get("/alerts", response_model=list[FuelPumpResponse])
def list_pumps_with_alerts(
    db: DBDep,
    current_user: CurrentUserDep,
) -> list[FuelPumpResponse]:
    """List fuel pumps with active alerts (low level or maintenance due)."""
    pumps = fuel_pump_service.get_with_alerts(
        db,
        organization_id=current_user.organization_id,
    )
    return [FuelPumpResponse.model_validate(p) for p in pumps]


@router.get("/stats")
def get_pump_stats(
    db: DBDep,
    current_user: CurrentUserDep,
) -> dict:
    """Get fuel pump statistics for the organization."""
    return fuel_pump_service.get_stats(
        db,
        organization_id=current_user.organization_id,
    )


@router.get("/by-fuel-type/{fuel_type}", response_model=list[FuelPumpResponse])
def list_pumps_by_fuel_type(
    fuel_type: FuelType,
    db: DBDep,
    current_user: CurrentUserDep,
    active_only: bool = True,
) -> list[FuelPumpResponse]:
    """List fuel pumps by fuel type (useful for POS pump selection)."""
    pumps = fuel_pump_service.get_by_fuel_type(
        db,
        organization_id=current_user.organization_id,
        fuel_type=fuel_type,
        active_only=active_only,
    )
    return [FuelPumpResponse.model_validate(p) for p in pumps]


@router.get("/{pump_id}", response_model=FuelPumpResponse)
def get_fuel_pump(
    pump_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> FuelPumpResponse:
    """Get a fuel pump by ID."""
    pump = fuel_pump_service.get_or_404(db, pump_id, organization_id=current_user.organization_id)
    return FuelPumpResponse.model_validate(pump)


@router.patch("/{pump_id}", response_model=FuelPumpResponse)
def update_fuel_pump(
    pump_id: str,
    pump_in: FuelPumpUpdate,
    db: DBDep,
    current_user: CurrentUserDep,
) -> FuelPumpResponse:
    """Update a fuel pump."""
    pump = fuel_pump_service.get_or_404(db, pump_id, organization_id=current_user.organization_id)
    updated = fuel_pump_service.update(db, db_obj=pump, obj_in=pump_in)
    return FuelPumpResponse.model_validate(updated)


@router.delete("/{pump_id}", status_code=204)
def delete_fuel_pump(
    pump_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> None:
    """Delete a fuel pump (soft delete)."""
    fuel_pump_service.delete(db, pump_id, organization_id=current_user.organization_id)


@router.post("/{pump_id}/adjust-level", response_model=FuelPumpResponse)
def adjust_pump_level(
    pump_id: str,
    adjustment: FuelPumpLevelAdjustment,
    db: DBDep,
    current_user: CurrentUserDep,
) -> FuelPumpResponse:
    """Manually adjust pump level (positive to add, negative to remove)."""
    pump = fuel_pump_service.adjust_level(
        db,
        pump_id=pump_id,
        adjustment=adjustment.adjustment,
        organization_id=current_user.organization_id,
    )
    return FuelPumpResponse.model_validate(pump)
