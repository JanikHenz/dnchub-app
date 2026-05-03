"""Fuel entry service."""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FuelEntry, Vehicle
from app.schemas import FuelAnalytics, FuelEntryCreate, FuelEntryUpdate
from app.shared.services.base import BaseService


class FuelService(BaseService[FuelEntry, FuelEntryCreate, FuelEntryUpdate]):
    """Fuel entry service with specialized operations."""

    def __init__(self):
        super().__init__(FuelEntry)

    def create(
        self,
        db: Session,
        *,
        obj_in: FuelEntryCreate,
    ) -> FuelEntry:
        """Create a fuel entry with calculated fields."""
        # Get vehicle to update odometer
        from app.modules.fleet.services.vehicle import vehicle_service

        vehicle = vehicle_service.get_or_404(db, obj_in.vehicle_id, organization_id=obj_in.organization_id)

        # Calculate total cost
        total_cost = obj_in.volume * obj_in.price_per_unit

        # Get previous entry for this vehicle to calculate distance
        previous_entry = self._get_last_entry_for_vehicle(db, obj_in.vehicle_id)

        previous_odometer = None
        distance = None
        fuel_efficiency = None

        if previous_entry:
            previous_odometer = previous_entry.odometer
            if obj_in.odometer > previous_entry.odometer:
                distance = obj_in.odometer - previous_entry.odometer

                # Calculate efficiency if full tank
                if obj_in.full_tank and distance > 0:
                    fuel_efficiency = distance / obj_in.volume

        # Create entry data
        entry_data = obj_in.model_dump()
        entry_data["total_cost"] = total_cost
        entry_data["previous_odometer"] = previous_odometer
        entry_data["distance"] = distance
        entry_data["fuel_efficiency"] = fuel_efficiency

        db_obj = FuelEntry(**entry_data)
        db.add(db_obj)

        # Update vehicle odometer if new reading is higher
        if obj_in.odometer > vehicle.current_odometer:
            vehicle.current_odometer = obj_in.odometer

        # Update vehicle total fuel cost
        vehicle.total_fuel_cost = (vehicle.total_fuel_cost or Decimal("0")) + total_cost
        db.add(vehicle)

        db.flush()
        db.refresh(db_obj)
        return db_obj

    def _get_last_entry_for_vehicle(
        self,
        db: Session,
        vehicle_id: str,
    ) -> FuelEntry | None:
        """Get the most recent fuel entry for a vehicle."""
        result = db.execute(
            select(FuelEntry)
            .where(
                FuelEntry.vehicle_id == vehicle_id,
                FuelEntry.deleted_at.is_(None),
            )
            .order_by(FuelEntry.date.desc(), FuelEntry.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    def get_entries_by_vehicle(
        self,
        db: Session,
        vehicle_id: str,
        *,
        organization_id: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[FuelEntry]:
        """Get fuel entries for a specific vehicle."""
        result = db.execute(
            select(FuelEntry)
            .where(
                FuelEntry.vehicle_id == vehicle_id,
                FuelEntry.deleted_at.is_(None),
                FuelEntry.organization_id == organization_id
            )
            .order_by(FuelEntry.date.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    def get_entries_by_date_range(
        self,
        db: Session,
        organization_id: str,
        start_date: date,
        end_date: date,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[FuelEntry]:
        """Get fuel entries within a date range."""
        result = db.execute(
            select(FuelEntry)
            .where(
                FuelEntry.organization_id == organization_id,
                FuelEntry.date >= start_date,
                FuelEntry.date <= end_date,
                FuelEntry.deleted_at.is_(None),
            )
            .order_by(FuelEntry.date.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    def get_analytics(
        self,
        db: Session,
        organization_id: str,
        start_date: date,
        end_date: date,
    ) -> FuelAnalytics:
        """Get fuel analytics for a date range."""
        result = db.execute(
            select(
                func.sum(FuelEntry.volume).label("total_volume"),
                func.sum(FuelEntry.total_cost).label("total_cost"),
                func.avg(FuelEntry.price_per_unit).label("avg_price"),
                func.avg(FuelEntry.fuel_efficiency).label("avg_efficiency"),
                func.count(FuelEntry.id).label("count"),
            ).where(
                FuelEntry.organization_id == organization_id,
                FuelEntry.date >= start_date,
                FuelEntry.date <= end_date,
                FuelEntry.deleted_at.is_(None),
            )
        )
        row = result.one()

        return FuelAnalytics(
            total_volume=row.total_volume or Decimal("0"),
            total_cost=row.total_cost or Decimal("0"),
            average_price_per_unit=row.avg_price or Decimal("0"),
            average_efficiency=row.avg_efficiency,
            entries_count=row.count or 0,
            period_start=start_date,
            period_end=end_date,
        )

    def get_entries_by_employee(
        self,
        db: Session,
        employee_id: str,
        *,
        organization_id: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[FuelEntry]:
        """Get fuel entries for a specific employee."""
        result = db.execute(
            select(FuelEntry)
            .where(
                FuelEntry.employee_id == employee_id,
                FuelEntry.deleted_at.is_(None),
                FuelEntry.organization_id == organization_id
            )
            .order_by(FuelEntry.date.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    def delete(
        self,
        db: Session,
        id: str,
        soft_delete: bool = True,
        *,
        organization_id: str | None = None,
    ) -> FuelEntry | None:
        """Delete a fuel entry and update vehicle total fuel cost."""
        entry = self.get(db, id, organization_id=organization_id)
        if entry is None:
            return None

        # Update vehicle total fuel cost
        from app.modules.fleet.services.vehicle import vehicle_service

        vehicle = vehicle_service.get(db, entry.vehicle_id)
        if vehicle and entry.total_cost:
            vehicle.total_fuel_cost = max(
                Decimal("0"),
                (vehicle.total_fuel_cost or Decimal("0")) - entry.total_cost
            )
            db.add(vehicle)

        # Call parent delete
        return super().delete(db, id, soft_delete)


fuel_service = FuelService()
