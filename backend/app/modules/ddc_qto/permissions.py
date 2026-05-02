"""DDC QTO permission definitions."""

from app.core.permissions import Role, permission_registry


def register_ddc_qto_permissions() -> None:
    permission_registry.register_module_permissions(
        "ddc_qto",
        {
            "ddc_qto.summarize": Role.VIEWER,
            "ddc_qto.batch": Role.EDITOR,
        },
    )
