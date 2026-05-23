from __future__ import annotations

from ..postprocess import (
    CropCenterStep,
    FrameExtractorStep,
    PostProcessContext,
    PostProcessStep,
    QuantizeStep,
    RemoveBackgroundStep,
    ResizeStep,
)


class PostProcessPipeline:
    def __init__(self, steps: list[PostProcessStep] | None = None) -> None:
        self.steps = steps or [
            FrameExtractorStep(),
            RemoveBackgroundStep(),
            CropCenterStep(),
            ResizeStep(),
            QuantizeStep(),
        ]

    async def run(self, context: PostProcessContext) -> PostProcessContext:
        context.image = context.image.convert("RGBA")
        for step in self.steps:
            context = await step.run(context)
        return context
