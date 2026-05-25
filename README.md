# NiuQI2D

NiuQI2D 是一个面向 2D 游戏开发的 AI 美术素材生成工具。它把「文字描述 -> 提示词优化 -> 图像生成 -> 本地后处理 -> 素材管理 -> 游戏工程导出」串成一条完整工作流，适合独立游戏、Game Jam、教学原型和小团队快速制作像素角色、Tile、地图与 Sprite Sheet。

项目当前由 React/Vite 前端、Electron 桌面壳和 Python FastAPI 后端组成。Electron 开发模式会自动拉起 Python 服务；纯 Web 模式下也可以分别启动前后端进行调试。

## 主要功能

- **文本生成游戏素材**：输入中文或英文描述，后端会先用文本模型优化为适合生图模型的英文 Prompt。
- **素材类型**：支持角色、Tile、Map，并保留 Prop、UI、Effect 等资产类型扩展位。
- **角色动画流程**：支持静态角色和动画 Sprite Sheet；质量管线可先生成基础角色，再逐方向生成动画行并合成表格。
- **风格档案**：内置预设风格，支持自定义画风、色板、默认尺寸、视角和参考图。
- **参考图分析**：可上传参考图并生成风格描述，用于后续生成时保持视觉一致性。
- **本地后处理**：包含透明背景、居中裁切、最近邻缩放、K-Means 色彩量化、帧切分和图集拼接等能力。
- **素材库管理**：按项目管理资产，支持状态、标签、搜索、筛选、详情查看、批量删除和动画预览。
- **导出**：支持单张 PNG、Sprite Sheet PNG + JSON、Tileset PNG + JSON。
- **多模型提供商**：图片生成支持 OpenAI、火山引擎 Visual、豆包 Ark；文本优化支持 OpenAI、DeepSeek、豆包。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 前端 | React 19, TypeScript, Vite 8, Zustand, React Router |
| 桌面端 | Electron 42, vite-plugin-electron, electron-builder |
| 后端 | Python 3.11+, FastAPI, SQLAlchemy async, SQLite, Pydantic, Pillow |
| 图像生成 | OpenAI Images API, 火山引擎 Visual API, 豆包 Ark Images API |
| 打包 | PyInstaller, electron-builder NSIS |
| 测试 | unittest, FastAPI TestClient |

## 目录结构

```text
.
├── electron/                  # Electron 主进程、preload、Python 服务管理
│   ├── main.ts
│   ├── preload.ts
│   └── pythonManager.ts
├── frontend/                  # React 前端
│   ├── src/
│   │   ├── components/        # generate、asset、export、settings、sidebar、common
│   │   ├── hooks/             # 快捷键等 hooks
│   │   ├── layouts/           # 主布局
│   │   ├── pages/             # 生成、素材库、导出、设置
│   │   ├── services/          # API 客户端
│   │   ├── stores/            # Zustand 状态
│   │   └── types/             # 前端类型定义
│   ├── package.json
│   └── vite.config.ts
├── python/                    # FastAPI 后端
│   ├── fastapi_app/
│   │   ├── crud/              # 数据库访问层
│   │   ├── data/              # 内置预设风格
│   │   ├── postprocess/       # 图像后处理管线
│   │   ├── providers/         # 生图提供商适配
│   │   ├── routers/           # REST API
│   │   ├── services/          # 生成、导出、风格、配置等业务逻辑
│   │   └── templates/         # 不同素材类型的 Prompt 模板
│   ├── build_exe.py           # PyInstaller 打包入口
│   ├── pyproject.toml
│   └── requirements.txt
├── tests/                     # 单元测试和端到端后端流程测试
└── docs/                      # 需求拆解、API、执行计划和开发手册
```

## 环境要求

- Node.js 18 或更高版本
- Python 3.11 或更高版本
- Windows 开发环境优先；当前 Electron 安装包配置为 Windows x64 NSIS

## 快速开始

### 1. 安装前端依赖

```powershell
cd frontend
npm install
```

### 2. 安装后端依赖

```powershell
cd python
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Electron 开发模式默认查找 `python/.venv/Scripts/python.exe`，建议保留这个虚拟环境路径。

### 3. 配置 API Key

首次启动后可以在设置页填写配置；也可以通过环境变量预先注入。配置文件默认保存在：

```text
~/.niuqi2d/data/config.json
```

Electron 打包版本会把数据目录切到应用的 `userData` 路径。

## 启动开发环境

### 方式一：Electron 桌面开发模式

```powershell
cd frontend
npm run electron:dev
```

该命令会启动 Vite、构建 Electron 主进程，并由 Electron 自动寻找空闲端口启动 Python FastAPI 服务。前端通过 preload 暴露的端口连接后端。

### 方式二：纯 Web 调试模式

分别启动后端和前端：

```powershell
cd python
.\.venv\Scripts\activate
python -m fastapi_app --host 127.0.0.1 --port 8000
```

```powershell
cd frontend
npm run dev
```

浏览器打开 `http://localhost:5173`。非 Electron 环境下，前端默认请求 `http://127.0.0.1:8000/api/v1`。

## 常用命令

```powershell
# 前端开发
cd frontend
npm run dev

# Electron 开发
cd frontend
npm run electron:dev

# 前端类型检查与构建
cd frontend
npm run build

# 前端 lint
cd frontend
npm run lint

# 后端测试
python -m unittest discover -s tests
```

## 配置项

后端配置来源优先级为：环境变量 > `config.json` > 默认值。

| 环境变量 | 说明 |
| --- | --- |
| `NIUQI2D_HOST` | 后端监听地址，默认 `127.0.0.1` |
| `NIUQI2D_PORT` | 后端端口，默认 `8000` |
| `NIUQI2D_DATA_DIR` | 数据目录，默认 `~/.niuqi2d/data` |
| `NIUQI2D_DB_PATH` | SQLite 数据库路径，默认在数据目录下 |
| `NIUQI2D_IMAGE_API_PROVIDER` | 图片生成提供商：`openai`、`volcengine`、`doubao` |
| `NIUQI2D_IMAGE_API_KEY` | OpenAI 图片 API Key |
| `NIUQI2D_IMAGE_API_MODEL` | OpenAI 图片模型，默认 `gpt-image-1` |
| `NIUQI2D_TEXT_API_PROVIDER` | 文本优化提供商：`openai`、`deepseek`、`doubao` |
| `NIUQI2D_TEXT_API_KEY` | 文本优化 API Key |
| `NIUQI2D_TEXT_API_MODEL` | 文本优化模型，默认 `gpt-4o-mini` |
| `NIUQI2D_PREVIEW_IMAGE_MODEL` | 预览模式使用的图片模型 |
| `NIUQI2D_QUALITY_IMAGE_MODEL` | 质量模式使用的图片模型 |
| `NIUQI2D_VOLCENGINE_AK` | 火山引擎 Access Key |
| `NIUQI2D_VOLCENGINE_SK` | 火山引擎 Secret Key |
| `NIUQI2D_VOLCENGINE_REQ_KEY` | 火山引擎 Visual `req_key` |
| `NIUQI2D_DOUBAO_API_KEY` | 豆包 Ark API Key |
| `NIUQI2D_DOUBAO_MODEL` | 豆包图片模型 |
| `NIUQI2D_DEFAULT_STYLE_ID` | 默认风格 ID |
| `NIUQI2D_DEFAULT_EXPORT_PATH` | 默认导出目录 |
| `NIUQI2D_DEV` | 设为 `1` 时启用开发日志和开发 CORS 配置 |

## 核心工作流

1. **创建项目**：项目记录默认风格，并关联资产、生成历史和导出历史。
2. **选择或创建风格**：风格包含画风、色板、默认尺寸、视角和额外参数。
3. **输入描述并生成**：前端提交素材类型、尺寸、动作、方向数、帧数、参考图等参数。
4. **提示词优化**：后端根据素材类型套用模板，并调用文本模型生成英文 Prompt。
5. **调用图片模型**：根据设置选择 OpenAI、火山引擎或豆包生成图片。
6. **后处理**：根据素材类型执行去背景、裁切、缩放、量化、帧提取、Sprite Sheet 合成等处理。
7. **选择入库**：用户从候选结果中选择资产，写入素材库。
8. **导出**：按目标格式输出 PNG、Sprite Sheet 或 Tileset，并记录导出历史。

## API 概览

后端健康检查不带版本前缀：

```text
GET /health
```

业务 API 默认前缀为 `/api/v1`：

| 模块 | 主要接口 |
| --- | --- |
| 上传 | `POST /upload` |
| 项目 | `GET/POST /projects`, `GET/PUT/DELETE /projects/{id}` |
| 风格 | `GET/POST /styles`, `GET/PUT/DELETE /styles/{id}`, `POST /styles/{id}/reference` |
| 生成 | `POST /generate`, `POST /generate/preview`, `GET /generation`, `POST /generation/{id}/select` |
| 高质量角色管线 | `POST /generate/quality-pipeline/base`, `POST /generate/quality-pipeline/directions` |
| 素材库 | `GET /assets`, `GET/PUT/DELETE /assets/{id}`, `POST /assets/batch-delete`, `GET /assets/{id}/animation` |
| 标签 | `GET /tags` |
| 导出 | `POST /export`, `GET /export/history`, `GET/DELETE /export/{id}` |
| 设置 | `GET/PUT /settings`, `POST /settings/test-image-api`, `POST /settings/test-text-api` |

完整字段定义可参考 `python/fastapi_app/schemas.py` 和 `frontend/src/types/index.ts`。

## 数据与文件

默认数据目录为 `~/.niuqi2d/data`，主要包含：

```text
config.json          # API Key、默认模型、默认导出目录等配置
niuqi2d.db           # SQLite 数据库
images/              # 生成图、缩略图、上传参考图等静态资源
logs/app.log         # 后端滚动日志
```

后端会把 `images/` 挂载到 `/images`，前端通过该路径加载生成结果和缩略图。

## 打包

### 1. 打包 Python 后端

```powershell
cd python
.\.venv\Scripts\activate
pip install pyinstaller
python build_exe.py
```

输出文件：

```text
python/dist/niuqi2d-backend.exe
```

### 2. 打包 Electron 安装包

```powershell
cd frontend
npm run electron:build
```

`electron-builder` 会把 `python/dist/niuqi2d-backend.exe` 作为额外资源放入安装包。Windows 安装包输出到：

```text
release/
```

## 测试

当前测试覆盖了 Prompt 优化、风格选项压缩、动画预览处理和一次完整的后端生成-选择-导出流程。运行：

```powershell
python -m unittest discover -s tests
```

- **`NiuQI2D Setup x.x.x.exe`** — NSIS 安装程序，分发给用户使用
- **`win-unpacked/`** — 免安装绿色版，可直接运行

## 打包常见问题

### npm install 网络超时（ECONNRESET）

国内网络不稳定时可能失败，使用淘宝镜像：

```bash
npm install --registry=https://registry.npmmirror.com
```

### electron-builder 下载 Electron 二进制包超时

从 GitHub 下载 Electron 时网络不通，设置镜像：

```powershell
# PowerShell
$env:ELECTRON_MIRROR="https://npmmirror.com/mirrors/electron/"
```

```bash
# CMD
set ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/
```

### electron-builder 下载 NSIS 等构建工具超时

打包最后阶段需要下载 NSIS、winCodeSign 等工具，同样需要设置镜像：

```powershell
# PowerShell
$env:ELECTRON_BUILDER_BINARIES_MIRROR="https://registry.npmmirror.com/-/binary/electron-builder-binaries/"
```

备选镜像：

```powershell
# 华为云
$env:ELECTRON_BUILDER_BINARIES_MIRROR="https://mirrors.huaweicloud.com/electron-builder-binaries/"
# 清华
$env:ELECTRON_BUILDER_BINARIES_MIRROR="https://mirrors.tuna.tsinghua.edu.cn/electron-builder-binaries/"
```

### 完整打包命令（含镜像设置）

```powershell
# PowerShell — 一次性设置所有镜像
$env:ELECTRON_MIRROR="https://npmmirror.com/mirrors/electron/"
$env:ELECTRON_BUILDER_BINARIES_MIRROR="https://registry.npmmirror.com/-/binary/electron-builder-binaries/"
npm run electron:build
```

### PyInstaller 未安装

后端打包报 `No module named PyInstaller`，在虚拟环境中安装：

```bash
cd python
.venv\Scripts\activate
pip install pyinstaller
python build_exe.py
```

### release 目录被占用，打包失败

`remove app.asar: The process cannot access the file` — 上次打包的文件被锁定。关闭所有可能占用的进程（资源管理器、终端、IDE）后删除 `release` 目录重试：

```powershell
Remove-Item -Recurse -Force E:\Code\NiuQI2D\release
Remove-Item -Recurse -Force E:\Code\NiuQI2D\frontend\dist-electron
npm run electron:build
```

## 环境变量

## 参考文档

- `docs/TASK_BREAKDOWN.md`：产品目标、功能拆解和风险分析
- `docs/plans/backend-api.md`：后端 API 设计
- `docs/plans/dev-handbook.md`：开发手册
- `docs/plans/task-execution-order.md`：任务执行顺序
- `frontend/frontend-integration-checklist.md`：前端集成检查清单

## License

MIT
