# M5：产品化

> 里程碑目标：设置页完善、异常处理规范化、成本统计、快捷键、Electron 打包为可分发的安装包。无自动更新，手动版本检查。

---

## M5-01 | BE | API 配置持久化与测试

### 职责

实现 API Key 的本地存储、连接测试接口、配置读写接口。API Key 使用本地配置文件存储（桌面应用场景，无远程传输风险）。

### 涉及文件

```
python/fastapi_app/
├── routers/
│   └── settings.py              # 设置 API
├── services/
│   └── config_service.py        # 配置管理（本地 JSON 文件存储）
```

### 依赖

M1-02（FastAPI 服务）

### 验收标准

- [ ] `GET /api/v1/settings` 返回当前配置（API Key 脱敏显示）
- [ ] `PUT /api/v1/settings` 更新配置（API Key 明文存入本地 `config.json`）
- [ ] `POST /api/v1/settings/test-image-api` 测试图片 API 连接
- [ ] `POST /api/v1/settings/test-text-api` 测试文字 API 连接
- [ ] 测试结果包含：连接状态、延迟、错误信息
- [ ] 配置存储在 `{data_dir}/config.json`，首次运行自动创建
- [ ] 支持配置每种生成模式使用的图片模型（preview_image_model、quality_image_model）

### 接口约定

```python
class SettingsResponse(BaseModel):
    image_api_provider: str
    image_api_key_set: bool          # 只返回是否已设置，不返回明文
    image_api_model: str
    text_api_provider: str
    text_api_key_set: bool
    text_api_model: str
    preview_image_model: str         # 快速预览模式使用的模型
    quality_image_model: str         # 高质量模式使用的模型
    default_style_id: str | None
    default_export_path: str

class UpdateSettingsRequest(BaseModel):
    image_api_provider: str | None = None
    image_api_key: str | None = None
    image_api_model: str | None = None
    text_api_provider: str | None = None
    text_api_key: str | None = None
    text_api_model: str | None = None
    preview_image_model: str | None = None
    quality_image_model: str | None = None
    default_style_id: str | None = None
    default_export_path: str | None = None

class ApiTestResponse(BaseModel):
    success: bool
    message: str                       # "连接成功" / "API Key 无效" / "网络超时"
    latency_ms: int | None = None
```

**API Key 存储策略：**

桌面应用本地场景，API Key 直接存入 `{data_dir}/config.json`。理由：
- 桌面应用数据目录仅当前用户可访问（操作系统级保护）
- 不涉及远程传输，无网络窃取风险
- 简单可靠，不依赖额外系统服务
- `config.json` 加入 `.gitignore`（虽然不在项目目录内，但养成习惯）

---

## M5-02 | BE | 异常处理规范化

### 职责

统一全部 API 的错误响应格式，增加全局异常处理中间件。

### 涉及文件

```
python/fastapi_app/
├── main.py                      # 添加全局异常 handler
├── exceptions.py                # 自定义异常类
├── schemas.py                   # 补充错误响应 schema
```

### 依赖

M1-02（FastAPI 服务）

### 验收标准

- [ ] 全部 API 错误使用统一的 JSON 格式
- [ ] 自定义异常类型覆盖：API 调用失败、超时、参数无效、资源不存在、存储空间不足
- [ ] 未预期异常返回 500 + 通用错误信息（不泄露内部细节）
- [ ] 错误信息包含 error code，前端可根据 code 展示不同提示

### 接口约定

```python
class ErrorResponse(BaseModel):
    error: ErrorDetail

class ErrorDetail(BaseModel):
    code: str              # "API_KEY_INVALID" / "TIMEOUT" / "RESOURCE_NOT_FOUND" / ...
    message: str
    details: dict | None

# 自定义异常
class NiuQIError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 500, details: dict | None = None): ...

class ApiKeyInvalidError(NiuQIError): ...      # 401
class ApiCallFailedError(NiuQIError): ...      # 502
class GenerationTimeoutError(NiuQIError): ...  # 408
class ResourceNotFoundError(NiuQIError): ...   # 404
class InvalidParamError(NiuQIError): ...       # 400
class StorageFullError(NiuQIError): ...        # 507
```

---

## M5-03 | FE | 设置页 UI

### 职责

实现设置页面的全部 UI 和交互。

### 涉及文件

```
src/
├── pages/
│   └── SettingsPage.tsx          # 设置页（替换 M1 占位符）
├── components/
│   ├── settings/
│   │   ├── ApiConfigSection.tsx  # API 配置区
│   │   ├── ModelSelector.tsx     # 生成模式模型选择（预览/高质量分别配置）
│   │   ├── DefaultParams.tsx     # 默认参数区
│   │   └── StorageManager.tsx    # 存储管理区
```

### 依赖

M1-06（React 项目）、M5-01（设置 API）

### 验收标准

- [ ] API 配置区：
  - 图片 API：供应商下拉（OpenAI / 其他）+ API Key 输入（密码模式）+ 模型下拉 + "测试连接"按钮
  - 文字 API：同上，独立配置
  - 测试连接后显示结果（成功/失败 + 延时）
- [ ] 生成模式模型选择：
  - 快速预览模式：模型下拉（如 dall-e-3）
  - 高质量模式：模型下拉（如 gpt-image-1）
  - 用户可自定义每种模式使用的模型
- [ ] 默认参数区：默认风格下拉、默认导出路径选择
- [ ] 存储管理区：
  - 数据目录路径展示 + "打开目录"按钮
  - 占用空间显示
  - "清理缓存"按钮（确认弹窗）
- [ ] 所有保存操作有成功/失败提示（Toast）

### 接口约定

```typescript
interface SettingsPageState {
  settings: SettingsResponse;
  isTestingImage: boolean;
  isTestingText: boolean;
}
```

---

## M5-04 | FE | 快捷键与全局交互优化

### 职责

实现全局快捷键、Toast 消息提示、确认弹窗组件。

### 涉及文件

```
src/
├── hooks/
│   └── useShortcuts.ts          # 快捷键 hook
├── components/
│   └── common/
│       ├── Toast.tsx             # 全局消息提示
│       └── ConfirmDialog.tsx     # 确认弹窗
```

### 依赖

M1-06（React 项目）

### 验收标准

- [ ] 快捷键：
  - `Enter`：生成页提交生成（焦点在输入框时，非 Shift+Enter）
  - `Escape`：关闭弹窗/模态
  - `Ctrl+N`：新建项目
  - `Ctrl+E`：导出选中资产
  - `Delete`：删除选中资产（确认弹窗）
- [ ] 全局 Toast 消息提示（成功/失败/警告）
- [ ] 统一的确认弹窗组件（用于删除操作、清理缓存等）
- [ ] 快捷键不与系统快捷键冲突

### 接口约定

```typescript
// Toast 使用示例
toast.success("资产已加入资产库");
toast.error("生成失败：" + error.message);
toast.warning("API Key 未配置");
```

---

## M5-05 | EL | Electron 打包与安装包

### 职责

配置 Electron Builder，将 Electron + 内嵌 Python 打包为可分发的安装包。无自动更新，设置页提供手动版本检查。

### 涉及文件

```
electron-builder.yml            # 打包配置（完善 M1 骨架）
scripts/
├── build-python.py             # 打包 Python 环境脚本
├── prebuild.js                 # 预构建脚本（下载/准备 Python 嵌入式包）
└── postinstall.js              # 安装后脚本
```

### 依赖

M1-01（Electron 初始化）、全部功能完成后

### 验收标准

- [ ] `npm run build` 输出 Windows 安装包（.exe）
- [ ] 安装包包含嵌入式 Python 环境 + 所有依赖
- [ ] 安装后首次启动自动初始化数据库和预设数据
- [ ] 应用图标、名称、版本号正确
- [ ] 卸载时提示是否保留用户数据
- [ ] 安装包体积合理（目标 < 300MB）

### 技术要点

**Python 嵌入式打包方案：**

1. 下载 Windows embeddable Python（python-3.11.x-embed-amd64.zip）
2. 解压到 `resources/python/` 目录
3. 安装依赖到 `resources/python/Lib/site-packages/`
4. 修改 `python311._pth` 文件，确保能找到 site-packages
5. Electron Builder 配置将 `resources/` 目录整体打包

**`electron-builder.yml` 关键配置：**

```yaml
appId: com.niuqi2d.app
productName: NiuQI2D
directories:
  output: dist
extraResources:
  - from: "resources/python"
    to: "python"
    filter:
      - "**/*"
win:
  target: nsis
  icon: assets/icon.ico
nsis:
  oneClick: false
  allowToChangeInstallationDirectory: true
  createDesktopShortcut: true
```

**版本检查（手动）：**

```typescript
// 前端设置页"检查更新"按钮
async function checkForUpdates(): Promise<void> {
  const currentVersion = window.electronAPI.app.getVersion();
  const response = await fetch("https://api.github.com/repos/{owner}/NiuQI2D/releases/latest");
  const latest = await response.json();
  if (semverCompare(latest.tag_name, currentVersion) > 0) {
    // 显示"有新版本可用"，提供下载链接
  } else {
    // 显示"已是最新版本"
  }
}
```

---

## M5-06 | FE + BE | 全流程集成测试

### 职责

端到端验证全部核心流程。

### 涉及文件

```
tests/
├── e2e/
│   ├── test_generation_flow.py     # 生成全流程
│   ├── test_export_flow.py         # 导出全流程
│   └── test_style_project_flow.py  # 风格与项目流程
```

### 依赖

M5 全部任务

### 验收标准

- [ ] 生成流程：输入描述 → 选择风格 → 快速预览 → 选中候选 → 出现在资产库
- [ ] 导出流程：选择资产 → 配置 Sprite Sheet 导出 → 输出 PNG + JSON → JSON 格式正确 → 资产状态变为 exported
- [ ] 风格流程：创建自定义风格 → 上传参考图 → 自动提取风格描述 → 用该风格生成 → 风格一致性可接受
- [ ] 项目流程：创建项目 → 切换项目 → 资产隔离正确 → 删除项目清理干净
- [ ] 异常流程：无 API Key 时提示 → API 调用失败时重试 → 存储空间不足时警告
