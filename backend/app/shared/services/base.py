"""Base service class with common CRUD operations."""

from typing import Any, Generic, TypeVar
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base service with common CRUD operations."""

    def __init__(self, model: type[ModelType]):
        """Initialize service with model class."""
        self.model = model

    def get(
        self,
        db: Session,
        id: str,
        *,
        organization_id: str | None = None,
        include_deleted: bool = False,
    ) -> ModelType | None:
        """Get a single record by ID."""
        query = select(self.model).where(self.model.id == id)

        # Filter by organization if model has organization_id
        if organization_id and hasattr(self.model, "organization_id"):
            query = query.where(self.model.organization_id == organization_id)

        # Filter out soft-deleted records
        if not include_deleted and hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))

        result = db.execute(query)
        return result.scalar_one_or_none()

    def get_or_404(
        self,
        db: Session,
        id: str,
        *,
        organization_id: str | None = None,
        include_deleted: bool = False,
    ) -> ModelType:
        """Get a single record by ID or raise NotFoundError."""
        obj = self.get(db, id, organization_id=organization_id, include_deleted=include_deleted)
        if obj is None:
            raise NotFoundError(self.model.__name__, id)
        return obj

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        organization_id: str | None = None,
        include_deleted: bool = False,
    ) -> list[ModelType]:
        """Get multiple records with pagination."""
        query = select(self.model)

        # Filter by organization if model has organization_id
        if organization_id and hasattr(self.model, "organization_id"):
            query = query.where(self.model.organization_id == organization_id)

        # Filter out soft-deleted records
        if not include_deleted and hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))

        query = query.offset(skip).limit(limit)
        result = db.execute(query)
        return list(result.scalars().all())

    def count(
        self,
        db: Session,
        *,
        organization_id: str | None = None,
        include_deleted: bool = False,
    ) -> int:
        """Count total records."""
        query = select(func.count()).select_from(self.model)

        if organization_id and hasattr(self.model, "organization_id"):
            query = query.where(self.model.organization_id == organization_id)

        if not include_deleted and hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))

        result = db.execute(query)
        return result.scalar_one()

    def create(
        self,
        db: Session,
        *,
        obj_in: CreateSchemaType,
    ) -> ModelType:
        """Create a new record."""
        obj_data = obj_in.model_dump() if hasattr(obj_in, "model_dump") else dict(obj_in)

        # Generate ID if not provided
        if "id" not in obj_data:
            obj_data["id"] = str(uuid4())

        db_obj = self.model(**obj_data)
        db.add(db_obj)
        db.flush()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
    ) -> ModelType:
        """Update an existing record."""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        db.add(db_obj)
        db.flush()
        db.refresh(db_obj)
        return db_obj

    def delete(
        self,
        db: Session,
        id: str,
        soft_delete: bool = True,
        *,
        organization_id: str | None = None,
    ) -> ModelType | None:
        """Delete a record (soft or hard delete)."""
        obj = self.get(db, id, organization_id=organization_id)
        if obj is None:
            return None

        if soft_delete and hasattr(obj, "deleted_at"):
            from datetime import datetime, timezone
            obj.deleted_at = datetime.now(timezone.utc)
            db.add(obj)
        else:
            db.delete(obj)

        db.flush()
        return obj
