"""Sustainability / CO₂ module manifest."""

from app.core.module_loader import ModuleManifest

manifest = ModuleManifest(
    name="oe_sustainability",
    version="0.1.0",
    display_name="Sustainability / CO₂",
    description="Embodied-carbon calculation aligned with GSA P100 + Buy Clean Act categories.",
    author="NEXUS / O'Neill Contractors",
    category="core",
    depends=["oe_projects", "oe_boq"],
    auto_install=True,
    enabled=True,
)
