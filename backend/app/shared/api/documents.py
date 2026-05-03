"""Document endpoints."""

from fastapi import APIRouter

from app.shared.api.deps import CurrentUserDep, DBDep, FleetManagerDep
from app.models.enums import DocumentType
from app.schemas import (
    DocumentCreate,
    DocumentResponse,
    DocumentUpdate,
)
from app.services import document_service

router = APIRouter()


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    db: DBDep,
    current_user: CurrentUserDep,
    skip: int = 0,
    limit: int = 100,
    vehicle_id: str | None = None,
    employee_id: str | None = None,
    document_type: DocumentType | None = None,
) -> list[DocumentResponse]:
    """List documents with optional filters."""
    if vehicle_id:
        documents = document_service.get_documents_by_vehicle(
            db, vehicle_id, organization_id=current_user.organization_id, skip=skip, limit=limit
        )
    elif employee_id:
        documents = document_service.get_documents_by_employee(
            db, employee_id, organization_id=current_user.organization_id, skip=skip, limit=limit
        )
    elif document_type:
        documents = document_service.get_documents_by_type(
            db,
            organization_id=current_user.organization_id,
            document_type=document_type,
            skip=skip,
            limit=limit,
        )
    else:
        documents = document_service.get_multi(
            db,
            skip=skip,
            limit=limit,
            organization_id=current_user.organization_id,
        )
    return [DocumentResponse.model_validate(d) for d in documents]


@router.post("", response_model=DocumentResponse, status_code=201)
def create_document(
    document_in: DocumentCreate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> DocumentResponse:
    """Create a document."""
    document_data = document_in.model_copy(update={"organization_id": current_user.organization_id})
    document = document_service.create(db, obj_in=document_data)
    return DocumentResponse.model_validate(document)


@router.get("/expiring", response_model=list[DocumentResponse])
def list_expiring_documents(
    db: DBDep,
    current_user: CurrentUserDep,
    days: int = 30,
) -> list[DocumentResponse]:
    """List documents expiring within specified days."""
    documents = document_service.get_expiring_documents(
        db,
        organization_id=current_user.organization_id,
        days=days,
    )
    return [DocumentResponse.model_validate(d) for d in documents]


@router.get("/expired", response_model=list[DocumentResponse])
def list_expired_documents(
    db: DBDep,
    current_user: CurrentUserDep,
) -> list[DocumentResponse]:
    """List expired documents."""
    documents = document_service.get_expired_documents(
        db, organization_id=current_user.organization_id
    )
    return [DocumentResponse.model_validate(d) for d in documents]


@router.get("/summary")
def get_document_summary(
    db: DBDep,
    current_user: CurrentUserDep,
) -> dict:
    """Get document summary for organization."""
    return document_service.get_document_summary(
        db, organization_id=current_user.organization_id
    )


@router.post("/update-expired-statuses")
def update_expired_statuses(
    db: DBDep,
    current_user: FleetManagerDep,
) -> dict:
    """Update status of all expired documents."""
    count = document_service.update_expired_statuses(
        db, organization_id=current_user.organization_id
    )
    return {"updated_count": count}


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    db: DBDep,
    current_user: CurrentUserDep,
) -> DocumentResponse:
    """Get a document by ID."""
    document = document_service.get_or_404(db, document_id, organization_id=current_user.organization_id)
    return DocumentResponse.model_validate(document)


@router.patch("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: str,
    document_in: DocumentUpdate,
    db: DBDep,
    current_user: FleetManagerDep,
) -> DocumentResponse:
    """Update a document."""
    document = document_service.get_or_404(db, document_id, organization_id=current_user.organization_id)
    updated = document_service.update(db, db_obj=document, obj_in=document_in)
    return DocumentResponse.model_validate(updated)


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: str,
    db: DBDep,
    current_user: FleetManagerDep,
) -> None:
    """Delete a document."""
    document_service.delete(db, document_id, organization_id=current_user.organization_id)


@router.post("/{document_id}/verify", response_model=DocumentResponse)
def verify_document(
    document_id: str,
    db: DBDep,
    current_user: FleetManagerDep,
) -> DocumentResponse:
    """Verify a document."""
    document = document_service.get_or_404(db, document_id, organization_id=current_user.organization_id)
    updated = document_service.verify_document(
        db, document, verified_by=current_user.id
    )
    return DocumentResponse.model_validate(updated)


@router.post("/{document_id}/reject", response_model=DocumentResponse)
def reject_document(
    document_id: str,
    reason: str,
    db: DBDep,
    current_user: FleetManagerDep,
) -> DocumentResponse:
    """Reject a document."""
    document = document_service.get_or_404(db, document_id, organization_id=current_user.organization_id)
    updated = document_service.reject_document(
        db, document, rejection_reason=reason
    )
    return DocumentResponse.model_validate(updated)
