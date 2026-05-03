"""Consumable endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.shared.api.deps import CurrentUserDep, DBDep, FleetManagerDep
from app.schemas import (
    ConsumableCreate,
    ConsumableResponse,
    ConsumableUpdate,
    ConsumableAdjustQuantity,
)
from app.services import consumable_service

router = APIRouter()


@router.get("", response_model=list[ConsumableResponse])
def list_consumables(
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 500,
    case_id: str | None = None,
    low_stock_only: bool = False,
) -> list[ConsumableResponse]:
    """List consumables in the organization."""
    if case_id:
        items = consumable_service.get_by_case(db, case_id=case_id, organization_id=current_user.organization_id)
    elif low_stock_only:
        items = consumable_service.get_low_stock(
            db, organization_id=current_user.organization_id
        )
    else:
        items = consumable_service.get_multi(
            db,
            skip=skip,
            limit=limit,
            organization_id=current_user.organization_id,
        )
    return [ConsumableResponse.model_validate(c) for c in items]


@router.post("", response_model=ConsumableResponse, status_code=201)
def create_consumable(
    consumable_in: ConsumableCreate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> ConsumableResponse:
    """Create a new consumable."""
    data = consumable_in.model_copy(
        update={"organization_id": current_user.organization_id}
    )
    consumable = consumable_service.create(db, obj_in=data)
    return ConsumableResponse.model_validate(consumable)


@router.get("/by-erp/{erp_code}", response_model=ConsumableResponse)
def get_consumable_by_erp_code(
    erp_code: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> ConsumableResponse:
    """Find a consumable by its ERP code."""
    consumable = consumable_service.get_by_erp_code(
        db,
        organization_id=current_user.organization_id,
        erp_code=erp_code,
    )
    if consumable is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Consumable with ERP code '{erp_code}' not found",
        )
    return ConsumableResponse.model_validate(consumable)


@router.get("/{consumable_id}", response_model=ConsumableResponse)
def get_consumable(
    consumable_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> ConsumableResponse:
    """Get a consumable by ID."""
    consumable = consumable_service.get_or_404(db, consumable_id, organization_id=current_user.organization_id)
    return ConsumableResponse.model_validate(consumable)


@router.put("/{consumable_id}", response_model=ConsumableResponse)
def update_consumable(
    consumable_id: str,
    consumable_in: ConsumableUpdate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> ConsumableResponse:
    """Update a consumable."""
    consumable = consumable_service.get_or_404(db, consumable_id, organization_id=current_user.organization_id)
    updated = consumable_service.update(db, db_obj=consumable, obj_in=consumable_in)
    return ConsumableResponse.model_validate(updated)


@router.post("/{consumable_id}/adjust-quantity", response_model=ConsumableResponse)
def adjust_quantity(
    consumable_id: str,
    adjustment: ConsumableAdjustQuantity,
    db: DBDep,
    current_user: FleetManagerDep,
) -> ConsumableResponse:
    """Adjust consumable stock quantity. Use positive delta to add, negative to consume."""
    consumable = consumable_service.get_or_404(db, consumable_id, organization_id=current_user.organization_id)
    updated = consumable_service.adjust_quantity(
        db, consumable=consumable, delta=adjustment.delta
    )
    return ConsumableResponse.model_validate(updated)


@router.delete("/{consumable_id}", status_code=204)
def delete_consumable(
    consumable_id: str,
    db: DBDep,
    current_user: FleetManagerDep,
) -> None:
    """Soft-delete a consumable."""
    consumable_service.delete(db, consumable_id, organization_id=current_user.organization_id)
