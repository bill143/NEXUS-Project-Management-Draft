"""3D Viewer permission definitions."""

from app.core.permissions import Role, permission_registry


def register_viewer3d_permissions() -> None:
    permission_registry.register_module_permissions(
        "viewer3d",
        {
            "viewer3d.read": Role.VIEWER,
            "viewer3d.upload": Role.EDITOR,
        },
    )
