# M5：产品化

> 里程碑目标：设置页完善、异常处理规范化、成本统计、快捷键、Electron 打包为可分发的安装包。

---

## M5-01 | BE | API 配置持久化与测试

### 职责

实现 API Key 的加密存储、连接测试接口、配置读写接口。

### 涉及文件

```
python/fastapi_app/
├── routers/
│   └── settings.py              # 设置 API
├── services/
│   └── config_service.py        # 配置管理（加密存储 API Key）
```

### 依赖

M1-02（FastAPI 服务）

### 验收标准

- [ ] `GET /api/v1/settings` 返回当前配置（API Key 脱敏显示）
- [ ] `PUT /api/v1/settings` 更新配置（API Key 加密后存入 config.json 或数据库）
- [ ] `POST /api/v1/settings/test-image-api` 测试图片 API 连接（发一次低参数调用，验证 Key 有效性）
- [ ] `POST /api/v1/settings/test-text-api` 测试文字 API 连接
- [ ] API Key 使用 AES 或系统 keyring 加密存储
- [ ] 测试结果包含：连接状态、余额信息（如 API 支持）、错误信息

### 接口约定

```python
class SettingsResponse(BaseModel):
    image_api_provider: str
    image_api_key_set: bool          # 只返回是否已设置，不返回明文
    image_api_model: str
    text_api_provider: str
    text_api_key_set: bool
    text_api_model: str
    default_style_id: str | None
    default_export_path: str

class UpdateSettingsRequest(BaseModel):
    image_api_provider: str | None = None
    image_api_key: str | None = None         # 明文传入，后端加密存储
    image_api_model: str | None = None
    text_api_provider: str | None = None
    text_api_key: str | None = None
    text_api_model: str | None = None
    default_style_id: str | None = None
    default_export_path: str | None = None

class ApiTestResponse(BaseModel):
    success: bool
    message: str                       # "连接成功" / "API Key 无效" / "网络超时"
    latency_ms: int | None = None
```

---

## M5-02 | BE | 成本统计

### 职责

实现 API 调用成本统计接口，聚合 GenerationRecord 中的 cost_estimate。

### 涉及文件

```
python/fastapi_app/
├── routers/
│   └── settings.py              # 补充成本统计路由
├── services/
│   └── cost_service.py          # 成本计算与聚合
```

### 依赖

M1-03（数据库，读取 GenerationRecord）

### 验收标准

- [ ] `GET /api/v1/settings/costs` 返回成本统计
- [ ] 支持按时间范围筛选（今日、本周、本月、全部）
- [ ] 支持按项目筛选
- [ ] 返回：总调用次数、总成本、图片 API 成本、文字 API 成本、日均成本

### 接口约定

```python
class CostStatsResponse(BaseModel):
    period: str                        # "today" / "week" / "month" / "all"
    total_calls: int
    total_cost_usd: float
    image_api_cost: float
    text_api_cost: float
    avg_daily_cost: float
    by_date: list[DailyCost]           # 按天明细（图表用）

class DailyCost(BaseModel):
    date: str                          # "2026-05-23"
    calls: int
    cost: float
```

---

## M5-03 | BE | 异常处理规范化

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
    message: str           # 人类可读的错误描述
    details: dict | None   # 额外上下文（如 API 返回的原始错误）

# HTTP 状态码约定：
# 400 - 参数无效
# 404 - 资源不存在
# 408 - 超时
# 429 - API 调用频率限制
# 500 - 内部错误
# 502 - 外部 API 调用失败

# 自定义异常
class NiuQIError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 500, details: dict | None = None): ...

class ApiKeyInvalidError(NiuQIError): ...      # 401
class ApiCallFailedError(NiuQIError): ...      # 502
class TimeoutError(NiuQIError): ...            # 408
class ResourceNotFoundError(NiuQIError): ...   # 404
class InvalidParamError(NiuQIError): ...       # 400
class StorageFullError(NiuQIError): ...        # 507
```

---

## M5-04 | FE | 设置页 UI

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
│   │   ├── DefaultParams.tsx     # 默认参数区
│   │   ├── StorageManager.tsx    # 存储管理区
│   │   └── CostStats.tsx         # 成本统计展示
```

### 依赖

M1-05（React 项目）、M5-01（设置 API）、M5-02（成本统计）

### 验收标准

- [ ] API 配置区：
  - 图片 API：供应商下拉（OpenAI / 其他）+ API Key 输入（密码模式）+ 模型下拉 + "测试连接"按钮
  - 文字 API：同上，独立配置
  - 测试连接后显示结果（成功/失败 + 延时）
- [ ] 默认参数区：默认风格下拉、默认导出路径选择
- [ ] 存储管理区：
  - 数据目录路径展示 + "打开目录"按钮
  - 占用空间显示
  - "清理缓存"按钮（确认弹窗）
- [ ] 成本统计区：
  - 时间范围切换（今日/本周/本月/全部）
  - 总调用次数、总成本、日均成本
  - 按天成本图表（简单柱状图或折线图）
- [ ] 所有保存操作有成功/失败提示

### 接口约定

```typescript
interface SettingsPageState {
  settings: SettingsResponse;
  costStats: CostStatsResponse | null;
  isTestingImage: boolean;
  isTestingText: boolean;
}
```

---

## M5-05 | FE | 快捷键与全局交互优化

### 职责

实现全局快捷键、优化交互细节。

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

M1-05（React 项目）

### 验收标准

- [ ] 快捷键：
  - `Enter`：生成页提交生成（焦点在输入框时）
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

## M5-06 | EL | Electron 打包与安装包

### 职责

配置 Electron Builder，将 Electron + 内嵌 Python 打包为可分发的安装包。

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

---

## M5-07 | FE + BE | 全流程集成测试

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
- [ ] 导出流程：选择资产 → 配置 Sprite Sheet 导出 → 输出 PNG + JSON → JSON 格式正确
- [ ] 风格流程：创建自定义风格 → 上传参考图 → 用该风格生成 → 风格一致性可接受
- [ ] 项目流程：创建项目 → 切换项目 → 资产隔离正确 → 删除项目清理干净
- [ ] 异常流程：无 API Key 时提示 → API 调用失败时重试 → 存储空间不足时警告
