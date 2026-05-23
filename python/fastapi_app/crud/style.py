from __future__ import annotations

from ..models import StyleProfile
from ..schemas import StyleProfileCreateRequest, StyleProfileUpdateRequest
from .base import CRUDBase


class StyleCRUD(CRUDBase[StyleProfile, StyleProfileCreateRequest, StyleProfileUpdateRequest]):
    def __init__(self) -> None:
        super().__init__(StyleProfile, "风格档案")
