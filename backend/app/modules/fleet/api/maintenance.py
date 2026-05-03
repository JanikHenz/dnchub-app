"""Maintenance endpoints."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Query

from app.shared.api.deps import CurrentUserDep, DBDep, FleetManagerDep
from app.models.enums import MaintenanceStatus
from app.schemas import (
    MaintenanceScheduleCreate,
    MaintenanceScheduleResponse,
    MaintenanceScheduleUpdate,
    MaintenanceTaskCreate,
    MaintenanceTaskResponse,
    MaintenanceTaskUpdate,
)
from app.services import maintenance_schedule_service, maintenance_task_service

router = APIRouter()


# Maintenance Task endpoints
@router.get("/tasks", response_model=list[MaintenanceTaskResponse])
def list_maintenance_tasks(
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
    status: MaintenanceStatus | None = None,
    vehicle_id: str | None = None,
) -> list[MaintenanceTaskResponse]:
    """List maintenance tasks with optional filters."""
    if vehicle_id:
        tasks = maintenance_task_service.get_tasks_by_vehicle(
            db, vehicle_id, organization_id=current_user.organization_id, skip=skip, limit=limit
        )
    elif status:
        tasks = maintenance_task_service.get_tasks_by_status(
            db,
            organization_id=current_user.organization_id,
            status=status,
            skip=skip,
            limit=limit,
        )
    else:
        tasks = maintenance_task_service.get_multi(
            db,
            skip=skip,
            limit=limit,
            organization_id=current_user.organization_id,
        )
    return [MaintenanceTaskResponse.model_validate(t) for t in tasks]


@router.post("/tasks", response_model=MaintenanceTaskResponse, status_code=201)
def create_maintenance_task(
    task_in: MaintenanceTaskCreate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> MaintenanceTaskResponse:
    """Create a maintenance task."""
    task_data = task_in.model_copy(update={"organization_id": current_user.organization_id})
    task = maintenance_task_service.create(db, obj_in=task_data)
    return MaintenanceTaskResponse.model_validate(task)


@router.get("/tasks/overdue", response_model=list[MaintenanceTaskResponse])
def list_overdue_tasks(
    db: DBDep,
    current_user: CurrentUserDep,
) -> list[MaintenanceTaskResponse]:
    """List overdue maintenance tasks."""
    tasks = maintenance_task_service.get_overdue_tasks(
        db, organization_id=current_user.organization_id
    )
    return [MaintenanceTaskResponse.model_validate(t) for t in tasks]


@router.get("/tasks/upcoming", response_model=list[MaintenanceTaskResponse])
def list_upcoming_tasks(
    db: DBDep,
    current_user: CurrentUserDep,
    days: int = Query(default=7, ge=1, le=90),
) -> list[MaintenanceTaskResponse]:
    """List upcoming maintenance tasks."""
    tasks = maintenance_task_service.get_upcoming_tasks(
        db,
        organization_id=current_user.organization_id,
        days=days,
    )
    return [MaintenanceTaskResponse.model_validate(t) for t in tasks]


@router.get("/tasks/cost-summary")
def get_maintenance_cost_summary(
    db: DBDep,
    current_user: CurrentUserDep,
    start_date: date = Query(...),
    end_date: date = Query(...),
) -> dict:
    """Get maintenance cost summary for a period."""
    return maintenance_task_service.get_maintenance_cost_summary(
        db,
        organization_id=current_user.organization_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/tasks/{task_id}", response_model=MaintenanceTaskResponse)
def get_maintenance_task(
    task_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> MaintenanceTaskResponse:
    """Get a maintenance task by ID."""
    task = maintenance_task_service.get_or_404(db, task_id, organization_id=current_user.organization_id)
    return MaintenanceTaskResponse.model_validate(task)


@router.patch("/tasks/{task_id}", response_model=MaintenanceTaskResponse)
def update_maintenance_task(
    task_id: str,
    task_in: MaintenanceTaskUpdate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> MaintenanceTaskResponse:
    """Update a maintenance task."""
    task = maintenance_task_service.get_or_404(db, task_id, organization_id=current_user.organization_id)
    updated = maintenance_task_service.update(db, db_obj=task, obj_in=task_in)
    return MaintenanceTaskResponse.model_validate(updated)


@router.post("/tasks/{task_id}/complete", response_model=MaintenanceTaskResponse)
def complete_maintenance_task(
    task_id: str,
    db: DBDep,
    current_user: FleetManagerDep,
    actual_cost: Decimal | None = None,
    notes: str | None = None,
) -> MaintenanceTaskResponse:
    """Mark a maintenance task as completed."""
    task = maintenance_task_service.get_or_404(db, task_id, organization_id=current_user.organization_id)
    updated = maintenance_task_service.complete_task(
        db, task, actual_cost=actual_cost, notes=notes
    )
    return MaintenanceTaskResponse.model_validate(updated)


@router.post("/tasks/{task_id}/cancel", response_model=MaintenanceTaskResponse)
def cancel_maintenance_task(
    task_id: str,
    db: DBDep,
    current_user: FleetManagerDep,
    reason: str | None = None,
) -> MaintenanceTaskResponse:
    """Cancel a maintenance task."""
    task = maintenance_task_service.get_or_404(db, task_id, organization_id=current_user.organization_id)
    updated = maintenance_task_service.cancel_task(db, task, reason=reason)
    return MaintenanceTaskResponse.model_validate(updated)


@router.delete("/tasks/{task_id}", status_code=204)
def delete_maintenance_task(
    task_id: str,
    db: DBDep,
    current_user: FleetManagerDep,
) -> None:
    """Delete a maintenance task."""
    maintenance_task_service.delete(db, task_id, organization_id=current_user.organization_id)


# Maintenance Schedule endpoints
@router.get("/schedules", response_model=list[MaintenanceScheduleResponse])
def list_maintenance_schedules(
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
    vehicle_id: str | None = None,
) -> list[MaintenanceScheduleResponse]:
    """List maintenance schedules."""
    if vehicle_id:
        schedules = maintenance_schedule_service.get_schedules_by_vehicle(
            db, vehicle_id, organization_id=current_user.organization_id
        )
    else:
        schedules = maintenance_schedule_service.get_multi(
            db,
            skip=skip,
            limit=limit,
            organization_id=current_user.organization_id,
        )
    return [MaintenanceScheduleResponse.model_validate(s) for s in schedules]


@router.post("/schedules", response_model=MaintenanceScheduleResponse, status_code=201)
def create_maintenance_schedule(
    schedule_in: MaintenanceScheduleCreate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> MaintenanceScheduleResponse:
    """Create a maintenance schedule."""
    schedule_data = schedule_in.model_copy(update={"organization_id": current_user.organization_id})
    schedule = maintenance_schedule_service.create(db, obj_in=schedule_data)
    return MaintenanceScheduleResponse.model_validate(schedule)


@router.get("/schedules/due")
def check_due_schedules(
    db: DBDep,
    current_user: CurrentUserDep,
) -> list[dict]:
    """Check which schedules are due for maintenance."""
    due = maintenance_schedule_service.check_due_schedules(
        db, organization_id=current_user.organization_id
    )
    return [
        {
            "schedule_id": item["schedule"].id,
            "vehicle_id": item["vehicle"].id,
            "vehicle_plate": item["vehicle"].registration_plate,
            "reason": item["reason"],
        }
        for item in due
    ]


@router.get("/schedules/{schedule_id}", response_model=MaintenanceScheduleResponse)
def get_maintenance_schedule(
    schedule_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> MaintenanceScheduleResponse:
    """Get a maintenance schedule by ID."""
    schedule = maintenance_schedule_service.get_or_404(db, schedule_id, organization_id=current_user.organization_id)
    return MaintenanceScheduleResponse.model_validate(schedule)


@router.patch("/schedules/{schedule_id}", response_model=MaintenanceScheduleResponse)
def update_maintenance_schedule(
    schedule_id: str,
    schedule_in: MaintenanceScheduleUpdate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> MaintenanceScheduleResponse:
    """Update a maintenance schedule."""
    schedule = maintenance_schedule_service.get_or_404(db, schedule_id, organization_id=current_user.organization_id)
    updated = maintenance_schedule_service.update(
        db, db_obj=schedule, obj_in=schedule_in
    )
    return MaintenanceScheduleResponse.model_validate(updated)


@router.post("/schedules/{schedule_id}/create-task", response_model=MaintenanceTaskResponse)
def create_task_from_schedule(
    schedule_id: str,
    db: DBDep,
    current_user: FleetManagerDep,
    scheduled_date: date | None = None,
) -> MaintenanceTaskResponse:
    """Create a maintenance task from a schedule."""
    schedule = maintenance_schedule_service.get_or_404(db, schedule_id, organization_id=current_user.organization_id)
    task = maintenance_schedule_service.create_task_from_schedule(
        db, schedule, scheduled_date=scheduled_date
    )
    return MaintenanceTaskResponse.model_validate(task)


@router.delete("/schedules/{schedule_id}", status_code=204)
def delete_maintenance_schedule(
    schedule_id: str,
    db: DBDep,
    current_user: FleetManagerDep,
) -> None:
    """Delete a maintenance schedule."""
    maintenance_schedule_service.delete(db, schedule_id, organization_id=current_user.organization_id)
