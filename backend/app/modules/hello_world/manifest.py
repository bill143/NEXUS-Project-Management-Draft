"""Hello World module manifest."""

from app.core.module_loader import ModuleManifest

manifest = ModuleManifest(
    name="oe_hello_world",
    version="0.1.0",
    display_name="Hello World",
    description="My first module",
    author="Me",
    category="community",
    depends=[],
    auto_install=True,
    enabled=True,
)
