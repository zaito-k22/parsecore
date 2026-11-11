from datetime import date
from decimal import Decimal

import pytest

from app.services.normalization.service import parse_amount, to_invoice_fields


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("7.557,48", "7557.48"),
        ("7,557.48", "7557.48"),
        ("1,234.56", "1234.56"),  # bug original: daba 1.23456
        ("1.234.567,89", "1234567.89"),
        ("1,234,567.89", "1234567.89"),
        ("1.234", "1234"),  # miles, no decimal
        ("1,250,000", "1250000"),
        ("$ 1.250.000", "1250000"),
        ("243.8", "243.8"),
        ("243,8", "243.8"),
        ("0,123", "0.123"),
        ("1.2345", "1.2345"),
        ("-5,50", "-5.50"),
        ("(100,00)", "-100.00"),
        ("EUR 243,80", "243.80"),
        (243.8, "243.8"),
        (300000, "300000"),
        (Decimal("1.5"), "1.5"),
    ],
)
def test_parse_amount(raw, expected):
    assert parse_amount(raw) == Decimal(expected)


@pytest.mark.parametrize("raw", [None, "", "   ", "abc", "N/A", True, "..,"])
def test_parse_amount_invalid(raw):
    assert parse_amount(raw) is None


def test_to_invoice_fields_complete():
    document = {
        "supplier": {"name": " VicVal SI ", "tax_id": "B30142516", "country": "es"},
        "invoice": {"number": "2017-0002", "date": "23/06/2017", "currency": "eur"},
        "amounts": {"subtotal": "201,65", "tax_total": "42,35", "total": "243,80"},
    }

    assert to_invoice_fields(document) == {
        "supplier_name": "VicVal SI",
        "tax_id": "B30142516",
        "tax_id_country": "ES",
        "invoice_number": "2017-0002",
        "currency": "EUR",
        "issue_date": date(2017, 6, 23),
        "issue_date_raw": "23/06/2017",
        "subtotal": Decimal("201.65"),
        "tax": Decimal("42.35"),
        "total": Decimal("243.80"),
    }


@pytest.mark.parametrize(
    "document",
    [
        {},
        {"supplier": None, "invoice": None, "amounts": None},
        {"supplier": "texto", "invoice": [], "amounts": 5},
        {"supplier": {"name": None}, "invoice": {"number": ""}, "amounts": {"total": "x"}},
    ],
)
def test_to_invoice_fields_tolerates_bad_structure(document):
    fields = to_invoice_fields(document)

    assert set(fields) == {
        "supplier_name", "tax_id", "tax_id_country", "invoice_number",
        "currency", "issue_date", "issue_date_raw", "subtotal", "tax", "total",
    }
    assert all(value is None for value in fields.values())
