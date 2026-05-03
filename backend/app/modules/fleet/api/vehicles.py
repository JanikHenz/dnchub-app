"""Vehicle endpoints."""

from fastapi import APIRouter

from app.shared.api.deps import CurrentUserDep, DBDep, FleetManagerDep
from app.models.enums import VehicleStatus
from app.schemas import (
    VehicleCreate,
    VehicleGroupCreate,
    VehicleGroupResponse,
    VehicleGroupUpdate,
    VehicleResponse,
    VehicleUpdate,
)
from app.services import vehicle_group_service, vehicle_service

router = APIRouter()


# Vehicle endpoints
@router.get("", response_model=list[VehicleResponse])
def list_vehicles(
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
    status: VehicleStatus | None = None,
) -> list[VehicleResponse]:
    """List vehicles in the organization."""
    if status:
        vehicles = vehicle_service.get_by_status(
            db,
            organization_id=current_user.organization_id,
            status=status,
        )
    else:
        vehicles = vehicle_service.get_multi(
            db,
            skip=skip,
            limit=limit,
            organization_id=current_user.organization_id,
        )
    return [VehicleResponse.model_validate(v) for v in vehicles]


@router.post("", response_model=VehicleResponse, status_code=201)
def create_vehicle(
    vehicle_in: VehicleCreate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> VehicleResponse:
    """Create a new vehicle."""
    vehicle_data = vehicle_in.model_copy(update={"organization_id": current_user.organization_id})
    vehicle = vehicle_service.create(db, obj_in=vehicle_data)
    return VehicleResponse.model_validate(vehicle)


@router.get("/available", response_model=list[VehicleResponse])
def list_available_vehicles(
    db: DBDep,
    current_user: CurrentUserDep,
) -> list[VehicleResponse]:
    """List vehicles available for assignment."""
    vehicles = vehicle_service.get_available_for_assignment(
        db, organization_id=current_user.organization_id
    )
    return [VehicleResponse.model_validate(v) for v in vehicles]


@router.get("/{vehicle_id}", response_model=VehicleResponse)
def get_vehicle(
    vehicle_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> VehicleResponse:
    """Get a vehicle by ID."""
    vehicle = vehicle_service.get_or_404(db, vehicle_id, organization_id=current_user.organization_id)
    return VehicleResponse.model_validate(vehicle)


@router.patch("/{vehicle_id}", response_model=VehicleResponse)
def update_vehicle(
    vehicle_id: str,
    vehicle_in: VehicleUpdate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> VehicleResponse:
    """Update a vehicle."""
    vehicle = vehicle_service.get_or_404(db, vehicle_id, organization_id=current_user.organization_id)
    updated = vehicle_service.update(db, db_obj=vehicle, obj_in=vehicle_in)
    return VehicleResponse.model_validate(updated)


@router.delete("/{vehicle_id}", status_code=204)
def delete_vehicle(
    vehicle_id: str,
    db: DBDep,
    current_user: FleetManagerDep,
) -> None:
    """Delete a vehicle."""
    vehicle_service.delete(db, vehicle_id, organization_id=current_user.organization_id)


@router.post("/{vehicle_id}/odometer", response_model=VehicleResponse)
def update_odometer(
    vehicle_id: str,
    new_odometer: float,
    db: DBDep,
    current_user: CurrentUserDep,
) -> VehicleResponse:
    """Update vehicle odometer reading."""
    vehicle = vehicle_service.get_or_404(db, vehicle_id, organization_id=current_user.organization_id)
    updated = vehicle_service.update_odometer(db, vehicle, new_odometer)
    return VehicleResponse.model_validate(updated)


# Vehicle Group endpoints
@router.get("/groups", response_model=list[VehicleGroupResponse])
def list_vehicle_groups(
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
) -> list[VehicleGroupResponse]:
    """List vehicle groups."""
    groups = vehicle_group_service.get_multi(
        db,
        skip=skip,
        limit=limit,
        organization_id=current_user.organization_id,
    )
    return [VehicleGroupResponse.model_validate(g) for g in groups]


@router.post("/groups", response_model=VehicleGroupResponse, status_code=201)
def create_vehicle_group(
    group_in: VehicleGroupCreate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> VehicleGroupResponse:
    """Create a vehicle group."""
    group_data = group_in.model_copy(update={"organization_id": current_user.organization_id})
    group = vehicle_group_service.create(db, obj_in=group_data)
    return VehicleGroupResponse.model_validate(group)


@router.get("/groups/{group_id}", response_model=VehicleGroupResponse)
def get_vehicle_group(
    group_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> VehicleGroupResponse:
    """Get a vehicle group by ID."""
    group = vehicle_group_service.get_or_404(db, group_id, organization_id=current_user.organization_id)
    return VehicleGroupResponse.model_validate(group)


@router.patch("/groups/{group_id}", response_model=VehicleGroupResponse)
def update_vehicle_group(
    group_id: str,
    group_in: VehicleGroupUpdate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> VehicleGroupResponse:
    """Update a vehicle group."""
    group = vehicle_group_service.get_or_404(db, group_id, organization_id=current_user.organization_id)
    updated = vehicle_group_service.update(db, db_obj=group, obj_in=group_in)
    return VehicleGroupResponse.model_validate(updated)


@router.delete("/groups/{group_id}", status_code=204)
def delete_vehicle_group(
    group_id: str,
    db: DBDep,
    current_user: FleetManagerDep,
) -> None:
    """Delete a vehicle group."""
    vehicle_group_service.delete(db, group_id, organization_id=current_user.organization_id)


@router.post("/groups/{group_id}/vehicles/{vehicle_id}", status_code=201)
def add_vehicle_to_group(
    group_id: str,
    vehicle_id: str,
    db: DBDep,
    current_user: FleetManagerDep,
) -> dict:
    """Add a vehicle to a group."""
    vehicle_group_service.add_vehicle(db, group_id, vehicle_id)
    return {"message": "Vehicle added to group"}


@router.delete("/groups/{group_id}/vehicles/{vehicle_id}", status_code=204)
def remove_vehicle_from_group(
    group_id: str,
    vehicle_id: str,
    db: DBDep,
    current_user: FleetManagerDep,
) -> None:
    """Remove a vehicle from a group."""
    vehicle_group_service.remove_vehicle(db, group_id, vehicle_id)
