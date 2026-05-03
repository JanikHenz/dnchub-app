"""Maintenance service."""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import MaintenanceSchedule, MaintenanceTask, Vehicle
from app.models.enums import MaintenanceStatus, MaintenancePriority
from app.schemas import (
    MaintenanceScheduleCreate,
    MaintenanceScheduleUpdate,
    MaintenanceTaskCreate,
    MaintenanceTaskUpdate,
)
from app.shared.services.base import BaseService


class MaintenanceTaskService(
    BaseService[MaintenanceTask, MaintenanceTaskCreate, MaintenanceTaskUpdate]
):
    """Maintenance task service."""

    def __init__(self):
        super().__init__(MaintenanceTask)

    def get_tasks_by_vehicle(
        self,
        db: Session,
        vehicle_id: str,
        *,
        organization_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[MaintenanceTask]:
        """Get maintenance tasks for a specific vehicle."""
        result = db.execute(
            select(MaintenanceTask)
            .where(
                MaintenanceTask.vehicle_id == vehicle_id,
                MaintenanceTask.deleted_at.is_(None),
                MaintenanceTask.organization_id == organization_id
            )
            .order_by(MaintenanceTask.scheduled_date.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    def get_tasks_by_status(
        self,
        db: Session,
        organization_id: str,
        status: MaintenanceStatus,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[MaintenanceTask]:
        """Get maintenance tasks by status."""
        result = db.execute(
            select(MaintenanceTask)
            .where(
                MaintenanceTask.organization_id == organization_id,
                MaintenanceTask.status == status,
                MaintenanceTask.deleted_at.is_(None),
            )
            .order_by(MaintenanceTask.scheduled_date.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    def get_overdue_tasks(
        self,
        db: Session,
        organization_id: str,
    ) -> list[MaintenanceTask]:
        """Get overdue maintenance tasks."""
        today = date.today()
        result = db.execute(
            select(MaintenanceTask)
            .where(
                MaintenanceTask.organization_id == organization_id,
                MaintenanceTask.status.in_([
                    MaintenanceStatus.SCHEDULED,
                    MaintenanceStatus.IN_PROGRESS,
                ]),
                MaintenanceTask.scheduled_date < today,
                MaintenanceTask.deleted_at.is_(None),
            )
            .order_by(MaintenanceTask.scheduled_date.asc())
        )
        return list(result.scalars().all())

    def get_upcoming_tasks(
        self,
        db: Session,
        organization_id: str,
        days: int = 7,
    ) -> list[MaintenanceTask]:
        """Get upcoming maintenance tasks within specified days."""
        today = date.today()
        end_date = today + timedelta(days=days)
        result = db.execute(
            select(MaintenanceTask)
            .where(
                MaintenanceTask.organization_id == organization_id,
                MaintenanceTask.status == MaintenanceStatus.SCHEDULED,
                MaintenanceTask.scheduled_date >= today,
                MaintenanceTask.scheduled_date <= end_date,
                MaintenanceTask.deleted_at.is_(None),
            )
            .order_by(MaintenanceTask.scheduled_date.asc())
        )
        return list(result.scalars().all())

    def complete_task(
        self,
        db: Session,
        task: MaintenanceTask,
        actual_cost: Decimal | None = None,
        notes: str | None = None,
    ) -> MaintenanceTask:
        """Mark a maintenance task as completed."""
        task.status = MaintenanceStatus.COMPLETED
        task.completed_date = date.today()
        if actual_cost is not None:
            task.actual_cost = actual_cost
        if notes is not None:
            task.notes = notes

        db.add(task)
        db.flush()
        db.refresh(task)
        return task

    def cancel_task(
        self,
        db: Session,
        task: MaintenanceTask,
        reason: str | None = None,
    ) -> MaintenanceTask:
        """Cancel a maintenance task."""
        task.status = MaintenanceStatus.CANCELLED
        if reason:
            task.notes = f"{task.notes or ''}\nCancellation reason: {reason}".strip()

        db.add(task)
        db.flush()
        db.refresh(task)
        return task

    def get_maintenance_cost_summary(
        self,
        db: Session,
        organization_id: str,
        start_date: date,
        end_date: date,
    ) -> dict:
        """Get maintenance cost summary for a period."""
        result = db.execute(
            select(
                func.count(MaintenanceTask.id).label("total_tasks"),
                func.sum(MaintenanceTask.actual_cost).label("total_cost"),
                func.avg(MaintenanceTask.actual_cost).label("avg_cost"),
            ).where(
                MaintenanceTask.organization_id == organization_id,
                MaintenanceTask.status == MaintenanceStatus.COMPLETED,
                MaintenanceTask.completed_date >= start_date,
                MaintenanceTask.completed_date <= end_date,
                MaintenanceTask.deleted_at.is_(None),
            )
        )
        row = result.one()
        return {
            "total_tasks": row.total_tasks or 0,
            "total_cost": row.total_cost or Decimal("0"),
            "average_cost": row.avg_cost or Decimal("0"),
            "period_start": start_date,
            "period_end": end_date,
        }


class MaintenanceScheduleService(
    BaseService[MaintenanceSchedule, MaintenanceScheduleCreate, MaintenanceScheduleUpdate]
):
    """Maintenance schedule service."""

    def __init__(self):
        super().__init__(MaintenanceSchedule)

    def get_schedules_by_vehicle(
        self,
        db: Session,
        vehicle_id: str,
        *,
        organization_id: str,
    ) -> list[MaintenanceSchedule]:
        """Get maintenance schedules for a vehicle."""
        result = db.execute(
            select(MaintenanceSchedule)
            .where(
                MaintenanceSchedule.vehicle_id == vehicle_id,
                MaintenanceSchedule.is_active == True,
                MaintenanceSchedule.deleted_at.is_(None),
                MaintenanceSchedule.organization_id == organization_id
            )
        )
        return list(result.scalars().all())

    def get_active_schedules(
        self,
        db: Session,
        organization_id: str,
    ) -> list[MaintenanceSchedule]:
        """Get all active maintenance schedules."""
        result = db.execute(
            select(MaintenanceSchedule)
            .where(
                MaintenanceSchedule.organization_id == organization_id,
                MaintenanceSchedule.is_active == True,
                MaintenanceSchedule.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    def check_due_schedules(
        self,
        db: Session,
        organization_id: str,
    ) -> list[dict]:
        """Check which schedules are due for maintenance."""
        schedules = self.get_active_schedules(db, organization_id)
        due_schedules = []

        for schedule in schedules:
            vehicle = db.get(Vehicle, schedule.vehicle_id)
            if not vehicle:
                continue

            is_due = False
            reason = ""

            # Check interval-based trigger
            if schedule.interval_km:
                km_since_last = vehicle.current_odometer - (schedule.last_performed_odometer or Decimal("0"))
                if km_since_last >= schedule.interval_km:
                    is_due = True
                    reason = f"Exceeded {schedule.interval_km} km interval"

            # Check time-based trigger
            if schedule.interval_days and schedule.last_performed_date:
                days_since_last = (date.today() - schedule.last_performed_date).days
                if days_since_last >= schedule.interval_days:
                    is_due = True
                    reason = f"Exceeded {schedule.interval_days} days interval"

            if is_due:
                due_schedules.append({
                    "schedule": schedule,
                    "vehicle": vehicle,
                    "reason": reason,
                })

        return due_schedules

    def create_task_from_schedule(
        self,
        db: Session,
        schedule: MaintenanceSchedule,
        scheduled_date: date | None = None,
    ) -> MaintenanceTask:
        """Create a maintenance task from a schedule."""
        task = MaintenanceTask(
            organization_id=schedule.organization_id,
            vehicle_id=schedule.vehicle_id,
            type=schedule.maintenance_type,
            description=schedule.description,
            scheduled_date=scheduled_date or date.today(),
            estimated_cost=schedule.estimated_cost,
            priority=MaintenancePriority.MEDIUM,
            status=MaintenanceStatus.SCHEDULED,
        )
        db.add(task)
        db.flush()
        db.refresh(task)
        return task

    def update_after_completion(
        self,
        db: Session,
        schedule: MaintenanceSchedule,
        vehicle: Vehicle,
    ) -> MaintenanceSchedule:
        """Update schedule after task completion."""
        schedule.last_performed_date = date.today()
        schedule.last_performed_odometer = vehicle.current_odometer
        db.add(schedule)
        db.flush()
        db.refresh(schedule)
        return schedule


maintenance_task_service = MaintenanceTaskService()
maintenance_schedule_service = MaintenanceScheduleService()
