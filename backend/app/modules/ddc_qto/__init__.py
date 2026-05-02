"""DDC QTO (Quantity Takeoff) — group/aggregate service.

Ports the grouping + aggregation logic from two DDC reference repos:

* ``QuantityTakeoff-Python`` (Dash + Plotly web app) — group elements from a
  Revit/IFC export by any property, sum quantities, return summary.
* ``Quick-QTO`` (50-line notebook) — batch the above across many files.

Stateless: no DB tables, no migration. Just a transformation service +
REST endpoint that accepts an element list and grouping spec and returns
per-group aggregates. The DB-backed BOQ / takeoff modules consume the
output of this service to populate priced takeoff lines.
"""


async def on_startup() -> None:
    """Module startup hook — register permissions."""
    from app.modules.ddc_qto.permissions import register_ddc_qto_permissions

    register_ddc_qto_permissions()
