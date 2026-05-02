"""DDC Revit-Excel export module manifest."""

from app.core.module_loader import ModuleManifest

manifest = ModuleManifest(
    name="oe_ddc_revit_export",
    version="0.1.0",
    display_name="DDC Revit-Excel Export",
    description="Produces Excel files compatible with the ImportExcelToRevit Revit add-in (Amendment 1).",
    author="NEXUS / O'Neill Contractors",
    category="integration",
    depends=[],
    auto_install=True,
    enabled=True,
)
