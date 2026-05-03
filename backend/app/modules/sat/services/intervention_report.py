"""SAT intervention report service."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.sat.models.intervention_report import SatInterventionReport
from app.modules.sat.schemas.intervention_report import (
    SatInterventionReportCreate,
    SatInterventionReportUpdate,
)
from app.shared.models.enums import ReportStatus
from app.shared.services.base import BaseService


class SatInterventionReportService(
    BaseService[SatInterventionReport, SatInterventionReportCreate, SatInterventionReportUpdate]
):
    """SAT intervention report service with assistance-level queries."""

    def __init__(self):
        super().__init__(SatInterventionReport)

    def get_by_assistance(
        self,
        db: Session,
        assistance_id: str,
        *,
        organization_id: str,
    ) -> SatInterventionReport | None:
        """Get the intervention report for a specific assistance."""
        result = db.execute(
            select(SatInterventionReport).where(
                SatInterventionReport.assistance_id == assistance_id,
                SatInterventionReport.deleted_at.is_(None),
                SatInterventionReport.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()

    def search(
        self,
        db: Session,
        *,
        organization_id: str,
        report_status: ReportStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SatInterventionReport]:
        """Search intervention reports with filters."""
        stmt = select(SatInterventionReport).where(
            SatInterventionReport.organization_id == organization_id,
            SatInterventionReport.deleted_at.is_(None),
        )
        if report_status:
            stmt = stmt.where(SatInterventionReport.report_status == report_status)
        stmt = stmt.order_by(SatInterventionReport.created_at.desc())
        stmt = stmt.offset(skip).limit(limit)
        result = db.execute(stmt)
        return list(result.scalars().all())


sat_intervention_report_service = SatInterventionReportService()
