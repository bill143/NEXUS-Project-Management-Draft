"""DDC QTO module manifest."""

from app.core.module_loader import ModuleManifest

manifest = ModuleManifest(
    name="oe_ddc_qto",
    version="0.1.0",
    display_name="DDC QTO",
    description="Quantity-takeoff grouping and aggregation ported from DDC's QuantityTakeoff-Python and Quick-QTO notebooks.",
    author="NEXUS / O'Neill Contractors",
    category="core",
    depends=["oe_takeoff"],
    auto_install=True,
    enabled=True,
)
