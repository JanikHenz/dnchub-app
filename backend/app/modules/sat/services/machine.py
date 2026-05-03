"""SAT machine service."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.sat.models.machine import SatMachine
from app.modules.sat.schemas.machine import SatMachineCreate, SatMachineUpdate
from app.shared.models.enums import MachineType
from app.shared.services.base import BaseService


class SatMachineService(BaseService[SatMachine, SatMachineCreate, SatMachineUpdate]):
    """SAT machine service with customer and search capabilities."""

    def __init__(self):
        super().__init__(SatMachine)

    def get_by_customer(
        self,
        db: Session,
        customer_id: str,
        *,
        organization_id: str,
    ) -> list[SatMachine]:
        """Get all machines for a customer, excluding deleted."""
        result = db.execute(
            select(SatMachine).where(
                SatMachine.customer_id == customer_id,
                SatMachine.deleted_at.is_(None),
                SatMachine.organization_id == organization_id
            )
        )
        return list(result.scalars().all())

    def search(
        self,
        db: Session,
        *,
        organization_id: str,
        customer_id: str | None = None,
        machine_type: MachineType | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SatMachine]:
        """Search machines by organization, customer, and type."""
        stmt = select(SatMachine).where(
            SatMachine.organization_id == organization_id,
            SatMachine.deleted_at.is_(None),
        )
        if customer_id:
            stmt = stmt.where(SatMachine.customer_id == customer_id)
        if machine_type:
            stmt = stmt.where(SatMachine.machine_type == machine_type)
        stmt = stmt.offset(skip).limit(limit)
        result = db.execute(stmt)
        return list(result.scalars().all())


sat_machine_service = SatMachineService()
