"""SAT contact endpoints."""

from fastapi import APIRouter

from app.shared.api.deps import CurrentUserDep, DBDep, SatManagerDep
from app.modules.sat.schemas import (
    SatContactCreate,
    SatContactResponse,
    SatContactUpdate,
)
from app.modules.sat.services import sat_contact_service

router = APIRouter()


@router.get("/customers/{customer_id}/contacts", response_model=list[SatContactResponse])
def list_contacts(
    customer_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> list[SatContactResponse]:
    """List contacts for a SAT customer."""
    contacts = sat_contact_service.get_by_customer(db, customer_id=customer_id, organization_id=current_user.organization_id)
    return [SatContactResponse.model_validate(c) for c in contacts]


@router.post(
    "/customers/{customer_id}/contacts",
    response_model=SatContactResponse,
    status_code=201,
)
def create_contact(
    customer_id: str,
    contact_in: SatContactCreate,
    db: DBDep,
    current_user: SatManagerDep,
) -> SatContactResponse:
    """Create a new contact for a SAT customer."""
    contact_data = contact_in.model_copy(
        update={
            "organization_id": current_user.organization_id,
            "customer_id": customer_id,
        }
    )
    contact = sat_contact_service.create(db, obj_in=contact_data)
    return SatContactResponse.model_validate(contact)


@router.patch("/contacts/{contact_id}", response_model=SatContactResponse)
def update_contact(
    contact_id: str,
    contact_in: SatContactUpdate,
    db: DBDep,
    current_user: SatManagerDep,
) -> SatContactResponse:
    """Update a SAT contact."""
    contact = sat_contact_service.get_or_404(db, contact_id, organization_id=current_user.organization_id)
    updated = sat_contact_service.update(db, db_obj=contact, obj_in=contact_in)
    return SatContactResponse.model_validate(updated)


@router.delete("/contacts/{contact_id}", status_code=204)
def delete_contact(
    contact_id: str,
    db: DBDep,
    current_user: SatManagerDep,
) -> None:
    """Delete a SAT contact."""
    sat_contact_service.delete(db, contact_id, organization_id=current_user.organization_id)
