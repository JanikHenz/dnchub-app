"""Notification endpoints."""

from fastapi import APIRouter, HTTPException

from app.shared.api.deps import CurrentUserDep, DBDep
from app.models.enums import NotificationType
from app.schemas import (
    NotificationResponse,
)
from app.services import notification_service

router = APIRouter()


@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 50,
    unread_only: bool = False,
    notification_type: NotificationType | None = None,
) -> list[NotificationResponse]:
    """List notifications for the current user."""
    if notification_type:
        notifications = notification_service.get_notifications_by_type(
            db,
            user_id=current_user.id,
            notification_type=notification_type,
            skip=skip,
            limit=limit,
        )
    else:
        notifications = notification_service.get_user_notifications(
            db,
            user_id=current_user.id,
            unread_only=unread_only,
            skip=skip,
            limit=limit,
        )
    return [NotificationResponse.model_validate(n) for n in notifications]


@router.get("/unread-count")
def get_unread_count(
    db: DBDep,
    current_user: CurrentUserDep,
) -> dict:
    """Get count of unread notifications."""
    count = notification_service.get_unread_count(
        db, user_id=current_user.id
    )
    return {"unread_count": count}


@router.get("/high-priority", response_model=list[NotificationResponse])
def list_high_priority_notifications(
    db: DBDep,
    current_user: CurrentUserDep,
) -> list[NotificationResponse]:
    """List unread high priority notifications."""
    notifications = notification_service.get_high_priority_notifications(
        db, user_id=current_user.id
    )
    return [NotificationResponse.model_validate(n) for n in notifications]


@router.get("/{notification_id}", response_model=NotificationResponse)
def get_notification(
    notification_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> NotificationResponse:
    """Get a notification by ID."""
    notification = notification_service.get_or_404(db, notification_id)
    if notification.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Notification with id '{notification_id}' not found")
    return NotificationResponse.model_validate(notification)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_as_read(
    notification_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> NotificationResponse:
    """Mark a notification as read."""
    notification = notification_service.get_or_404(db, notification_id)
    if notification.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Notification with id '{notification_id}' not found")
    updated = notification_service.mark_as_read(db, notification)
    return NotificationResponse.model_validate(updated)


@router.post("/mark-all-read")
def mark_all_as_read(
    db: DBDep,
    current_user: CurrentUserDep,
) -> dict:
    """Mark all notifications as read."""
    count = notification_service.mark_all_as_read(
        db, user_id=current_user.id
    )
    return {"marked_count": count}


@router.delete("/{notification_id}", status_code=204)
def delete_notification(
    notification_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> None:
    """Delete a notification."""
    notification = notification_service.get_or_404(db, notification_id)
    if notification.user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"Notification with id '{notification_id}' not found")
    notification_service.delete(db, notification_id)


@router.delete("/old")
def delete_old_notifications(
    db: DBDep,
    current_user: CurrentUserDep,
    days_old: int = 90,
) -> dict:
    """Delete notifications older than specified days."""
    count = notification_service.delete_old_notifications(
        db,
        user_id=current_user.id,
        days_old=days_old,
    )
    return {"deleted_count": count}
