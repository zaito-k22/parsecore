from sqlalchemy.orm import Session

from app.models.invoice import Invoice


class InvoiceRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, invoice: Invoice) -> Invoice:
        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def get_by_id(self, invoice_id: int) -> Invoice | None:
        return (
            self.db.query(Invoice)
            .filter(Invoice.id == invoice_id)
            .first()
        )

    def list(self) -> list[Invoice]:
        return (
            self.db.query(Invoice)
            .order_by(Invoice.created_at.desc())
            .all()
        )

    def update(self, invoice: Invoice) -> Invoice:
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def delete(self, invoice: Invoice) -> None:
        self.db.delete(invoice)
        self.db.commit()