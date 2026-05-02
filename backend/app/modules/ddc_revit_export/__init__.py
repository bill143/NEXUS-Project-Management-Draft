"""DDC Revit-Excel export — produces .xlsx files compatible with the
``ImportExcelToRevit`` Revit add-in.

Per Amendment 1 of the NEXUS consolidation plan: keep ImportExcelToRevit
as a separately distributed Revit MSI; this module is the NEXUS-side end
of the round-trip pipeline that emits Excel in the exact shape that MSI
expects, so the Revit-Excel Bridge has a working end-to-end path.

Format expected by ImportExcelToRevit (from its README):

* One sheet per model, sheet name = model name truncated to 25 chars.
* Header row contains parameter names. Values for an existing parameter
  are written under the matching column name.
* New parameters are created automatically when a column name starts with
  ``new_`` and the cell has a value. The created parameter is a *shared*
  parameter on the element category.
* The data type annotation appears after the parameter name with a
  ``" : <type>"`` separator. Currently only ``" : String"`` is supported
  by the Revit add-in.
"""


async def on_startup() -> None:
    from app.modules.ddc_revit_export.permissions import register_ddc_revit_export_permissions

    register_ddc_revit_export_permissions()
