"""VisualBIM read-only analytics service.

Queries existing ``oe_bim_model`` + ``oe_bim_element`` tables (from the
``bim_hub`` module) and reshapes each BIMElement into a 3D-scatter point.

The five "dim" parameters tell the service which fields to project onto:

* ``dim_x``, ``dim_y``, ``dim_z``  — numeric. Resolved against
  ``BIMElement.quantities`` first (e.g. ``"volume"`` → ``quantities["volume"]``),
  then against ``properties`` as a fallback.
* ``dim_color``                    — categorical. Resolved against the
  element's top-level fields first (``element_type``, ``storey``,
  ``discipline``, ``name``), then against ``properties``.
* ``dim_size``                     — numeric, same lookup as x/y/z. Use
  the literal string ``"count"`` for a fixed size of 1 (uniform points).

The service stays pure-Python, no pandas dependency.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bim_hub.models import BIMElement, BIMModel
from app.modules.visualbim.schemas import CloudPoint, CloudResponse, CompareResponse


_DEFAULTS = {
    "dim_x": "volume",
    "dim_y": "area",
    "dim_z": "length",
    "dim_color": "element_type",
    "dim_size": "count",
}


def _coerce_float(value: Any) -> float:
    if value is None or isinstance(value, bool):
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(str(value).strip().replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _resolve_numeric(elem: BIMElement, key: str) -> float:
    """Look up ``key`` in quantities, then properties; coerce to float."""
    if key == "count":
        return 1.0
    qty = elem.quantities or {}
    if key in qty:
        return _coerce_float(qty[key])
    props = elem.properties or {}
    if key in props:
        return _coerce_float(props[key])
    return 0.0


def _resolve_categorical(elem: BIMElement, key: str) -> str:
    """Look up ``key`` on the element top-level fields, then properties."""
    direct = {
        "element_type": elem.element_type,
        "storey": elem.storey,
        "discipline": elem.discipline,
        "name": elem.name,
    }
    if key in direct:
        v = direct[key]
        return str(v) if v is not None else "(unknown)"
    props = elem.properties or {}
    if key in props:
        v = props[key]
        return str(v) if v is not None else "(unknown)"
    return "(unknown)"


def _label(elem: BIMElement) -> str:
    if elem.name:
        return str(elem.name)
    if elem.stable_id:
        return str(elem.stable_id)
    return str(elem.id)


class VisualBimService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _project_elements(self, project_id: uuid.UUID) -> list[BIMElement]:
        # Two-step query: model ids first, then elements (avoids forcing a join when
        # the caller may have many models)
        model_ids = await self.session.execute(
            select(BIMModel.id).where(BIMModel.project_id == project_id),
        )
        ids = [row[0] for row in model_ids.all()]
        if not ids:
            return []
        result = await self.session.execute(
            select(BIMElement).where(BIMElement.model_id.in_(ids)),
        )
        return list(result.scalars().all())

    async def cloud(
        self,
        project_id: uuid.UUID,
        dim_x: str | None = None,
        dim_y: str | None = None,
        dim_z: str | None = None,
        dim_color: str | None = None,
        dim_size: str | None = None,
    ) -> CloudResponse:
        dx = dim_x or _DEFAULTS["dim_x"]
        dy = dim_y or _DEFAULTS["dim_y"]
        dz = dim_z or _DEFAULTS["dim_z"]
        dc = dim_color or _DEFAULTS["dim_color"]
        ds = dim_size or _DEFAULTS["dim_size"]

        elements = await self._project_elements(project_id)
        points: list[CloudPoint] = []
        seen_colors: set[str] = set()
        seen_sizes: set[str] = set()

        for elem in elements:
            color_val = _resolve_categorical(elem, dc)
            size_val = _resolve_numeric(elem, ds)
            seen_colors.add(color_val)
            if ds != "count":
                seen_sizes.add(str(round(size_val, 2)))
            points.append(
                CloudPoint(
                    id=elem.id,
                    label=_label(elem),
                    x=_resolve_numeric(elem, dx),
                    y=_resolve_numeric(elem, dy),
                    z=_resolve_numeric(elem, dz),
                    color=color_val,
                    size=max(size_val, 1.0),
                ),
            )

        return CloudResponse(
            project_id=project_id,
            point_count=len(points),
            dim_x=dx,
            dim_y=dy,
            dim_z=dz,
            dim_color=dc,
            dim_size=ds,
            points=points,
            available_dims={
                "color_categories": sorted(seen_colors),
            },
        )

    async def compare(
        self,
        project_a: uuid.UUID,
        project_b: uuid.UUID,
        dim_x: str = "volume",
        dim_y: str = "area",
        dim_z: str = "length",
    ) -> CompareResponse:
        a = await self.cloud(project_a, dim_x=dim_x, dim_y=dim_y, dim_z=dim_z)
        b = await self.cloud(project_b, dim_x=dim_x, dim_y=dim_y, dim_z=dim_z)
        return CompareResponse(
            project_a=a,
            project_b=b,
            summary={
                "delta_count": b.point_count - a.point_count,
                "shared_categories": sorted(
                    set(a.available_dims.get("color_categories", []))
                    & set(b.available_dims.get("color_categories", [])),
                ),
            },
        )
