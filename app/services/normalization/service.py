import re
from decimal import Decimal, InvalidOperation
from typing import Any


def parse_amount(value: Any) -> Decimal | None:
    """
    Convierte un monto leído de una factura en Decimal.

    Soporta formato español/latinoamericano (7.557,48), anglosajón
    (7,557.48) y valores con símbolos de moneda o paréntesis
    contables. Devuelve None si no se puede interpretar.

    Regla para el caso ambiguo de un solo separador seguido de
    exactamente 3 dígitos ("1.234" o "1,234"): se interpreta como
    separador de miles, salvo que la parte entera sea 0 ("0,123").
    """

    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, Decimal):
        return value

    if isinstance(value, (int, float)):
        return Decimal(str(value))

    text = str(value).strip()

    if not text:
        return None

    negative = text.startswith("-") or (
        text.startswith("(") and text.endswith(")")
    )

    text = re.sub(r"[^\d,.]", "", text)

    if not any(char.isdigit() for char in text):
        return None

    has_dot = "." in text
    has_comma = "," in text

    if has_dot and has_comma:
        # El último separador que aparece es el decimal.
        decimal_sep = "." if text.rfind(".") > text.rfind(",") else ","
        thousands_sep = "," if decimal_sep == "." else "."
        text = text.replace(thousands_sep, "").replace(decimal_sep, ".")

    elif has_dot or has_comma:
        sep = "." if has_dot else ","
        parts = text.split(sep)

        if len(parts) > 2:
            # Varios separadores iguales: son de miles.
            text = "".join(parts)

        else:
            integer_part, fraction = parts

            is_thousands = (
                len(fraction) == 3
                and integer_part not in ("", "0")
                and len(integer_part) <= 3
            )

            text = (
                integer_part + fraction
                if is_thousands
                else f"{integer_part or '0'}.{fraction}"
            )

    try:
        amount = Decimal(text)

    except InvalidOperation:
        return None

    return -amount if negative else amount


def _section(document: dict, key: str) -> dict:
    """Devuelve document[key] solo si es un dict; si no, {}."""

    section = document.get(key)

    return section if isinstance(section, dict) else {}


def _text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    return text or None


def to_invoice_fields(document: dict) -> dict:
    """
    Extrae del JSON del LLM los campos que se guardan como columnas.
    Tolera secciones ausentes o con tipos inesperados.
    """

    supplier = _section(document, "supplier")
    invoice = _section(document, "invoice")
    amounts = _section(document, "amounts")

    def amount(key: str) -> float | None:
        parsed = parse_amount(amounts.get(key))

        return float(parsed) if parsed is not None else None

    return {
        "supplier_name": _text(supplier.get("name")),
        "supplier_nit": _text(supplier.get("tax_id")),
        "invoice_number": _text(invoice.get("number")),
        "issue_date": _text(invoice.get("date")),
        "subtotal": amount("subtotal"),
        "tax": amount("tax_total"),
        "total": amount("total"),
    }
