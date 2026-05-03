"""SAT attachment endpoints."""

from fastapi import APIRouter

from app.shared.api.deps import DBDep, SatManagerDep
from app.modules.sat.schemas import SatAttachmentCreate, SatAttachmentResponse
from app.modules.sat.services import sat_attachment_service

router = APIRouter()


@router.post("", response_model=SatAttachmentResponse, status_code=201)
def create_attachment(
    attachment_in: SatAttachmentCreate,
    db: DBDep,
    current_user: SatManagerDep,
) -> SatAttachmentResponse:
    """Create a new SAT attachment."""
    attachment_data = attachment_in.model_copy(
        update={"organization_id": current_user.organization_id}
    )
    attachment = sat_attachment_service.create(db, obj_in=attachment_data)
    return SatAttachmentResponse.model_validate(attachment)


@router.delete("/{attachment_id}", status_code=204)
def delete_attachment(
    attachment_id: str,
    db: DBDep,
    current_user: SatManagerDep,
) -> None:
    """Delete a SAT attachment."""
    sat_attachment_service.delete(db, attachment_id, organization_id=current_user.organization_id)
