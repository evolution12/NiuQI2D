# M2：生成闭环

> 里程碑目标：用户能输入描述 → 看到优化后的 Prompt → 获得生成候选图（Sprite Sheet） → 选择入库。核心生成流程跑通。

---

## M2-01 | BE | Prompt Optimizer 模块

### 职责

实现 Prompt 优化器，调用文字 LLM 将用户描述 + 风格参数 + 素材类型模板重写为专业图片生成 Prompt。支持参考图风格描述注入。

### 涉及文件

```
python/fastapi_app/
├── services/
│   ├── __init__.py
│   └── prompt_optimizer.py       # Prompt 优化核心逻辑
├── templates/
│   ├── character_prompt.py       # 角色动画 Sprite Sheet Prompt 模板
│   └── tile_prompt.py            # Tile Prompt 模板
```

### 依赖

M1-02（FastAPI 服务初始化）、M1-03（数据库，读取风格档案）

### 验收标准

- [ ] 输入用户描述 + 素材类型 + 风格参数，输出优化后的 Prompt
- [ ] 角色模板注入：Sprite Sheet 布局关键词（行列数、每帧尺寸、网格排列、方向顺序、帧数）
- [ ] Tile 模板注入：无缝拼接、边缘规则、重复纹理、地形类型等关键词
- [ ] 结合风格参数（art_style、perspective、default_size）注入画风描述词
- [ ] API 能力感知：当前 API 支持透明背景时加入 `transparent background`
- [ ] 支持参考图风格描述作为额外输入（由 M4-01 的视觉 LLM 生成）
- [ ] 输出 Prompt 长度合理（200-500 词），不超出图片 API 的 Prompt 限制
- [ ] 处理超时和 API 错误，返回有意义的错误信息

### 接口约定

**核心函数签名：**

```python
class PromptOptimizer:
    def __init__(self, api_provider: str, api_key: str, api_model: str): ...

    async def optimize(
        self,
        user_prompt: str,
        asset_type: AssetType,
        style: StyleProfile,
        api_capabilities: ApiCapabilities,
        reference_style_description: str | None = None,  # 参考图视觉描述（M4-01 生成）
    ) -> OptimizedPrompt:

@dataclass
class ApiCapabilities:
    supports_transparent_background: bool
    max_image_size: tuple[int, int]
    supported_sizes: list[tuple[int, int]]

@dataclass
class OptimizedPrompt:
    prompt: str                   # 最终优化后的 Prompt
    template_used: str            # 使用的模板名称
    user_prompt_original: str     # 用户原始输入（原样保存）
```

**System Prompt 设计要求：**

```
你是一个专业的游戏美术 Prompt 工程师。你的任务是将用户的简短描述转化为
精确的 AI 图片生成 Prompt。

规则：
1. 保持用户描述的核心意图不变
2. 根据素材类型模板注入专业关键词
3. 根据风格参数调整画风描述
4. 如果 API 支持透明背景，在 Prompt 中明确要求纯色背景便于后期处理
5. 如果提供了参考图风格描述，融合其视觉特征关键词
6. 输出英文 Prompt
7. 不要输出解释性文字，只输出 Prompt 本身
```

**角色 Sprite Sheet 模板（`character_prompt.py`）：**

```python
CHARACTER_SPRITESHEET_TEMPLATE = """
{style_keywords} sprite sheet of {user_description},
{perspective} view, {direction_count} rows (one per direction: {directions}),
{frame_count} columns per row ({frame_count} animation frames per direction),
each cell {cell_size}px × {cell_size}px,
arranged in a clean grid layout with no overlap, uniform cell size,
character centered in each cell, clean outlines,
game asset style, no background elements,
{extra_style_keywords}
"""
```

**Tile 模板（`tile_prompt.py`）：**

```python
TILE_TEMPLATE = """
{style_keywords} tileset of {user_description},
seamless tiles, {tile_size}px per tile,
{edge_rule} edges, {terrain_type} terrain,
repeating texture, game asset style,
{extra_style_keywords}
"""
```

---

## M2-02 | BE | 素材生成 Engine

### 职责

实现图片生成模块，封装不同 API 提供商的调用逻辑，支持多候选生成、快速预览/高质量模式切换。

### 涉及文件

```
python/fastapi_app/
├── services/
│   └── image_generator.py       # 图片生成核心逻辑
├── providers/
│   ├── __init__.py
│   ├── base.py                  # 生成器基类/接口
│   └── openai_provider.py       # OpenAI (gpt-image-1 / DALL-E 3) 实现
```

### 依赖

M1-02（FastAPI 服务初始化）、M1-03（数据库）

### 验收标准

- [ ] 支持通过配置切换 API 提供商（V1 先实现 OpenAI）
- [ ] 支持单次生成和批量多候选生成（n=2~6）
- [ ] 支持传入 `background: "transparent"` 参数（当 API 和用户选择支持时）
- [ ] 生成模式区分：
  - **快速预览：** 使用 `preview_image_model`（默认 dall-e-3 standard），4-6 候选
  - **高质量：** 使用 `quality_image_model`（默认 gpt-image-1），2-3 候选
  - 用户可在设置页自定义每种模式使用的模型
- [ ] 生成结果（图片二进制 + API 返回元数据）持久化到文件系统
- [ ] 生成记录写入 GenerationRecord 表
- [ ] API 调用失败时有重试机制（最多 3 次，指数退避）
- [ ] 超时处理（单次生成超时 60s）

### 接口约定

**生成器接口：**

```python
class ImageGeneratorBase(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        size: tuple[int, int] = (1024, 1024),
        n: int = 1,
        transparent_background: bool = False,
        seed: str | None = None,
    ) -> list[GeneratedImage]:

    @abstractmethod
    def get_capabilities(self) -> ApiCapabilities:

@dataclass
class GeneratedImage:
    image_data: bytes             # PNG 二进制
    seed: str | None
    revised_prompt: str | None
    size: tuple[int, int]
    cost: float
```

**OpenAI 提供商实现要点：**

```python
class OpenAIProvider(ImageGeneratorBase):
    # gpt-image-1: 使用 openai.Images.generate()
    #   - model="gpt-image-1"
    #   - size: "1024x1024" (只支持预设尺寸)
    #   - background: "transparent" (gpt-image-1 专有参数)
    #   - n: 1-4 (单次请求数量)
    #   - output_format: "png"
    #
    # DALL-E 3: 使用 openai.Images.generate()
    #   - model="dall-e-3"
    #   - size: "1024x1024" / "1792x1024" / "1024x1792"
    #   - quality: "standard" / "hd"
    #   - n: 1 (DALL-E 3 单次只能生成 1 张)
    #
    # 多候选策略：
    #   - DALL-E 3 (n=1): 循环调用 N 次获得 N 张候选
    #   - gpt-image-1 (n=1-4): 单次请求获得 min(n,4) 张
```

---

## M2-03 | BE | 图像后处理管线

### 职责

实现条件式后处理管线：帧提取（从 Sprite Sheet 切割）、去背景、裁切居中、尺寸标准化、色板量化。

### 涉及文件

```
python/fastapi_app/
├── services/
│   └── postprocess.py           # 后处理管线编排
├── postprocess/
│   ├── __init__.py
│   ├── base.py                  # 管线步骤基类
│   ├── frame_extractor.py       # 帧提取（从 AI 生成的 Sprite Sheet 切割为独立帧）
│   ├── remove_bg.py             # 去背景（rembg）
│   ├── crop_center.py           # 裁切 + 居中
│   ├── resize.py                # 尺寸标准化
│   └── quantize.py              # 色板量化
```

### 依赖

M1-02（FastAPI 服务初始化）

### 验收标准

- [ ] 管线为条件式，每个步骤根据输入参数决定是否执行
- [ ] **帧提取（仅角色动画）：** 从 AI 生成的 Sprite Sheet 图片中，按网格切割为独立帧。假设行列数与 Prompt 指定的一致，检测每帧边界并切割
- [ ] **去背景：** 当 `api_had_transparent_bg=False` 时，使用 rembg 去背景；否则跳过
- [ ] **裁切居中：** 始终执行。裁掉透明区域多余空白，将主体居中
- [ ] **尺寸标准化：** 始终执行。像素风使用 `Image.NEAREST`；其他风格使用 `Image.LANCZOS`
- [ ] **色板量化：** 当 `art_style=pixel` 时执行，限制颜色数量
- [ ] 每个步骤执行后记录到 `postprocess_log`（结构见下方）
- [ ] 整个管线处理单张图片耗时 < 5s（不含去背景；去背景 < 10s）
- [ ] Sprite Sheet 拼接不在本任务范围（M3-01 负责）。本任务输出的是独立帧图片列表

### 接口约定

```python
@dataclass
class PostProcessContext:
    """后处理管线上下文，在步骤间传递"""
    image: PIL.Image.Image           # 当前图片（初始为 AI 生成的完整图）
    extracted_frames: list[PIL.Image.Image]  # 帧提取后的独立帧列表（仅角色动画）
    asset_type: AssetType
    style: StyleProfile
    api_had_transparent_bg: bool
    target_size: tuple[int, int]
    sheet_rows: int | None           # Sprite Sheet 行数（仅角色）
    sheet_cols: int | None           # Sprite Sheet 列数（仅角色）
    log: list[PostProcessLog]

@dataclass
class PostProcessLog:
    step: str          # 步骤名称
    executed: bool     # 是否执行
    params: dict       # 使用的参数
    duration_ms: int   # 耗时

class PostProcessPipeline:
    def __init__(self): ...

    async def run(self, context: PostProcessContext) -> PostProcessContext:
        """依次执行所有步骤，条件跳过。角色动画输出 extracted_frames。"""
```

**帧提取算法要点：**

```
输入：AI 生成的 Sprite Sheet 图片 + 预期行列数 + 预期帧尺寸
1. 计算每帧的理论尺寸：total_width / cols, total_height / rows
2. 如果实际帧尺寸与预期不符（AI 未精确遵循尺寸指令），按实际切割
3. 逐帧切割，存入 extracted_frames 列表
4. 对每帧独立执行后续裁切/居中/缩放步骤
```

---

## M2-04 | BE | 生成 API 路由

### 职责

实现素材生成的完整 HTTP API，串联 Prompt 优化 → 图片生成 → 后处理 → 入库。

### 涉及文件

```
python/fastapi_app/
├── routers/
│   └── generation.py            # 生成相关 API（替换 M1 中的空路由）
├── schemas.py                   # 补充生成相关的请求/响应 schema
```

### 依赖

M2-01（Prompt Optimizer）、M2-02（素材生成 Engine）、M2-03（后处理管线）、M1-05（文件上传 API）

### 验收标准

- [ ] `POST /api/v1/generate` 完整流程跑通（高质量模式）
- [ ] `POST /api/v1/generate/preview` 快速预览模式
- [ ] `GET /api/v1/generation/{id}` 查询单条生成记录
- [ ] `GET /api/v1/generation?project_id=xxx` 按项目查询生成记录列表
- [ ] `POST /api/v1/generation/{id}/select` 将生成记录选中为资产

### 接口约定

**`POST /api/v1/generate`**

```python
class GenerateRequest(BaseModel):
    project_id: str
    user_prompt: str
    asset_type: AssetType                     # character / tile
    style_id: str | None = None               # 不传则用项目默认风格
    reference_image_path: str | None = None   # 参考图路径（通过 M1-05 上传获得）
    reference_style_description: str | None = None  # 参考图风格描述（M4 提供，V1 可为空）

    # 角色专用参数
    direction_count: int = 4
    frame_count: int = 3
    target_size: tuple[int, int] = (16, 16)

    # 生成参数
    preview_mode: bool = False                # True=快速预览
    transparent_background: bool = True

class GenerateResponse(BaseModel):
    records: list[GenerationRecordResponse]
    optimized_prompt: str

class GenerationRecordResponse(BaseModel):
    id: str
    image_url: str                            # /images/{project_id}/raw/{record_id}.png
    user_prompt: str
    optimized_prompt: str
    seed: str | None
    cost: float
    postprocess_log: list[dict]
    created_at: str
```

**`POST /api/v1/generation/{id}/select`**

```python
class SelectRecordRequest(BaseModel):
    name: str
    tags: list[str] = []

class SelectRecordResponse(BaseModel):
    asset: AssetResponse
```

**完整调用流程：**

```
1. 前端传入 GenerateRequest
2. 读取风格档案（style_id 或项目默认）
3. PromptOptimizer.optimize() → 优化 Prompt
   - 角色动画：生成 Sprite Sheet 布局 Prompt（指定行列数、帧尺寸）
   - Tile：生成 Tileset Prompt
4. ImageGenerator.generate() → 获得原始图片
5. PostProcessPipeline.run() → 后处理
   - 角色：帧提取 → 逐帧裁切/居中/缩放 → 输出独立帧列表
   - Tile：裁切/居中/缩放
6. 保存处理后的图片到文件系统
7. 写入 GenerationRecord
8. 返回候选列表给前端
```

---

## M2-05 | FE | 生成页 UI

### 职责

实现生成页的全部 UI 组件和交互逻辑。

### 涉及文件

```
src/
├── pages/
│   └── GeneratePage.tsx            # 生成页（替换 M1 占位符）
├── components/
│   ├── generate/
│   │   ├── AssetTypeSelector.tsx   # 素材类型选择器
│   │   ├── PromptInput.tsx         # 文字描述输入
│   │   ├── PromptPreview.tsx       # 优化后 Prompt 预览（可展开查看）
│   │   ├── ParamPanel.tsx          # 动态参数面板
│   │   ├── ReferenceUpload.tsx     # 参考图上传
│   │   ├── CandidateGrid.tsx       # 候选结果网格
│   │   ├── CandidateCard.tsx       # 单个候选卡片
│   │   └── ImageModal.tsx          # 图片放大查看
│   └── common/
│       └── ImagePreview.tsx        # 棋盘格底图预览（M1 已创建骨架）
```

### 依赖

M1-06（React 项目初始化）、M2-04（生成 API）

### 验收标准

- [ ] 素材类型选择器（角色动画 / Tile），选中态视觉区分明确
- [ ] 多行文本输入框，Enter 提交（Shift+Enter 换行）
- [ ] 参数面板根据素材类型动态切换：
  - 角色模式：风格选择、尺寸、视角、帧数、方向数
  - Tile 模式：风格选择、尺寸、边缘规则
- [ ] 参考图上传区（拖拽 + 点击），调用 M1-05 上传 API，上传后显示预览
- [ ] "快速预览" 和 "高质量生成" 两个按钮
- [ ] 生成中显示加载状态（进度指示，请求期间 disable 按钮）
- [ ] 生成完成后，显示优化后的 Prompt 预览（可折叠/展开）
- [ ] 候选结果以网格展示，棋盘格底图
- [ ] 点击候选图放大查看（Sprite Sheet 整图预览）
- [ ] 每个候选可操作：加入资产库 / 重试 / 生成变体
- [ ] 加入资产库时弹出命名对话框
- [ ] 空状态有引导文案

### 接口约定

```typescript
interface ParamPanelProps {
  assetType: AssetType;
  onParamsChange: (params: GenerateParams) => void;
}

interface GenerateParams {
  asset_type: AssetType;
  style_id?: string;
  target_size: [number, number];
  direction_count?: number;    // 角色
  frame_count?: number;        // 角色
  reference_image_path?: string;
}

interface CandidateGridProps {
  records: GenerationRecord[];
  optimizedPrompt: string;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onAddToLibrary: (id: string, name: string, tags: string[]) => void;
  onRetry: () => void;
  onVariant: (id: string) => void;
}
```

**API 调用流程：**

```
1. 用户填写参数 + 描述 → 点击生成
2. 如有参考图：先 POST /api/v1/upload（purpose=reference）→ 获取 path
3. POST /api/v1/generate（或 /generate/preview）
4. 等待返回结果
5. 渲染 PromptPreview + CandidateGrid
6. 用户选中一个 → POST /api/v1/generation/{id}/select
```
