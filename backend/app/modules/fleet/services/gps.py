"""GPS and trip service."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Geofence, GpsAlert, Trip, TripPosition, Vehicle
from app.models.enums import AlertSeverity, AlertType
from app.schemas import (
    GeofenceCreate,
    GeofenceUpdate,
    GpsAlertCreate,
    GpsAlertUpdate,
    TripCreate,
    TripPositionCreate,
    TripPositionUpdate,
    TripUpdate,
)
from app.shared.services.base import BaseService


class TripService(BaseService[Trip, TripCreate, TripUpdate]):
    """Trip service."""

    def __init__(self):
        super().__init__(Trip)

    def get_active_trip_for_vehicle(
        self,
        db: Session,
        vehicle_id: str,
        *,
        organization_id: str,
    ) -> Trip | None:
        """Get the current active trip for a vehicle."""
        result = db.execute(
            select(Trip).where(
                Trip.vehicle_id == vehicle_id,
                Trip.end_time.is_(None),  # Active trip has no end_time
                Trip.organization_id == organization_id
            )
        )
        return result.scalar_one_or_none()

    def start_trip(
        self,
        db: Session,
        vehicle_id: str,
        employee_id: str | None,
        organization_id: str,
        start_latitude: Decimal,
        start_longitude: Decimal,
    ) -> Trip:
        """Start a new trip."""
        now = datetime.now(timezone.utc)
        trip = Trip(
            organization_id=organization_id,
            vehicle_id=vehicle_id,
            employee_id=employee_id,
            start_time=now,
            start_latitude=start_latitude,
            start_longitude=start_longitude,
            start_timestamp=now,
        )
        db.add(trip)
        db.flush()
        db.refresh(trip)
        return trip

    def end_trip(
        self,
        db: Session,
        trip: Trip,
        end_latitude: Decimal | None = None,
        end_longitude: Decimal | None = None,
    ) -> Trip:
        """End an active trip."""
        now = datetime.now(timezone.utc)
        trip.end_time = now
        trip.end_timestamp = now
        if end_latitude is not None:
            trip.end_latitude = end_latitude
        if end_longitude is not None:
            trip.end_longitude = end_longitude

        # Calculate duration in seconds
        if trip.start_time and trip.end_time:
            duration = trip.end_time - trip.start_time
            trip.duration = int(duration.total_seconds())

        db.add(trip)
        db.flush()
        db.refresh(trip)
        return trip

    def get_trips_by_vehicle(
        self,
        db: Session,
        vehicle_id: str,
        *,
        organization_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Trip]:
        """Get trips for a vehicle."""
        result = db.execute(
            select(Trip)
            .where(Trip.vehicle_id == vehicle_id, Trip.organization_id == organization_id)
            .order_by(Trip.start_time.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    def get_trips_by_employee(
        self,
        db: Session,
        employee_id: str,
        *,
        organization_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Trip]:
        """Get trips for an employee."""
        result = db.execute(
            select(Trip)
            .where(Trip.employee_id == employee_id, Trip.organization_id == organization_id)
            .order_by(Trip.start_time.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    def get_trip_statistics(
        self,
        db: Session,
        organization_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> dict:
        """Get trip statistics for a period."""
        result = db.execute(
            select(
                func.count(Trip.id).label("total_trips"),
                func.sum(Trip.distance).label("total_distance"),
                func.sum(Trip.duration).label("total_duration"),
                func.avg(Trip.distance).label("avg_distance"),
                func.avg(Trip.duration).label("avg_duration"),
            ).where(
                Trip.organization_id == organization_id,
                Trip.end_time.is_not(None),  # Completed trips have end_time
                Trip.start_time >= start_date,
                Trip.start_time <= end_date,
            )
        )
        row = result.one()

        return {
            "total_trips": row.total_trips or 0,
            "total_distance": row.total_distance or Decimal("0"),
            "total_duration_seconds": row.total_duration or 0,
            "average_distance": row.avg_distance or Decimal("0"),
            "average_duration_seconds": row.avg_duration or 0,
            "period_start": start_date,
            "period_end": end_date,
        }


class TripPositionService(BaseService[TripPosition, TripPositionCreate, TripPositionUpdate]):
    """Trip position service for GPS tracking."""

    def __init__(self):
        super().__init__(TripPosition)

    def add_position(
        self,
        db: Session,
        trip_id: str,
        latitude: Decimal,
        longitude: Decimal,
        speed: Decimal | None = None,
        heading: int | None = None,
    ) -> TripPosition:
        """Add a GPS position to a trip."""
        position = TripPosition(
            trip_id=trip_id,
            latitude=latitude,
            longitude=longitude,
            speed=speed,
            heading=heading,
            recorded_at=datetime.now(timezone.utc),
        )
        db.add(position)
        db.flush()
        db.refresh(position)
        return position

    def get_trip_route(
        self,
        db: Session,
        trip_id: str,
    ) -> list[TripPosition]:
        """Get all positions for a trip route."""
        result = db.execute(
            select(TripPosition)
            .where(TripPosition.trip_id == trip_id)
            .order_by(TripPosition.recorded_at.asc())
        )
        return list(result.scalars().all())

    def get_latest_position_for_vehicle(
        self,
        db: Session,
        vehicle_id: str,
        *,
        organization_id: str,
    ) -> TripPosition | None:
        """Get the latest GPS position for a vehicle."""
        result = db.execute(
            select(TripPosition)
            .join(Trip)
            .where(Trip.vehicle_id == vehicle_id, Trip.organization_id == organization_id)
            .order_by(TripPosition.recorded_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


class GeofenceService(BaseService[Geofence, GeofenceCreate, GeofenceUpdate]):
    """Geofence service."""

    def __init__(self):
        super().__init__(Geofence)

    def get_active_geofences(
        self,
        db: Session,
        organization_id: str,
    ) -> list[Geofence]:
        """Get all active geofences."""
        result = db.execute(
            select(Geofence).where(
                Geofence.organization_id == organization_id,
                Geofence.is_active == True,
                Geofence.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    def check_position_in_geofence(
        self,
        geofence: Geofence,
        latitude: Decimal,
        longitude: Decimal,
    ) -> bool:
        """Check if a position is inside a geofence (circular)."""
        from math import asin, cos, radians, sin, sqrt

        # Haversine formula for circular geofence
        lat1 = radians(float(geofence.center_latitude))
        lat2 = radians(float(latitude))
        lon1 = radians(float(geofence.center_longitude))
        lon2 = radians(float(longitude))

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))

        # Earth's radius in meters
        r = 6371000

        distance = c * r

        return distance <= float(geofence.radius)


class GpsAlertService(BaseService[GpsAlert, GpsAlertCreate, GpsAlertUpdate]):
    """GPS alert service."""

    def __init__(self):
        super().__init__(GpsAlert)

    def create_alert(
        self,
        db: Session,
        organization_id: str,
        vehicle_id: str,
        trip_id: str | None,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        latitude: Decimal | None = None,
        longitude: Decimal | None = None,
    ) -> GpsAlert:
        """Create a GPS alert."""
        alert = GpsAlert(
            organization_id=organization_id,
            vehicle_id=vehicle_id,
            trip_id=trip_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            latitude=latitude,
            longitude=longitude,
            triggered_at=datetime.now(timezone.utc),
            is_acknowledged=False,
        )
        db.add(alert)
        db.flush()
        db.refresh(alert)
        return alert

    def get_unacknowledged_alerts(
        self,
        db: Session,
        organization_id: str,
        *,
        severity: AlertSeverity | None = None,
    ) -> list[GpsAlert]:
        """Get unacknowledged alerts."""
        query = select(GpsAlert).where(
            GpsAlert.organization_id == organization_id,
            GpsAlert.is_acknowledged == False,
            GpsAlert.deleted_at.is_(None),
        )

        if severity:
            query = query.where(GpsAlert.severity == severity)

        result = db.execute(
            query.order_by(GpsAlert.triggered_at.desc())
        )
        return list(result.scalars().all())

    def acknowledge_alert(
        self,
        db: Session,
        alert: GpsAlert,
        acknowledged_by: str | None = None,
    ) -> GpsAlert:
        """Acknowledge an alert."""
        alert.is_acknowledged = True
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = acknowledged_by
        db.add(alert)
        db.flush()
        db.refresh(alert)
        return alert

    def get_alerts_by_vehicle(
        self,
        db: Session,
        vehicle_id: str,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[GpsAlert]:
        """Get alerts for a vehicle."""
        result = db.execute(
            select(GpsAlert)
            .where(
                GpsAlert.vehicle_id == vehicle_id,
                GpsAlert.deleted_at.is_(None),
            )
            .order_by(GpsAlert.triggered_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


trip_service = TripService()
trip_position_service = TripPositionService()
geofence_service = GeofenceService()
gps_alert_service = GpsAlertService()
