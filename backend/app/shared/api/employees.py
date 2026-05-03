"""Employee endpoints."""

from fastapi import APIRouter

from app.shared.api.deps import CurrentUserDep, DBDep, FleetManagerDep
from app.shared.schemas.employee import (
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
)
from app.shared.services.employee import employee_service

router = APIRouter()


@router.get("", response_model=list[EmployeeResponse])
def list_employees(
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
) -> list[EmployeeResponse]:
    """List employees in the organization."""
    if status:
        employees = employee_service.get_employees_by_status(
            db,
            organization_id=current_user.organization_id,
            status=status,
        )
    else:
        employees = employee_service.get_multi(
            db,
            skip=skip,
            limit=limit,
            organization_id=current_user.organization_id,
        )
    return [EmployeeResponse.model_validate(e) for e in employees]


@router.post("", response_model=EmployeeResponse, status_code=201)
def create_employee(
    employee_in: EmployeeCreate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> EmployeeResponse:
    """Create a new employee."""
    employee_data = employee_in.model_copy(update={"organization_id": current_user.organization_id})
    employee = employee_service.create(db, obj_in=employee_data)
    return EmployeeResponse.model_validate(employee)


@router.get("/available", response_model=list[EmployeeResponse])
def list_available_employees(
    db: DBDep,
    current_user: CurrentUserDep,
) -> list[EmployeeResponse]:
    """List available employees for assignment."""
    employees = employee_service.get_available_employees(
        db, organization_id=current_user.organization_id
    )
    return [EmployeeResponse.model_validate(e) for e in employees]


@router.get("/expiring-licenses", response_model=list[EmployeeResponse])
def list_expiring_licenses(
    db: DBDep,
    current_user: CurrentUserDep,
    days: int = 30,
) -> list[EmployeeResponse]:
    """List employees with expiring licenses."""
    employees = employee_service.get_employees_with_expiring_licenses(
        db,
        organization_id=current_user.organization_id,
        days=days,
    )
    return [EmployeeResponse.model_validate(e) for e in employees]


@router.get("/by-vehicle/{vehicle_id}", response_model=EmployeeResponse | None)
def get_employee_by_vehicle(
    vehicle_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> EmployeeResponse | None:
    """Get employee assigned to a vehicle."""
    employee = employee_service.get_by_assigned_vehicle(
        db,
        vehicle_id=vehicle_id,
        organization_id=current_user.organization_id,
    )
    if employee:
        return EmployeeResponse.model_validate(employee)
    return None


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    employee_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> EmployeeResponse:
    """Get an employee by ID."""
    employee = employee_service.get_or_404(db, employee_id, organization_id=current_user.organization_id)
    return EmployeeResponse.model_validate(employee)


@router.patch("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: str,
    employee_in: EmployeeUpdate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> EmployeeResponse:
    """Update an employee."""
    employee = employee_service.get_or_404(db, employee_id, organization_id=current_user.organization_id)
    updated = employee_service.update(db, db_obj=employee, obj_in=employee_in)
    return EmployeeResponse.model_validate(updated)


@router.delete("/{employee_id}", status_code=204)
def delete_employee(
    employee_id: str,
    db: DBDep,
    current_user: FleetManagerDep,
) -> None:
    """Delete an employee."""
    employee_service.delete(db, employee_id, organization_id=current_user.organization_id)


@router.post("/{employee_id}/pin", response_model=EmployeeResponse)
def set_employee_pin(
    employee_id: str,
    pin_code: str,
    db: DBDep,
    current_user: FleetManagerDep,
) -> EmployeeResponse:
    """Set employee PIN code for POS access."""
    employee = employee_service.get_or_404(db, employee_id, organization_id=current_user.organization_id)
    updated = employee_service.set_pin(db, employee, pin_code)
    return EmployeeResponse.model_validate(updated)


@router.post("/sync-assignments", status_code=200)
def sync_employee_vehicle_assignments(
    db: DBDep,
    current_user: FleetManagerDep,
) -> dict:
    """Sync all employee-vehicle assignments to fix inconsistent data."""
    synced_count = employee_service.sync_all_assignments(
        db, organization_id=current_user.organization_id
    )
    return {"synced": synced_count, "message": f"Synced {synced_count} employee-vehicle assignments"}
