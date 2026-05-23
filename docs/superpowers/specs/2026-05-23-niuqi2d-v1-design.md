# NiuQI2D v1 设计文档

## 1. 产品概述

NiuQI2D 是一个面向游戏开发者的 2D 游戏素材生成桌面工具。用户通过输入文字描述和简单参数，即可生成可直接用于游戏开发的 2D 素材（透明 PNG、Sprite Sheet），并导出为 Unity/Godot/Cocos 等主流引擎可导入的通用格式。

### 1.1 产品形态

- **桌面应用**（Electron）
- **安装即用**，一个 .exe 安装包，无需额外配置环境

### 1.2 目标用户

先做通用版，面向所有游戏开发者（独立开发者、小团队、Game Jam 参赛者、教学原型用户），后续再细分。

### 1.3 AI 能力来源

调用商业 API：
- **图片生成：** OpenAI gpt-image-1 / DALL-E 3 等
- **Prompt 优化：** 调用文字 LLM（如 GPT-4o-mini）重写用户描述

### 1.4 V1 范围

| 维度 | V1 范围 | 后续扩展 |
|------|---------|---------|
| 素材类型 | 角色动画、地图 Tile | 道具图标、UI 元素、特效 |
| 风格支持 | 内置 3-5 种预设 + 参考图驱动 | 更多预设、风格微调 |
| 导出格式 | 通用 PNG + JSON | Unity/Godot/Cocos 原生格式 |
| 引擎集成 | 通用格式文件 | 引擎插件自动导入 |

---

## 2. 架构设计

### 2.1 三层架构

```
┌─────────────────────────────────────────────┐
│              Electron 主进程                  │
│  ┌───────────┐  ┌──────────┐  ┌──────────┐  │
│  │ 窗口管理   │  │ 文件系统  │  │ 自动更新  │  │
│  └───────────┘  └──────────┘  └──────────┘  │
│         │ IPC (Electron IPC)                 │
│         ▼                                    │
│  ┌───────────────────────────────────────┐   │
│  │         渲染进程 (React + TypeScript)  │   │
│  │  生成页 │ 资产库 │ 导出页 │ 设置页     │   │
│  └───────────────────────────────────────┘   │
│         │ HTTP (localhost)                    │
│         ▼                                    │
│  ┌───────────────────────────────────────┐   │
│  │         Python 子进程 (FastAPI)        │   │
│  │  AI API 调用 │ 图像后处理 │ 任务队列   │   │
│  │  Prompt 优化 │ 导出打包   │ 风格管理   │   │
│  └───────────────────────────────────────┘   │
│         │                                    │
│         ▼                                    │
│  ┌───────────────────────────────────────┐   │
│  │  本地存储 (SQLite + 文件系统)          │   │
│  │  - 项目/资产元数据 (SQLite)            │   │
│  │  - 生成图片 + 导出文件 (文件系统)      │   │
│  │  - 风格档案 (SQLite)                   │   │
│  └───────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

### 2.2 技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| UI 层 | Electron + React + TypeScript | Electron 渲染进程，Web 技术构建 UI |
| 核心层 | Python + FastAPI | Electron 启动时以子进程拉起，HTTP 通信 |
| 存储层 | SQLite + 本地文件系统 | 轻量、零配置、单文件数据库 |

### 2.3 进程通信

- Electron 主进程启动时拉起 Python 子进程（FastAPI 监听 localhost 随机端口）
- 渲染进程通过 HTTP 调用 Python 服务
- Electron 主进程管理 Python 子进程生命周期（启动、健康检查、关闭）

---

## 3. 功能模块

### 3.1 模块总览

```
用户输入描述 + 选择风格/参考图
       │
       ▼
  ② 风格管理 ──风格参数──┐
                         │
  ⑦ 项目管理 ──项目上下文─┤
                         ▼
                   ③ Prompt Optimizer
                         │
                    优化后的 Prompt
                         │
                         ▼
  ① 素材生成 Engine ──调用──▶ 图片 API
                         │
                      原始图片
                         │
                         ▼
                   ④ 后处理管线（条件式）
                         │
                    处理后的图片
                         │
                    ┌────┴────┐
                    ▼         ▼
              ⑤ 资产管理   ⑥ 导出打包
              (入库存储)   (PNG + JSON)
```

共 7 个模块：

| # | 模块 | 核心职责 |
|---|------|---------|
| ① | 素材生成 Engine | 接收优化后的 Prompt，调用图片生成 API，返回原始图片 |
| ② | 风格管理 | 管理风格预设、用户自定义风格、参考图、风格特征提取 |
| ③ | Prompt Optimizer | 调用文字 LLM，将用户描述 + 风格参数 + 素材类型模板重写为专业 Prompt |
| ④ | 图像后处理 | 条件式管线：去背景、裁切居中、尺寸标准化、Sprite Sheet 拼接、色板量化 |
| ⑤ | 资产管理 | 生成历史、分类浏览、标签收藏、批量选择、版本状态管理 |
| ⑥ | 导出打包 | 输出 PNG + JSON 元数据（含帧信息、锚点、尺寸） |
| ⑦ | 项目管理 | 创建项目、关联风格档案、隔离资产、保存生成参数 |

### 3.2 Prompt Optimizer（核心创新模块）

**问题：** 用户输入通常模糊简短（如"弓箭手"），直接传给图片 API 效果不稳定。

**方案：** 在调用图片 API 前，先调用文字 LLM 重写 Prompt。

**输入：**
- 用户原始文字描述
- 素材类型（角色动画 / Tile）
- 风格档案参数（画风、尺寸、视角等）
- 参考图特征描述（如有）

**处理：**
- System Prompt 定义为"游戏素材 Prompt 工程师"角色
- 根据素材类型注入对应 Prompt 模板：
  - 角色动画模板：注入姿势描述、方向、帧数、锚点居中、轮廓清晰等关键词
  - Tile 模板：注入无缝拼接、边缘规则、重复纹理、地形类型等关键词
- 结合风格参数注入画风描述词
- 感知当前 API 能力（如支持透明背景则加入 `transparent background`）
- 加入质量提升关键词

**输出：** 优化后的结构化图片生成 Prompt。

### 3.3 图像后处理（条件式管线）

根据 API 能力和素材类型条件执行后处理步骤：

```
原始图片
    │
    ▼
去背景（条件：API 不支持透明背景时才执行，用 rembg）
    │
    ▼
裁切 + 居中（始终执行）
    │
    ▼
尺寸标准化（始终执行，像素风用最近邻缩放）
    │
    ▼
Sprite Sheet 拼接（条件：素材类型为角色动画时执行）
    │
    ▼
色板量化（条件：风格为像素风时执行）
```

---

## 4. 数据模型

SQLite 存储，5 个核心实体：

### 4.1 Project（项目）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | |
| name | TEXT | 项目名称 |
| style_id | FK → StyleProfile | 项目默认风格 |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### 4.2 StyleProfile（风格档案）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | |
| name | TEXT | 风格名称，如"像素风-16x16" |
| art_style | ENUM | pixel / hand_drawn / cartoon / realistic / custom |
| color_palette | JSON (可选) | 色板数组 ["#2d1b00", ...] |
| reference_image_path | TEXT (可选) | 参考图本地路径 |
| default_size | JSON | {"w": 16, "h": 16} |
| perspective | ENUM | top_down / side_scroller / isometric |
| extra_params | JSON | 其他风格约束 |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### 4.3 Asset（资产）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | |
| project_id | FK → Project | 所属项目 |
| name | TEXT | 资产名称 |
| asset_type | ENUM | character / tile / prop / ui / effect |
| status | ENUM | draft / selected / exported / discarded |
| source_path | TEXT | 处理后的图片文件路径 |
| thumbnail_path | TEXT | 缩略图路径 |
| tags | JSON | 标签数组 ["弓箭手", "森林"] |
| created_at | DATETIME | |
| updated_at | DATETIME | |

### 4.4 GenerationRecord（生成记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | |
| asset_id | FK → Asset (可空) | 被选中才关联 Asset |
| user_prompt | TEXT | 用户原始输入 |
| optimized_prompt | TEXT | LLM 重写后的 Prompt |
| style_id | FK → StyleProfile | |
| asset_type | ENUM | |
| api_provider | TEXT | "openai" 等 |
| api_model | TEXT | "gpt-image-1" 等 |
| api_params | JSON | {"size": "1024x1024", "background": "transparent"} |
| seed | TEXT (可选) | 可复现种子 |
| reference_image_path | TEXT (可选) | |
| postprocess_log | JSON | 记录执行了哪些后处理步骤 |
| created_at | DATETIME | |

### 4.5 ExportRecord（导出记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID (PK) | |
| asset_ids | JSON | 导出的资产 ID 列表 |
| export_format | ENUM | png_single / spritesheet_png_json / tileset_png_json |
| export_path | TEXT | 导出文件路径 |
| metadata | JSON | 导出的 JSON 元数据内容快照 |
| file_size | INTEGER | |
| created_at | DATETIME | |

### 4.6 实体关系

- Project 1:N Asset
- Project 1:1 StyleProfile（项目级默认风格）
- StyleProfile 1:N GenerationRecord
- Asset 1:N GenerationRecord（一个资产可有多次生成尝试）
- Asset N:N ExportRecord（批量导出时多资产关联一条记录）

### 4.7 设计决策

- **GenerationRecord 独立于 Asset：** 用户可对同一描述生成多次挑选最佳，每次生成都是独立记录，被选中的才关联 Asset 入库
- **风格档案与项目解耦：** 风格是独立实体，多个项目可共用同一风格，生成时可临时覆盖项目默认风格
- **postprocess_log：** 记录实际执行了哪些后处理步骤，方便调试和复现

---

## 5. 导出格式规范

V1 输出通用格式（PNG + JSON），确保 Unity/Godot/Cocos 都能导入。

### 5.1 导出类型

| 导出类型 | 适用场景 | 输出文件 |
|---------|---------|---------|
| 单图 PNG | Tile 地块、单帧道具 | `{name}.png` |
| Sprite Sheet + JSON | 角色多帧动画 | `{name}_sheet.png` + `{name}_sheet.json` |
| Tileset + JSON | 地图 Tile 组 | `{name}_tiles.png` + `{name}_tiles.json` |

### 5.2 Sprite Sheet JSON 格式

```json
{
  "meta": {
    "app": "NiuQI2D",
    "version": "1.0.0",
    "image": "archer_sheet.png",
    "size": { "w": 192, "h": 64 },
    "format": "RGBA8888",
    "scale": 1
  },
  "frames": [
    {
      "filename": "archer_idle_down_0",
      "frame": { "x": 0, "y": 0, "w": 16, "h": 16 },
      "rotated": false,
      "trimmed": true,
      "spriteSourceSize": { "x": 2, "y": 1, "w": 16, "h": 16 },
      "sourceSize": { "w": 16, "h": 16 },
      "pivot": { "x": 0.5, "y": 0.5 }
    }
  ],
  "animations": {
    "idle_down":  { "frames": [0, 1, 2], "speed": 8 },
    "idle_up":    { "frames": [3, 4, 5], "speed": 8 },
    "idle_left":  { "frames": [6, 7, 8], "speed": 8 },
    "idle_right": { "frames": [9, 10, 11], "speed": 8 }
  },
  "generation": {
    "prompt": "优化后的 prompt",
    "style_id": "uuid",
    "seed": "abc123",
    "api_model": "gpt-image-1"
  }
}
```

**帧命名规范：** `{角色名}_{动作}_{方向}_{帧号}`

### 5.3 Tileset JSON 格式

```json
{
  "meta": {
    "app": "NiuQI2D",
    "version": "1.0.0",
    "image": "forest_tiles.png",
    "tile_size": { "w": 16, "h": 16 },
    "tile_count": 12,
    "columns": 4,
    "spacing": 0,
    "margin": 0
  },
  "tiles": [
    { "id": 0, "type": "grass_plain", "terrain": ["grass", "grass", "grass", "grass"] },
    { "id": 1, "type": "grass_dirt_nw", "terrain": ["dirt", "grass", "grass", "grass"] }
  ],
  "generation": {
    "prompt": "...",
    "style_id": "uuid",
    "seed": "abc123"
  }
}
```

### 5.4 通用性说明

| 引擎 | 导入方式 |
|------|---------|
| Unity | Sprite Sheet 模式导入，JSON 兼容 Texture2D Sprite slicing；pivot 字段对应 Unity Pivot |
| Godot | sprite_frames 资源可用脚本从 JSON 生成；animations 结构与 AnimatedSprite2D 对应 |
| Cocos Creator | frames 结构与 plist Atlas 格式类似，可写转换脚本 |
| 通用 | 任何引擎都可读取 PNG + 解析 JSON 得到帧信息 |

后续扩展时只需加导出适配层，将通用 JSON 转为特定引擎原生格式（Unity .meta、Godot .tres、Cocos .plist），数据本身不变。

---

## 6. 前端设计要求

### 6.1 应用结构

**布局模式：** 左侧固定侧边栏 + 右侧主内容区，单窗口桌面应用。

**侧边栏（常驻）：**
- 项目列表（创建 / 切换 / 删除项目）
- 风格库入口（浏览 / 管理风格预设和自定义风格）
- 设置入口（API 配置、默认参数、存储管理）

**主内容区（4 个页面）：**

| 页面 | 优先级 | 说明 |
|------|--------|------|
| 生成页 | P0 | 默认首页，打开即用 |
| 资产库 | P0 | 按项目分组的资产管理 |
| 导出页 | P0 | 资产导出配置与执行 |
| 设置页 | P1 | API 密钥、默认参数、存储 |

### 6.2 全局交互要求

| 项目 | 要求 |
|------|------|
| 项目上下文 | 全局关联一个"当前项目"，切换后所有页面数据跟随切换 |
| 风格上下文 | 当前项目有默认风格，生成页可临时覆盖，风格库独立管理 |
| 任务状态 | 生成任务为异步操作，需要全局进度指示（侧边栏角标或顶栏状态） |
| 响应范围 | 桌面固定窗口，最小宽度 1024px，无需考虑移动端 |
| 图片预览 | 所有图片预览需棋盘格透明背景显示 |
| 动画预览 | 角色类资产需支持动画帧序列播放预览 |

### 6.3 核心交互流程

**流程 1：生成素材（核心流程）**

1. 选择素材类型（角色动画 / Tile）
2. 输入文字描述（自由文本）
3. 设置参数（面板根据素材类型动态切换字段）：
   - 角色：风格、尺寸、视角、帧数、方向数、参考图（可选）
   - Tile：风格、尺寸、边缘规则、参考图（可选）
4. 选择生成模式：
   - "快速预览"：低成本，多候选（4-6 张）
   - "高质量"：完整参数，少量候选（2-3 张）
5. 查看候选结果（网格排列，点击放大，棋盘格底图）
6. 操作：选中一个 / 重新生成 / 生成变体 / 直接入库
7. 加入资产库（自动关联当前项目和风格）

**流程 2：管理资产**

1. 进入资产库页
2. 筛选/搜索（按类型、状态、标签、关键词）
3. 查看资产详情（图片预览、角色支持动画播放、生成参数只读展示）
4. 操作：复现（相同参数重新生成）/ 变体（微调再生成）/ 删除
5. 选择资产 → 进入导出流程

**流程 3：导出资产**

1. 选择资产（从资产库勾选，或从生成页直接跳转）
2. 选择导出类型（单图 PNG / Sprite Sheet + JSON / Tileset + JSON）
3. 配置导出选项：
   - Sprite Sheet：排列方式、间距、补边
   - Tileset：Tile 尺寸、列数、间距
4. 选择导出路径
5. 执行导出 → 输出 PNG + JSON

### 6.4 各页面 UI 组件要求

**生成页：**
- 素材类型选择器（卡片/标签式，选中态明确区分）
- 多行文本输入框
- 动态参数表单（根据素材类型切换字段组合）
- 参考图上传区（拖拽 + 点击上传，支持预览）
- 两个操作按钮（快速预览 / 高质量生成）
- 候选结果网格（2-6 列，选中态、放大查看）
- 候选操作栏（加入资产库 / 重试 / 变体）

**资产库页：**
- 筛选器组（类型下拉、状态下拉、标签筛选）
- 搜索框（实时搜索）
- 资产网格/列表切换视图
- 资产卡片（缩略图 + 名称 + 类型标签 + 状态标记）
- 批量选择工具栏（全选、批量导出、批量删除）
- 资产详情面板（侧滑或模态）：大图预览 + 动画播放控制 + 生成参数 + 操作按钮

**导出页：**
- 资产选择区（已选资产缩略图列表）
- 导出类型单选组
- 动态配置表单（根据导出类型切换）
- 路径选择器
- 导出按钮 + 进度条
- 导出历史列表（文件名、日期、大小、打开文件夹）

**设置页：**
- API 配置区（供应商下拉 + API Key 输入 + 连接测试按钮，图片和文字分别配置）
- 默认参数区（风格、尺寸下拉选择）
- 存储管理区（数据目录路径、占用空间显示、缓存清理、打开目录按钮）

### 6.5 视觉与体验要求

| 项目 | 要求 |
|------|------|
| 设计风格 | 工具型产品，专业但不沉重，偏向深色主题（游戏开发者偏好） |
| 图片展示 | 所有图片默认棋盘格底图（表示透明区域），游戏开发工具行业标准 |
| 状态反馈 | 生成中、处理中、导出中等异步操作需明确进度/加载状态 |
| 空状态 | 资产库为空、无生成历史等场景需引导性空状态设计 |
| 快捷键 | 生成页 Enter 提交、Esc 关闭弹窗等常用快捷键 |

---

## 7. API 能力与后处理策略

### 7.1 图片 API 能力评估

| API | 可控参数 | 限制 |
|-----|---------|------|
| OpenAI gpt-image-1 | 尺寸（1024x1024 等）、background=transparent、output_format=png | 无法控制具体像素尺寸，无法指定帧数/锚点/网格对齐 |
| DALL-E 3 | 尺寸、质量(standard/hd) | 无透明背景支持 |
| Stable Diffusion API | ControlNet、Inpaint、种子、步数、CFG | 需自部署或第三方服务 |

### 7.2 后处理策略

| 步骤 | 能否 API 替代 | V1 策略 |
|------|-------------|---------|
| 去背景 | gpt-image-1 可直接输出透明背景 | 优先走 API 参数，降级保留 rembg |
| 裁切/居中/对齐 | 不能 | 必须后处理 |
| Sprite Sheet 拼接 | 不能 | 必须后处理 |
| 帧间位置对齐 | 不能 | 必须后处理 |
| 色板量化 | Prompt 可引导但不精确 | 像素风场景需后处理量化 |

---

## 8. 里程碑规划

### Milestone 1: 基础框架

- Electron + React 项目搭建
- Python FastAPI 服务 + 子进程管理
- SQLite 数据模型 + 本地文件存储
- 基本页面路由和布局

### Milestone 2: 生成闭环

- Prompt Optimizer 模块（文字 LLM 调用）
- 素材生成 Engine（图片 API 调用）
- 图像后处理管线（去背景、裁切、缩放）
- 生成页 UI（输入、参数、候选结果展示）

### Milestone 3: 导出与资产库

- Sprite Sheet 拼接 + 帧对齐
- JSON 元数据生成
- 导出页 UI + 导出功能
- 资产库页 UI（列表、筛选、详情）

### Milestone 4: 风格与项目管理

- 风格档案 CRUD
- 参考图上传 + 风格特征注入
- 项目管理（创建、切换、风格绑定）
- 复现和变体生成功能

### Milestone 5: 产品化

- API Key 配置 + 连接测试
- 导出历史
- 快捷键
- 异常处理和错误提示优化

---

## 9. 风险与应对

| 风险 | 应对 |
|------|------|
| 风格不一致 | 项目级风格档案 + 参考图 + 色板锁定 + Prompt 模板 |
| 生成成本过高 | 快速预览模式（低成本多候选）+ 缓存复用 |
| 图片 API 输出不稳定 | Prompt Optimizer 优化 + 多候选 + 重试机制 |
| Sprite Sheet 帧不对齐 | 后处理帧对齐 + 锚点标准化 |
| 像素风质量差 | 色板量化后处理 + 最近邻缩放 + 专用 Prompt 模板 |
| Python 打包体积大 | 使用 python-embedded 精简包，只包含必需依赖 |
