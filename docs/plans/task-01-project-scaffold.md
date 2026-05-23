# M1：项目脚手架与基础框架

> 里程碑目标：Electron 能启动，Python 服务能运行，数据库能读写，React 页面能渲染，三层能通信。

---

## M1-01 | EL | Electron 项目初始化

### 职责

搭建 Electron 主进程，配置窗口、IPC 通信桥、开发构建工具链。

### 涉及文件

```
electron/
├── main.ts                  # Electron 主进程入口
├── preload.ts               # preload 脚本，暴露安全 API 给渲染进程
├── python-manager.ts        # Python 子进程生命周期管理
└── ipc-handlers.ts          # 主进程 IPC handler 注册
package.json                  # 项目配置（Electron、构建脚本）
electron-builder.yml          # 打包配置
tsconfig.json                 # TypeScript 配置（主进程）
```

### 依赖

无

### 验收标准

- [ ] `npm run dev` 启动 Electron 窗口，显示空白页面
- [ ] 渲染进程可通过 `window.electronAPI` 调用主进程方法
- [ ] 窗口最小尺寸 1024×700，默认尺寸 1280×800
- [ ] 开发模式支持 hot reload

### 接口约定

**preload 暴露给渲染进程的 API（`window.electronAPI`）：**

```typescript
interface ElectronAPI {
  // Python 服务管理
  python: {
    getPort(): Promise<number>;         // 获取 Python 服务端口
    isReady(): Promise<boolean>;        // 检查 Python 服务是否就绪
  };
  // 文件系统（用于导出路径选择等）
  fs: {
    selectDirectory(): Promise<string | null>;  // 打开文件夹选择对话框
    selectFile(filters?: FileFilter[]): Promise<string | null>;
  };
  // 应用信息
  app: {
    getVersion(): string;
    getDataPath(): string;              // 应用数据目录
  };
}
```

**`python-manager.ts` 核心逻辑：**

- 启动时在 `resources/python/` 目录下找到 Python 可执行文件
- 拉起 `python -m fastapi_app` 子进程，监听 `--port {随机端口}`
- 通过轮询 `GET /health` 确认服务就绪
- 端口号写入环境变量，渲染进程通过 IPC 获取
- 应用关闭时发送 SIGTERM 并等待进程退出（超时后 kill）

---

## M1-02 | BE | Python FastAPI 服务初始化

### 职责

搭建 Python FastAPI 后端服务，定义目录结构、配置管理、健康检查接口。

### 涉及文件

```
python/
├── fastapi_app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口，挂载路由
│   ├── config.py            # 配置管理（从环境变量/配置文件读取）
│   ├── database.py          # SQLite 连接管理
│   ├── models.py            # SQLAlchemy ORM 模型定义
│   └── routers/
│       ├── __init__.py
│       ├── health.py         # GET /health 健康检查
│       ├── projects.py       # 项目管理路由（M4 实现）
│       ├── styles.py         # 风格管理路由（M4 实现）
│       ├── generation.py     # 素材生成路由（M2 实现）
│       ├── assets.py         # 资产管理路由（M3 实现）
│       └── export.py         # 导出路由（M3 实现）
├── requirements.txt          # Python 依赖
└── pyproject.toml
```

### 依赖

无

### 验收标准

- [ ] `python -m fastapi_app --port 8000` 能启动服务
- [ ] `GET /health` 返回 `{"status": "ok"}`
- [ ] 目录结构符合上方规范，路由文件已创建（可暂为空路由）
- [ ] 配置能从环境变量和 JSON 配置文件读取

### 接口约定

**配置结构（`config.py`）：**

```python
class Settings:
    # 服务
    host: str = "127.0.0.1"
    port: int = 8000

    # 数据存储
    data_dir: str = "~/.niuqi2d/data"         # 可通过环境变量覆盖
    db_path: str                               # = data_dir + "/niuqi2d.db"

    # API 配置（用户在设置页配置后持久化到数据库，这里提供默认值）
    image_api_provider: str = "openai"
    image_api_key: str = ""
    image_api_model: str = "gpt-image-1"
    text_api_provider: str = "openai"
    text_api_key: str = ""
    text_api_model: str = "gpt-4o-mini"
```

**API 路径前缀：** 所有路由统一加 `/api/v1` 前缀。

---

## M1-03 | BE | SQLite 数据模型与存储

### 职责

实现全部 5 个数据表的 ORM 模型、数据库迁移、基础 CRUD 操作。

### 涉及文件

```
python/fastapi_app/
├── models.py              # SQLAlchemy ORM 模型（5 张表）
├── database.py            # 数据库连接、初始化、会话管理
├── schemas.py             # Pydantic 请求/响应 schema
├── crud/
│   ├── __init__.py
│   ├── project.py         # Project CRUD
│   ├── style.py           # StyleProfile CRUD
│   ├── asset.py           # Asset CRUD
│   ├── generation.py      # GenerationRecord CRUD
│   └── export.py          # ExportRecord CRUD
```

### 依赖

M1-02（FastAPI 服务初始化）

### 验收标准

- [ ] 服务启动时自动创建 SQLite 文件和全部表（如不存在）
- [ ] 5 张表结构与设计文档 4.1-4.5 节完全一致
- [ ] 每个 CRUD 模块提供：创建、按 ID 查询、列表查询（分页）、更新、删除
- [ ] Pydantic schema 完整定义请求体和响应体
- [ ] 所有 ENUM 字段使用 Python Enum 类型

### 接口约定

**ORM 模型核心字段（参考设计文档第 4 节）：**

```python
# 枚举定义
class ArtStyle(str, Enum):
    PIXEL = "pixel"
    HAND_DRAWN = "hand_drawn"
    CARTOON = "cartoon"
    REALISTIC = "realistic"
    CUSTOM = "custom"

class Perspective(str, Enum):
    TOP_DOWN = "top_down"
    SIDE_SCROLLER = "side_scroller"
    ISOMETRIC = "isometric"

class AssetType(str, Enum):
    CHARACTER = "character"
    TILE = "tile"
    PROP = "prop"
    UI = "ui"
    EFFECT = "effect"

class AssetStatus(str, Enum):
    DRAFT = "draft"
    SELECTED = "selected"
    EXPORTED = "exported"
    DISCARDED = "discarded"

class ExportFormat(str, Enum):
    PNG_SINGLE = "png_single"
    SPRITESHEET_PNG_JSON = "spritesheet_png_json"
    TILESET_PNG_JSON = "tileset_png_json"
```

**数据库初始化策略：** 应用启动时检查 `db_path` 是否存在，不存在则创建全部表。不使用 Alembic 迁移工具，V1 直接 `create_all()`。

---

## M1-04 | BE | 文件存储管理

### 职责

实现本地文件存储模块，管理生成图片、缩略图、导出文件的读写和目录结构。

### 涉及文件

```
python/fastapi_app/
├── storage.py             # 文件存储管理器
```

### 依赖

M1-02（FastAPI 服务初始化）

### 验收标准

- [ ] 首次运行自动创建目录结构
- [ ] 提供保存图片、读取图片、生成缩略图的方法
- [ ] 提供清理缓存的方法（统计占用空间 + 删除指定目录内容）

### 接口约定

**目录结构：**

```
{data_dir}/
├── niuqi2d.db                           # SQLite 数据库
├── images/
│   ├── {project_id}/
│   │   ├── raw/                          # AI 生成的原始图片
│   │   │   └── {record_id}.png
│   │   ├── processed/                    # 后处理后的图片
│   │   │   └── {asset_id}.png
│   │   └── thumbnails/                   # 缩略图
│   │       └── {asset_id}_thumb.png
│   └── references/                       # 参考图
│       └── {style_id}.png
├── exports/                              # 导出文件
│   └── {project_id}/
│       └── {export_id}/
│           ├── *.png
│           └── *.json
└── config.json                           # 应用配置
```

**`storage.py` 核心接口：**

```python
class StorageManager:
    def __init__(self, data_dir: str): ...

    async def save_raw_image(self, project_id: str, record_id: str, image_data: bytes) -> str
    async def save_processed_image(self, project_id: str, asset_id: str, image_data: bytes) -> str
    async def save_reference_image(self, style_id: str, image_data: bytes) -> str
    async def get_image(self, path: str) -> bytes
    async def generate_thumbnail(self, image_path: str, size: tuple = (128, 128)) -> str
    async def get_storage_usage(self) -> dict  # {"total_mb": 128, "images_mb": 100, "exports_mb": 28}
    async def clear_cache(self, project_id: str = None) -> int  # 返回清理的 MB 数
```

---

## M1-05 | FE | React 项目初始化

### 职责

搭建 React 前端项目，配置路由、全局布局、状态管理、UI 组件库。

### 涉及文件

```
src/
├── main.tsx                   # React 入口
├── App.tsx                    # 根组件，路由配置
├── layouts/
│   └── MainLayout.tsx         # 全局布局（侧边栏 + 主内容区）
├── pages/
│   ├── GeneratePage.tsx       # 生成页（M2 实现）
│   ├── AssetLibraryPage.tsx   # 资产库页（M3 实现）
│   ├── ExportPage.tsx         # 导出页（M3 实现）
│   └── SettingsPage.tsx       # 设置页（M5 实现）
├── components/
│   ├── sidebar/
│   │   ├── Sidebar.tsx        # 侧边栏主组件
│   │   ├── ProjectList.tsx    # 项目列表（M4 实现）
│   │   └── StyleEntry.tsx     # 风格库入口
│   └── common/
│       ├── ImagePreview.tsx   # 图片预览组件（棋盘格底图）
│       ├── LoadingOverlay.tsx # 全局加载遮罩
│       └── EmptyState.tsx     # 空状态占位
├── stores/
│   └── appStore.ts            # Zustand 全局状态（当前项目、Python 服务状态等）
├── services/
│   └── api.ts                 # HTTP 客户端封装（调用 Python FastAPI）
├── types/
│   └── index.ts               # TypeScript 类型定义
├── styles/
│   └── globals.css            # 全局样式、CSS 变量（深色主题）
package.json
vite.config.ts
tsconfig.json
```

### 依赖

无

### 验收标准

- [ ] `npm run dev` 启动开发服务器，页面正常渲染
- [ ] 侧边栏 + 主内容区布局正确显示
- [ ] 4 个页面路由可切换（页面内容可为占位符）
- [ ] 深色主题 CSS 变量已定义
- [ ] `api.ts` 能通过 Electron preload 获取 Python 端口并发起 HTTP 请求
- [ ] Zustand store 包含基础状态结构

### 接口约定

**全局状态（Zustand store）：**

```typescript
interface AppState {
  // Python 服务状态
  pythonReady: boolean;
  pythonPort: number | null;

  // 当前项目上下文
  currentProject: Project | null;
  currentStyle: StyleProfile | null;

  // 全局任务状态（用于进度指示）
  activeTasks: TaskInfo[];

  // Actions
  setPythonReady(ready: boolean): void;
  setCurrentProject(project: Project | null): void;
  setCurrentStyle(style: StyleProfile | null): void;
  addTask(task: TaskInfo): void;
  removeTask(taskId: string): void;
}

interface TaskInfo {
  id: string;
  type: "generation" | "export" | "postprocess";
  status: "pending" | "running" | "completed" | "failed";
  progress?: number;  // 0-100
  message?: string;
}
```

**API 客户端（`services/api.ts`）：**

```typescript
class ApiClient {
  private baseUrl: string;

  constructor() {
    // 通过 window.electronAPI.python.getPort() 获取端口
    // baseUrl = `http://127.0.0.1:${port}/api/v1`
  }

  // 通用请求方法
  async get<T>(path: string): Promise<T>;
  async post<T>(path: string, body: unknown): Promise<T>;
  async delete(path: string): Promise<void>;
}
```

**TypeScript 类型定义（`types/index.ts`）：**

```typescript
// 与后端 Pydantic schema 对齐，参考设计文档第 4 节
interface Project { id: string; name: string; style_id: string; created_at: string; updated_at: string; }
interface StyleProfile { id: string; name: string; art_style: ArtStyle; ... }
interface Asset { id: string; project_id: string; name: string; asset_type: AssetType; status: AssetStatus; ... }
interface GenerationRecord { id: string; asset_id: string | null; user_prompt: string; optimized_prompt: string; ... }
interface ExportRecord { id: string; asset_ids: string[]; export_format: ExportFormat; ... }
```

---

## M1 集成联调

### 参与角色

EL + BE + FE

### 验收标准

- [ ] `npm run dev` 一条命令启动 Electron，自动拉起 Python 服务，React 页面正常显示
- [ ] React 页面能通过 `GET /health` 确认 Python 服务状态
- [ ] 侧边栏 + 内容区布局正确
- [ ] 4 个页面路由可切换
- [ ] 关闭窗口时 Python 进程正确退出
