"""Fuel pump service."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FuelPump
from app.models.enums import FuelType, PumpStatus
from app.schemas import FuelPumpCreate, FuelPumpUpdate
from app.shared.services.base import BaseService


class FuelPumpService(BaseService[FuelPump, FuelPumpCreate, FuelPumpUpdate]):
    """Fuel pump service with specialized operations."""

    def __init__(self):
        super().__init__(FuelPump)

    def get_by_code(
        self,
        db: Session,
        organization_id: str,
        code: str,
    ) -> FuelPump | None:
        """Get pump by code within organization."""
        result = db.execute(
            select(FuelPump).where(
                FuelPump.organization_id == organization_id,
                FuelPump.code == code,
                FuelPump.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    def get_by_fuel_type(
        self,
        db: Session,
        organization_id: str,
        fuel_type: FuelType,
        *,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = True,
    ) -> list[FuelPump]:
        """Get pumps by fuel type within organization."""
        query = select(FuelPump).where(
            FuelPump.organization_id == organization_id,
            FuelPump.fuel_type == fuel_type,
            FuelPump.deleted_at.is_(None),
        )

        if active_only:
            query = query.where(FuelPump.status == PumpStatus.ACTIVE)

        result = db.execute(
            query.order_by(FuelPump.name).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    def get_with_alerts(
        self,
        db: Session,
        organization_id: str,
    ) -> list[FuelPump]:
        """Get all pumps with active alerts (low level or maintenance due)."""
        today = date.today()
        result = db.execute(
            select(FuelPump).where(
                FuelPump.organization_id == organization_id,
                FuelPump.deleted_at.is_(None),
                FuelPump.status == PumpStatus.ACTIVE,
            )
        )
        pumps = list(result.scalars().all())

        # Filter to only those with alerts
        return [
            p for p in pumps
            if p.is_low_level or p.is_maintenance_due
        ]

    def dispense_fuel(
        self,
        db: Session,
        pump_id: str,
        volume: Decimal,
        new_odometer: Decimal | None = None,
        organization_id: str | None = None,
    ) -> FuelPump:
        """Reduce pump level after fuel dispensing."""
        pump = self.get_or_404(db, pump_id, organization_id=organization_id)

        # Reduce the level
        pump.current_level = max(Decimal("0"), pump.current_level - volume)

        # Update odometer if provided
        if new_odometer is not None and new_odometer > pump.current_odometer:
            pump.current_odometer = new_odometer

        db.add(pump)
        db.flush()
        db.refresh(pump)
        return pump

    def receive_delivery(
        self,
        db: Session,
        pump_id: str,
        volume: Decimal,
        new_odometer: Decimal | None = None,
        organization_id: str | None = None,
    ) -> FuelPump:
        """Increase pump level after fuel delivery."""
        pump = self.get_or_404(db, pump_id, organization_id=organization_id)

        # Increase the level (cap at capacity)
        new_level = pump.current_level + volume
        pump.current_level = min(new_level, pump.capacity)

        # Update odometer if provided
        if new_odometer is not None:
            pump.current_odometer = new_odometer

        db.add(pump)
        db.flush()
        db.refresh(pump)
        return pump

    def adjust_level(
        self,
        db: Session,
        pump_id: str,
        adjustment: Decimal,
        organization_id: str | None = None,
    ) -> FuelPump:
        """Manually adjust pump level (positive to add, negative to remove)."""
        pump = self.get_or_404(db, pump_id, organization_id=organization_id)

        new_level = pump.current_level + adjustment
        # Ensure level stays within bounds
        pump.current_level = max(Decimal("0"), min(new_level, pump.capacity))

        db.add(pump)
        db.flush()
        db.refresh(pump)
        return pump

    def update_maintenance(
        self,
        db: Session,
        pump_id: str,
        maintenance_date: date,
        organization_id: str | None = None,
    ) -> FuelPump:
        """Update maintenance date and calculate next maintenance."""
        pump = self.get_or_404(db, pump_id, organization_id=organization_id)

        pump.last_maintenance_date = maintenance_date

        # Calculate next maintenance date if interval is set
        if pump.maintenance_interval_days:
            from datetime import timedelta
            pump.next_maintenance_date = maintenance_date + timedelta(
                days=pump.maintenance_interval_days
            )

        db.add(pump)
        db.flush()
        db.refresh(pump)
        return pump

    def get_stats(
        self,
        db: Session,
        organization_id: str,
    ) -> dict:
        """Get pump statistics for organization."""
        result = db.execute(
            select(FuelPump).where(
                FuelPump.organization_id == organization_id,
                FuelPump.deleted_at.is_(None),
            )
        )
        pumps = list(result.scalars().all())

        total_capacity = sum(p.capacity for p in pumps)
        total_current = sum(p.current_level for p in pumps)
        active_count = sum(1 for p in pumps if p.status == PumpStatus.ACTIVE)
        alert_count = sum(1 for p in pumps if p.is_low_level or p.is_maintenance_due)

        return {
            "total_pumps": len(pumps),
            "active_pumps": active_count,
            "total_capacity": total_capacity,
            "total_current_level": total_current,
            "alerts_count": alert_count,
        }


fuel_pump_service = FuelPumpService()
