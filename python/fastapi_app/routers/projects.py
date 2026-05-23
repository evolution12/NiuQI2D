from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.project import ProjectCRUD
from ..database import get_session
from ..schemas import ProjectCreateRequest, ProjectResponse, ProjectUpdateRequest

router = APIRouter(prefix="/projects", tags=["projects"])
crud = ProjectCRUD()


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    session: AsyncSession = Depends(get_session),
) -> list[ProjectResponse]:
    items, _ = await crud.list(session, page_size=100)
    return [ProjectResponse.model_validate(p) for p in items]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
) -> ProjectResponse:
    item = await crud.get(session, project_id)
    return ProjectResponse.model_validate(item)


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    body: ProjectCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> ProjectResponse:
    item = await crud.create(session, body)
    return ProjectResponse.model_validate(item)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    body: ProjectUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> ProjectResponse:
    item = await crud.update(session, project_id, body)
    return ProjectResponse.model_validate(item)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    await crud.delete(session, project_id)
