# M2：生成闭环

> 里程碑目标：用户能输入描述 → 看到优化后的 Prompt → 获得生成候选图 → 选择入库。核心生成流程跑通。

---

## M2-01 | BE | Prompt Optimizer 模块

### 职责

实现 Prompt 优化器，调用文字 LLM 将用户描述 + 风格参数 + 素材类型模板重写为专业图片生成 Prompt。

### 涉及文件

```
python/fastapi_app/
├── services/
│   ├── __init__.py
│   └── prompt_optimizer.py       # Prompt 优化核心逻辑
├── templates/
│   ├── character_prompt.py       # 角色动画 Prompt 模板
│   └── tile_prompt.py            # Tile Prompt 模板
```

### 依赖

M1-02（FastAPI 服务初始化）、M1-03（数据库，读取风格档案）

### 验收标准

- [ ] 输入用户描述 + 素材类型 + 风格参数，输出优化后的 Prompt
- [ ] 角色模板注入：姿势描述、方向、帧数、锚点居中、轮廓清晰等关键词
- [ ] Tile 模板注入：无缝拼接、边缘规则、重复纹理、地形类型等关键词
- [ ] 结合风格参数（art_style、perspective、default_size）注入画风描述词
- [ ] API 能力感知：当前 API 支持透明背景时加入 `transparent background`
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
        reference_description: str | None = None,
    ) -> OptimizedPrompt:
        """
        返回优化后的 Prompt 和使用的模板信息。
        """

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
4. 如果 API 支持透明背景，在 Prompt 中明确要求白色/纯色背景便于后期处理
5. 输出英文 Prompt
6. 不要输出解释性文字，只输出 Prompt 本身
```

**角色模板示例（`character_prompt.py`）：**

```python
CHARACTER_TEMPLATE = """
{style_keywords} sprite sheet of {user_description},
{perspective} view, {direction_count}-directional,
{frame_count} frames per direction,
character centered in each frame,
clean outlines, {size} per frame,
game asset style, no background elements,
{extra_style_keywords}
"""
```

**Tile 模板示例（`tile_prompt.py`）：**

```python
TILE_TEMPLATE = """
{style_keywords} tileset of {user_description},
seamless tiles, {size} per tile,
{edge_rule} edges, {terrain_type} terrain,
repeating texture, game asset style,
{extra_style_keywords}
"""
```

---

## M2-02 | BE | 素材生成 Engine

### 职责

实现图片生成模块，封装不同 API 提供商的调用逻辑，支持多候选生成。

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
- [ ] 生成结果（图片二进制 + API 返回元数据）持久化到文件系统
- [ ] 生成记录写入 GenerationRecord 表（含 user_prompt、optimized_prompt、api_params、cost_estimate）
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
        """生成图片，返回结果列表。"""

    @abstractmethod
    def get_capabilities(self) -> ApiCapabilities:
        """返回当前 API 提供商的能力。"""

@dataclass
class GeneratedImage:
    image_data: bytes             # PNG 二进制
    seed: str | None              # 可复现种子
    revised_prompt: str | None    # API 可能修订的 Prompt
    size: tuple[int, int]
    cost: float                   # 本次调用成本（美元）
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
    # 注意：DALL-E 3 不支持透明背景，需要降级到后处理去背景
```

---

## M2-03 | BE | 图像后处理管线

### 职责

实现条件式后处理管线：去背景、裁切居中、尺寸标准化、Sprite Sheet 拼接、色板量化。

### 涉及文件

```
python/fastapi_app/
├── services/
│   └── postprocess.py           # 后处理管线
├── postprocess/
│   ├── __init__.py
│   ├── base.py                  # 管线步骤基类
│   ├── remove_bg.py             # 去背景（rembg）
│   ├── crop_center.py           # 裁切 + 居中
│   ├── resize.py                # 尺寸标准化
│   ├── spritesheet.py           # Sprite Sheet 拼接（M3 完善细节）
│   └── quantize.py              # 色板量化
```

### 依赖

M1-02（FastAPI 服务初始化）

### 验收标准

- [ ] 管线为条件式，每个步骤根据输入参数决定是否执行
- [ ] **去背景：** 当 `transparent_background=False`（API 不支持或用户未选）时，使用 rembg 去背景；否则跳过
- [ ] **裁切居中：** 始终执行。裁掉透明区域多余空白，将主体居中
- [ ] **尺寸标准化：** 始终执行。缩放到目标尺寸。像素风使用 `Image.NEAREST`（最近邻插值，不做抗锯齿）；其他风格使用 `Image.LANCZOS`
- [ ] **Sprite Sheet 拼接：** 当 `asset_type=character` 时执行（M3 完善帧分割逻辑）
- [ ] **色板量化：** 当 `art_style=pixel` 时执行，限制颜色数量（如 16 色、32 色）
- [ ] 每个步骤执行后记录到 `postprocess_log`
- [ ] 整个管线处理单张图片耗时 < 5s（不含去背景；去背景 < 10s）

### 接口约定

```python
@dataclass
class PostProcessContext:
    """后处理管线上下文，在步骤间传递"""
    image: PIL.Image.Image           # 当前图片
    asset_type: AssetType            # 素材类型
    style: StyleProfile              # 风格参数
    api_had_transparent_bg: bool     # API 是否已输出透明背景
    target_size: tuple[int, int]     # 目标尺寸，如 (16, 16)
    log: list[PostProcessLog]        # 执行日志

@dataclass
class PostProcessLog:
    step: str          # 步骤名称
    executed: bool     # 是否执行
    params: dict       # 使用的参数
    duration_ms: int   # 耗时

class PostProcessPipeline:
    def __init__(self): ...  # 注册所有步骤

    async def run(self, context: PostProcessContext) -> PostProcessContext:
        """依次执行所有步骤，条件跳过。"""
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

M2-01（Prompt Optimizer）、M2-02（素材生成 Engine）、M2-03（后处理管线）

### 验收标准

- [ ] `POST /api/v1/generate` 完整流程跑通
- [ ] `POST /api/v1/generate/preview` 快速预览模式（低成本多候选）
- [ ] `GET /api/v1/generation/{id}` 查询单条生成记录
- [ ] `GET /api/v1/generation?project_id=xxx` 按项目查询生成记录列表
- [ ] `POST /api/v1/generation/{id}/select` 将生成记录选中为资产

### 接口约定

**`POST /api/v1/generate`**

```python
# 请求体
class GenerateRequest(BaseModel):
    project_id: str
    user_prompt: str                          # 用户原始描述
    asset_type: AssetType                     # character / tile
    style_id: str | None = None               # 不传则用项目默认风格
    reference_image_path: str | None = None   # 参考图路径

    # 角色专用参数
    direction_count: int = 4                  # 方向数
    frame_count: int = 3                      # 每方向帧数
    target_size: tuple[int, int] = (16, 16)   # 单帧尺寸

    # 生成参数
    preview_mode: bool = False                # True=低成本多候选
    transparent_background: bool = True       # 是否请求透明背景

# 响应体
class GenerateResponse(BaseModel):
    records: list[GenerationRecordResponse]   # 生成的候选列表
    optimized_prompt: str                     # 优化后的 Prompt

class GenerationRecordResponse(BaseModel):
    id: str
    image_url: str                            # 前端可通过此 URL 获取图片
    user_prompt: str
    optimized_prompt: str
    seed: str | None
    cost: float
    postprocess_log: list[dict]
    created_at: str
```

**`POST /api/v1/generation/{id}/select`**

```python
# 请求体
class SelectRecordRequest(BaseModel):
    name: str                  # 资产名称
    tags: list[str] = []

# 响应体
class SelectRecordResponse(BaseModel):
    asset: AssetResponse       # 新创建的资产
```

**图片获取：** `GET /api/v1/images/{path:path}` — 静态文件服务，返回图片文件。前端通过此 URL 在 `<img>` 标签中展示。

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
│   │   ├── ParamPanel.tsx          # 动态参数面板
│   │   ├── ReferenceUpload.tsx     # 参考图上传
│   │   ├── CandidateGrid.tsx       # 候选结果网格
│   │   ├── CandidateCard.tsx       # 单个候选卡片
│   │   └── ImageModal.tsx          # 图片放大查看
│   └── common/
│       └── ImagePreview.tsx        # 棋盘格底图预览（M1 已创建骨架）
```

### 依赖

M1-05（React 项目初始化）、M2-04（生成 API）

### 验收标准

- [ ] 素材类型选择器（角色动画 / Tile），选中态视觉区分明确
- [ ] 多行文本输入框，Enter 提交（Shift+Enter 换行）
- [ ] 参数面板根据素材类型动态切换：
  - 角色模式：风格选择、尺寸、视角、帧数、方向数
  - Tile 模式：风格选择、尺寸、边缘规则
- [ ] 参考图上传区（拖拽 + 点击），上传后显示预览
- [ ] "快速预览" 和 "高质量生成" 两个按钮
- [ ] 生成中显示加载状态（进度指示，请求期间 disable 按钮）
- [ ] 候选结果以网格展示，棋盘格底图
- [ ] 点击候选图放大查看
- [ ] 每个候选可操作：加入资产库 / 重试 / 生成变体
- [ ] 加入资产库时弹出命名对话框
- [ ] 空状态有引导文案

### 接口约定

**组件 Props 参考：**

```typescript
// ParamPanel 接收素材类型，切换表单字段
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
  reference_image?: File;
}

// CandidateGrid 展示生成结果
interface CandidateGridProps {
  records: GenerationRecord[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onAddToLibrary: (id: string, name: string, tags: string[]) => void;
  onRetry: (id: string) => void;
  onVariant: (id: string) => void;
}
```

**API 调用流程：**

```
1. 用户填写参数 + 描述 → 点击生成
2. POST /api/v1/generate（或 /generate/preview）
   - 如有参考图：先 POST /api/v1/upload/reference 上传图片，获取路径，再调用生成
3. 轮询或等待返回结果
4. 渲染 CandidateGrid
5. 用户选中一个 → POST /api/v1/generation/{id}/select
```
