"""SAT contact service."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.sat.models.contact import SatContact
from app.modules.sat.schemas.contact import SatContactCreate, SatContactUpdate
from app.shared.services.base import BaseService


class SatContactService(BaseService[SatContact, SatContactCreate, SatContactUpdate]):
    """SAT contact service with customer-level queries."""

    def __init__(self):
        super().__init__(SatContact)

    def get_by_customer(
        self,
        db: Session,
        customer_id: str,
        *,
        organization_id: str,
    ) -> list[SatContact]:
        """Get all contacts for a customer, excluding deleted."""
        result = db.execute(
            select(SatContact).where(
                SatContact.customer_id == customer_id,
                SatContact.deleted_at.is_(None),
                SatContact.organization_id == organization_id
            )
        )
        return list(result.scalars().all())


sat_contact_service = SatContactService()
