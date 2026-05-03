"""SAT intervention report endpoints."""

from fastapi import APIRouter

from app.shared.api.deps import CurrentUserDep, DBDep, SatManagerDep
from app.shared.models.enums import ReportStatus
from app.modules.sat.schemas import (
    SatInterventionReportCreate,
    SatInterventionReportResponse,
    SatInterventionReportUpdate,
)
from app.modules.sat.services import sat_intervention_report_service

router = APIRouter()


@router.get("", response_model=list[SatInterventionReportResponse])
def list_reports(
    db: DBDep,
    current_user: CurrentUserDep,
    report_status: ReportStatus | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[SatInterventionReportResponse]:
    """List SAT intervention reports with optional status filter."""
    reports = sat_intervention_report_service.search(
        db,
        organization_id=current_user.organization_id,
        report_status=report_status,
        skip=skip,
        limit=limit,
    )
    return [SatInterventionReportResponse.model_validate(r) for r in reports]


@router.post("", response_model=SatInterventionReportResponse, status_code=201)
def create_report(
    report_in: SatInterventionReportCreate,
    db: DBDep,
    current_user: SatManagerDep,
) -> SatInterventionReportResponse:
    """Create a new SAT intervention report."""
    report_data = report_in.model_copy(
        update={"organization_id": current_user.organization_id}
    )
    report = sat_intervention_report_service.create(db, obj_in=report_data)
    return SatInterventionReportResponse.model_validate(report)


@router.get("/{report_id}", response_model=SatInterventionReportResponse)
def get_report(
    report_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> SatInterventionReportResponse:
    """Get a SAT intervention report by ID."""
    report = sat_intervention_report_service.get_or_404(db, report_id, organization_id=current_user.organization_id)
    return SatInterventionReportResponse.model_validate(report)


@router.patch("/{report_id}", response_model=SatInterventionReportResponse)
def update_report(
    report_id: str,
    report_in: SatInterventionReportUpdate,
    db: DBDep,
    current_user: SatManagerDep,
) -> SatInterventionReportResponse:
    """Update a SAT intervention report."""
    report = sat_intervention_report_service.get_or_404(db, report_id, organization_id=current_user.organization_id)
    updated = sat_intervention_report_service.update(db, db_obj=report, obj_in=report_in)
    return SatInterventionReportResponse.model_validate(updated)


@router.delete("/{report_id}", status_code=204)
def delete_report(
    report_id: str,
    db: DBDep,
    current_user: SatManagerDep,
) -> None:
    """Delete a SAT intervention report."""
    sat_intervention_report_service.delete(db, report_id, organization_id=current_user.organization_id)
