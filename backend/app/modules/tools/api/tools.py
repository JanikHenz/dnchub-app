"""Tool endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.shared.api.deps import CurrentUserDep, DBDep, FleetManagerDep
from app.schemas import (
    ToolCaseResponse,
    ToolCreate,
    ToolResponse,
    ToolUpdate,
)
from app.services import tool_case_service, tool_service
from app.modules.tools.models.tool_case import ToolCase

router = APIRouter()


@router.get("", response_model=list[ToolResponse])
def list_tools(
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 2000,
    unassigned: bool = False,
) -> list[ToolResponse]:
    """List tools in the organization. Use unassigned=true to return only tools not assigned to any case."""
    if unassigned:
        tools = tool_service.get_unassigned(db, organization_id=current_user.organization_id)
    else:
        tools = tool_service.get_multi(
            db,
            skip=skip,
            limit=limit,
            organization_id=current_user.organization_id,
        )
    return [ToolResponse.model_validate(t) for t in tools]


@router.post("", response_model=ToolResponse, status_code=201)
def create_tool(
    tool_in: ToolCreate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> ToolResponse:
    """Create a new tool."""
    tool_data = tool_in.model_copy(
        update={"organization_id": current_user.organization_id}
    )
    tool = tool_service.create(db, obj_in=tool_data)
    return ToolResponse.model_validate(tool)


@router.get("/by-erp/{erp_code}", response_model=ToolResponse)
def get_tool_by_erp_code(
    erp_code: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> ToolResponse:
    """Find a tool by its ERP code."""
    tool = tool_service.get_by_erp_code(
        db,
        organization_id=current_user.organization_id,
        erp_code=erp_code,
    )
    if tool is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool with ERP code '{erp_code}' not found",
        )
    return ToolResponse.model_validate(tool)


@router.get("/by-category/{category_id}", response_model=list[ToolResponse])
def list_tools_by_category(
    category_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> list[ToolResponse]:
    """List tools in a specific category."""
    tools = tool_service.get_by_category(
        db,
        organization_id=current_user.organization_id,
        category_id=category_id,
    )
    return [ToolResponse.model_validate(t) for t in tools]


@router.get("/by-case/{case_id}", response_model=list[ToolResponse])
def list_tools_by_case(
    case_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> list[ToolResponse]:
    """List tools assigned to a specific case."""
    tools = tool_service.get_by_case(db, case_id=case_id, organization_id=current_user.organization_id)
    return [ToolResponse.model_validate(t) for t in tools]


@router.get("/{tool_id}", response_model=ToolResponse)
def get_tool(
    tool_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> ToolResponse:
    """Get a tool by ID."""
    tool = tool_service.get_or_404(db, tool_id, organization_id=current_user.organization_id)
    return ToolResponse.model_validate(tool)


@router.put("/{tool_id}", response_model=ToolResponse)
def update_tool(
    tool_id: str,
    tool_in: ToolUpdate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> ToolResponse:
    """Update a tool."""
    tool = tool_service.get_or_404(db, tool_id, organization_id=current_user.organization_id)
    updated = tool_service.update(db, db_obj=tool, obj_in=tool_in)
    return ToolResponse.model_validate(updated)


@router.delete("/{tool_id}", status_code=204)
def delete_tool(
    tool_id: str,
    db: DBDep,
    current_user: FleetManagerDep,
) -> None:
    """Delete a tool (soft delete)."""
    tool_service.delete(db, tool_id, organization_id=current_user.organization_id)


@router.post("/{tool_id}/convert-to-case", response_model=ToolCaseResponse, status_code=201)
def convert_tool_to_case(
    tool_id: str,
    db: DBDep,
    current_user: FleetManagerDep,
) -> ToolCaseResponse:
    """Convert a tool record to a case record. Soft-deletes the tool."""
    tool = tool_service.get_or_404(db, tool_id, organization_id=current_user.organization_id)

    existing = (
        db.query(ToolCase)
        .filter(
            ToolCase.organization_id == current_user.organization_id,
            ToolCase.erp_code == tool.erp_code,
            ToolCase.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A case with ERP code '{tool.erp_code}' already exists",
        )

    new_case = ToolCase(
        organization_id=tool.organization_id,
        erp_code=tool.erp_code,
        name=tool.name,
        description=tool.description,
        status=tool.status,
        condition=tool.condition,
        images=tool.images,
        notes=tool.notes,
        location_id=tool.location_id,
    )
    db.add(new_case)
    tool.deleted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(new_case)
    return ToolCaseResponse.model_validate(new_case)
