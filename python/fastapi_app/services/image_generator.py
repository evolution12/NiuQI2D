from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings, get_settings
from ..crud.generation import GenerationCRUD
from ..exceptions import InvalidParamError
from ..models import AssetSubtype, AssetType
from ..providers.base import CostEstimate, GeneratedImage, GenerationMode, ImageGeneratorBase
from ..providers.openai_provider import OpenAIProvider
from ..schemas import GenerationRecordCreateRequest
from ..storage import StorageManager

PREVIEW_MIN_CANDIDATES = 4
PREVIEW_MAX_CANDIDATES = 6
QUALITY_MIN_CANDIDATES = 2
QUALITY_MAX_CANDIDATES = 3
DEFAULT_PROVIDER_IMAGE_SIZE = (1024, 1024)


@dataclass(slots=True)
class StoredGeneratedImage:
    record_id: str
    image_path: str
    image: GeneratedImage
    cost_estimate: CostEstimate


@dataclass(slots=True)
class ImageGenerationResult:
    mode: GenerationMode
    provider: str
    model: str
    records: list[StoredGeneratedImage]


class ImageGenerator:
    def __init__(
        self,
        session: AsyncSession,
        storage: StorageManager,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.storage = storage
        self.settings = settings or get_settings()
        self.generation_crud = GenerationCRUD()

    async def generate_one(
        self,
        project_id: str,
        user_prompt: str,
        optimized_prompt: str,
        style_id: str,
        asset_type: AssetType,
        asset_subtype: AssetSubtype | None = None,
        mode: GenerationMode = GenerationMode.QUALITY,
        transparent_background: bool = False,
        provider_size: tuple[int, int] = DEFAULT_PROVIDER_IMAGE_SIZE,
        seed: str | None = None,
        reference_image_path: str | None = None,
    ) -> StoredGeneratedImage:
        result = await self.generate_candidates(
            project_id=project_id,
            user_prompt=user_prompt,
            optimized_prompt=optimized_prompt,
            style_id=style_id,
            asset_type=asset_type,
            asset_subtype=asset_subtype,
            mode=mode,
            candidate_count=1,
            transparent_background=transparent_background,
            provider_size=provider_size,
            seed=seed,
            reference_image_path=reference_image_path,
        )
        return result.records[0]

    async def generate_candidates(
        self,
        project_id: str,
        user_prompt: str,
        optimized_prompt: str,
        style_id: str,
        asset_type: AssetType,
        asset_subtype: AssetSubtype | None = None,
        mode: GenerationMode = GenerationMode.QUALITY,
        candidate_count: int | None = None,
        transparent_background: bool = False,
        provider_size: tuple[int, int] = DEFAULT_PROVIDER_IMAGE_SIZE,
        seed: str | None = None,
        reference_image_path: str | None = None,
    ) -> ImageGenerationResult:
        selected_count = self._candidate_count(mode, candidate_count)
        provider = self._build_provider(mode)
        images = await provider.generate(
            prompt=optimized_prompt,
            size=provider_size,
            n=selected_count,
            transparent_background=transparent_background,
            seed=seed,
        )
        cost_estimate = provider.estimate_cost(n=len(images), size=provider_size)
        records = await self._persist_images(
            project_id=project_id,
            user_prompt=user_prompt,
            optimized_prompt=optimized_prompt,
            style_id=style_id,
            asset_type=asset_type,
            asset_subtype=asset_subtype,
            provider=provider,
            images=images,
            cost_estimate=cost_estimate,
            mode=mode,
            transparent_background=transparent_background,
            reference_image_path=reference_image_path,
        )
        return ImageGenerationResult(
            mode=mode,
            provider=provider.provider_name,
            model=provider.model,
            records=records,
        )

    def estimate_cost(
        self,
        mode: GenerationMode = GenerationMode.QUALITY,
        candidate_count: int | None = None,
        provider_size: tuple[int, int] = DEFAULT_PROVIDER_IMAGE_SIZE,
    ) -> CostEstimate:
        selected_count = self._candidate_count(mode, candidate_count)
        provider = self._build_provider(mode)
        return provider.estimate_cost(n=selected_count, size=provider_size)

    async def _persist_images(
        self,
        project_id: str,
        user_prompt: str,
        optimized_prompt: str,
        style_id: str,
        asset_type: AssetType,
        asset_subtype: AssetSubtype | None,
        provider: ImageGeneratorBase,
        images: list[GeneratedImage],
        cost_estimate: CostEstimate,
        mode: GenerationMode,
        transparent_background: bool,
        reference_image_path: str | None,
    ) -> list[StoredGeneratedImage]:
        records: list[StoredGeneratedImage] = []
        for index, image in enumerate(images):
            record = await self.generation_crud.create(
                self.session,
                GenerationRecordCreateRequest(
                    project_id=project_id,
                    user_prompt=user_prompt,
                    optimized_prompt=optimized_prompt,
                    style_id=style_id,
                    asset_type=asset_type,
                    asset_subtype=asset_subtype,
                    api_provider=provider.provider_name,
                    api_model=provider.model,
                    api_params={
                        "mode": mode.value,
                        "project_id": project_id,
                        "candidate_index": index,
                        "provider_size": {"w": image.size[0], "h": image.size[1]},
                        "transparent_background": transparent_background,
                        "cost_estimate": {
                            "estimated_usd": cost_estimate.estimated_usd,
                            "image_count": cost_estimate.image_count,
                            "details": cost_estimate.details,
                        },
                        "provider_metadata": image.metadata,
                    },
                    seed=image.seed,
                    reference_image_path=reference_image_path,
                ),
            )
            image_path = await self.storage.save_raw_image(project_id, record.id, image.image_data)
            record = await self.generation_crud.update(
                self.session,
                record.id,
                {
                    "api_params": {
                        **record.api_params,
                        "raw_image_path": image_path,
                        "image_url": f"/images/{image_path}",
                        "revised_prompt": image.revised_prompt,
                    }
                },
            )
            records.append(
                StoredGeneratedImage(
                    record_id=record.id,
                    image_path=image_path,
                    image=image,
                    cost_estimate=cost_estimate,
                )
            )
        return records

    def _build_provider(self, mode: GenerationMode) -> ImageGeneratorBase:
        provider = self.settings.image_api_provider
        if provider == "openai":
            model = self._model_for_mode(mode)
            quality = "standard" if mode == GenerationMode.PREVIEW else "hd"
            return OpenAIProvider(
                api_key=self.settings.image_api_key,
                model=model,
                quality=quality,
            )
        if provider == "volcengine":
            from ..providers.volcengine_provider import VolcengineProvider
            return VolcengineProvider(
                access_key=self.settings.volcengine_access_key,
                secret_key=self.settings.volcengine_secret_key,
                req_key=self.settings.volcengine_req_key,
            )
        if provider == "doubao":
            from ..providers.doubao_provider import DoubaoArkProvider
            return DoubaoArkProvider(
                api_key=self.settings.doubao_api_key,
                model=self.settings.doubao_model,
            )
        raise InvalidParamError(f"暂不支持图片生成提供商 {provider}")

    def _model_for_mode(self, mode: GenerationMode) -> str:
        if mode == GenerationMode.PREVIEW:
            return self.settings.preview_image_model
        return self.settings.quality_image_model

    def _candidate_count(self, mode: GenerationMode, requested_count: int | None) -> int:
        if requested_count is not None:
            if requested_count < 1 or requested_count > 6:
                raise InvalidParamError("候选数量必须在 1 到 6 之间")
            return requested_count
        if mode == GenerationMode.PREVIEW:
            return PREVIEW_MIN_CANDIDATES
        return QUALITY_MIN_CANDIDATES
