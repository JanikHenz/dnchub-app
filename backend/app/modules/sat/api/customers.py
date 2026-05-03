"""SAT customer endpoints."""

from fastapi import APIRouter

from app.shared.api.deps import CurrentUserDep, DBDep, SatManagerDep
from app.modules.sat.schemas import (
    SatCustomerCreate,
    SatCustomerResponse,
    SatCustomerUpdate,
)
from app.modules.sat.services import sat_customer_service

router = APIRouter()


@router.get("", response_model=list[SatCustomerResponse])
def list_customers(
    db: DBDep,
    current_user: CurrentUserDep,
    search: str | None = None,
    city: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[SatCustomerResponse]:
    """List SAT customers with optional search and city filter."""
    customers = sat_customer_service.search(
        db,
        organization_id=current_user.organization_id,
        query=search,
        city=city,
        skip=skip,
        limit=limit,
    )
    return [SatCustomerResponse.model_validate(c) for c in customers]


@router.post("", response_model=SatCustomerResponse, status_code=201)
def create_customer(
    customer_in: SatCustomerCreate,
    db: DBDep,
    current_user: SatManagerDep,
) -> SatCustomerResponse:
    """Create a new SAT customer."""
    customer_data = customer_in.model_copy(
        update={"organization_id": current_user.organization_id}
    )
    customer = sat_customer_service.create(db, obj_in=customer_data)
    return SatCustomerResponse.model_validate(customer)


@router.get("/{customer_id}", response_model=SatCustomerResponse)
def get_customer(
    customer_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> SatCustomerResponse:
    """Get a SAT customer by ID."""
    customer = sat_customer_service.get_or_404(db, customer_id, organization_id=current_user.organization_id)
    return SatCustomerResponse.model_validate(customer)


@router.patch("/{customer_id}", response_model=SatCustomerResponse)
def update_customer(
    customer_id: str,
    customer_in: SatCustomerUpdate,
    db: DBDep,
    current_user: SatManagerDep,
) -> SatCustomerResponse:
    """Update a SAT customer."""
    customer = sat_customer_service.get_or_404(db, customer_id, organization_id=current_user.organization_id)
    updated = sat_customer_service.update(db, db_obj=customer, obj_in=customer_in)
    return SatCustomerResponse.model_validate(updated)


@router.delete("/{customer_id}", status_code=204)
def delete_customer(
    customer_id: str,
    db: DBDep,
    current_user: SatManagerDep,
) -> None:
    """Delete a SAT customer."""
    sat_customer_service.delete(db, customer_id, organization_id=current_user.organization_id)
