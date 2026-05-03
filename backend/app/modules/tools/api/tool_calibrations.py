"""Tool calibration endpoints."""

from fastapi import APIRouter

from app.shared.api.deps import CurrentUserDep, DBDep, FleetManagerDep
from app.schemas import (
    ToolCalibrationCreate,
    ToolCalibrationResponse,
    ToolCalibrationUpdate,
)
from app.services import tool_calibration_service

router = APIRouter()


@router.get("", response_model=list[ToolCalibrationResponse])
def list_tool_calibrations(
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
) -> list[ToolCalibrationResponse]:
    """List tool calibrations in the organization."""
    calibrations = tool_calibration_service.get_multi(
        db,
        skip=skip,
        limit=limit,
        organization_id=current_user.organization_id,
    )
    return [ToolCalibrationResponse.model_validate(c) for c in calibrations]


@router.post("", response_model=ToolCalibrationResponse, status_code=201)
def create_tool_calibration(
    calibration_in: ToolCalibrationCreate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> ToolCalibrationResponse:
    """Create a new tool calibration record."""
    calibration_data = calibration_in.model_copy(
        update={"organization_id": current_user.organization_id}
    )
    calibration = tool_calibration_service.create(db, obj_in=calibration_data)
    return ToolCalibrationResponse.model_validate(calibration)


@router.get("/{calibration_id}", response_model=ToolCalibrationResponse)
def get_tool_calibration(
    calibration_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> ToolCalibrationResponse:
    """Get a tool calibration record by ID."""
    calibration = tool_calibration_service.get_or_404(db, calibration_id, organization_id=current_user.organization_id)
    return ToolCalibrationResponse.model_validate(calibration)


@router.put("/{calibration_id}", response_model=ToolCalibrationResponse)
def update_tool_calibration(
    calibration_id: str,
    calibration_in: ToolCalibrationUpdate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> ToolCalibrationResponse:
    """Update a tool calibration record."""
    calibration = tool_calibration_service.get_or_404(db, calibration_id, organization_id=current_user.organization_id)
    updated = tool_calibration_service.update(
        db, db_obj=calibration, obj_in=calibration_in
    )
    return ToolCalibrationResponse.model_validate(updated)
