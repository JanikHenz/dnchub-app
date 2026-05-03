"""Fuel pump delivery endpoints."""

from datetime import date

from fastapi import APIRouter, Query

from app.shared.api.deps import CurrentUserDep, DBDep
from app.schemas import (
    FuelPumpDeliveryCreate,
    FuelPumpDeliveryResponse,
    FuelPumpDeliveryUpdate,
)
from app.services import fuel_pump_delivery_service

router = APIRouter()


@router.get("", response_model=list[FuelPumpDeliveryResponse])
def list_fuel_pump_deliveries(
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
    pump_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[FuelPumpDeliveryResponse]:
    """List fuel pump deliveries with optional filters."""
    if pump_id:
        deliveries = fuel_pump_delivery_service.get_by_pump(
            db,
            pump_id=pump_id,
            organization_id=current_user.organization_id,
            skip=skip,
            limit=limit,
        )
    elif start_date and end_date:
        deliveries = fuel_pump_delivery_service.get_by_date_range(
            db,
            organization_id=current_user.organization_id,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=limit,
        )
    else:
        deliveries = fuel_pump_delivery_service.get_multi(
            db,
            skip=skip,
            limit=limit,
            organization_id=current_user.organization_id,
        )
    return [FuelPumpDeliveryResponse.model_validate(d) for d in deliveries]


@router.post("", response_model=FuelPumpDeliveryResponse, status_code=201)
def create_fuel_pump_delivery(
    delivery_in: FuelPumpDeliveryCreate,
    db: DBDep,
    current_user: CurrentUserDep,
) -> FuelPumpDeliveryResponse:
    """Create a new fuel pump delivery (automatically updates pump level)."""
    delivery_data = delivery_in.model_copy(
        update={"organization_id": current_user.organization_id}
    )
    delivery = fuel_pump_delivery_service.create(db, obj_in=delivery_data)
    return FuelPumpDeliveryResponse.model_validate(delivery)


@router.get("/summary")
def get_delivery_summary(
    db: DBDep,
    current_user: CurrentUserDep,
    start_date: date = Query(..., description="Start date for summary"),
    end_date: date = Query(..., description="End date for summary"),
) -> dict:
    """Get delivery summary for a date range."""
    return fuel_pump_delivery_service.get_summary(
        db,
        organization_id=current_user.organization_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/pump/{pump_id}", response_model=list[FuelPumpDeliveryResponse])
def list_deliveries_by_pump(
    pump_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
) -> list[FuelPumpDeliveryResponse]:
    """List all deliveries for a specific pump."""
    deliveries = fuel_pump_delivery_service.get_by_pump(
        db,
        pump_id=pump_id,
        organization_id=current_user.organization_id,
        skip=skip,
        limit=limit,
    )
    return [FuelPumpDeliveryResponse.model_validate(d) for d in deliveries]


@router.get("/{delivery_id}", response_model=FuelPumpDeliveryResponse)
def get_fuel_pump_delivery(
    delivery_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> FuelPumpDeliveryResponse:
    """Get a fuel pump delivery by ID."""
    delivery = fuel_pump_delivery_service.get_or_404(db, delivery_id, organization_id=current_user.organization_id)
    return FuelPumpDeliveryResponse.model_validate(delivery)


@router.patch("/{delivery_id}", response_model=FuelPumpDeliveryResponse)
def update_fuel_pump_delivery(
    delivery_id: str,
    delivery_in: FuelPumpDeliveryUpdate,
    db: DBDep,
    current_user: CurrentUserDep,
) -> FuelPumpDeliveryResponse:
    """Update a fuel pump delivery."""
    delivery = fuel_pump_delivery_service.get_or_404(db, delivery_id, organization_id=current_user.organization_id)
    updated = fuel_pump_delivery_service.update(db, db_obj=delivery, obj_in=delivery_in)
    return FuelPumpDeliveryResponse.model_validate(updated)


@router.delete("/{delivery_id}", status_code=204)
def delete_fuel_pump_delivery(
    delivery_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> None:
    """Delete a fuel pump delivery (soft delete)."""
    fuel_pump_delivery_service.delete(db, delivery_id, organization_id=current_user.organization_id)
