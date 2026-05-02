"""VisualBIM module manifest."""

from app.core.module_loader import ModuleManifest

manifest = ModuleManifest(
    name="oe_visualbim",
    version="0.1.0",
    display_name="VisualBIM",
    description="Multi-dimensional point-cloud visualization of BIM project parameters.",
    author="NEXUS / O'Neill Contractors",
    category="core",
    depends=["oe_bim_hub"],
    auto_install=True,
    enabled=True,
)
