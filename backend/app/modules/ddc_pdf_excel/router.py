"""DDC PDF→Excel API.

Auto-mounted at ``/api/v1/ddc_pdf_excel/``.
"""

from urllib.parse import quote

from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from app.modules.ddc_pdf_excel.service import pdf_bytes_to_excel

router = APIRouter()


_MAX_PDF_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/extract")
async def extract_tables(file: UploadFile) -> StreamingResponse:
    """Extract tables from an uploaded PDF and stream back an .xlsx.

    Returns 415 if the upload isn't a PDF, 413 if it exceeds 50 MB,
    422 if pdfplumber found no tables.
    """
    if file.content_type and file.content_type not in {
        "application/pdf",
        "application/x-pdf",
    }:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Expected a PDF, got {file.content_type}",
        )

    pdf_bytes = await file.read()
    if len(pdf_bytes) > _MAX_PDF_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"PDF exceeds {_MAX_PDF_SIZE // 1024 // 1024} MB limit",
        )
    if not pdf_bytes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")

    buf, table_count = pdf_bytes_to_excel(pdf_bytes)
    if table_count == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No tables detected in PDF",
        )

    base_name = (file.filename or "tables").rsplit(".", 1)[0] or "tables"
    out_name = f"{base_name}_tables.xlsx"
    headers = {"Content-Disposition": f'attachment; filename="{quote(out_name)}"'}
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
