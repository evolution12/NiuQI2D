# M3：导出与资产库

> 里程碑目标：用户能浏览已生成的资产、查看动画预览、配置导出参数、输出 PNG+JSON 文件。

---

## M3-01 | BE | Sprite Sheet 拼接引擎

### 职责

实现多帧图片的 Sprite Sheet 拼接，支持按动作/方向排列、帧间对齐、间距/补边配置。接收 M2 后处理管线输出的独立帧列表作为输入。

### 涉及文件

```
python/fastapi_app/
├── postprocess/
│   └── spritesheet.py           # Sprite Sheet 拼接（本任务完全实现）
```

### 依赖

M2-03（后处理管线，输出独立帧列表）

### 验收标准

- [ ] 输入一组同尺寸帧图片，输出排列好的 Sprite Sheet PNG
- [ ] 支持按动作/方向分行排列（如 4 行方向 × 3 帧列）
- [ ] 帧间位置对齐：所有帧的主体在画布内居中对齐（基于透明区域边界框）
- [ ] 支持配置帧间距（padding）和画布补边（margin）
- [ ] 同时输出 JSON 元数据，包含每帧的 `frame`（x,y,w,h）、`filename`、`pivot`
- [ ] 帧命名遵循 `{角色名}_{动作}_{方向}_{帧号}` 规范

### 接口约定

```python
@dataclass
class SpriteSheetConfig:
    frame_size: tuple[int, int]          # 单帧尺寸，如 (16, 16)
    columns: int                         # 列数（每行帧数）
    rows: int                            # 行数
    padding: int = 0                     # 帧间距（像素）
    margin: int = 0                      # 画布补边（像素）

@dataclass
class SpriteSheetResult:
    sheet_image: PIL.Image.Image
    frames_metadata: list[FrameMetadata]

@dataclass
class FrameMetadata:
    filename: str          # "archer_idle_down_0"
    frame: dict            # {"x": 0, "y": 0, "w": 16, "h": 16}
    rotated: bool = False
    trimmed: bool = True
    spriteSourceSize: dict  # {"x": 2, "y": 1, "w": 16, "h": 16}
    sourceSize: dict        # {"w": 16, "h": 16}
    pivot: dict             # {"x": 0.5, "y": 0.5}

def build_sprite_sheet(
    frames: list[PIL.Image.Image],
    config: SpriteSheetConfig,
    naming_template: str,           # 如 "archer_{action}_{direction}_{frame}"
    actions: list[str],             # ["idle", "walk"]
    directions: list[str],          # ["down", "up", "left", "right"]
    frames_per_action: int,         # 3
) -> SpriteSheetResult:
    """
    frames 按 M2 后处理管线输出的顺序排列：
    [idle_down_0, idle_down_1, idle_down_2, idle_up_0, ...]
    """
```

**帧对齐算法要点：**

```
0. 检测实际帧尺寸是否一致，如不一致则统一缩放到目标帧尺寸（像素风用 NEAREST）
1. 对每帧图片计算非透明区域的边界框 (bounding box)
2. 计算所有帧边界框的最大宽高 (max_w, max_h)
3. 对每帧：将主体在 max_w × max_h 画布内居中
4. 缩放画布到 target_size（如果 max > target）
5. 按行列排列到最终 Sprite Sheet
```

---

## M3-02 | BE | Tileset 拼接引擎

### 职责

实现 Tile 图片的 Tileset 拼接，支持配置列数、间距、margin。

### 涉及文件

```
python/fastapi_app/
├── postprocess/
│   └── tileset.py               # Tileset 拼接
```

### 依赖

M2-03（后处理管线）

### 验收标准

- [ ] 输入一组同尺寸 Tile 图片，输出排列好的 Tileset PNG
- [ ] 支持配置列数、Tile 间距、画布 margin
- [ ] 输出 JSON 元数据，包含每个 Tile 的 id、位置、type、terrain 信息

### 接口约定

```python
@dataclass
class TilesetConfig:
    tile_size: tuple[int, int]    # 单 Tile 尺寸，如 (16, 16)
    columns: int                  # 列数
    spacing: int = 0
    margin: int = 0

@dataclass
class TilesetResult:
    tileset_image: PIL.Image.Image
    tiles_metadata: list[TileMetadata]

@dataclass
class TileMetadata:
    id: int
    type: str          # "grass_plain", "grass_dirt_nw" 等
    terrain: list[str] # 四边地形标记

def build_tileset(
    tiles: list[PIL.Image.Image],
    config: TilesetConfig,
    tile_types: list[str],       # 每个 tile 的类型名
) -> TilesetResult: ...
```

---

## M3-03 | BE | 导出 API

### 职责

实现导出功能的 HTTP API，串联资产查询 → 拼接 → JSON 生成 → 文件写入 → 资产状态更新。

### 涉及文件

```
python/fastapi_app/
├── routers/
│   └── export.py                # 导出 API（替换 M1 中的空路由）
├── services/
│   └── export_service.py        # 导出业务逻辑
```

### 依赖

M3-01（Sprite Sheet）、M3-02（Tileset）

### 验收标准

- [ ] `POST /api/v1/export` 支持三种导出类型
- [ ] 单图 PNG：直接将资产图片复制到导出路径
- [ ] Sprite Sheet + JSON：调用拼接引擎，输出 PNG + JSON
- [ ] Tileset + JSON：调用拼接引擎，输出 PNG + JSON
- [ ] JSON 格式严格遵循设计文档第 5 节规范
- [ ] 导出记录写入 ExportRecord 表
- [ ] 导出成功后将关联资产的 status 更新为 `exported`
- [ ] 支持批量导出（多个资产合并为一个 Sprite Sheet）
- [ ] 导出路径不存在时自动创建

### 接口约定

**`POST /api/v1/export`**

```python
class ExportRequest(BaseModel):
    asset_ids: list[str]
    export_format: ExportFormat
    export_path: str

    # Sprite Sheet 选项
    sheet_layout: str = "by_action"
    sheet_padding: int = 0
    sheet_margin: int = 0

    # Tileset 选项
    tileset_columns: int = 8
    tileset_spacing: int = 0
    tileset_margin: int = 0

class ExportResponse(BaseModel):
    export_id: str
    files: list[ExportFileInfo]
    total_size: int

class ExportFileInfo(BaseModel):
    filename: str
    path: str
    size: int
```

**`GET /api/v1/export/history?project_id=xxx`** — 导出历史列表

**`GET /api/v1/export/{id}`** — 单条导出记录详情

---

## M3-04 | BE | 资产管理 API

### 职责

实现资产库的 CRUD API，支持列表查询、筛选、搜索、批量操作。

### 涉及文件

```
python/fastapi_app/
├── routers/
│   └── assets.py                # 资产管理 API（替换 M1 中的空路由）
```

### 依赖

M1-03（数据库 CRUD）

### 验收标准

- [ ] `GET /api/v1/assets?project_id=xxx` 分页列表，支持筛选参数：
  - `asset_type`、`status`、`tag`、`search`（名称模糊搜索）
- [ ] `GET /api/v1/assets/{id}` 单个资产详情
- [ ] `PUT /api/v1/assets/{id}` 更新资产（名称、标签、状态）
- [ ] `DELETE /api/v1/assets/{id}` 删除资产（同时删除文件）
- [ ] `POST /api/v1/assets/batch-delete` 批量删除
- [ ] `GET /api/v1/assets/{id}/animation` 返回动画帧序列（角色类资产）
- [ ] 缩略图自动生成（资产创建时触发，按素材类型区分尺寸）
- [ ] `GET /api/v1/tags?project_id=xxx` 返回项目内所有标签列表（用于筛选器下拉选项）

### 接口约定

**`GET /api/v1/assets`**

**`GET /api/v1/tags`**

```python
class TagsResponse(BaseModel):
    tags: list[str]             # 去重后的标签列表，如 ["弓箭手", "森林", "NPC", "草地"]
```

**`GET /api/v1/assets`**
    project_id: str
    asset_type: AssetType | None = None
    status: AssetStatus | None = None
    tag: str | None = None
    search: str | None = None
    page: int = 1
    page_size: int = 20
    sort_by: str = "created_at"
    sort_order: str = "desc"

class AssetListResponse(BaseModel):
    items: list[AssetResponse]
    total: int
    page: int
    page_size: int
```

**`GET /api/v1/assets/{id}/animation`**

```python
class AnimationResponse(BaseModel):
    frames: list[str]         # 每帧图片 URL 列表（有序）
    frame_count: int
    frame_delay_ms: int       # 默认帧间隔（毫秒）
    actions: dict[str, list[int]]  # {"idle_down": [0,1,2], "idle_up": [3,4,5]}
```

---

## M3-05 | FE | 资产库页 UI

### 职责

实现资产库页面的全部 UI 和交互。

### 涉及文件

```
src/
├── pages/
│   └── AssetLibraryPage.tsx       # 资产库页（替换 M1 占位符）
├── components/
│   ├── asset/
│   │   ├── AssetGrid.tsx          # 资产网格视图
│   │   ├── AssetCard.tsx          # 资产卡片
│   │   ├── AssetDetailPanel.tsx   # 资产详情侧滑面板
│   │   ├── AnimationPlayer.tsx    # 动画帧播放器
│   │   ├── AssetFilterBar.tsx     # 筛选器组
│   │   └── BatchActionBar.tsx     # 批量操作工具栏
```

### 依赖

M1-06（React 项目）、M3-04（资产管理 API）

### 验收标准

- [ ] 资产以网格展示，每张卡片显示缩略图 + 名称 + 类型标签 + 状态标记
- [ ] 筛选器组：类型下拉、状态下拉、标签筛选
- [ ] 搜索框实时搜索（debounce 300ms）
- [ ] 支持网格/列表视图切换
- [ ] 多选模式：勾选后出现批量操作栏（全选、批量导出、批量删除）
- [ ] 点击卡片打开详情侧滑面板：
  - 大图预览（棋盘格底图）
  - 角色类资产显示 AnimationPlayer（播放/暂停、帧率调节）
  - 生成参数只读展示（原始 Prompt、优化后 Prompt、风格、API 模型）
  - 操作按钮：复现、变体、删除
- [ ] 空状态引导文案
- [ ] 分页加载或滚动加载

### 接口约定

```typescript
interface AssetDetail {
  asset: Asset;
  generation_records: GenerationRecord[];
  animation?: AnimationResponse;
}

interface AnimationPlayerProps {
  frames: string[];
  frameDelayMs: number;
  actions?: Record<string, number[]>;
}
```

---

## M3-06 | FE | 导出页 UI

### 职责

实现导出页面的全部 UI 和交互。

### 涉及文件

```
src/
├── pages/
│   └── ExportPage.tsx             # 导出页（替换 M1 占位符）
├── components/
│   ├── export/
│   │   ├── AssetSelector.tsx      # 已选资产列表
│   │   ├── ExportTypeSelector.tsx # 导出类型单选
│   │   ├── ExportConfigForm.tsx   # 动态导出配置表单
│   │   ├── PathSelector.tsx       # 导出路径选择
│   │   └── ExportHistory.tsx      # 导出历史列表
```

### 依赖

M1-06（React 项目）、M3-03（导出 API）

### 验收标准

- [ ] 资产选择区展示已选资产缩略图列表（可从资产库页跳转带入，也可在导出页手动添加）
- [ ] 导出类型单选组：单图 PNG / Sprite Sheet + JSON / Tileset + JSON
- [ ] 配置表单根据导出类型动态切换：
  - Sprite Sheet：排列方式下拉、帧间距、画布补边
  - Tileset：Tile 尺寸、列数、间距
  - 单图 PNG：无额外配置
- [ ] 路径选择器调用 `window.electronAPI.fs.selectDirectory()`
- [ ] 导出按钮 + 进度条
- [ ] 导出完成后可点击"打开文件夹"
- [ ] 导出历史列表展示（文件名、日期、大小）
- [ ] 空状态：未选择资产时引导用户去资产库选择

### 接口约定

```typescript
interface ExportPageState {
  selectedAssets: Asset[];
  exportFormat: ExportFormat;
  exportPath: string;
  config: ExportConfig;
}

type ExportConfig =
  | { format: "png_single" }
  | { format: "spritesheet_png_json"; layout: string; padding: number; margin: number }
  | { format: "tileset_png_json"; columns: number; spacing: number; margin: number }
```
