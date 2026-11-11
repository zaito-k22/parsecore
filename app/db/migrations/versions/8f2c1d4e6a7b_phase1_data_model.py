"""phase 1 data model

Revision ID: 8f2c1d4e6a7b
Revises: b5ae3ed92e39
Create Date: 2026-10-25 00:00:00.000000

"""
from datetime import date, datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "8f2c1d4e6a7b"
down_revision: Union[str, Sequence[str], None] = "b5ae3ed92e39"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"


def _parse_historical_date(value: str | None) -> date | None:
    if not value:
        return None

    for date_format in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue

    return None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute(
        sa.text(
            "INSERT INTO tenants (id, name) VALUES "
            "(CAST(:tenant_id AS uuid), 'default')"
        ).bindparams(tenant_id=DEFAULT_TENANT_ID)
    )

    op.alter_column(
        "invoices",
        "supplier_nit",
        new_column_name="tax_id",
        existing_type=sa.String(length=50),
        existing_nullable=True,
    )
    op.add_column("invoices", sa.Column("tax_id_country", sa.String(length=2), nullable=True))
    op.add_column("invoices", sa.Column("currency", sa.String(length=3), nullable=True))
    op.add_column("invoices", sa.Column("public_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("invoices", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("invoices", sa.Column("sha256", sa.String(length=64), nullable=True))
    op.add_column("invoices", sa.Column("storage_uri", sa.String(length=1024), nullable=True))
    op.add_column("invoices", sa.Column("issue_date_raw", sa.Text(), nullable=True))
    op.add_column("invoices", sa.Column("issue_date_date", sa.Date(), nullable=True))
    op.add_column("invoices", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("invoices", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    op.execute("UPDATE invoices SET issue_date_raw = issue_date")

    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, issue_date_raw FROM invoices")
    ).mappings().all()

    for row in rows:
        parsed_date = _parse_historical_date(row["issue_date_raw"])
        bind.execute(
            sa.text(
                "UPDATE invoices SET issue_date_date = :issue_date WHERE id = :invoice_id"
            ),
            {"issue_date": parsed_date, "invoice_id": row["id"]},
        )

    op.drop_column("invoices", "issue_date")
    op.alter_column(
        "invoices",
        "issue_date_date",
        new_column_name="issue_date",
        existing_type=sa.Date(),
        existing_nullable=True,
    )

    op.alter_column(
        "invoices",
        "subtotal",
        type_=sa.Numeric(precision=18, scale=2),
        existing_type=sa.Float(),
        existing_nullable=True,
        postgresql_using="subtotal::numeric(18, 2)",
    )
    op.alter_column(
        "invoices",
        "tax",
        type_=sa.Numeric(precision=18, scale=2),
        existing_type=sa.Float(),
        existing_nullable=True,
        postgresql_using="tax::numeric(18, 2)",
    )
    op.alter_column(
        "invoices",
        "total",
        type_=sa.Numeric(precision=18, scale=2),
        existing_type=sa.Float(),
        existing_nullable=True,
        postgresql_using="total::numeric(18, 2)",
    )
    op.alter_column(
        "invoices",
        "created_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=False,
        server_default=sa.text("now()"),
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )

    op.execute(
        """
        UPDATE invoices
        SET status = CASE
            WHEN status = 'processed' THEN 'done'
            WHEN status IN ('queued', 'processing', 'done', 'needs_review', 'failed')
                THEN status
            ELSE 'needs_review'
        END
        """
    )
    op.alter_column(
        "invoices",
        "status",
        existing_type=sa.String(length=30),
        existing_nullable=False,
        server_default=sa.text("'processing'"),
    )
    op.create_check_constraint(
        "ck_invoices_status",
        "invoices",
        "status IN ('queued', 'processing', 'done', 'needs_review', 'failed')",
    )

    op.execute("UPDATE invoices SET public_id = gen_random_uuid() WHERE public_id IS NULL")
    op.alter_column(
        "invoices",
        "public_id",
        existing_type=postgresql.UUID(as_uuid=True),
        existing_nullable=True,
        nullable=False,
    )
    op.create_unique_constraint(
        "uq_invoices_public_id",
        "invoices",
        ["public_id"],
    )

    op.execute(
        sa.text(
            "UPDATE invoices SET tenant_id = CAST(:tenant_id AS uuid)"
        ).bindparams(tenant_id=DEFAULT_TENANT_ID)
    )
    op.alter_column(
        "invoices",
        "tenant_id",
        existing_type=postgresql.UUID(as_uuid=True),
        existing_nullable=True,
        nullable=False,
    )
    op.create_foreign_key(
        "fk_invoices_tenant_id_tenants",
        "invoices",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.execute("UPDATE invoices SET updated_at = created_at WHERE updated_at IS NULL")
    op.alter_column(
        "invoices",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
        nullable=False,
        server_default=sa.text("now()"),
    )

    op.create_index("ix_invoices_tenant_id", "invoices", ["tenant_id"])
    op.create_index("ix_invoices_status", "invoices", ["status"])
    op.create_index("ix_invoices_issue_date", "invoices", ["issue_date"])
    op.create_index(
        "uq_invoices_tenant_sha256_active",
        "invoices",
        ["tenant_id", "sha256"],
        unique=True,
        postgresql_where=sa.text("sha256 IS NOT NULL AND deleted_at IS NULL"),
    )

    op.create_table(
        "extractions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("ocr_engine", sa.Text(), nullable=True),
        sa.Column("llm_model", sa.Text(), nullable=True),
        sa.Column("prompt_version", sa.Text(), nullable=True),
        sa.Column("ocr_text", sa.Text(), nullable=True),
        sa.Column("ocr_lines", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoices.id"],
            name="fk_extractions_invoice_id_invoices",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "invoice_id",
            "version",
            name="uq_extractions_invoice_version",
        ),
    )
    op.create_index("ix_extractions_invoice_id", "extractions", ["invoice_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=True),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("diff", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoices.id"],
            name="fk_audit_events_invoice_id_invoices",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_audit_events_tenant_id_tenants",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_tenant_id", "audit_events", ["tenant_id"])
    op.create_index("ix_audit_events_invoice_id", "audit_events", ["invoice_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_invoice_id", table_name="audit_events")
    op.drop_index("ix_audit_events_tenant_id", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_index("ix_extractions_invoice_id", table_name="extractions")
    op.drop_table("extractions")

    op.drop_index("uq_invoices_tenant_sha256_active", table_name="invoices")
    op.drop_index("ix_invoices_issue_date", table_name="invoices")
    op.drop_index("ix_invoices_status", table_name="invoices")
    op.drop_index("ix_invoices_tenant_id", table_name="invoices")

    op.drop_constraint("ck_invoices_status", "invoices", type_="check")
    op.execute("UPDATE invoices SET status = 'processed' WHERE status = 'done'")
    op.alter_column(
        "invoices",
        "status",
        existing_type=sa.String(length=30),
        existing_nullable=False,
        server_default=None,
    )

    op.drop_constraint("uq_invoices_public_id", "invoices", type_="unique")
    op.drop_constraint("fk_invoices_tenant_id_tenants", "invoices", type_="foreignkey")

    op.add_column(
        "invoices",
        sa.Column("issue_date_legacy", sa.String(length=30), nullable=True),
    )
    op.execute(
        "UPDATE invoices SET issue_date_legacy = COALESCE(issue_date_raw, issue_date::text)"
    )
    op.drop_column("invoices", "issue_date_raw")
    op.drop_column("invoices", "issue_date")
    op.alter_column(
        "invoices",
        "issue_date_legacy",
        new_column_name="issue_date",
        existing_type=sa.String(length=30),
        existing_nullable=True,
    )

    op.alter_column(
        "invoices",
        "subtotal",
        type_=sa.Float(),
        existing_type=sa.Numeric(precision=18, scale=2),
        existing_nullable=True,
        postgresql_using="subtotal::double precision",
    )
    op.alter_column(
        "invoices",
        "tax",
        type_=sa.Float(),
        existing_type=sa.Numeric(precision=18, scale=2),
        existing_nullable=True,
        postgresql_using="tax::double precision",
    )
    op.alter_column(
        "invoices",
        "total",
        type_=sa.Float(),
        existing_type=sa.Numeric(precision=18, scale=2),
        existing_nullable=True,
        postgresql_using="total::double precision",
    )
    op.alter_column(
        "invoices",
        "created_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        server_default=None,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )

    op.drop_column("invoices", "deleted_at")
    op.drop_column("invoices", "updated_at")
    op.drop_column("invoices", "storage_uri")
    op.drop_column("invoices", "sha256")
    op.drop_column("invoices", "tenant_id")
    op.drop_column("invoices", "public_id")
    op.drop_column("invoices", "currency")
    op.drop_column("invoices", "tax_id_country")

    op.alter_column(
        "invoices",
        "tax_id",
        new_column_name="supplier_nit",
        existing_type=sa.String(length=50),
        existing_nullable=True,
    )

    op.drop_table("tenants")
