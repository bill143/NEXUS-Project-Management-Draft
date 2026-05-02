"""VisualBIM API routes.

Auto-mounted at ``/api/v1/visualbim/``.
"""

import uuid

from fastapi import APIRouter, Depends, Query

from app.dependencies import SessionDep
from app.modules.visualbim.schemas import CloudResponse, CompareRequest, CompareResponse
from app.modules.visualbim.service import VisualBimService

router = APIRouter()


def _service(session: SessionDep) -> VisualBimService:
    return VisualBimService(session)


@router.get(
    "/projects/{project_id}/cloud", response_model=CloudResponse,
)
async def project_cloud(
    project_id: uuid.UUID,
    dim_x: str | None = Query(None),
    dim_y: str | None = Query(None),
    dim_z: str | None = Query(None),
    dim_color: str | None = Query(None),
    dim_size: str | None = Query(None),
    service: VisualBimService = Depends(_service),
) -> CloudResponse:
    return await service.cloud(
        project_id,
        dim_x=dim_x,
        dim_y=dim_y,
        dim_z=dim_z,
        dim_color=dim_color,
        dim_size=dim_size,
    )


@router.post("/compare", response_model=CompareResponse)
async def compare_projects(
    req: CompareRequest,
    service: VisualBimService = Depends(_service),
) -> CompareResponse:
    return await service.compare(
        project_a=req.project_a,
        project_b=req.project_b,
        dim_x=req.dim_x,
        dim_y=req.dim_y,
        dim_z=req.dim_z,
    )
