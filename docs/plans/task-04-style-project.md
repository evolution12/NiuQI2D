# M4：风格管理与项目管理

> 里程碑目标：用户能创建/管理风格档案，上传参考图并自动提取风格特征，创建项目绑定风格，复现和变体生成。

---

## M4-01 | BE | 风格管理 API + 参考图视觉描述提取

### 职责

实现风格档案的 CRUD API，包含预设风格初始化、自定义风格创建、参考图上传。核心新增：调用视觉 LLM 对参考图进行风格描述提取，生成的描述文本供 Prompt Optimizer 使用。

### 涉及文件

```
python/fastapi_app/
├── routers/
│   └── styles.py                # 风格管理 API（替换 M1 中的空路由）
├── services/
│   ├── style_service.py         # 风格业务逻辑
│   └── reference_analyzer.py    # 参考图视觉描述提取（调用 vision LLM）
├── data/
│   └── preset_styles.json       # 内置预设风格定义
```

### 依赖

M1-03（数据库 CRUD）、M1-05（文件上传 API）

### 验收标准

- [ ] `GET /api/v1/styles` 列出所有风格（预设 + 用户自定义）
- [ ] `GET /api/v1/styles/{id}` 单个风格详情
- [ ] `POST /api/v1/styles` 创建自定义风格
- [ ] `PUT /api/v1/styles/{id}` 更新风格参数
- [ ] `DELETE /api/v1/styles/{id}` 删除自定义风格（预设风格不可删除）
- [ ] `POST /api/v1/styles/{id}/reference` 上传参考图并自动提取风格描述
- [ ] `DELETE /api/v1/styles/{id}/reference` 删除参考图
- [ ] 首次启动时自动初始化预设风格到数据库
- [ ] 参考图上传后自动调用视觉 LLM 提取风格描述，结果存入 StyleProfile 的 extra_params 中

### 接口约定

**`POST /api/v1/styles/{id}/reference`**

```python
class ReferenceUploadResponse(BaseModel):
    reference_image_path: str
    style_description: str       # 视觉 LLM 提取的风格描述
    # 示例："pixel art style, 16x16, top-down perspective, limited color palette
    #        with earthy tones, bold outlines, no anti-aliasing, flat shading"
```

**`reference_analyzer.py` 核心接口：**

```python
class ReferenceAnalyzer:
    def __init__(self, api_provider: str, api_key: str, api_model: str):
        """
        使用支持 vision 的模型（如 gpt-4o）分析参考图。
        图片和文字 API 可以共用同一个 Key（如果供应商相同）。
        """

    async def analyze_style(self, image_path: str) -> str:
        """
        调用视觉 LLM 分析参考图的风格特征。
        返回结构化的风格描述文本，供 Prompt Optimizer 使用。

        Vision Prompt 示例：
        "分析这张游戏素材图片的视觉风格，包括：
         1. 画风格式（像素风/手绘/卡通/写实）
         2. 调色板特征（主要颜色、明暗对比）
         3. 线条风格（粗细、是否抗锯齿）
         4. 阴影和光照方式
         5. 整体尺寸和细节密度
         用简洁的关键词描述，输出英文。"
        """
```

**预设风格（`data/preset_styles.json`）：**

```json
[
  {
    "name": "像素风 16×16",
    "art_style": "pixel",
    "default_size": {"w": 16, "h": 16},
    "perspective": "top_down",
    "extra_params": {"color_count": 16, "outline": true}
  },
  {
    "name": "像素风 32×32",
    "art_style": "pixel",
    "default_size": {"w": 32, "h": 32},
    "perspective": "top_down",
    "extra_params": {"color_count": 32, "outline": true}
  },
  {
    "name": "像素风 64×64",
    "art_style": "pixel",
    "default_size": {"w": 64, "h": 64},
    "perspective": "side_scroller",
    "extra_params": {"color_count": 48, "outline": true}
  },
  {
    "name": "手绘风",
    "art_style": "hand_drawn",
    "default_size": {"w": 128, "h": 128},
    "perspective": "top_down",
    "extra_params": {"line_width": "varied", "watercolor": false}
  },
  {
    "name": "卡通风",
    "art_style": "cartoon",
    "default_size": {"w": 256, "h": 256},
    "perspective": "side_scroller",
    "extra_params": {"bold_outlines": true, "cel_shading": true}
  }
]
```

---

## M4-02 | BE | 项目管理 API

### 职责

实现项目的 CRUD API，包含风格绑定、资产隔离、项目切换上下文。

### 涉及文件

```
python/fastapi_app/
├── routers/
│   └── projects.py              # 项目管理 API（替换 M1 中的空路由）
├── services/
│   └── project_service.py       # 项目业务逻辑
```

### 依赖

M1-03（数据库 CRUD）

### 验收标准

- [ ] `GET /api/v1/projects` 列出所有项目
- [ ] `GET /api/v1/projects/{id}` 项目详情（含关联的风格档案和资产统计）
- [ ] `POST /api/v1/projects` 创建项目（可指定默认风格）
- [ ] `PUT /api/v1/projects/{id}` 更新项目（名称、默认风格）
- [ ] `DELETE /api/v1/projects/{id}` 删除项目（级联删除资产和文件，需确认）

### 接口约定

```python
class CreateProjectRequest(BaseModel):
    name: str
    style_id: str | None = None

class ProjectDetailResponse(BaseModel):
    id: str
    name: str
    style: StyleProfile | None
    asset_count: int
    latest_asset_at: str | None
    created_at: str
    updated_at: str
```

---

## M4-03 | BE | 复现与变体生成

### 职责

实现基于历史生成记录的复现（相同参数重新生成）和变体（微调参数再生成）功能。变体支持修改描述、风格、尺寸、视角、参考图。

### 涉及文件

```
python/fastapi_app/
├── routers/
│   └── generation.py            # 补充复现/变体路由
```

### 依赖

M2-04（生成 API）、M1-03（数据库）

### 验收标准

- [ ] `POST /api/v1/generation/{id}/reproduce` 复现：读取原始 GenerationRecord 的所有参数，重新走一遍完整流程
- [ ] `POST /api/v1/generation/{id}/variant` 变体：继承原始参数，允许用户修改以下字段后重新生成
- [ ] 两次复现结果可能不完全相同（取决于 API 是否支持固定 seed），但风格应一致

### 接口约定

```python
class VariantRequest(BaseModel):
    prompt_override: str | None = None           # 覆盖描述文本
    style_id_override: str | None = None         # 切换风格
    target_size_override: tuple[int, int] | None = None  # 修改尺寸
    perspective_override: str | None = None      # 修改视角
    reference_image_path: str | None = None      # 替换参考图
    reference_style_description: str | None = None  # 替换参考图风格描述
    seed_override: str | None = None

# 两个接口返回类型与 POST /api/v1/generate 相同
# 未覆盖的字段从原始 GenerationRecord 继承
```

---

## M4-04 | FE | 风格库 UI

### 职责

实现风格管理界面，包含风格列表、创建/编辑、参考图上传（含风格提取反馈）。

### 涉及文件

```
src/
├── components/
│   ├── style/
│   │   ├── StyleLibrary.tsx      # 风格库主页面（模态或侧滑）
│   │   ├── StyleCard.tsx         # 风格卡片
│   │   ├── StyleEditor.tsx       # 风格创建/编辑表单
│   │   └── StylePreview.tsx      # 风格预览（展示该风格下的示例素材）
```

### 依赖

M1-06（React 项目）、M4-01（风格管理 API）

### 验收标准

- [ ] 风格库以模态或侧滑面板展示
- [ ] 预设风格和自定义风格分区展示，预设风格不可删除/编辑（但可复制为自定义后修改）
- [ ] 创建自定义风格表单：名称、画风（下拉）、尺寸、视角、色板（可选）、参考图上传
- [ ] 参考图上传后显示预览 + 自动提取的风格描述文本（只读展示，用户可了解系统如何理解该风格）
- [ ] 编辑已有自定义风格
- [ ] 删除自定义风格（确认弹窗）

### 接口约定

```typescript
interface StyleEditorProps {
  style?: StyleProfile;
  onSave: (style: CreateStyleRequest) => void;
  onCancel: () => void;
}

interface StyleCardProps {
  style: StyleProfile;
  isPreset: boolean;
  onEdit?: (id: string) => void;
  onDelete?: (id: string) => void;
  onDuplicate: (id: string) => void;
}
```

---

## M4-05 | FE | 项目管理 + 侧边栏完善

### 职责

实现侧边栏的项目列表、项目切换、风格入口、全局上下文切换。

### 涉及文件

```
src/
├── components/
│   ├── sidebar/
│   │   ├── Sidebar.tsx           # 完善侧边栏（替换 M1 骨架）
│   │   ├── ProjectList.tsx       # 项目列表
│   │   ├── ProjectCreateModal.tsx # 创建项目弹窗
│   │   └── StyleEntry.tsx        # 风格库入口按钮
```

### 依赖

M1-06（React 项目）、M4-02（项目管理 API）、M4-04（风格库 UI）

### 验收标准

- [ ] 侧边栏显示项目列表，点击切换当前项目
- [ ] 切换项目后所有页面数据跟随切换（通过 Zustand store 全局状态）
- [ ] 新建项目弹窗：输入项目名 + 选择默认风格
- [ ] 删除项目（确认弹窗，提示将删除关联资产）
- [ ] 风格库入口点击打开风格库面板
- [ ] 侧边栏底部显示设置入口
- [ ] 当前项目名称在侧边栏高亮
- [ ] 生成任务进行中时侧边栏显示进度角标

### 接口约定

```typescript
// 侧边栏状态扩展（追加到 Zustand store）
interface AppState {
  // ... M1 定义的状态
  projects: Project[];
  loadProjects(): Promise<void>;
  switchProject(id: string): void;
}
```
