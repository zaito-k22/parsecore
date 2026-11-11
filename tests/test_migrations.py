from datetime import date, datetime
from decimal import Decimal

import pytest
from alembic import command
from sqlalchemy import text

from app.core.tenants import DEFAULT_TENANT_ID

OLD_REVISION = "b5ae3ed92e39"


def _totals(conn) -> tuple[int, Decimal, Decimal, Decimal]:
    row = conn.execute(
        text(
            "SELECT count(*) AS count, "
            "COALESCE(sum(subtotal), 0) AS subtotal, "
            "COALESCE(sum(tax), 0) AS tax, "
            "COALESCE(sum(total), 0) AS total "
            "FROM invoices"
        )
    ).mappings().one()

    cents = Decimal("0.01")

    return (
        row["count"],
        Decimal(str(row["subtotal"])).quantize(cents),
        Decimal(str(row["tax"])).quantize(cents),
        Decimal(str(row["total"])).quantize(cents),
    )


@pytest.mark.db
def test_phase_one_migration_preserves_history_and_downgrades(
    alembic_config,
    test_db_engine,
):
    with test_db_engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))

    try:
        command.upgrade(alembic_config, OLD_REVISION)

        with test_db_engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO invoices ("
                    "invoice_number, supplier_name, supplier_nit, issue_date, "
                    "subtotal, tax, total, original_filename, drive_file_id, "
                    "drive_folder, raw_json, status, created_at"
                    ") VALUES ("
                    ":number, :supplier, :nit, :issue_date, "
                    ":subtotal, :tax, :total, :filename, NULL, NULL, "
                    ":raw_json, :status, :created_at"
                    ")"
                ),
                [
                    {
                        "number": "F-1",
                        "supplier": "Proveedor Uno",
                        "nit": "A-1",
                        "issue_date": "15/03/2024",
                        "subtotal": 100.10,
                        "tax": 19.02,
                        "total": 119.12,
                        "filename": "f-1.pdf",
                        "raw_json": '{"supplier": {"name": "Proveedor Uno"}}',
                        "status": "processed",
                        "created_at": datetime(2024, 3, 15, 10, 0),
                    },
                    {
                        "number": "F-2",
                        "supplier": "Proveedor Dos",
                        "nit": "B-2",
                        "issue_date": "sin-fecha",
                        "subtotal": 50.00,
                        "tax": 9.50,
                        "total": 59.50,
                        "filename": "f-2.pdf",
                        "raw_json": '{"supplier": {"name": "Proveedor Dos"}}',
                        "status": "legacy_unknown",
                        "created_at": datetime(2024, 4, 1, 12, 30),
                    },
                ],
            )
            before = _totals(conn)

        command.upgrade(alembic_config, "head")

        with test_db_engine.begin() as conn:
            after = _totals(conn)
            rows = conn.execute(
                text(
                    "SELECT tax_id, tenant_id, public_id, status, issue_date, "
                    "issue_date_raw, subtotal, tax, total "
                    "FROM invoices ORDER BY id"
                )
            ).mappings().all()
            tenant = conn.execute(
                text("SELECT id FROM tenants WHERE name = 'default'")
            ).scalar_one()
            tables = set(
                conn.execute(
                    text(
                        "SELECT tablename FROM pg_tables "
                        "WHERE schemaname = 'public'"
                    )
                ).scalars()
            )
            indexes = set(
                conn.execute(
                    text(
                        "SELECT indexname FROM pg_indexes "
                        "WHERE schemaname = 'public' AND tablename = 'invoices'"
                    )
                ).scalars()
            )

        assert after == before
        assert after[0] == 2
        assert after[1] == Decimal("150.10")
        assert after[2] == Decimal("28.52")
        assert after[3] == Decimal("178.62")

        assert tenant == DEFAULT_TENANT_ID
        assert {row["tenant_id"] for row in rows} == {DEFAULT_TENANT_ID}
        assert {row["tax_id"] for row in rows} == {"A-1", "B-2"}
        assert {row["status"] for row in rows} == {"done", "needs_review"}
        assert len({row["public_id"] for row in rows}) == 2
        assert rows[0]["issue_date"] == date(2024, 3, 15)
        assert rows[0]["issue_date_raw"] == "15/03/2024"
        assert rows[1]["issue_date"] is None
        assert rows[1]["issue_date_raw"] == "sin-fecha"
        assert rows[0]["subtotal"] == Decimal("100.10")
        assert rows[0]["tax"] == Decimal("19.02")
        assert rows[0]["total"] == Decimal("119.12")

        assert {"extractions", "audit_events", "tenants"} <= tables
        assert "uq_invoices_tenant_sha256_active" in indexes

        command.downgrade(alembic_config, OLD_REVISION)

        with test_db_engine.begin() as conn:
            downgraded = _totals(conn)
            rows = conn.execute(
                text(
                    "SELECT supplier_nit, issue_date, status "
                    "FROM invoices ORDER BY id"
                )
            ).mappings().all()
            columns = set(
                conn.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema = 'public' AND table_name = 'invoices'"
                    )
                ).scalars()
            )
            tables = set(
                conn.execute(
                    text(
                        "SELECT tablename FROM pg_tables "
                        "WHERE schemaname = 'public'"
                    )
                ).scalars()
            )

        assert downgraded == before
        assert "supplier_nit" in columns
        assert "tax_id" not in columns
        assert "public_id" not in columns
        assert "tenant_id" not in columns
        assert "deleted_at" not in columns
        assert rows[0]["supplier_nit"] == "A-1"
        assert rows[0]["issue_date"] == "15/03/2024"
        assert rows[0]["status"] == "processed"
        assert rows[1]["issue_date"] == "sin-fecha"
        assert rows[1]["status"] == "needs_review"
        assert not {"extractions", "audit_events", "tenants"} & tables
    finally:
        command.upgrade(alembic_config, "head")
