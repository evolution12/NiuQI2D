from __future__ import annotations

from ..models import Project
from ..schemas import ProjectCreateRequest, ProjectUpdateRequest
from .base import CRUDBase


class ProjectCRUD(CRUDBase[Project, ProjectCreateRequest, ProjectUpdateRequest]):
    def __init__(self) -> None:
        super().__init__(Project, "项目")
