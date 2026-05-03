"""Tool service."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.tools.models.tool import Tool
from app.modules.tools.schemas.tool import ToolCreate, ToolUpdate
from app.shared.services.base import BaseService


class ToolService(BaseService[Tool, ToolCreate, ToolUpdate]):
    """Tool service with specialized operations."""

    def __init__(self):
        super().__init__(Tool)

    def get_by_erp_code(
        self,
        db: Session,
        organization_id: str,
        erp_code: str,
    ) -> Tool | None:
        """Find a tool by its ERP code within an organization."""
        result = db.execute(
            select(Tool).where(
                Tool.organization_id == organization_id,
                Tool.erp_code == erp_code,
                Tool.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    def get_by_case(
        self,
        db: Session,
        case_id: str,
        *,
        organization_id: str,
    ) -> list[Tool]:
        """List all tools assigned to a specific case."""
        result = db.execute(
            select(Tool).where(
                Tool.case_id == case_id,
                Tool.deleted_at.is_(None),
                Tool.organization_id == organization_id
            )
        )
        return list(result.scalars().all())

    def get_unassigned(
        self,
        db: Session,
        organization_id: str,
    ) -> list[Tool]:
        """List tools not assigned to any case."""
        result = db.execute(
            select(Tool).where(
                Tool.organization_id == organization_id,
                Tool.case_id.is_(None),
                Tool.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    def get_by_category(
        self,
        db: Session,
        organization_id: str,
        category_id: str,
    ) -> list[Tool]:
        """List all tools in a specific category within an organization."""
        result = db.execute(
            select(Tool).where(
                Tool.organization_id == organization_id,
                Tool.category_id == category_id,
                Tool.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())


tool_service = ToolService()
