from datetime import date
from uuid import UUID

from sqlalchemy.orm import Query, Session

from app.models.audit_event import AuditEvent
from app.models.extraction import Extraction
from app.models.invoice import Invoice


class InvoiceRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        tenant_id: UUID,
        invoice_id: int,
    ) -> Invoice | None:
        return (
            self.db.query(Invoice)
            .filter(
                Invoice.tenant_id == tenant_id,
                Invoice.id == invoice_id,
                Invoice.deleted_at.is_(None),
            )
            .first()
        )

    def get_by_sha256(
        self,
        tenant_id: UUID,
        sha256: str,
    ) -> Invoice | None:
        return (
            self.db.query(Invoice)
            .filter(
                Invoice.tenant_id == tenant_id,
                Invoice.sha256 == sha256,
                Invoice.deleted_at.is_(None),
            )
            .first()
        )

    def list(
        self,
        tenant_id: UUID,
        *,
        status: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        supplier: str | None = None,
        tax_id: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[Invoice], int]:
        query = self._filtered_query(
            tenant_id,
            status=status,
            from_date=from_date,
            to_date=to_date,
            supplier=supplier,
            tax_id=tax_id,
        )

        total = query.order_by(None).count()

        invoices = (
            query.order_by(Invoice.created_at.desc(), Invoice.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return invoices, total

    def _filtered_query(
        self,
        tenant_id: UUID,
        *,
        status: str | None,
        from_date: date | None,
        to_date: date | None,
        supplier: str | None,
        tax_id: str | None,
    ) -> Query:
        query = self.db.query(Invoice).filter(
            Invoice.tenant_id == tenant_id,
            Invoice.deleted_at.is_(None),
        )

        if status is not None:
            query = query.filter(Invoice.status == status)

        if from_date is not None:
            query = query.filter(Invoice.issue_date >= from_date)

        if to_date is not None:
            query = query.filter(Invoice.issue_date <= to_date)

        if supplier:
            query = query.filter(Invoice.supplier_name.ilike(f"%{supplier}%"))

        if tax_id:
            query = query.filter(Invoice.tax_id == tax_id)

        return query

    def add(self, invoice: Invoice) -> Invoice:
        """Agrega la factura a la sesion sin commit. El service gestiona la transaccion."""
        self.db.add(invoice)
        self.db.flush()
        self.db.refresh(invoice)
        return invoice

    def add_extraction(self, extraction: Extraction) -> Extraction:
        """Agrega la extraccion a la sesion sin commit."""
        self.db.add(extraction)
        return extraction

    def add_audit_event(self, event: AuditEvent) -> AuditEvent:
        """Agrega el evento de auditoria a la sesion sin commit."""
        self.db.add(event)
        return event

    def commit(self) -> None:
        """Confirma la transaccion actual."""
        self.db.commit()

    def rollback(self) -> None:
        """Revuelve la transaccion actual."""
        self.db.rollback()