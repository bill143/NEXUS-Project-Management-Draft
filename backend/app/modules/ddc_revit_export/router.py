"""DDC Revit-Excel export API.

Auto-mounted at ``/api/v1/ddc_revit_export/``.
"""

from urllib.parse import quote

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.modules.ddc_revit_export.schemas import RevitExportRequest
from app.modules.ddc_revit_export.service import build_excel, sanitize_sheet_name

router = APIRouter()


@router.post("/build")
async def build_revit_excel(req: RevitExportRequest) -> StreamingResponse:
    """Build an ImportExcelToRevit-compatible .xlsx and stream it back.

    Response is the Excel binary with a Content-Disposition header so
    browsers and CLI tools save it to disk. The filename matches the
    ImportExcelToRevit convention: ``<sanitized_model_name>_rvt.xlsx``.
    """
    buf = build_excel(
        model_name=req.model_name,
        rows=req.rows,
        id_field=req.id_field,
        extra_columns=req.extra_columns,
        add_string_type_annotation=req.add_string_type_annotation,
    )
    filename = f"{sanitize_sheet_name(req.model_name)}_rvt.xlsx"
    headers = {
        # quote() handles non-ASCII model names safely
        "Content-Disposition": f'attachment; filename="{quote(filename)}"',
    }
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
