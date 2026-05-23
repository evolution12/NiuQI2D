# NiuQI2D 编码约定

> 本文档供开发 agent 参考，确保多个 agent 产出风格一致的代码。

---

## 1. Python 后端约定

**框架：** FastAPI + SQLAlchemy + Pydantic

**命名风格：**
- 文件/目录：`snake_case`（如 `prompt_optimizer.py`、`postprocess/`）
- 类名：`PascalCase`（如 `PromptOptimizer`、`GenerationRecord`）
- 函数/变量：`snake_case`（如 `optimize_prompt`、`asset_type`）
- 常量：`UPPER_SNAKE_CASE`（如 `DEFAULT_THUMBNAIL_SIZE`）
- Pydantic schema：请求 `XxxRequest`，响应 `XxxResponse`

**路由文件模式：**
```python
# routers/xxx.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_session
from ..schemas import XxxCreateRequest, XxxResponse
from ..crud.xxx import XxxCRUD

router = APIRouter(prefix="/xxx", tags=["xxx"])

@router.get("", response_model=list[XxxResponse])
async def list_xxx(
    project_id: str,
    session: AsyncSession = Depends(get_session),
): ...

@router.post("", response_model=XxxResponse, status_code=201)
async def create_xxx(
    body: XxxCreateRequest,
    session: AsyncSession = Depends(get_session),
): ...
```

**Service 文件模式：**
```python
# services/xxx_service.py
class XxxService:
    def __init__(self, session: AsyncSession): ...

    async def do_something(self, ...) -> ResultType: ...
```

**异常处理：** 使用 `exceptions.py` 中的自定义异常，不要裸抛 `ValueError` 或 `HTTPException`。

**类型注解：** 所有函数必须写参数和返回值类型注解。用 `str | None` 而非 `Optional[str]`。

**异步：** 所有 IO 操作（数据库、文件、API 调用）使用 `async/await`。

---

## 2. React 前端约定

**框架：** React + TypeScript + Zustand

**命名风格：**
- 文件/目录：`PascalCase` 组件（如 `CandidateGrid.tsx`），`camelCase` 工具（如 `api.ts`）
- 组件名：`PascalCase`，与文件名一致
- 函数/变量：`camelCase`
- 类型/接口：`PascalCase`（如 `AssetType`、`GenerateParams`）
- store action：`verb + noun`（如 `setCurrentProject`、`loadProjects`）

**组件文件模式：**
```tsx
// components/generate/CandidateGrid.tsx
import { useState } from 'react';

interface CandidateGridProps {
  records: GenerationRecord[];
  onSelect: (id: string) => void;
}

export function CandidateGrid({ records, onSelect }: CandidateGridProps) {
  // hooks 在顶部
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // 事件处理函数
  const handleClick = (id: string) => { ... };

  // JSX 返回
  return (
    <div className="candidate-grid">
      {records.map(record => (
        <CandidateCard key={record.id} ... />
      ))}
    </div>
  );
}
```

**状态管理：** 全局状态用 Zustand，组件局部状态用 `useState`。不要用 Context 做全局状态。

**API 调用：** 统一通过 `services/api.ts` 的 `ApiClient`，不要直接用 `fetch`。

**样式：** CSS Modules 或 Tailwind（由前端设计师定），不使用 CSS-in-JS。

---

## 3. 前后端类型同步

**规则：以 `python/fastapi_app/schemas.py` 为单一数据源。**

- 每个 TypeScript 类型必须标注对应的 Pydantic 类名
- 后端修改 schema 后，同步修改前端 `types/index.ts`

```typescript
/** 对齐 schemas.py -> AssetResponse */
interface Asset {
  id: string;
  project_id: string;
  name: string;
  asset_type: AssetType;
  status: AssetStatus;
  // ...
}
```

**枚举值两端必须完全一致：**
```python
# Python
class AssetType(str, Enum):
    CHARACTER = "character"
    TILE = "tile"
```
```typescript
// TypeScript
type AssetType = "character" | "tile";
```

---

## 4. 图片处理约定

| 规则 | 说明 |
|------|------|
| 内部格式 | 统一 PNG (RGBA) |
| 像素风缩放 | `Image.NEAREST`（不做抗锯齿） |
| 其他风格缩放 | `Image.LANCZOS` |
| 缩略图尺寸 | character: 64×64, tile: 32×32, 其他: 128×128 |
| 前端图片预览 | 必须棋盘格底图 |

---

## 5. API 路径与错误格式

**路径：** 所有 API 加 `/api/v1` 前缀。资源名复数，动作用 HTTP Method。

**错误响应统一格式：**
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "资产 xxx 不存在",
    "details": null
  }
}
```

**自定义异常：** 定义在 `exceptions.py`，全局 handler 在 `main.py` 注册。不要直接返回 `HTTPException`。

---

## 6. 配置与模式区分

| 配置 | 开发模式 | 生产模式 |
|------|---------|---------|
| Python 路径 | `python/.venv/Scripts/python.exe` | `resources/python/python.exe` |
| CORS | 启用（`NIUQI2D_DEV=1`） | 不启用 |
| 静态文件 | `/images/` → data_dir + `/images` | 同左 |
| 日志 | 控制台 + 文件 | 仅文件 |

**生成模式区分：**
- 快速预览：`preview_image_model`（默认 dall-e-3），4-6 候选
- 高质量：`quality_image_model`（默认 gpt-image-1），2-3 候选
- 用户在设置页自定义模型，应用不提供任何内置 API 服务
