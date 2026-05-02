"""DDC Revit-Excel export permission definitions."""

from app.core.permissions import Role, permission_registry


def register_ddc_revit_export_permissions() -> None:
    permission_registry.register_module_permissions(
        "ddc_revit_export",
        {
            "ddc_revit_export.build": Role.EDITOR,
        },
    )
