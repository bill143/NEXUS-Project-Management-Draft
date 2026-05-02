"""VisualBIM permission definitions."""

from app.core.permissions import Role, permission_registry


def register_visualbim_permissions() -> None:
    permission_registry.register_module_permissions(
        "visualbim",
        {
            "visualbim.read": Role.VIEWER,
        },
    )
