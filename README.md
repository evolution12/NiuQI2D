# NiuQI2D

AI 驱动的 2D 游戏美术素材生成器。通过文字描述快速生成像素风角色、瓦片、地图等 2D 游戏素材，支持自动去背景、裁剪、调色板量化等后处理，以及动画 Sprite Sheet 的生成与导出。

## 功能概览

- **素材生成** — 输入文字描述，通过 LLM 优化提示词后调用图像生成 API，产出可用的 2D 游戏素材
- **多种素材类型** — 支持角色（静态/动画 Sprite Sheet）、瓦片（Tile）、地图（Map）
- **高质量动画流程** — 先生成基础角色，选定后逐方向生成动画帧，最终合成完整 Sprite Sheet
- **本地后处理管线** — 自动去背景、裁剪居中、最近邻缩放、K-Means 色彩量化
- **素材库管理** — 项目化管理生成的素材，支持标签、筛选、批量操作
- **多格式导出** — PNG 单帧、Sprite Sheet（PNG + JSON 元数据）、Tileset（PNG + JSON）
- **风格系统** — 预设/自定义风格配置，支持参考图上传与 AI 风格分析
- **多 API 提供商** — 支持 OpenAI（GPT-Image-1 / DALL-E 3）、火山引擎、豆包

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 19, TypeScript, Vite 8, Zustand 5, react-router-dom 7 |
| 桌面端 | Electron 42, vite-plugin-electron |
| 后端 | Python 3.11+, FastAPI, SQLAlchemy 2 (async SQLite), Pydantic 2, Pillow |
| 打包 | electron-builder (NSIS), PyInstaller |

## 目录结构

```
├── electron/               # Electron 主进程 & preload
│   ├── main.ts             # 窗口管理、Python 子进程生命周期、IPC
│   ├── preload.ts          # contextBridge 暴露 electronAPI
│   └── pythonManager.ts    # Python 后端启动/健康检查/停止
├── frontend/               # React 前端
│   ├── src/
│   │   ├── pages/          # GeneratePage, AssetLibraryPage, ExportPage, SettingsPage
│   │   ├── components/     # generate/, asset/, export/, settings/, sidebar/, common/
│   │   ├── services/       # api.ts (HTTP 客户端)
│   │   ├── stores/         # Zustand 全局状态
│   │   └── types/          # TypeScript 类型定义
│   ├── package.json
│   └── vite.config.ts
├── python/                 # FastAPI 后端
│   ├── fastapi_app/
│   │   ├── routers/        # API 路由 (generation, assets, export, projects, styles, settings)
│   │   ├── services/       # 业务逻辑 (生成、导出、后处理、提示词优化)
│   │   ├── providers/      # 图像生成提供商 (OpenAI, 火山引擎, 豆包)
│   │   ├── postprocess/    # 后处理管线 (去背景、裁剪、缩放、量化)
│   │   ├── crud/           # 数据库 CRUD 层
│   │   └── data/           # 预设风格数据
│   ├── requirements.txt
│   └── build_exe.py        # PyInstaller 打包脚本
└── docs/                   # 设计文档 & 开发计划
```

## 环境要求

- **Node.js** >= 18
- **Python** >= 3.11
- **操作系统**: Windows（当前仅支持 Windows 打包）

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/evolution12/NiuQI2D.git
cd NiuQI2D
```

### 2. 安装前端依赖

```bash
cd frontend
npm install
```

### 3. 创建 Python 虚拟环境并安装依赖

```bash
cd ../python
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## 使用方法

### 纯 Web 开发模式（无 Electron）

分别启动后端和前端：

```bash
# 终端 1 — 启动后端 (在 python/ 目录下)
cd python
.venv\Scripts\python -m fastapi_app --host 127.0.0.1 --port 8000

# 终端 2 — 启动前端 (在 frontend/ 目录下)
cd frontend
npm run dev
```

浏览器访问 `http://localhost:5173`，前端会连接到 `localhost:8000` 的后端。

### Electron 桌面开发模式

一条命令启动 Electron + 后端：

```bash
cd frontend
npm run electron:dev
```

Electron 会自动分配随机端口启动 Python 后端，健康检查通过后打开窗口。

### 配置 API 密钥

首次运行后在 **设置页面** 配置：

- **图像 API** — 选择提供商（OpenAI / 火山引擎 / 豆包），填入 API Key，选择模型
- **文本 API** — 选择提供商（OpenAI / DeepSeek / 豆包），填入 API Key，用于提示词优化

## 打包发布

### 打包 Python 后端为 exe

```bash
cd python
pip install pyinstaller
python build_exe.py
```

输出: `python/dist/niuqi2d-backend.exe`

### 打包 Electron 安装包

确保 `python/dist/niuqi2d-backend.exe` 已存在，然后：

```bash
cd frontend
npm run electron:build
```

输出: `release/` 目录下的 NSIS 安装包（Windows x64）。

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

后端支持以下环境变量（可选，优先级高于配置文件）：

| 变量 | 说明 |
|---|---|
| `NIUQI2D_PORT` | 服务端口（默认 8000） |
| `NIUQI2D_HOST` | 监听地址（默认 127.0.0.1） |
| `NIUQI2D_DATA_DIR` | 数据存储目录 |
| `NIUQI2D_DEV` | 开发模式标志 |

## 许可证

MIT
