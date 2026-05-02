"""3D Viewer module manifest."""

from app.core.module_loader import ModuleManifest

manifest = ModuleManifest(
    name="oe_viewer3d",
    version="0.1.0",
    display_name="3D Viewer",
    description="Browser-based 3D model viewer (Online3DViewer / three.js).",
    author="NEXUS / O'Neill Contractors",
    category="core",
    depends=["oe_projects"],
    auto_install=True,
    enabled=True,
)
