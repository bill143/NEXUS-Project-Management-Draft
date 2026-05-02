"""Build .xlsx files for the ImportExcelToRevit Revit add-in.

Stateless. Takes a model name + a list of element dicts (one row per Revit
element, dict keys = parameter names) and returns a BytesIO containing the
.xlsx payload.

Sheet-naming rules (per the add-in):
* Sheet name = model name truncated to 25 characters AND with characters
  forbidden by Excel ([], :, *, ?, /, \\) replaced with underscore.

Column rules:
* Existing parameter: column name = parameter name (or
  ``"<name> : String"`` to be explicit about type).
* New parameter to create on import: column name MUST start with
  ``new_``. Optional ``" : String"`` suffix — currently the only type the
  add-in accepts.
* The first column is always ``ElementId`` (or whatever ``id_field`` the
  caller provides) so the add-in can match rows to Revit elements.

Supported types: any value that openpyxl accepts (str, int, float, bool,
datetime, None). Cells with ``None`` are written as empty cells, which the
add-in treats as "do not change the parameter value".
"""

from __future__ import annotations

import re
from io import BytesIO
from typing import Any

# Forbidden by Excel sheet-name spec
_BAD_SHEET_CHARS = re.compile(r"[\[\]:\*\?/\\]")
_MAX_SHEET_NAME_LEN = 25  # ImportExcelToRevit hard-truncates at 25 chars
_DEFAULT_ID_FIELD = "ElementId"
_NEW_PARAM_PREFIX = "new_"


def sanitize_sheet_name(name: str) -> str:
    """Apply the add-in's sheet-name rules.

    Truncates to 25 chars (the add-in's hard limit) and strips characters
    Excel forbids in sheet names.
    """
    cleaned = _BAD_SHEET_CHARS.sub("_", name).strip()
    if not cleaned:
        cleaned = "Model"
    return cleaned[:_MAX_SHEET_NAME_LEN]


def collect_columns(
    rows: list[dict[str, Any]],
    id_field: str,
    extra_columns: list[str] | None = None,
) -> list[str]:
    """Determine the column order for the sheet.

    1. ``id_field`` is always first (the add-in keys on it).
    2. Then any explicit ``extra_columns`` (lets callers force a known
       order or include parameters that are absent from every row).
    3. Then the rest in insertion order (Python 3.7+ dict ordering means
       the first row's keys win, then the next row's new keys, etc.).
    4. Columns starting with ``new_`` are kept — that prefix is meaningful
       to the add-in.
    """
    seen = {id_field}
    result = [id_field]
    for c in extra_columns or []:
        if c not in seen:
            seen.add(c)
            result.append(c)
    for row in rows:
        for k in row.keys():
            if k not in seen:
                seen.add(k)
                result.append(k)
    return result


def build_excel(
    model_name: str,
    rows: list[dict[str, Any]],
    *,
    id_field: str = _DEFAULT_ID_FIELD,
    extra_columns: list[str] | None = None,
    add_string_type_annotation: bool = False,
) -> BytesIO:
    """Build an .xlsx file in the ImportExcelToRevit-compatible format.

    Args:
        model_name: name of the Revit model — becomes the sheet name
            (sanitized + truncated to 25 chars).
        rows: one dict per element; keys are parameter names, values are
            cell contents. Use ``None`` for "leave parameter unchanged".
        id_field: name of the field that holds the Revit ElementId for
            each row. Default ``"ElementId"``.
        extra_columns: optional explicit list of columns to include even
            if no row has them. Useful for new shared parameters that are
            being added (their column name should start with ``new_``).
        add_string_type_annotation: when True, append ``" : String"`` to
            every column header except the id_field. This matches the
            add-in's strictest mode where it requires explicit type tags.

    Returns:
        A ``BytesIO`` positioned at 0. Caller can stream it to disk or to
        an HTTP response without rewinding.
    """
    try:
        from openpyxl import Workbook
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "openpyxl is required for Excel export — install it with `pip install openpyxl`"
        ) from e

    wb = Workbook()
    ws = wb.active
    ws.title = sanitize_sheet_name(model_name)

    columns = collect_columns(rows, id_field, extra_columns)

    def _format_header(col: str) -> str:
        if not add_string_type_annotation or col == id_field:
            return col
        if " : " in col:  # already annotated
            return col
        return f"{col} : String"

    ws.append([_format_header(c) for c in columns])
    for row in rows:
        ws.append([row.get(c) for c in columns])

    out = BytesIO()
    wb.save(out)
    out.seek(0)
    return out


def is_new_parameter_column(column_name: str) -> bool:
    """Does this column header trigger 'create new shared parameter on import'?"""
    base = column_name.split(" : ", 1)[0].strip()
    return base.startswith(_NEW_PARAM_PREFIX)
