from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Invoice(Base):
    __tablename__ = "invoices"

    # ==========================
    # Identificador
    # ==========================

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    # ==========================
    # Información principal
    # ==========================

    invoice_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    supplier_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    supplier_nit: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    issue_date: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    subtotal: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    tax: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    total: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # ==========================
    # Archivo original
    # ==========================

    original_filename: Mapped[str] = mapped_column(
        String(255),
    )

    drive_file_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    drive_folder: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # ==========================
    # Resultado completo del LLM
    # ==========================

    raw_json: Mapped[str] = mapped_column(
        Text,
    )

    # ==========================
    # Estado
    # ==========================

    status: Mapped[str] = mapped_column(
        String(30),
        default="processed",
    )

    # ==========================
    # Auditoría
    # ==========================

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )