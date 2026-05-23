from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.project import ProjectCRUD
from ..crud.style import StyleCRUD
from ..database import get_session
from ..models import Asset, Project
from ..schemas import ProjectCreateRequest, ProjectDetailResponse, ProjectResponse, ProjectUpdateRequest

router = APIRouter(prefix="/projects", tags=["projects"])

project_crud = ProjectCRUD()
style_crud = StyleCRUD()


@router.get("", response_model=list[ProjectDetailResponse])
async def list_projects(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> list[ProjectDetailResponse]:
    stmt = select(Project).order_by(Project.updated_at.desc(), Project.created_at.desc())
    items, _ = await project_crud.list(session, page=page, page_size=page_size, statement=stmt)
    return [await _project_detail(session, project) for project in items]


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> Project:
    await _ensure_style_exists(session, body.style_id)
    return await project_crud.create(session, body)


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
) -> ProjectDetailResponse:
    project = await project_crud.get(session, project_id)
    return await _project_detail(session, project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    body: ProjectUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> Project:
    await _ensure_style_exists(session, body.style_id)
    return await project_crud.update(session, project_id, body)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def patch_project(
    project_id: str,
    body: ProjectUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> Project:
    await _ensure_style_exists(session, body.style_id)
    return await project_crud.update(session, project_id, body)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> None:
    await project_crud.get(session, project_id)
    await request.app.state.storage.clear_cache(project_id)
    await project_crud.delete(session, project_id)


async def _ensure_style_exists(session: AsyncSession, style_id: str | None) -> None:
    if style_id is not None:
        await style_crud.get(session, style_id)


async def _project_detail(session: AsyncSession, project: Project) -> ProjectDetailResponse:
    asset_count = await session.scalar(
        select(func.count()).select_from(Asset).where(Asset.project_id == project.id)
    )
    latest_asset_at = await session.scalar(
        select(func.max(Asset.created_at)).where(Asset.project_id == project.id)
    )
    style = await style_crud.get(session, project.style_id) if project.style_id else None
    return ProjectDetailResponse(
        id=project.id,
        name=project.name,
        style_id=project.style_id,
        style=style,
        asset_count=int(asset_count or 0),
        latest_asset_at=latest_asset_at,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )
