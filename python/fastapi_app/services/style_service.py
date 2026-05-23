from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.style import StyleCRUD
from ..exceptions import InvalidParamError
from ..models import GenerationRecord, Project, StyleProfile
from ..schemas import StyleProfileCreateRequest


class StyleService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.style_crud = StyleCRUD()

    async def ensure_presets(self) -> None:
        preset_path = Path(__file__).resolve().parent.parent / "data" / "preset_styles.json"
        presets = json.loads(preset_path.read_text(encoding="utf-8"))
        for preset in presets:
            result = await self.session.execute(
                select(StyleProfile).where(
                    StyleProfile.name == preset["name"],
                    StyleProfile.is_preset.is_(True),
                )
            )
            if result.scalar_one_or_none() is not None:
                continue
            await self.style_crud.create(
                self.session,
                {
                    **StyleProfileCreateRequest(**preset).model_dump(mode="json"),
                    "is_preset": True,
                },
            )

    async def ensure_deletable(self, style: StyleProfile) -> None:
        if style.is_preset:
            raise InvalidParamError("预设风格不可删除")
        project_count = await self.session.scalar(
            select(Project).where(Project.style_id == style.id).limit(1)
        )
        generation_count = await self.session.scalar(
            select(GenerationRecord).where(GenerationRecord.style_id == style.id).limit(1)
        )
        if project_count is not None or generation_count is not None:
            raise InvalidParamError("风格已被项目或生成记录引用，不能删除")
