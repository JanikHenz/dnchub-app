"""GPS and trip endpoints."""

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Query

from app.shared.api.deps import CurrentUserDep, DBDep, FleetManagerDep
from app.models.enums import AlertSeverity, AlertType
from app.schemas import (
    GeofenceCreate,
    GeofenceResponse,
    GeofenceUpdate,
    GpsAlertCreate,
    GpsAlertResponse,
    GpsAlertUpdate,
    TripCreate,
    TripPositionCreate,
    TripPositionResponse,
    TripResponse,
    TripUpdate,
)
from app.services import (
    geofence_service,
    gps_alert_service,
    trip_position_service,
    trip_service,
)

router = APIRouter()


# Trip endpoints
@router.get("/trips", response_model=list[TripResponse])
def list_trips(
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
    vehicle_id: str | None = None,
    employee_id: str | None = None,
) -> list[TripResponse]:
    """List trips with optional filters."""
    if vehicle_id:
        trips = trip_service.get_trips_by_vehicle(
            db, vehicle_id, organization_id=current_user.organization_id, skip=skip, limit=limit
        )
    elif employee_id:
        trips = trip_service.get_trips_by_employee(
            db, employee_id, organization_id=current_user.organization_id, skip=skip, limit=limit
        )
    else:
        trips = trip_service.get_multi(
            db,
            skip=skip,
            limit=limit,
            organization_id=current_user.organization_id,
        )
    return [TripResponse.model_validate(t) for t in trips]


@router.post("/trips/start", response_model=TripResponse, status_code=201)
def start_trip(
    vehicle_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
    employee_id: str | None = None,
    start_location: str | None = None,
    start_odometer: Decimal | None = None,
) -> TripResponse:
    """Start a new trip."""
    trip = trip_service.start_trip(
        db,
        vehicle_id=vehicle_id,
        employee_id=employee_id,
        organization_id=current_user.organization_id,
        start_location=start_location,
        start_odometer=start_odometer,
    )
    return TripResponse.model_validate(trip)


@router.post("/trips/{trip_id}/end", response_model=TripResponse)
def end_trip(
    trip_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
    end_location: str | None = None,
    end_odometer: Decimal | None = None,
) -> TripResponse:
    """End an active trip."""
    trip = trip_service.get_or_404(db, trip_id, organization_id=current_user.organization_id)
    updated = trip_service.end_trip(
        db,
        trip=trip,
        end_location=end_location,
        end_odometer=end_odometer,
    )
    return TripResponse.model_validate(updated)


@router.get("/trips/active/{vehicle_id}", response_model=TripResponse | None)
def get_active_trip(
    vehicle_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> TripResponse | None:
    """Get active trip for a vehicle."""
    trip = trip_service.get_active_trip_for_vehicle(db, vehicle_id, organization_id=current_user.organization_id)
    return TripResponse.model_validate(trip) if trip else None


@router.get("/trips/statistics")
def get_trip_statistics(
    db: DBDep,
    current_user: CurrentUserDep,
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
) -> dict:
    """Get trip statistics for a period."""
    return trip_service.get_trip_statistics(
        db,
        organization_id=current_user.organization_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/trips/{trip_id}", response_model=TripResponse)
def get_trip(
    trip_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> TripResponse:
    """Get a trip by ID."""
    trip = trip_service.get_or_404(db, trip_id, organization_id=current_user.organization_id)
    return TripResponse.model_validate(trip)


@router.get("/trips/{trip_id}/route", response_model=list[TripPositionResponse])
def get_trip_route(
    trip_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> list[TripPositionResponse]:
    """Get trip route (GPS positions)."""
    trip_service.get_or_404(db, trip_id, organization_id=current_user.organization_id)
    positions = trip_position_service.get_trip_route(db, trip_id)
    return [TripPositionResponse.model_validate(p) for p in positions]


@router.post("/trips/{trip_id}/position", response_model=TripPositionResponse, status_code=201)
def add_trip_position(
    trip_id: str,
    latitude: Decimal,
    longitude: Decimal,
    db: DBDep,
    current_user: CurrentUserDep,
    speed: Decimal | None = None,
    heading: int | None = None,
) -> TripPositionResponse:
    """Add GPS position to a trip."""
    trip_service.get_or_404(db, trip_id, organization_id=current_user.organization_id)
    position = trip_position_service.add_position(
        db,
        trip_id=trip_id,
        latitude=latitude,
        longitude=longitude,
        speed=speed,
        heading=heading,
    )
    return TripPositionResponse.model_validate(position)


@router.get("/vehicles/{vehicle_id}/position", response_model=TripPositionResponse | None)
def get_vehicle_latest_position(
    vehicle_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> TripPositionResponse | None:
    """Get latest GPS position for a vehicle."""
    position = trip_position_service.get_latest_position_for_vehicle(
        db, vehicle_id, organization_id=current_user.organization_id
    )
    return TripPositionResponse.model_validate(position) if position else None


# Geofence endpoints
@router.get("/geofences", response_model=list[GeofenceResponse])
def list_geofences(
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
) -> list[GeofenceResponse]:
    """List geofences."""
    if active_only:
        geofences = geofence_service.get_active_geofences(
            db, organization_id=current_user.organization_id
        )
    else:
        geofences = geofence_service.get_multi(
            db,
            skip=skip,
            limit=limit,
            organization_id=current_user.organization_id,
        )
    return [GeofenceResponse.model_validate(g) for g in geofences]


@router.post("/geofences", response_model=GeofenceResponse, status_code=201)
def create_geofence(
    geofence_in: GeofenceCreate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> GeofenceResponse:
    """Create a geofence."""
    geofence_data = geofence_in.model_copy(update={"organization_id": current_user.organization_id})
    geofence = geofence_service.create(db, obj_in=geofence_data)
    return GeofenceResponse.model_validate(geofence)


@router.get("/geofences/{geofence_id}", response_model=GeofenceResponse)
def get_geofence(
    geofence_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> GeofenceResponse:
    """Get a geofence by ID."""
    geofence = geofence_service.get_or_404(db, geofence_id, organization_id=current_user.organization_id)
    return GeofenceResponse.model_validate(geofence)


@router.patch("/geofences/{geofence_id}", response_model=GeofenceResponse)
def update_geofence(
    geofence_id: str,
    geofence_in: GeofenceUpdate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> GeofenceResponse:
    """Update a geofence."""
    geofence = geofence_service.get_or_404(db, geofence_id, organization_id=current_user.organization_id)
    updated = geofence_service.update(db, db_obj=geofence, obj_in=geofence_in)
    return GeofenceResponse.model_validate(updated)


@router.delete("/geofences/{geofence_id}", status_code=204)
def delete_geofence(
    geofence_id: str,
    db: DBDep,
    current_user: FleetManagerDep,
) -> None:
    """Delete a geofence."""
    geofence_service.delete(db, geofence_id, organization_id=current_user.organization_id)


@router.post("/geofences/{geofence_id}/check")
def check_position_in_geofence(
    geofence_id: str,
    latitude: Decimal,
    longitude: Decimal,
    db: DBDep,
    current_user: CurrentUserDep,
) -> dict:
    """Check if a position is inside a geofence."""
    geofence = geofence_service.get_or_404(db, geofence_id, organization_id=current_user.organization_id)
    is_inside = geofence_service.check_position_in_geofence(
        geofence, latitude, longitude
    )
    return {"is_inside": is_inside}


# GPS Alert endpoints
@router.get("/alerts", response_model=list[GpsAlertResponse])
def list_gps_alerts(
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
    vehicle_id: str | None = None,
    unacknowledged_only: bool = False,
    severity: AlertSeverity | None = None,
) -> list[GpsAlertResponse]:
    """List GPS alerts with filters."""
    if vehicle_id:
        alerts = gps_alert_service.get_alerts_by_vehicle(
            db, vehicle_id, skip=skip, limit=limit
        )
    elif unacknowledged_only:
        alerts = gps_alert_service.get_unacknowledged_alerts(
            db,
            organization_id=current_user.organization_id,
            severity=severity,
        )
    else:
        alerts = gps_alert_service.get_multi(
            db,
            skip=skip,
            limit=limit,
            organization_id=current_user.organization_id,
        )
    return [GpsAlertResponse.model_validate(a) for a in alerts]


@router.post("/alerts", response_model=GpsAlertResponse, status_code=201)
def create_gps_alert(
    vehicle_id: str,
    alert_type: AlertType,
    severity: AlertSeverity,
    message: str,
    db: DBDep,
    current_user: CurrentUserDep,
    trip_id: str | None = None,
    latitude: Decimal | None = None,
    longitude: Decimal | None = None,
) -> GpsAlertResponse:
    """Create a GPS alert."""
    alert = gps_alert_service.create_alert(
        db,
        organization_id=current_user.organization_id,
        vehicle_id=vehicle_id,
        trip_id=trip_id,
        alert_type=alert_type,
        severity=severity,
        message=message,
        latitude=latitude,
        longitude=longitude,
    )
    return GpsAlertResponse.model_validate(alert)


@router.get("/alerts/{alert_id}", response_model=GpsAlertResponse)
def get_gps_alert(
    alert_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> GpsAlertResponse:
    """Get a GPS alert by ID."""
    alert = gps_alert_service.get_or_404(db, alert_id, organization_id=current_user.organization_id)
    return GpsAlertResponse.model_validate(alert)


@router.post("/alerts/{alert_id}/acknowledge", response_model=GpsAlertResponse)
def acknowledge_gps_alert(
    alert_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> GpsAlertResponse:
    """Acknowledge a GPS alert."""
    alert = gps_alert_service.get_or_404(db, alert_id, organization_id=current_user.organization_id)
    updated = gps_alert_service.acknowledge_alert(
        db, alert, acknowledged_by=current_user.id
    )
    return GpsAlertResponse.model_validate(updated)
