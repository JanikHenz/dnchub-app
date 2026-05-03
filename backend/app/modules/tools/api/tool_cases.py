"""Tool case endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.shared.api.deps import CurrentUserDep, DBDep, FleetManagerDep
from app.schemas import (
    ToolCaseCreate,
    ToolCaseResponse,
    ToolCaseUpdate,
    ToolResponse,
)
from app.services import tool_case_service, tool_service
from app.modules.tools.models.tool import Tool

router = APIRouter()


@router.get("", response_model=list[ToolCaseResponse])
def list_tool_cases(
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
) -> list[ToolCaseResponse]:
    """List tool cases in the organization."""
    cases = tool_case_service.get_multi(
        db,
        skip=skip,
        limit=limit,
        organization_id=current_user.organization_id,
    )
    return [ToolCaseResponse.model_validate(c) for c in cases]


@router.post("", response_model=ToolCaseResponse, status_code=201)
def create_tool_case(
    case_in: ToolCaseCreate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> ToolCaseResponse:
    """Create a new tool case."""
    case_data = case_in.model_copy(
        update={"organization_id": current_user.organization_id}
    )
    case = tool_case_service.create(db, obj_in=case_data)
    return ToolCaseResponse.model_validate(case)


@router.get("/{case_id}", response_model=ToolCaseResponse)
def get_tool_case(
    case_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> ToolCaseResponse:
    """Get a tool case by ID."""
    case = tool_case_service.get_or_404(db, case_id, organization_id=current_user.organization_id)
    return ToolCaseResponse.model_validate(case)


@router.put("/{case_id}", response_model=ToolCaseResponse)
def update_tool_case(
    case_id: str,
    case_in: ToolCaseUpdate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> ToolCaseResponse:
    """Update a tool case."""
    case = tool_case_service.get_or_404(db, case_id, organization_id=current_user.organization_id)
    updated = tool_case_service.update(db, db_obj=case, obj_in=case_in)
    return ToolCaseResponse.model_validate(updated)


@router.delete("/{case_id}", status_code=204)
def delete_tool_case(
    case_id: str,
    db: DBDep,
    current_user: FleetManagerDep,
) -> None:
    """Delete a tool case (soft delete)."""
    tool_case_service.delete(db, case_id, organization_id=current_user.organization_id)


@router.post("/{case_id}/convert-to-tool", response_model=ToolResponse, status_code=201)
def convert_case_to_tool(
    case_id: str,
    db: DBDep,
    current_user: FleetManagerDep,
) -> ToolResponse:
    """Convert a case record to a tool record. Soft-deletes the case."""
    case = tool_case_service.get_or_404(db, case_id, organization_id=current_user.organization_id)

    existing = (
        db.query(Tool)
        .filter(
            Tool.organization_id == current_user.organization_id,
            Tool.erp_code == case.erp_code,
            Tool.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A tool with ERP code '{case.erp_code}' already exists",
        )

    new_tool = Tool(
        organization_id=case.organization_id,
        erp_code=case.erp_code,
        name=case.name,
        description=case.description,
        status=case.status,
        condition=case.condition,
        images=case.images,
        notes=case.notes,
        location_id=case.location_id,
    )
    db.add(new_tool)
    case.deleted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(new_tool)
    return ToolResponse.model_validate(new_tool)


@router.get("/{case_id}/tools", response_model=list[ToolResponse])
def list_tools_in_case(
    case_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> list[ToolResponse]:
    """List all tools assigned to a specific case."""
    # Verify the case exists
    tool_case_service.get_or_404(db, case_id, organization_id=current_user.organization_id)
    tools = tool_service.get_by_case(db, case_id=case_id, organization_id=current_user.organization_id)
    return [ToolResponse.model_validate(t) for t in tools]
