"""Tool assignment endpoints."""

from fastapi import APIRouter

from app.shared.api.deps import CurrentUserDep, DBDep, FleetManagerDep
from app.shared.models.enums import ToolStatus
from app.schemas import (
    ToolAssignmentCreate,
    ToolAssignmentResponse,
    ToolAssignmentReturn,
)
from app.services import tool_assignment_service, tool_case_service, tool_service

router = APIRouter()


@router.get("", response_model=list[ToolAssignmentResponse])
def list_active_assignments(
    db: DBDep,
    current_user: CurrentUserDep,
) -> list[ToolAssignmentResponse]:
    """List active tool assignments (not yet returned)."""
    assignments = tool_assignment_service.get_active_assignments(
        db,
        organization_id=current_user.organization_id,
    )
    return [ToolAssignmentResponse.model_validate(a) for a in assignments]


@router.post("", response_model=ToolAssignmentResponse, status_code=201)
def create_assignment(
    assignment_in: ToolAssignmentCreate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> ToolAssignmentResponse:
    """Create a new tool/case assignment.

    Also updates the tool or case status to ASSIGNED.
    """
    assignment_data = assignment_in.model_copy(
        update={
            "organization_id": current_user.organization_id,
            "assigned_by_id": current_user.id,
        }
    )
    assignment = tool_assignment_service.create(db, obj_in=assignment_data)

    # Update tool status to ASSIGNED if a tool is being assigned
    if assignment.tool_id:
        tool = tool_service.get(db, assignment.tool_id)
        if tool:
            tool_service.update(db, db_obj=tool, obj_in={"status": ToolStatus.ASSIGNED})

    # Update case status to ASSIGNED if a case is being assigned
    if assignment.case_id:
        case = tool_case_service.get(db, assignment.case_id)
        if case:
            tool_case_service.update(db, db_obj=case, obj_in={"status": ToolStatus.ASSIGNED})

    return ToolAssignmentResponse.model_validate(assignment)


@router.get("/{assignment_id}", response_model=ToolAssignmentResponse)
def get_assignment(
    assignment_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> ToolAssignmentResponse:
    """Get a tool assignment by ID."""
    assignment = tool_assignment_service.get_or_404(db, assignment_id, organization_id=current_user.organization_id)
    return ToolAssignmentResponse.model_validate(assignment)


@router.post("/{assignment_id}/return", response_model=ToolAssignmentResponse)
def return_tool(
    assignment_id: str,
    return_in: ToolAssignmentReturn,
    db: DBDep,
    current_user: FleetManagerDep,
) -> ToolAssignmentResponse:
    """Return a tool/case from an assignment.

    Marks the assignment as returned and updates the tool or case status
    back to AVAILABLE.
    """
    assignment = tool_assignment_service.return_tool(
        db,
        assignment_id=assignment_id,
        condition_at_return=return_in.condition_at_return,
        notes=return_in.notes,
        organization_id=current_user.organization_id,
    )

    # Update tool status back to AVAILABLE
    if assignment.tool_id:
        tool = tool_service.get(db, assignment.tool_id)
        if tool:
            tool_service.update(db, db_obj=tool, obj_in={"status": ToolStatus.AVAILABLE})

    # Update case status back to AVAILABLE
    if assignment.case_id:
        case = tool_case_service.get(db, assignment.case_id)
        if case:
            tool_case_service.update(db, db_obj=case, obj_in={"status": ToolStatus.AVAILABLE})

    return ToolAssignmentResponse.model_validate(assignment)


@router.get("/by-employee/{employee_id}", response_model=list[ToolAssignmentResponse])
def list_assignments_by_employee(
    employee_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> list[ToolAssignmentResponse]:
    """List active tool assignments for a specific employee."""
    assignments = tool_assignment_service.get_by_employee(db, employee_id=employee_id, organization_id=current_user.organization_id)
    return [ToolAssignmentResponse.model_validate(a) for a in assignments]


@router.get("/by-vehicle/{vehicle_id}", response_model=list[ToolAssignmentResponse])
def list_assignments_by_vehicle(
    vehicle_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> list[ToolAssignmentResponse]:
    """List active tool assignments for a specific vehicle."""
    assignments = tool_assignment_service.get_by_vehicle(db, vehicle_id=vehicle_id, organization_id=current_user.organization_id)
    return [ToolAssignmentResponse.model_validate(a) for a in assignments]
