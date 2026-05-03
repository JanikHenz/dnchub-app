"""SAT assistance service."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.sat.models.assistance import SatAssistance
from app.modules.sat.schemas.assistance import SatAssistanceCreate, SatAssistanceUpdate
from app.shared.models.enums import AssistancePriority, AssistanceStatus
from app.shared.services.base import BaseService


class SatAssistanceService(BaseService[SatAssistance, SatAssistanceCreate, SatAssistanceUpdate]):
    """SAT assistance service with eager-loading and search."""

    def __init__(self):
        super().__init__(SatAssistance)

    def get_detail(
        self,
        db: Session,
        assistance_id: str,
        *,
        organization_id: str | None = None,
    ) -> SatAssistance | None:
        """Get an assistance with all relationships eagerly loaded."""
        result = db.execute(
            select(SatAssistance)
            .where(
                SatAssistance.id == assistance_id,
                SatAssistance.deleted_at.is_(None),
                SatAssistance.organization_id == organization_id
            )
            .options(
                selectinload(SatAssistance.report),
                selectinload(SatAssistance.customer),
                selectinload(SatAssistance.machine),
                selectinload(SatAssistance.technician),
                selectinload(SatAssistance.service_type),
            )
        )
        return result.scalar_one_or_none()

    def search(
        self,
        db: Session,
        *,
        organization_id: str,
        status: AssistanceStatus | None = None,
        priority: AssistancePriority | None = None,
        customer_id: str | None = None,
        technician_id: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SatAssistance]:
        """Search assistances with multiple filters."""
        stmt = select(SatAssistance).where(
            SatAssistance.organization_id == organization_id,
            SatAssistance.deleted_at.is_(None),
        )
        if status:
            stmt = stmt.where(SatAssistance.status == status)
        if priority:
            stmt = stmt.where(SatAssistance.priority == priority)
        if customer_id:
            stmt = stmt.where(SatAssistance.customer_id == customer_id)
        if technician_id:
            stmt = stmt.where(SatAssistance.technician_id == technician_id)
        stmt = stmt.order_by(SatAssistance.created_at.desc())
        stmt = stmt.offset(skip).limit(limit)
        result = db.execute(stmt)
        return list(result.scalars().all())


sat_assistance_service = SatAssistanceService()
