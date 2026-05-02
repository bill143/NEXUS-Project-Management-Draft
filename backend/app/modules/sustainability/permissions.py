"""Sustainability / CO₂ permission definitions."""

from app.core.permissions import Role, permission_registry


def register_sustainability_permissions() -> None:
    permission_registry.register_module_permissions(
        "sustainability",
        {
            "sustainability.read": Role.VIEWER,
            "sustainability.create": Role.EDITOR,
            "sustainability.update": Role.EDITOR,
            "sustainability.delete": Role.MANAGER,
            "sustainability.calculate": Role.EDITOR,
            "sustainability.factors.manage": Role.MANAGER,
        },
    )
