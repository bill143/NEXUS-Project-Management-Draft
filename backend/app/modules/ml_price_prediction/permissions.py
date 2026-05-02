"""ML Price-Prediction permission definitions."""

from app.core.permissions import Role, permission_registry


def register_ml_price_prediction_permissions() -> None:
    permission_registry.register_module_permissions(
        "ml_price_prediction",
        {
            "ml_price_prediction.read": Role.VIEWER,
            "ml_price_prediction.train": Role.MANAGER,
            "ml_price_prediction.predict": Role.EDITOR,
            "ml_price_prediction.delete": Role.MANAGER,
        },
    )
