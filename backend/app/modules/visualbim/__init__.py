"""VisualBIM — multi-dimensional point-cloud visualization of BIM elements.

Port of DDC's ``VisualBIM`` Dash/Plotly Python app (DDC ref repo #13).
Read-only analytics service over the existing ``bim_hub`` tables — does
NOT create a new BIM ingestion path. Each BIMElement becomes one point;
caller picks which numeric quantities map to x/y/z and which categorical
field colors / sizes the points.

Frontend renders the returned points via Plotly.js scatter3d.
"""


async def on_startup() -> None:
    from app.modules.visualbim.permissions import register_visualbim_permissions

    register_visualbim_permissions()
