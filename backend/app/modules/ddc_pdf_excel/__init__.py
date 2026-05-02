"""DDC PDF→Excel ingestion.

Ports the trivial DDC ``PDF-to-Excel`` notebook (50-line tabula-py
wrapper) into a proper FastAPI endpoint. The notebook used tabula-py
(Java-backed); this module uses pdfplumber instead — pure Python, no
JVM, already a NEXUS base dependency.

Stateless. No DB. One endpoint that accepts a PDF (multipart upload) and
returns an .xlsx with one sheet per detected table.
"""


async def on_startup() -> None:
    from app.modules.ddc_pdf_excel.permissions import register_ddc_pdf_excel_permissions

    register_ddc_pdf_excel_permissions()
