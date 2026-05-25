# NiuQI2D

NiuQI2D 是一个面向 2D 游戏素材生产的本地工具原型，目标是把角色、Tile、道具、UI 和特效素材的生成、筛选、管理与导出串成一条可用流程。

项目当前由 React 前端和 FastAPI 后端组成。前端提供生成页、资产库、导出页和设置页；后端负责项目/风格/素材数据管理、图片上传、Prompt 优化、外部图像模型调用、后处理与导出。

## 演示视频

- 在线查看：[NiuQi2D 项目演示 demo](https://www.bilibili.com/video/BV1DGGo6yE1d?vd_source=1bc5876eae824c11d5eb50d62ee61eee)
- 文件名：`demo演示.mp4`
- 网盘链接：[https://pan.baidu.com/s/1E-lVSElJGVvVRuw9Lz4mUw?pwd=emnp](https://pan.baidu.com/s/1E-lVSElJGVvVRuw9Lz4mUw?pwd=emnp)
- 提取码：`emnp`

## 功能概览

- 素材生成：支持角色、Tile、道具、UI、特效等素材类型。
- 风格管理：内置预设风格，也支持自定义风格和参考图上传。
- 项目管理：按项目组织生成记录、素材库和导出历史。
- 资产库：筛选、搜索、预览、选择、批量删除和状态管理。
- 导出流程：支持单图 PNG、Sprite Sheet + JSON、Tileset + JSON。
- 设置页：配置图像模型、文本模型、API Key 和默认导出路径。
- 后端 API：统一 `/api/v1` 路径、统一错误结构和 `/images` 静态图片服务。

## 技术栈

- Frontend：React 19、TypeScript、Vite、React Router、Zustand
- Backend：Python 3.11+、FastAPI、SQLAlchemy、Pydantic、Pillow
- Storage：本地 SQLite 数据库和本地图片文件目录

## 目录结构

```text
.
├── frontend/              # React + Vite 前端
├── python/                # FastAPI 后端
│   └── fastapi_app/
├── tests/                 # 单元测试和端到端测试
├── docs/                  # 设计文档、接口文档和任务拆分
└── README.md
```

## 本地开发

### 1. 后端

```powershell
cd python
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:NIUQI2D_DEV = "1"
python -m fastapi_app
```

后端默认提供：

- 健康检查：`http://127.0.0.1:8000/health`
- API 前缀：`http://127.0.0.1:8000/api/v1`
- 图片资源：`http://127.0.0.1:8000/images/...`

### 2. 前端

```powershell
cd frontend
npm install
npm run dev
```

无 Electron 环境时，前端会默认连接 `http://127.0.0.1:8000/api/v1`。

## 常用命令

```powershell
# 前端构建
cd frontend
npm run build

# 前端 lint
cd frontend
npm run lint

# 后端测试
python -m unittest discover tests
```

## 配置说明

应用不内置任何外部 AI 服务密钥。请在设置页或后端配置中填写所需模型服务的 API Key。

支持的配置项包括：

- 图片生成服务商和模型
- 文本模型服务商和模型
- 预览生成模型
- 高质量生成模型
- 默认风格
- 默认导出路径

## API 文档

后端接口说明见 [docs/plans/backend-api.md](docs/plans/backend-api.md)。

开发约定见 [docs/plans/dev-handbook.md](docs/plans/dev-handbook.md)。

## 仓库清理约定

本仓库不提交本地运行数据、临时数据库、上传缓存和构建产物。相关规则已写入 `.gitignore`，包括：

- `.tmp-*/`
- `.tmp-*.png`
- `*.db`
- `frontend/dist-electron/`
