"""My Module manifest."""

from app.core.module_loader import ModuleManifest

manifest = ModuleManifest(
    name="oe_my_module",
    version="0.1.0",
    display_name="My Module",
    description="One-line description",
    author="Your Name",
    category="community",
    depends=["oe_projects"],
    auto_install=False,
    enabled=True,
)
