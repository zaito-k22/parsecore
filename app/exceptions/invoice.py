class InvoiceNotFound(Exception):

    def __init__(self, invoice_id: int):

        self.invoice_id = invoice_id