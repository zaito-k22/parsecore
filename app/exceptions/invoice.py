class InvoiceNotFound(Exception):

    def __init__(self, invoice_id: int):

        self.invoice_id = invoice_id


class UnsupportedFileFormat(Exception):

    def __init__(self, extension: str):

        self.extension = extension


class LLMExtractionError(Exception):
    """El modelo respondió algo que no se puede usar como JSON de factura."""
