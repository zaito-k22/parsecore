from typing import Final

ALLOWED_INVOICE_STATUSES: Final = (
    "queued",
    "processing",
    "done",
    "needs_review",
    "failed",
)

LEGACY_STATUS_ALIASES: Final = {
    "processed": "done",
}

_INVOICE_STATUS_SET = frozenset(ALLOWED_INVOICE_STATUSES)


def normalize_status(value: str) -> str:
    normalized = value.strip().lower()
    normalized = LEGACY_STATUS_ALIASES.get(normalized, normalized)

    if normalized not in _INVOICE_STATUS_SET:
        allowed = ", ".join(ALLOWED_INVOICE_STATUSES)
        raise ValueError(f"Estado no válido: {value!r}. Valores permitidos: {allowed}.")

    return normalized
