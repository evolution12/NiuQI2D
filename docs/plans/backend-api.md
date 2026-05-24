# NiuQI2D 后端接口文档

> 面向前端开发使用。本文档基于当前 FastAPI 实现整理，并已通过 TestClient 端到端验收脚本与真实服务启动 smoke test 验证。

## 1. 基础信息

### 1.1 服务地址

Electron 开发模式下，前端应通过 `window.electronAPI.python.getPort()` 获取 Python 服务端口。

```ts
const port = await window.electronAPI.python.getPort();
const baseUrl = `http://127.0.0.1:${port}/api/v1`;
```

健康检查不带 `/api/v1` 前缀：

```http
GET /health
```

图片静态资源不带 `/api/v1` 前缀：

```http
GET /images/{relative_path}
```

### 1.2 通用约定

- 请求和响应均使用 JSON，上传接口除外。
- 时间字段为 ISO datetime 字符串。
- 图片路径字段通常返回相对路径，例如 `project_id/raw/xxx.png`。
- 前端展示图片时需要拼接为 `/images/{path}`。
- 所有业务 API 路径均以 `/api/v1` 开头。
- 所有错误响应使用统一结构。

### 1.3 错误格式

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "资源不存在",
    "details": null
  }
}
```

常见错误：

| code | 含义 |
|---|---|
| `INVALID_PARAM` | 请求参数无效 |
| `RESOURCE_NOT_FOUND` | 资源不存在 |
| `API_KEY_INVALID` | API Key 无效 |
| `API_CALL_FAILED` | 外部 API 调用失败 |
| `GENERATION_TIMEOUT` | 生成超时 |
| `STORAGE_FULL` | 存储空间不足 |
| `INTERNAL_ERROR` | 未预期服务端错误 |

## 2. 枚举

```ts
type ArtStyle = "pixel" | "hand_drawn" | "cartoon" | "realistic" | "custom";
type Perspective = "top_down" | "side_scroller" | "isometric";
type AssetType = "character" | "tile" | "prop" | "ui" | "effect";
type AssetSubtype = "static_image" | "animated_spritesheet";
type AssetStatus = "draft" | "selected" | "exported" | "discarded";
type ExportFormat = "png_single" | "spritesheet_png_json" | "tileset_png_json";
type GenerationMode = "preview" | "quality";
```

角色素材必须传 `asset_subtype`；非角色素材不要传 `asset_subtype`。

## 3. 健康检查

### GET `/health`

用于 Electron 判断 Python 服务是否就绪。

响应：

```json
{
  "status": "ok"
}
```

## 4. 设置接口

### GET `/api/v1/settings`

读取当前配置。API Key 不返回明文，只返回是否已设置。

响应：

```json
{
  "image_api_provider": "openai",
  "image_api_key_set": false,
  "image_api_model": "gpt-image-1",
  "text_api_provider": "openai",
  "text_api_key_set": false,
  "text_api_model": "gpt-4o-mini",
  "preview_image_model": "dall-e-3",
  "quality_image_model": "gpt-image-1",
  "volcengine_access_key_set": false,
  "volcengine_req_key": "high_aes_general_v21",
  "doubao_api_key_set": false,
  "doubao_model": "doubao-seedream-4-5-251128",
  "default_style_id": null,
  "default_export_path": ""
}
```

### PUT `/api/v1/settings`

更新配置。只传需要修改的字段。

请求：

```json
{
  "image_api_provider": "openai",
  "image_api_key": "sk-...",
  "image_api_model": "gpt-image-1",
  "text_api_provider": "openai",
  "text_api_key": "sk-...",
  "text_api_model": "gpt-4o-mini",
  "preview_image_model": "dall-e-3",
  "quality_image_model": "gpt-image-1",
  "default_style_id": null,
  "default_export_path": "D:/Exports"
}
```

响应：同 `GET /settings`。

### POST `/api/v1/settings/test-image-api`

测试当前已保存的图片 API 配置。

请求体：无。

响应：

```json
{
  "success": false,
  "message": "API Key 未配置",
  "latency_ms": 0
}
```

### POST `/api/v1/settings/test-text-api`

测试当前已保存的文本 API 配置。

请求体：无。

响应结构同上。

## 5. 风格接口

### GET `/api/v1/styles`

查询风格列表。

Query：

| 参数 | 类型 | 默认 | 说明 |
|---|---:|---:|---|
| `include_presets` | boolean | `true` | 是否包含内置风格 |
| `page` | number | `1` | 页码 |
| `page_size` | number | `100` | 每页数量，最大 100 |

响应：

```json
[
  {
    "id": "uuid",
    "name": "像素风 16x16",
    "art_style": "pixel",
    "color_palette": null,
    "reference_image_path": null,
    "default_size": { "w": 16, "h": 16 },
    "perspective": "top_down",
    "extra_params": { "color_count": 16, "outline": true },
    "is_preset": true,
    "created_at": "2026-05-24T10:00:00",
    "updated_at": "2026-05-24T10:00:00"
  }
]
```

### POST `/api/v1/styles`

创建自定义风格。

请求：

```json
{
  "name": "Pixel Test",
  "art_style": "pixel",
  "color_palette": ["#000000", "#ffffff"],
  "reference_image_path": null,
  "default_size": { "w": 16, "h": 16 },
  "perspective": "top_down",
  "extra_params": { "color_count": 16, "outline": true }
}
```

响应：`StyleProfileResponse`，状态码 `201`。

### GET `/api/v1/styles/{style_id}`

查询单个风格。

### PUT `/api/v1/styles/{style_id}`

整体更新风格。字段都是可选，行为与 PATCH 接近。

### PATCH `/api/v1/styles/{style_id}`

局部更新风格。

请求示例：

```json
{
  "name": "Pixel 32",
  "extra_params": { "color_count": 32, "outline": true }
}
```

### DELETE `/api/v1/styles/{style_id}`

删除自定义风格。预设风格不可删除。

成功状态码：`204`。

### POST `/api/v1/styles/{style_id}/reference`

上传参考图并提取风格描述。

Content-Type：`multipart/form-data`

字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `file` | file | png/jpg/webp 图片 |

响应：

```json
{
  "reference_image_path": "references/style-id.png",
  "style_description": "pixel art, limited palette, clean silhouette"
}
```

### DELETE `/api/v1/styles/{style_id}/reference`

删除参考图和风格描述。

成功状态码：`204`。

## 6. 项目接口

### GET `/api/v1/projects`

查询项目列表。

Query：

| 参数 | 类型 | 默认 |
|---|---:|---:|
| `page` | number | `1` |
| `page_size` | number | `100` |

响应：

```json
[
  {
    "id": "uuid",
    "name": "My Project",
    "style_id": "style-uuid",
    "style": null,
    "asset_count": 0,
    "latest_asset_at": null,
    "created_at": "2026-05-24T10:00:00",
    "updated_at": "2026-05-24T10:00:00"
  }
]
```

### POST `/api/v1/projects`

创建项目。

请求：

```json
{
  "name": "My Project",
  "style_id": "style-uuid"
}
```

响应：`ProjectResponse`，状态码 `201`。

### GET `/api/v1/projects/{project_id}`

查询项目详情，包含风格和资产统计。

### PUT `/api/v1/projects/{project_id}`

更新项目。

请求：

```json
{
  "name": "New Name",
  "style_id": "style-uuid"
}
```

### PATCH `/api/v1/projects/{project_id}`

局部更新项目。

### DELETE `/api/v1/projects/{project_id}`

删除项目，同时清理该项目缓存文件。

成功状态码：`204`。

## 7. 上传接口

### POST `/api/v1/upload`

通用图片上传接口。

Content-Type：`multipart/form-data`

字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `file` | file | 是 | png/jpg/jpeg/webp，最大 10MB |
| `purpose` | string | 是 | `reference` 或 `raw_image` |
| `project_id` | string | 条件 | `purpose=raw_image` 时必填 |
| `style_id` | string | 条件 | `purpose=reference` 时必填 |

响应：

```json
{
  "path": "project-id/raw/file.png",
  "url": "/images/project-id/raw/file.png",
  "filename": "file.png",
  "size": 1024,
  "content_type": "image/png"
}
```

## 8. 生成接口

### POST `/api/v1/generate/preview`

快速预览生成。后端会强制使用 `preview` 模式。

### POST `/api/v1/generate`

高质量生成。若 `preview_mode=true`，内部仍会按 preview 模式处理；正常前端建议高质量按钮使用此接口并传 `preview_mode=false`。

请求：

```json
{
  "project_id": "project-uuid",
  "user_prompt": "blue idle hero",
  "asset_type": "character",
  "asset_subtype": "static_image",
  "style_id": "style-uuid",
  "reference_image_path": null,
  "reference_style_description": null,
  "direction_count": 4,
  "frame_count": 3,
  "actions": ["idle", "walk"],
  "target_size": [16, 16],
  "preview_mode": false,
  "transparent_background": true,
  "candidate_count": 2,
  "seed": null
}
```

Tile 请求示例：

```json
{
  "project_id": "project-uuid",
  "user_prompt": "grass ground tile",
  "asset_type": "tile",
  "style_id": "style-uuid",
  "target_size": [16, 16],
  "candidate_count": 1
}
```

响应：

```json
{
  "records": [
    {
      "id": "record-uuid",
      "project_id": "project-uuid",
      "asset_id": null,
      "image_url": "/images/project-id/raw/record.png",
      "user_prompt": "blue idle hero",
      "optimized_prompt": "optimized prompt...",
      "style_id": "style-uuid",
      "asset_type": "character",
      "asset_subtype": "static_image",
      "api_provider": "openai",
      "api_model": "gpt-image-1",
      "api_params": {
        "image_url": "/images/project-id/raw/record.png",
        "raw_image_path": "project-id/raw/record.png",
        "project_id": "project-uuid",
        "target_size": { "w": 16, "h": 16 }
      },
      "seed": null,
      "reference_image_path": null,
      "postprocess_log": [],
      "created_at": "2026-05-24T10:00:00"
    }
  ],
  "optimized_prompt": "optimized prompt...",
  "mode": "quality"
}
```

### GET `/api/v1/generation`

查询生成记录列表。

Query：

| 参数 | 类型 | 默认 |
|---|---:|---:|
| `project_id` | string | 可选 |
| `page` | number | `1` |
| `page_size` | number | `20` |

响应：`GenerationCandidateResponse[]`。

### GET `/api/v1/generation/{record_id}`

查询单条生成记录。

### POST `/api/v1/generation/{record_id}/select`

将生成候选加入资产库。

请求：

```json
{
  "name": "blue hero",
  "tags": ["hero", "test"]
}
```

响应：

```json
{
  "asset": {
    "id": "asset-uuid",
    "project_id": "project-uuid",
    "name": "blue hero",
    "asset_type": "character",
    "status": "selected",
    "source_path": "project-id/raw/record.png",
    "thumbnail_path": "project-id/thumbnails/asset_thumb.png",
    "tags": ["hero", "test"],
    "created_at": "2026-05-24T10:00:00",
    "updated_at": "2026-05-24T10:00:00"
  }
}
```

### POST `/api/v1/generation/{record_id}/reproduce`

按历史记录参数复现生成。

请求体：无。

响应：同 `GenerateResponse`。

### POST `/api/v1/generation/{record_id}/variant`

基于历史记录生成变体。

请求：

```json
{
  "prompt_override": "red hero",
  "style_id_override": null,
  "target_size_override": [16, 16],
  "perspective_override": null,
  "reference_image_path": null,
  "reference_style_description": null,
  "seed_override": null,
  "candidate_count": 1
}
```

响应：同 `GenerateResponse`。

## 9. 资产接口

### GET `/api/v1/assets`

查询资产列表。

Query：

| 参数 | 类型 | 默认 | 说明 |
|---|---:|---:|---|
| `project_id` | string | 必填 | 项目 ID |
| `asset_type` | AssetType | 可选 | 类型筛选 |
| `status` | AssetStatus | 可选 | 状态筛选 |
| `tag` | string | 可选 | 标签筛选 |
| `search` | string | 可选 | 名称模糊搜索 |
| `page` | number | `1` | 页码 |
| `page_size` | number | `20` | 每页数量 |

响应：

```json
{
  "items": [
    {
      "id": "asset-uuid",
      "project_id": "project-uuid",
      "name": "blue hero",
      "asset_type": "character",
      "status": "selected",
      "source_path": "project-id/raw/record.png",
      "thumbnail_path": "project-id/thumbnails/asset_thumb.png",
      "tags": ["hero"],
      "created_at": "2026-05-24T10:00:00",
      "updated_at": "2026-05-24T10:00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

### POST `/api/v1/assets`

手动创建资产。一般前端优先使用 `generation/{id}/select`，该接口可用于导入已有 raw image。

请求：

```json
{
  "project_id": "project-uuid",
  "name": "grass tile",
  "asset_type": "tile",
  "status": "selected",
  "source_path": "project-id/raw/file.png",
  "thumbnail_path": null,
  "tags": ["tile"]
}
```

响应：`AssetResponse`，状态码 `201`。

### GET `/api/v1/assets/{asset_id}`

查询单个资产。

### PUT `/api/v1/assets/{asset_id}`

更新资产。

### PATCH `/api/v1/assets/{asset_id}`

局部更新资产。

请求示例：

```json
{
  "name": "blue hero updated",
  "tags": ["hero", "updated"],
  "status": "selected"
}
```

### DELETE `/api/v1/assets/{asset_id}`

删除资产并清理关联图片文件。

成功状态码：`204`。

### POST `/api/v1/assets/batch-delete`

批量删除资产。

请求：

```json
{
  "asset_ids": ["asset-uuid-1", "asset-uuid-2"]
}
```

响应：

```json
{
  "deleted_ids": ["asset-uuid-1", "asset-uuid-2"]
}
```

### GET `/api/v1/assets/{asset_id}/animation`

获取角色动画帧列表。当前实现对角色单图返回单帧；非角色资产返回 `INVALID_PARAM`。

响应：

```json
{
  "frames": ["/images/project-id/raw/record.png"],
  "frame_count": 1,
  "frame_delay_ms": 120,
  "actions": { "default": [0] }
}
```

### GET `/api/v1/tags`

查询项目内标签列表。

Query：

| 参数 | 类型 | 必填 |
|---|---|---:|
| `project_id` | string | 是 |

响应：

```json
{
  "tags": ["hero", "tile", "updated"]
}
```

## 10. 导出接口

### POST `/api/v1/export`

导出资产。

请求：

```json
{
  "asset_ids": ["asset-uuid"],
  "export_format": "png_single",
  "export_path": "D:/Exports",
  "sheet_layout": "linear",
  "sheet_padding": 0,
  "sheet_margin": 0,
  "tileset_columns": 8,
  "tileset_spacing": 0,
  "tileset_margin": 0
}
```

三种格式：

| export_format | 输出 |
|---|---|
| `png_single` | 每个资产复制为单独 PNG |
| `spritesheet_png_json` | `spritesheet.png` + `spritesheet.json` |
| `tileset_png_json` | `tileset.png` + `tileset.json` |

响应：

```json
{
  "export_id": "export-uuid",
  "files": [
    {
      "filename": "blue_hero.png",
      "path": "D:/Exports/blue_hero.png",
      "size": 1024
    }
  ],
  "total_size": 1024
}
```

导出成功后，相关资产状态会更新为 `exported`。

### GET `/api/v1/export/history`

查询导出历史。

Query：

| 参数 | 类型 | 必填 |
|---|---|---:|
| `project_id` | string | 否 |

响应：

```json
[
  {
    "id": "export-uuid",
    "asset_ids": ["asset-uuid"],
    "export_format": "png_single",
    "export_path": "D:/Exports",
    "metadata": {
      "project_id": "project-uuid",
      "files": []
    },
    "file_size": 1024,
    "created_at": "2026-05-24T10:00:00"
  }
]
```

### GET `/api/v1/export/{export_id}`

查询单条导出记录。

## 11. 前端调用建议

### 11.1 图片 URL 处理

后端返回的 `source_path`、`thumbnail_path` 是相对路径，前端展示时使用：

```ts
function imageUrl(path: string) {
  return `${serverOrigin}/images/${path}`;
}
```

如果后端直接返回 `image_url` 且以 `/images/` 开头，可直接拼接 origin：

```ts
const url = `${serverOrigin}${record.image_url}`;
```

### 11.2 推荐生成流程

```text
1. GET /styles 获取风格
2. POST /projects 创建或选择项目
3. 如有参考图，POST /upload 或 POST /styles/{id}/reference
4. POST /generate/preview 快速预览
5. POST /generation/{id}/select 加入资产库
6. GET /assets?project_id=xxx 刷新资产库
7. POST /export 导出
```

### 11.3 设置页注意事项

`POST /settings/test-image-api` 和 `POST /settings/test-text-api` 当前测试的是已保存配置，不接收临时请求体。前端如果想测试输入框中尚未保存的 Key，需要先 `PUT /settings` 保存，再调用测试接口。

### 11.4 角色与 Tile 参数注意事项

- `asset_type="character"` 必须传 `asset_subtype`。
- `asset_type!="character"` 时不要传 `asset_subtype`。
- `animated_spritesheet` 可传 `direction_count`、`frame_count`、`actions`。
- `target_size` 使用数组 `[w, h]`。

## 12. 验收记录

本轮验证结果：

- `python/.venv/Scripts/python.exe -m unittest tests.e2e.test_full_flow -v`：通过。
- TestClient 综合接口验收：54 项检查全部通过。
- 真实服务启动 smoke test：`GET /health` 返回 `ok`，`/openapi.json` 可访问，当前暴露 25 个 path。

未做真实外部 API 联网验收：

- 图像生成、Prompt 优化、参考图分析在综合测试中使用 mock provider 验证后端编排。
- 真实 OpenAI / Volcengine / Doubao 调用需要前端或用户配置有效 API Key 后再做联调。
