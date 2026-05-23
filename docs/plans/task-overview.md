# NiuQI2D v1 任务拆分总览

## 文档索引

| 文件 | 说明 |
|------|------|
| [dev-handbook.md](dev-handbook.md) | **开发手册**（必读）— 项目结构、环境配置、编码规范、接口约定 |
| [task-01-project-scaffold.md](task-01-project-scaffold.md) | M1：项目脚手架、Electron 壳层、Python 服务、数据库初始化、文件上传 |
| [task-02-generation-core.md](task-02-generation-core.md) | M2：Prompt 优化器、素材生成 Engine、图像后处理管线、生成页 UI |
| [task-03-export-asset-lib.md](task-03-export-asset-lib.md) | M3：Sprite Sheet 拼接、导出打包、资产库页、导出页 UI |
| [task-04-style-project.md](task-04-style-project.md) | M4：风格管理、项目管理、复现/变体生成、侧边栏 |
| [task-05-polish.md](task-05-polish.md) | M5：设置页、成本统计、异常处理、快捷键、打包发布 |

## 角色分工

| 角色 | 缩写 | 职责范围 |
|------|------|---------|
| 前端开发 | **FE** | React 页面、组件、状态管理、与后端 API 对接 |
| 后端开发 | **BE** | Python FastAPI 服务、AI API 调用、图像处理、数据库操作 |
| Electron 开发 | **EL** | Electron 主进程、Python 子进程管理、打包配置、原生能力 |

## 任务依赖总图

```
M1 基础框架（EL + BE + FE 并行）
 │
 ├─ EL: Electron 项目初始化 ─────────────────┐
 │                                            │
 ├─ BE: Python FastAPI + 数据库 + 文件存储 ───┤
 │                                            │
 ├─ BE: 文件上传 API + 静态文件服务 ──────────┤
 │                                            │
 └─ FE: React 项目 + 布局 + 路由 ─────────────┤
                                              │
                                     M1 集成联调
                                              │
 ▼ ▼ ▼ ▼ ▼ ▼ ▼ ▼ ▼ ▼ ▼ ▼ ▼ ▼ ▼ ▼ ▼ ▼ ▼ ▼ ▼
M2 生成闭环（BE 先行，FE 跟进）
 │
 ├─ BE: Prompt Optimizer（含参考图视觉描述）──┐
 ├─ BE: 素材生成 Engine ─────────────────────┤
 ├─ BE: 后处理管线（含帧提取）───────────────┤──▶ BE 提供完整 API 后
 │                                            │
 ├─ FE: 生成页 UI ───────────────────────────┘──▶ FE 对接联调
 │
 ▼
M3 导出与资产库（BE + FE 并行）
 │
 ├─ BE: Sprite Sheet 拼接 + JSON 生成
 ├─ BE: 导出 API（含资产状态更新）
 ├─ FE: 资产库页 UI
 └─ FE: 导出页 UI
 │
 ▼
M4 风格与项目管理（BE + FE 并行）
 │
 ├─ BE: 风格 CRUD + 参考图处理（含视觉描述提取）
 ├─ BE: 项目管理 API + 复现/变体（支持修改风格参数）
 ├─ FE: 风格库 UI
 └─ FE: 项目管理 + 侧边栏
 │
 ▼
M5 产品化（全角色）
 │
 ├─ FE: 设置页 + 成本统计
 ├─ BE: 异常处理规范化 + API Key 存储（keyring）
 └─ EL: 打包配置 + 安装包（无自动更新，手动版本检查）
```

## 任务状态说明

每个任务包含以下字段：

| 字段 | 说明 |
|------|------|
| **ID** | 任务唯一标识，格式 `M{里程碑}-{序号}` |
| **角色** | FE / BE / EL |
| **名称** | 简短描述 |
| **职责** | 具体要做什么 |
| **涉及文件** | 需要创建或修改的文件路径（相对项目根目录） |
| **依赖** | 前置任务 ID |
| **验收标准** | 怎样算完成 |
| **接口约定** | 与其他任务的对接协议（API 签名、数据结构等） |

## 重要约定

所有开发人员在开始编码前必须阅读 [dev-handbook.md](dev-handbook.md)，其中包含：
- 项目结构和环境配置
- 前后端类型同步机制
- 图片处理规范（缩略图尺寸、缩放算法）
- CORS 与网络配置
- Python 进程管理（开发/生产模式）
- 日志规范
- Git 提交规范
