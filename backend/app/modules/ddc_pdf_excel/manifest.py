"""DDC PDF→Excel ingestion module manifest."""

from app.core.module_loader import ModuleManifest

manifest = ModuleManifest(
    name="oe_ddc_pdf_excel",
    version="0.1.0",
    display_name="DDC PDF→Excel",
    description="Extract tabular data from construction PDFs into multi-sheet Excel.",
    author="NEXUS / O'Neill Contractors",
    category="integration",
    depends=[],
    auto_install=True,
    enabled=True,
)
