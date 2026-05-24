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
        preset_names = {p["name"] for p in presets}

        # Create or update current presets
        for preset in presets:
            result = await self.session.execute(
                select(StyleProfile).where(
                    StyleProfile.name == preset["name"],
                    StyleProfile.is_preset.is_(True),
                )
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                # Update existing preset in case it changed
                data = StyleProfileCreateRequest(**preset).model_dump(mode="json")
                for key, value in data.items():
                    setattr(existing, key, value)
                await self.session.commit()
                continue
            await self.style_crud.create(
                self.session,
                {
                    **StyleProfileCreateRequest(**preset).model_dump(mode="json"),
                    "is_preset": True,
                },
            )

        # Remove old presets no longer in the list (only if unreferenced)
        result = await self.session.execute(
            select(StyleProfile).where(
                StyleProfile.is_preset.is_(True),
                StyleProfile.name.notin_(preset_names),
            )
        )
        for old in result.scalars().all():
            # Check if referenced by any project or generation record
            proj = await self.session.execute(
                select(Project).where(Project.style_id == old.id).limit(1)
            )
            gen = await self.session.execute(
                select(GenerationRecord).where(GenerationRecord.style_id == old.id).limit(1)
            )
            if proj.scalar_one_or_none() is None and gen.scalar_one_or_none() is None:
                await self.session.delete(old)
        await self.session.commit()

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
