"""Fuel pump delivery service."""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FuelPumpDelivery
from app.schemas import FuelPumpDeliveryCreate, FuelPumpDeliveryUpdate
from app.shared.services.base import BaseService


class FuelPumpDeliveryService(
    BaseService[FuelPumpDelivery, FuelPumpDeliveryCreate, FuelPumpDeliveryUpdate]
):
    """Fuel pump delivery service with specialized operations."""

    def __init__(self):
        super().__init__(FuelPumpDelivery)

    def create(
        self,
        db: Session,
        *,
        obj_in: FuelPumpDeliveryCreate,
    ) -> FuelPumpDelivery:
        """Create a fuel pump delivery and update pump level."""
        from app.modules.fleet.services.fuel_pump import fuel_pump_service

        # Get pump to update level
        pump = fuel_pump_service.get_or_404(db, obj_in.pump_id, organization_id=obj_in.organization_id)

        # Calculate total cost
        total_cost = obj_in.volume * obj_in.price_per_unit

        # Create entry data
        entry_data = obj_in.model_dump()
        entry_data["total_cost"] = total_cost

        # Set level_before from pump's current level if not provided
        if entry_data.get("level_before") is None:
            entry_data["level_before"] = pump.current_level

        # Calculate level_after if not provided
        if entry_data.get("level_after") is None:
            entry_data["level_after"] = min(
                pump.current_level + obj_in.volume,
                pump.capacity,
            )

        # Set pump_odometer_before from pump if not provided
        if entry_data.get("pump_odometer_before") is None:
            entry_data["pump_odometer_before"] = pump.current_odometer

        db_obj = FuelPumpDelivery(**entry_data)
        db.add(db_obj)

        # Update pump level
        fuel_pump_service.receive_delivery(
            db,
            obj_in.pump_id,
            obj_in.volume,
            obj_in.pump_odometer_after,
            organization_id=obj_in.organization_id,
        )

        db.flush()
        db.refresh(db_obj)
        return db_obj

    def get_by_pump(
        self,
        db: Session,
        pump_id: str,
        *,
        organization_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[FuelPumpDelivery]:
        """Get deliveries for a specific pump."""
        result = db.execute(
            select(FuelPumpDelivery)
            .where(
                FuelPumpDelivery.pump_id == pump_id,
                FuelPumpDelivery.deleted_at.is_(None),
                FuelPumpDelivery.organization_id == organization_id
            )
            .order_by(FuelPumpDelivery.delivery_date.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    def get_by_date_range(
        self,
        db: Session,
        organization_id: str,
        start_date: date,
        end_date: date,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[FuelPumpDelivery]:
        """Get deliveries within a date range."""
        result = db.execute(
            select(FuelPumpDelivery)
            .where(
                FuelPumpDelivery.organization_id == organization_id,
                FuelPumpDelivery.delivery_date >= start_date,
                FuelPumpDelivery.delivery_date <= end_date,
                FuelPumpDelivery.deleted_at.is_(None),
            )
            .order_by(FuelPumpDelivery.delivery_date.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    def get_summary(
        self,
        db: Session,
        organization_id: str,
        start_date: date,
        end_date: date,
    ) -> dict:
        """Get delivery summary for a date range."""
        result = db.execute(
            select(
                func.sum(FuelPumpDelivery.volume).label("total_volume"),
                func.sum(FuelPumpDelivery.total_cost).label("total_cost"),
                func.avg(FuelPumpDelivery.price_per_unit).label("avg_price"),
                func.count(FuelPumpDelivery.id).label("count"),
            ).where(
                FuelPumpDelivery.organization_id == organization_id,
                FuelPumpDelivery.delivery_date >= start_date,
                FuelPumpDelivery.delivery_date <= end_date,
                FuelPumpDelivery.deleted_at.is_(None),
            )
        )
        row = result.one()

        return {
            "total_volume": row.total_volume or Decimal("0"),
            "total_cost": row.total_cost or Decimal("0"),
            "average_price_per_unit": row.avg_price or Decimal("0"),
            "deliveries_count": row.count or 0,
            "period_start": start_date,
            "period_end": end_date,
        }


fuel_pump_delivery_service = FuelPumpDeliveryService()
