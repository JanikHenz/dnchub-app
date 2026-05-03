"""Ticket endpoints."""

from datetime import date

from fastapi import APIRouter

from app.shared.api.deps import CurrentUserDep, DBDep, FleetManagerDep
from app.models.enums import TicketStatus, TicketType
from app.schemas import (
    TicketCreate,
    TicketPayRequest,
    TicketResponse,
    TicketStats,
    TicketUpdate,
)
from app.services import ticket_service

router = APIRouter()


@router.get("", response_model=list[TicketResponse])
def list_tickets(
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
    status: TicketStatus | None = None,
    type: TicketType | None = None,
    vehicle_id: str | None = None,
    employee_id: str | None = None,
    overdue_only: bool = False,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[TicketResponse]:
    """List tickets in the organization with optional filters."""
    tickets = ticket_service.get_multi_filtered(
        db,
        organization_id=current_user.organization_id,
        status=status,
        ticket_type=type,
        vehicle_id=vehicle_id,
        employee_id=employee_id,
        overdue_only=overdue_only,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    return [TicketResponse.model_validate(t) for t in tickets]


@router.post("", response_model=TicketResponse, status_code=201)
def create_ticket(
    ticket_in: TicketCreate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> TicketResponse:
    """Create a new ticket."""
    ticket_data = ticket_in.model_copy(update={"organization_id": current_user.organization_id})
    ticket = ticket_service.create(db, obj_in=ticket_data)
    return TicketResponse.model_validate(ticket)


@router.get("/overdue", response_model=list[TicketResponse])
def list_overdue_tickets(
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
) -> list[TicketResponse]:
    """List overdue tickets (past due date and not paid/cancelled)."""
    tickets = ticket_service.get_overdue(
        db,
        organization_id=current_user.organization_id,
        skip=skip,
        limit=limit,
    )
    return [TicketResponse.model_validate(t) for t in tickets]


@router.get("/stats", response_model=TicketStats)
def get_ticket_stats(
    db: DBDep,
    current_user: CurrentUserDep,
    start_date: date | None = None,
    end_date: date | None = None,
) -> TicketStats:
    """Get ticket statistics for the organization."""
    return ticket_service.get_stats(
        db,
        organization_id=current_user.organization_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/by-vehicle/{vehicle_id}", response_model=list[TicketResponse])
def list_tickets_by_vehicle(
    vehicle_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
) -> list[TicketResponse]:
    """List all tickets for a specific vehicle."""
    tickets = ticket_service.get_by_vehicle(
        db,
        vehicle_id=vehicle_id,
        organization_id=current_user.organization_id,
        skip=skip,
        limit=limit,
    )
    return [TicketResponse.model_validate(t) for t in tickets]


@router.get("/by-employee/{employee_id}", response_model=list[TicketResponse])
def list_tickets_by_employee(
    employee_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
) -> list[TicketResponse]:
    """List all tickets for a specific employee."""
    tickets = ticket_service.get_by_employee(
        db,
        employee_id=employee_id,
        organization_id=current_user.organization_id,
        skip=skip,
        limit=limit,
    )
    return [TicketResponse.model_validate(t) for t in tickets]


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> TicketResponse:
    """Get a ticket by ID."""
    ticket = ticket_service.get_or_404(db, ticket_id, organization_id=current_user.organization_id)
    return TicketResponse.model_validate(ticket)


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    ticket_id: str,
    ticket_in: TicketUpdate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> TicketResponse:
    """Update a ticket."""
    ticket = ticket_service.get_or_404(db, ticket_id, organization_id=current_user.organization_id)
    updated = ticket_service.update(db, db_obj=ticket, obj_in=ticket_in)
    return TicketResponse.model_validate(updated)


@router.delete("/{ticket_id}", status_code=204)
def delete_ticket(
    ticket_id: str,
    db: DBDep,
    current_user: FleetManagerDep,
) -> None:
    """Delete a ticket (soft delete)."""
    ticket_service.delete(db, ticket_id, organization_id=current_user.organization_id)


@router.post("/{ticket_id}/pay", response_model=TicketResponse)
def pay_ticket(
    ticket_id: str,
    payment_in: TicketPayRequest,
    db: DBDep,
    current_user: FleetManagerDep,
) -> TicketResponse:
    """Mark a ticket as paid with payment details."""
    ticket = ticket_service.get_or_404(db, ticket_id, organization_id=current_user.organization_id)
    updated = ticket_service.mark_as_paid(db, ticket, payment_in)
    return TicketResponse.model_validate(updated)


@router.post("/{ticket_id}/status", response_model=TicketResponse)
def update_ticket_status(
    ticket_id: str,
    new_status: TicketStatus,
    db: DBDep,
    current_user: FleetManagerDep,
) -> TicketResponse:
    """Update ticket status (e.g., to appealed or cancelled)."""
    ticket = ticket_service.get_or_404(db, ticket_id, organization_id=current_user.organization_id)
    updated = ticket_service.update_status(db, ticket, new_status)
    return TicketResponse.model_validate(updated)
