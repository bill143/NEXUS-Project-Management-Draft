"""ML Price-Prediction module manifest."""

from app.core.module_loader import ModuleManifest

manifest = ModuleManifest(
    name="oe_ml_price_prediction",
    version="0.1.0",
    display_name="ML Price-Prediction",
    description="sklearn-based bid-price forecasting model trained on historical project data.",
    author="NEXUS / O'Neill Contractors",
    category="core",
    depends=["oe_projects"],
    auto_install=True,
    enabled=True,
)
