// ============================================================
// NiuQI2D TypeScript 类型定义
// 对齐 python/fastapi_app/schemas.py 和 models.py
// ============================================================

// --- 枚举类型（对齐 models.py Enum 定义） ---

/** 对齐 models.py -> ArtStyle */
export type ArtStyle = 'pixel' | 'hand_drawn' | 'cartoon' | 'realistic' | 'custom';

/** 对齐 models.py -> Perspective */
export type Perspective = 'top_down' | 'side_scroller' | 'isometric';

/** 对齐 models.py -> AssetType */
export type AssetType = 'character' | 'tile' | 'prop' | 'ui' | 'effect';

/** 对齐 models.py -> AssetSubtype */
export type AssetSubtype = 'static_image' | 'animated_spritesheet';

/** 对齐 models.py -> AssetStatus */
export type AssetStatus = 'draft' | 'selected' | 'exported' | 'discarded';

/** 对齐 models.py -> ExportFormat */
export type ExportFormat = 'png_single' | 'spritesheet_png_json' | 'tileset_png_json';

// --- 数据模型 ---

/** 对齐 schemas.py -> ProjectResponse */
export interface Project {
  id: string;
  name: string;
  style_id: string;
  created_at: string;
  updated_at: string;
}

/** 对齐 schemas.py -> ProjectDetailResponse */
export interface ProjectDetail {
  id: string;
  name: string;
  style: StyleProfile | null;
  asset_count: number;
  latest_asset_at: string | null;
  created_at: string;
  updated_at: string;
}

/** 对齐 schemas.py -> StyleProfileResponse */
export interface StyleProfile {
  id: string;
  name: string;
  art_style: ArtStyle;
  color_palette: string[] | null;
  reference_image_path: string | null;
  default_size: { w: number; h: number };
  perspective: Perspective;
  extra_params: Record<string, unknown> | null;
  is_preset: boolean;
  created_at: string;
  updated_at: string;
}

/** 对齐 schemas.py -> AssetResponse */
export interface Asset {
  id: string;
  project_id: string;
  name: string;
  asset_type: AssetType;
  status: AssetStatus;
  source_path: string;
  thumbnail_path: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

/** 对齐 schemas.py -> GenerationRecordResponse */
export interface GenerationRecord {
  id: string;
  project_id: string;
  asset_id: string | null;
  image_url: string;
  user_prompt: string;
  optimized_prompt: string;
  style_id: string;
  asset_type: AssetType;
  asset_subtype: AssetSubtype | null;
  api_provider: string;
  api_model: string;
  seed: string | null;
  postprocess_log: PostProcessLog[];
  created_at: string;
}

/** 对齐 schemas.py -> ExportRecordResponse */
export interface ExportRecord {
  id: string;
  asset_ids: string[];
  export_format: ExportFormat;
  export_path: string;
  metadata: Record<string, unknown>;
  file_size: number;
  created_at: string;
}

/** 对齐 schemas.py -> PostProcessLog */
export interface PostProcessLog {
  step: string;
  executed: boolean;
  params: Record<string, unknown>;
  duration_ms: number;
}

// --- API 请求类型 ---

/** 对齐 schemas.py -> GenerateRequest */
export interface GenerateRequest {
  project_id: string;
  user_prompt: string;
  asset_type: AssetType;
  asset_subtype?: AssetSubtype;
  style_id?: string;
  reference_image_path?: string;
  reference_style_description?: string;
  direction_count?: number;
  frame_count?: number;
  actions?: string[];
  target_size: [number, number];
  preview_mode?: boolean;
  transparent_background?: boolean;
}

/** 对齐 schemas.py -> SelectRecordRequest */
export interface SelectRecordRequest {
  name: string;
  tags: string[];
}

/** 对齐 schemas.py -> CreateStyleRequest */
export interface CreateStyleRequest {
  name: string;
  art_style: ArtStyle;
  color_palette?: string[] | null;
  default_size: { w: number; h: number };
  perspective?: Perspective;
  extra_params?: Record<string, unknown> | null;
}

/** 对齐 schemas.py -> CreateProjectRequest */
export interface CreateProjectRequest {
  name: string;
  style_id?: string | null;
}

/** 对齐 schemas.py -> ExportRequest */
export interface ExportRequest {
  asset_ids: string[];
  export_format: ExportFormat;
  export_path: string;
  sheet_layout?: string;
  sheet_padding?: number;
  sheet_margin?: number;
  tileset_columns?: number;
  tileset_spacing?: number;
  tileset_margin?: number;
  tile_size?: [number, number];
}

/** 对齐 schemas.py -> UploadResponse */
export interface UploadResponse {
  path: string;
  url: string;
  filename: string;
  size: number;
  content_type: string;
}

/** 对齐 schemas.py -> SettingsResponse */
export interface SettingsResponse {
  image_api_provider: string;
  image_api_key_set: boolean;
  image_api_model: string;
  text_api_provider: string;
  text_api_key_set: boolean;
  text_api_model: string;
  preview_image_model: string;
  quality_image_model: string;
  volcengine_access_key_set: boolean;
  volcengine_req_key: string;
  doubao_api_key_set: boolean;
  doubao_model: string;
  default_style_id: string | null;
  default_export_path: string;
}

/** 对齐 schemas.py -> UpdateSettingsRequest */
export interface UpdateSettingsRequest {
  image_api_provider?: string;
  image_api_key?: string;
  image_api_model?: string;
  text_api_provider?: string;
  text_api_key?: string;
  text_api_model?: string;
  preview_image_model?: string;
  quality_image_model?: string;
  volcengine_access_key?: string;
  volcengine_secret_key?: string;
  volcengine_req_key?: string;
  doubao_api_key?: string;
  doubao_model?: string;
  default_style_id?: string | null;
  default_export_path?: string;
}

/** 对齐 schemas.py -> ApiTestResponse */
export interface ApiTestResponse {
  success: boolean;
  message: string;
  latency_ms: number | null;
}

/** 对齐 schemas.py -> AssetListResponse */
export interface AssetListResponse {
  items: Asset[];
  total: number;
  page: number;
  page_size: number;
}

/** 对齐 schemas.py -> AnimationResponse */
export interface AnimationResponse {
  frames: string[];
  frame_count: number;
  frame_delay_ms: number;
  actions: Record<string, number[]>;
}

/** 对齐 schemas.py -> ReferenceUploadResponse */
export interface ReferenceUploadResponse {
  reference_image_path: string;
  style_description: string;
}

/** 对齐 schemas.py -> ExportResponse */
export interface ExportResponse {
  export_id: string;
  files: ExportFileInfo[];
  total_size: number;
}

export interface ExportFileInfo {
  filename: string;
  path: string;
  size: number;
}

/** 对齐 schemas.py -> TagsResponse */
export interface TagsResponse {
  tags: string[];
}

// --- 前端专用类型 ---

/** 全局任务状态 */
export interface TaskInfo {
  id: string;
  type: 'generation' | 'export' | 'postprocess';
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress?: number;
  message?: string;
}

/** 前端生成参数（组件间传递） */
export interface GenerateParams {
  asset_type: AssetType;
  asset_subtype?: AssetSubtype;
  style_id?: string;
  target_size: [number, number];
  direction_count?: number;
  frame_count?: number;
  actions?: string[];
  reference_image_path?: string;
  terrain_type?: string;
}

/** 导出配置联合类型 */
export type ExportConfig =
  | { format: 'png_single' }
  | { format: 'spritesheet_png_json'; layout: string; padding: number; margin: number }
  | { format: 'tileset_png_json'; columns: number; spacing: number; margin: number };

/** 错误响应 */
export interface ErrorResponse {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown> | null;
  };
}
