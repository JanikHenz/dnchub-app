"""Tool assignment service."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.tools.models.tool_assignment import ToolAssignment
from app.modules.tools.schemas.tool_assignment import ToolAssignmentCreate
from app.shared.models.enums import ToolCondition
from app.shared.services.base import BaseService


class ToolAssignmentService(BaseService[ToolAssignment, ToolAssignmentCreate, ToolAssignmentCreate]):
    """Tool assignment service with specialized operations."""

    def __init__(self):
        super().__init__(ToolAssignment)

    def get_active_assignments(
        self,
        db: Session,
        organization_id: str,
    ) -> list[ToolAssignment]:
        """Get all active assignments (not yet returned) for an organization."""
        result = db.execute(
            select(ToolAssignment).where(
                ToolAssignment.organization_id == organization_id,
                ToolAssignment.returned_at.is_(None),
            )
        )
        return list(result.scalars().all())

    def get_by_employee(
        self,
        db: Session,
        employee_id: str,
        *,
        organization_id: str,
    ) -> list[ToolAssignment]:
        """Get active assignments for a specific employee."""
        result = db.execute(
            select(ToolAssignment).where(
                ToolAssignment.assigned_to_employee_id == employee_id,
                ToolAssignment.returned_at.is_(None),
                ToolAssignment.organization_id == organization_id
            )
        )
        return list(result.scalars().all())

    def get_by_vehicle(
        self,
        db: Session,
        vehicle_id: str,
        *,
        organization_id: str,
    ) -> list[ToolAssignment]:
        """Get active assignments for a specific vehicle."""
        result = db.execute(
            select(ToolAssignment).where(
                ToolAssignment.assigned_to_vehicle_id == vehicle_id,
                ToolAssignment.returned_at.is_(None),
                ToolAssignment.organization_id == organization_id
            )
        )
        return list(result.scalars().all())

    def return_tool(
        self,
        db: Session,
        assignment_id: str,
        condition_at_return: ToolCondition | None = None,
        notes: str | None = None,
        organization_id: str | None = None,
    ) -> ToolAssignment:
        """Mark an assignment as returned with optional condition and notes."""
        assignment = self.get_or_404(db, assignment_id, organization_id=organization_id)
        assignment.returned_at = datetime.now(timezone.utc)
        if condition_at_return is not None:
            assignment.condition_at_return = condition_at_return
        if notes is not None:
            assignment.notes = notes
        db.add(assignment)
        db.flush()
        db.refresh(assignment)
        return assignment


tool_assignment_service = ToolAssignmentService()
