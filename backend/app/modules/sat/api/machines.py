"""SAT machine endpoints."""

from fastapi import APIRouter

from app.shared.api.deps import CurrentUserDep, DBDep, SatManagerDep
from app.shared.models.enums import MachineType
from app.modules.sat.schemas import (
    SatMachineCreate,
    SatMachineResponse,
    SatMachineUpdate,
)
from app.modules.sat.services import sat_machine_service

router = APIRouter()


@router.get("", response_model=list[SatMachineResponse])
def list_machines(
    db: DBDep,
    current_user: CurrentUserDep,
    customer_id: str | None = None,
    machine_type: MachineType | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[SatMachineResponse]:
    """List SAT machines with optional customer and type filters."""
    machines = sat_machine_service.search(
        db,
        organization_id=current_user.organization_id,
        customer_id=customer_id,
        machine_type=machine_type,
        skip=skip,
        limit=limit,
    )
    return [SatMachineResponse.model_validate(m) for m in machines]


@router.post("", response_model=SatMachineResponse, status_code=201)
def create_machine(
    machine_in: SatMachineCreate,
    db: DBDep,
    current_user: SatManagerDep,
) -> SatMachineResponse:
    """Create a new SAT machine."""
    machine_data = machine_in.model_copy(
        update={"organization_id": current_user.organization_id}
    )
    machine = sat_machine_service.create(db, obj_in=machine_data)
    return SatMachineResponse.model_validate(machine)


@router.get("/{machine_id}", response_model=SatMachineResponse)
def get_machine(
    machine_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> SatMachineResponse:
    """Get a SAT machine by ID."""
    machine = sat_machine_service.get_or_404(db, machine_id, organization_id=current_user.organization_id)
    return SatMachineResponse.model_validate(machine)


@router.patch("/{machine_id}", response_model=SatMachineResponse)
def update_machine(
    machine_id: str,
    machine_in: SatMachineUpdate,
    db: DBDep,
    current_user: SatManagerDep,
) -> SatMachineResponse:
    """Update a SAT machine."""
    machine = sat_machine_service.get_or_404(db, machine_id, organization_id=current_user.organization_id)
    updated = sat_machine_service.update(db, db_obj=machine, obj_in=machine_in)
    return SatMachineResponse.model_validate(updated)


@router.delete("/{machine_id}", status_code=204)
def delete_machine(
    machine_id: str,
    db: DBDep,
    current_user: SatManagerDep,
) -> None:
    """Delete a SAT machine."""
    sat_machine_service.delete(db, machine_id, organization_id=current_user.organization_id)
