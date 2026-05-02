"""DDC profiling module manifest."""

from app.core.module_loader import ModuleManifest

manifest = ModuleManifest(
    name="oe_ddc_profiling",
    version="0.1.0",
    display_name="DDC Data Profiling",
    description="Pandas-backed EDA helpers ported from DDC's Revit Data Analysis Streamlit App.",
    author="NEXUS / O'Neill Contractors",
    category="core",
    depends=[],
    auto_install=True,
    enabled=True,
)
