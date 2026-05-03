"""Document service."""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document
from app.models.enums import DocumentStatus, DocumentType
from app.schemas import DocumentCreate, DocumentUpdate
from app.shared.services.base import BaseService


class DocumentService(BaseService[Document, DocumentCreate, DocumentUpdate]):
    """Document service."""

    def __init__(self):
        super().__init__(Document)

    def get_documents_by_vehicle(
        self,
        db: Session,
        vehicle_id: str,
        *,
        organization_id: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Document]:
        """Get documents for a vehicle."""
        result = db.execute(
            select(Document)
            .where(
                Document.vehicle_id == vehicle_id,
                Document.deleted_at.is_(None),
                Document.organization_id == organization_id
            )
            .order_by(Document.expiry_date.asc().nullslast())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    def get_documents_by_employee(
        self,
        db: Session,
        employee_id: str,
        *,
        organization_id: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Document]:
        """Get documents for an employee."""
        result = db.execute(
            select(Document)
            .where(
                Document.employee_id == employee_id,
                Document.deleted_at.is_(None),
                Document.organization_id == organization_id
            )
            .order_by(Document.expiry_date.asc().nullslast())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    def get_documents_by_type(
        self,
        db: Session,
        organization_id: str,
        document_type: DocumentType,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Document]:
        """Get documents by type."""
        result = db.execute(
            select(Document)
            .where(
                Document.organization_id == organization_id,
                Document.document_type == document_type,
                Document.deleted_at.is_(None),
            )
            .order_by(Document.expiry_date.asc().nullslast())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    def get_expiring_documents(
        self,
        db: Session,
        organization_id: str,
        days: int = 30,
    ) -> list[Document]:
        """Get documents expiring within specified days."""
        today = date.today()
        expiry_threshold = today + timedelta(days=days)
        result = db.execute(
            select(Document)
            .where(
                Document.organization_id == organization_id,
                Document.expiry_date.is_not(None),
                Document.expiry_date <= expiry_threshold,
                Document.status != DocumentStatus.EXPIRED,
                Document.deleted_at.is_(None),
            )
            .order_by(Document.expiry_date.asc())
        )
        return list(result.scalars().all())

    def get_expired_documents(
        self,
        db: Session,
        organization_id: str,
    ) -> list[Document]:
        """Get expired documents."""
        today = date.today()
        result = db.execute(
            select(Document)
            .where(
                Document.organization_id == organization_id,
                Document.expiry_date.is_not(None),
                Document.expiry_date < today,
                Document.deleted_at.is_(None),
            )
            .order_by(Document.expiry_date.asc())
        )
        return list(result.scalars().all())

    def update_expired_statuses(
        self,
        db: Session,
        organization_id: str,
    ) -> int:
        """Update status of expired documents. Returns count of updated documents."""
        today = date.today()
        result = db.execute(
            select(Document).where(
                Document.organization_id == organization_id,
                Document.expiry_date.is_not(None),
                Document.expiry_date < today,
                Document.status != DocumentStatus.EXPIRED,
                Document.deleted_at.is_(None),
            )
        )
        documents = result.scalars().all()

        for doc in documents:
            doc.status = DocumentStatus.EXPIRED
            db.add(doc)

        db.flush()
        return len(documents)

    def verify_document(
        self,
        db: Session,
        document: Document,
        verified_by: str,
    ) -> Document:
        """Mark a document as verified."""
        document.status = DocumentStatus.VALID
        document.verified_by = verified_by
        document.verified_at = date.today()
        db.add(document)
        db.flush()
        db.refresh(document)
        return document

    def reject_document(
        self,
        db: Session,
        document: Document,
        rejection_reason: str,
    ) -> Document:
        """Reject a document."""
        document.status = DocumentStatus.REJECTED
        document.notes = f"{document.notes or ''}\nRejection reason: {rejection_reason}".strip()
        db.add(document)
        db.flush()
        db.refresh(document)
        return document

    def get_document_summary(
        self,
        db: Session,
        organization_id: str,
    ) -> dict:
        """Get document summary for organization."""
        today = date.today()
        expiry_30_days = today + timedelta(days=30)

        # Get all documents
        result = db.execute(
            select(Document).where(
                Document.organization_id == organization_id,
                Document.deleted_at.is_(None),
            )
        )
        documents = list(result.scalars().all())

        total = len(documents)
        valid = sum(1 for d in documents if d.status == DocumentStatus.VALID)
        pending = sum(1 for d in documents if d.status == DocumentStatus.PENDING)
        expired = sum(
            1 for d in documents
            if d.expiry_date and d.expiry_date < today
        )
        expiring_soon = sum(
            1 for d in documents
            if d.expiry_date and today <= d.expiry_date <= expiry_30_days
        )

        return {
            "total_documents": total,
            "valid_documents": valid,
            "pending_documents": pending,
            "expired_documents": expired,
            "expiring_soon": expiring_soon,
        }


document_service = DocumentService()
