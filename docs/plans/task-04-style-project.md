# M4：风格管理与项目管理

> 里程碑目标：用户能创建/管理风格档案，上传参考图驱动风格，创建项目绑定风格，复现和变体生成。

---

## M4-01 | BE | 风格管理 API

### 职责

实现风格档案的 CRUD API，包含预设风格初始化、自定义风格创建、参考图上传。

### 涉及文件

```
python/fastapi_app/
├── routers/
│   └── styles.py                # 风格管理 API（替换 M1 中的空路由）
├── services/
│   └── style_service.py         # 风格业务逻辑
├── data/
│   └── preset_styles.json       # 内置预设风格定义
```

### 依赖

M1-03（数据库 CRUD）

### 验收标准

- [ ] `GET /api/v1/styles` 列出所有风格（预设 + 用户自定义）
- [ ] `GET /api/v1/styles/{id}` 单个风格详情
- [ ] `POST /api/v1/styles` 创建自定义风格
- [ ] `PUT /api/v1/styles/{id}` 更新风格参数
- [ ] `DELETE /api/v1/styles/{id}` 删除自定义风格（预设风格不可删除）
- [ ] `POST /api/v1/styles/{id}/reference` 上传参考图
- [ ] `DELETE /api/v1/styles/{id}/reference` 删除参考图
- [ ] 首次启动时自动初始化预设风格到数据库（如不存在）

### 接口约定

**`POST /api/v1/styles`**

```python
class CreateStyleRequest(BaseModel):
    name: str
    art_style: ArtStyle
    color_palette: list[str] | None = None       # ["#2d1b00", "#4a8c3f"]
    reference_image: UploadFile | None = None     # 参考图文件
    default_size: dict = {"w": 16, "h": 16}
    perspective: Perspective = Perspective.TOP_DOWN
    extra_params: dict | None = None
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

**`POST /api/v1/projects`**

```python
class CreateProjectRequest(BaseModel):
    name: str
    style_id: str | None = None   # 不传则使用全局默认风格

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

实现基于历史生成记录的复现（相同参数重新生成）和变体（微调参数再生成）功能。

### 涉及文件

```
python/fastapi_app/
├── routers/
│   └── generation.py            # 补充复现/变体路由
```

### 依赖

M2-04（生成 API）、M1-03（数据库）

### 验收标准

- [ ] `POST /api/v1/generation/{id}/reproduce` 复现：读取原始 GenerationRecord 的所有参数，重新走一遍完整流程（Prompt 优化 → 生成 → 后处理）
- [ ] `POST /api/v1/generation/{id}/variant` 变体：继承原始参数，允许用户修改描述文本后重新生成
- [ ] 两次复现结果可能不完全相同（取决于 API 是否支持固定 seed），但风格应一致

### 接口约定

```python
class VariantRequest(BaseModel):
    prompt_override: str | None = None   # 可选的描述覆盖
    seed_override: str | None = None     # 可选的种子覆盖

# 两个接口返回类型与 POST /api/v1/generate 相同
```

---

## M4-04 | FE | 风格库 UI

### 职责

实现风格管理界面，包含风格列表、创建/编辑、参考图上传。

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

M1-05（React 项目）、M4-01（风格管理 API）

### 验收标准

- [ ] 风格库以模态或侧滑面板展示
- [ ] 预设风格和自定义风格分区展示，预设风格不可删除/编辑（但可复制为自定义后修改）
- [ ] 创建自定义风格表单：名称、画风（下拉）、尺寸、视角、色板（可选）、参考图上传
- [ ] 参考图上传支持拖拽 + 预览
- [ ] 编辑已有自定义风格
- [ ] 删除自定义风格（确认弹窗）

### 接口约定

```typescript
interface StyleEditorProps {
  style?: StyleProfile;           // 不传则为创建模式
  onSave: (style: CreateStyleRequest) => void;
  onCancel: () => void;
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

M1-05（React 项目）、M4-02（项目管理 API）、M4-04（风格库 UI）

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
