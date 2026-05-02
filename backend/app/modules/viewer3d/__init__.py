"""3D Viewer module — backend for the Online3DViewer-based frontend page.

Stores uploaded 3D model files (.obj, .stl, .ply, .gltf, .3ds, .off, .3dm,
.fbx, .dae, .wrl, .3mf, .ifc) on disk and exposes them to the React viewer
via signed-URL-equivalent UUIDs.

Storage location: ``data/viewer3d_uploads/`` under the backend root, or
the dir referenced by the ``NEXUS_VIEWER3D_UPLOAD_DIR`` env var.
"""


async def on_startup() -> None:
    from app.modules.viewer3d.permissions import register_viewer3d_permissions

    register_viewer3d_permissions()
