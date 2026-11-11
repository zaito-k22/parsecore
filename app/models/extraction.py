from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Extraction(Base):
    __tablename__ = "extractions"
    __table_args__ = (
        UniqueConstraint("invoice_id", "version", name="uq_extractions_invoice_version"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    invoice_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("invoices.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    ocr_engine: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_model: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_lines: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    warnings: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
