"""My Module permission definitions."""

from app.core.permissions import Role, permission_registry


def register_my_module_permissions() -> None:
    """Register RBAC permissions for the my_module module."""
    permission_registry.register_module_permissions(
        "my_module",
        {
            "my_module.create": Role.EDITOR,
            "my_module.read": Role.VIEWER,
            "my_module.update": Role.EDITOR,
            "my_module.delete": Role.MANAGER,
        },
    )
