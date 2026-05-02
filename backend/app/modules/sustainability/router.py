"""Sustainability / CO₂ API routes.

Auto-mounted at ``/api/v1/sustainability/``.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.dependencies import SessionDep
from app.modules.sustainability.schemas import (
    CalculateRequest,
    CarbonReportResponse,
    ElementGroupCreate,
    ElementGroupResponse,
    ElementGroupUpdate,
    EmissionFactorCreate,
    EmissionFactorResponse,
)
from app.modules.sustainability.service import (
    CarbonCalculationService,
    ElementGroupService,
    EmissionFactorService,
)

router = APIRouter()


# ── Emission factors ────────────────────────────────────────────────────────


def _factor_service(session: SessionDep) -> EmissionFactorService:
    return EmissionFactorService(session)


@router.post("/factors", response_model=EmissionFactorResponse, status_code=status.HTTP_201_CREATED)
async def create_factor(
    data: EmissionFactorCreate,
    service: EmissionFactorService = Depends(_factor_service),
) -> EmissionFactorResponse:
    factor = await service.create_factor(data)
    return EmissionFactorResponse.model_validate(factor)


@router.get("/factors", response_model=list[EmissionFactorResponse])
async def list_factors(
    service: EmissionFactorService = Depends(_factor_service),
) -> list[EmissionFactorResponse]:
    return [EmissionFactorResponse.model_validate(f) for f in await service.list_factors()]


# ── Element groups ──────────────────────────────────────────────────────────


def _group_service(session: SessionDep) -> ElementGroupService:
    return ElementGroupService(session)


@router.post("/groups", response_model=ElementGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    data: ElementGroupCreate,
    service: ElementGroupService = Depends(_group_service),
) -> ElementGroupResponse:
    return ElementGroupResponse.model_validate(await service.create_group(data))


@router.get("/groups", response_model=list[ElementGroupResponse])
async def list_groups(
    project_id: uuid.UUID = Query(...),
    service: ElementGroupService = Depends(_group_service),
) -> list[ElementGroupResponse]:
    return [ElementGroupResponse.model_validate(g) for g in await service.list_groups(project_id)]


@router.patch("/groups/{group_id}", response_model=ElementGroupResponse)
async def update_group(
    group_id: uuid.UUID,
    data: ElementGroupUpdate,
    service: ElementGroupService = Depends(_group_service),
) -> ElementGroupResponse:
    return ElementGroupResponse.model_validate(await service.update_group(group_id, data))


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: uuid.UUID,
    service: ElementGroupService = Depends(_group_service),
) -> None:
    await service.delete_group(group_id)


# ── Carbon reports ──────────────────────────────────────────────────────────


def _calc_service(session: SessionDep) -> CarbonCalculationService:
    return CarbonCalculationService(session)


@router.post("/reports", response_model=CarbonReportResponse, status_code=status.HTTP_201_CREATED)
async def calculate_report(
    data: CalculateRequest,
    service: CarbonCalculationService = Depends(_calc_service),
) -> CarbonReportResponse:
    report = await service.calculate(
        project_id=data.project_id, title=data.title, methodology=data.methodology
    )
    return CarbonReportResponse.model_validate(report)


@router.get("/reports", response_model=list[CarbonReportResponse])
async def list_reports(
    project_id: uuid.UUID = Query(...),
    service: CarbonCalculationService = Depends(_calc_service),
) -> list[CarbonReportResponse]:
    return [
        CarbonReportResponse.model_validate(r) for r in await service.list_reports(project_id)
    ]
