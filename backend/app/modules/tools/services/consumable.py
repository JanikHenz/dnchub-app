"""Consumable service."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.tools.models.consumable import Consumable
from app.modules.tools.schemas.consumable import ConsumableCreate, ConsumableUpdate
from app.shared.models.enums import ConsumableStatus
from app.shared.services.base import BaseService


class ConsumableService(BaseService[Consumable, ConsumableCreate, ConsumableUpdate]):
    """Consumable service with stock management operations."""

    def __init__(self) -> None:
        super().__init__(Consumable)

    def get_by_erp_code(
        self,
        db: Session,
        organization_id: str,
        erp_code: str,
    ) -> Consumable | None:
        """Find a consumable by its ERP code within an organization."""
        result = db.execute(
            select(Consumable).where(
                Consumable.organization_id == organization_id,
                Consumable.erp_code == erp_code,
                Consumable.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    def get_by_case(
        self,
        db: Session,
        case_id: str,
        *,
        organization_id: str | None = None,
    ) -> list[Consumable]:
        """List all consumables stored in a specific case."""
        result = db.execute(
            select(Consumable).where(
                Consumable.case_id == case_id,
                Consumable.deleted_at.is_(None),
                Consumable.organization_id == organization_id
            )
        )
        return list(result.scalars().all())

    def get_low_stock(
        self,
        db: Session,
        organization_id: str,
    ) -> list[Consumable]:
        """Return consumables at or below their minimum quantity threshold."""
        result = db.execute(
            select(Consumable).where(
                Consumable.organization_id == organization_id,
                Consumable.deleted_at.is_(None),
                Consumable.current_quantity <= Consumable.minimum_quantity,
                Consumable.status.notin_([ConsumableStatus.RETIRED]),
            )
        )
        return list(result.scalars().all())

    def adjust_quantity(
        self,
        db: Session,
        consumable: Consumable,
        delta: int,
    ) -> Consumable:
        """Add or remove stock. Automatically updates status based on resulting quantity."""
        new_qty = max(0, consumable.current_quantity + delta)
        consumable.current_quantity = new_qty

        # Auto-update status unless manually set to ordered/retired
        if consumable.status not in (ConsumableStatus.ORDERED, ConsumableStatus.RETIRED):
            if new_qty == 0:
                consumable.status = ConsumableStatus.OUT_OF_STOCK
            elif new_qty <= consumable.minimum_quantity:
                consumable.status = ConsumableStatus.LOW_STOCK
            else:
                consumable.status = ConsumableStatus.IN_STOCK

        db.commit()
        db.refresh(consumable)
        return consumable


consumable_service = ConsumableService()
