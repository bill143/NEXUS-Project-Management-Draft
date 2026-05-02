"""DDC profiling permission definitions."""

from app.core.permissions import Role, permission_registry


def register_ddc_profiling_permissions() -> None:
    permission_registry.register_module_permissions(
        "ddc_profiling",
        {
            "ddc_profiling.read": Role.VIEWER,
        },
    )
