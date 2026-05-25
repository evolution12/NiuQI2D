import type {
  Asset,
  AssetListResponse,
  AnimationResponse,
  TagsResponse,
  CreateProjectRequest,
  CreateStyleRequest,
  ExportRequest,
  ExportResponse,
  GenerateRequest,
  GenerationRecord,
  Project,
  ProjectDetail,
  QualityPipelineBaseResponse,
  QualityPipelineDirectionRequest,
  QualityPipelineDirectionResponse,
  SelectRecordRequest,
  SettingsResponse,
  StyleProfile,
  UpdateSettingsRequest,
  UploadResponse,
  ApiTestResponse,
  ReferenceUploadResponse,
  ExportRecord,
  ErrorResponse,
} from '../types';

/**
 * HTTP 客户端封装，通过 Electron preload 获取 Python 端口
 */
class ApiClient {
  baseUrl: string = '';

  async ensureReady(): Promise<void> {
    if (this.baseUrl) return;

    const electronAPI = (window as any).electronAPI;
    if (electronAPI?.python?.getPort) {
      // Wait for Python backend to be ready (port may be null initially)
      let port = await electronAPI.python.getPort();
      const deadline = Date.now() + 30000; // wait up to 30s
      while (!port && Date.now() < deadline) {
        await new Promise((r) => setTimeout(r, 500));
        port = await electronAPI.python.getPort();
      }
      if (!port) throw new Error('Python backend failed to start');
      this.baseUrl = `http://127.0.0.1:${port}/api/v1`;
    } else {
      // Fallback for non-Electron mode
      this.baseUrl = 'http://127.0.0.1:8000/api/v1';
    }
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
    await this.ensureReady();

    const headers: Record<string, string> = {};
    let processedBody: BodyInit | undefined;

    if (body instanceof FormData) {
      processedBody = body;
    } else if (body !== undefined) {
      headers['Content-Type'] = 'application/json';
      processedBody = JSON.stringify(body);
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: processedBody,
      cache: method === 'GET' ? 'no-store' : undefined,
    });

    if (!response.ok) {
      const errorData: ErrorResponse = await response.json().catch(() => ({
        error: {
          code: 'UNKNOWN_ERROR',
          message: `请求失败: ${response.status}`,
          details: null,
        },
      }));
      throw new ApiError(
        errorData.error.code,
        errorData.error.message,
        response.status,
      );
    }

    // 204 No Content — no body to parse
    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  async get<T>(path: string): Promise<T> {
    return this.request<T>('GET', path);
  }

  async post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>('POST', path, body);
  }

  async put<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>('PUT', path, body);
  }

  async delete<T = void>(path: string): Promise<T> {
    return this.request<T>('DELETE', path);
  }

  async postFormData<T>(path: string, formData: FormData): Promise<T> {
    return this.request<T>('POST', path, formData);
  }
}

export class ApiError extends Error {
  code: string;
  status: number;

  constructor(code: string, message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
  }
}

export const api = new ApiClient();

/** 将 /images/... 等后端静态路径补全为完整 URL */
let _urlCacheBust = Date.now();
export function bustImageUrlCache(): void { _urlCacheBust = Date.now(); }

export function backendUrl(path: string): string {
  if (!path || path.startsWith('http')) return path;
  // Use api.baseUrl if available, otherwise fall back to default
  const base = (api.baseUrl || 'http://127.0.0.1:8000').replace(/\/api\/v1\/?$/, '');
  const sep = path.includes('?') ? '&' : '?';
  return `${base}${path.startsWith('/') ? '' : '/'}${path}${sep}_t=${_urlCacheBust}`;
}

// ============================================================
// API 方法：各模块封装
// ============================================================

// --- Health ---
export const healthApi = {
  check: () =>
    fetch(
      (window as any).electronAPI
        ? `http://127.0.0.1:${(window as any).electronAPI.python?.getPort?.() ?? 8000}/health`
        : 'http://127.0.0.1:8000/health',
    ).then((r) => r.json()),
};

// --- Upload ---
export const uploadApi = {
  upload: (file: File, purpose: string, options?: { project_id?: string; style_id?: string }) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('purpose', purpose);
    if (options?.project_id) formData.append('project_id', options.project_id);
    if (options?.style_id) formData.append('style_id', options.style_id);
    return api.postFormData<UploadResponse>('/upload', formData);
  },
};

// --- Generation ---
export const generationApi = {
  generate: (req: GenerateRequest) => api.post<{ records: GenerationRecord[]; optimized_prompt: string }>('/generate', req),
  generatePreview: (req: GenerateRequest) => api.post<{ records: GenerationRecord[]; optimized_prompt: string }>('/generate/preview', { ...req, preview_mode: true }),
  getRecord: (id: string) => api.get<GenerationRecord>(`/generation/${id}`),
  listRecords: (projectId: string) => api.get<GenerationRecord[]>(`/generation?project_id=${projectId}`),
  selectRecord: (id: string, req: SelectRecordRequest) => api.post<{ asset: Asset }>(`/generation/${id}/select`, req),
  reproduce: (id: string) => api.post<{ records: GenerationRecord[]; optimized_prompt: string }>(`/generation/${id}/reproduce`),
  variant: (id: string, req: Partial<GenerateRequest>) => api.post<{ records: GenerationRecord[]; optimized_prompt: string }>(`/generation/${id}/variant`, req),

  // Quality pipeline
  qualityPipelineBase: (req: GenerateRequest) =>
    api.post<QualityPipelineBaseResponse>('/generate/quality-pipeline/base', req),
  /**
   * Stream direction generation. Calls onProgress for each step, onDone/onError at end.
   */
  qualityPipelineDirectionsStream: async (
    req: QualityPipelineDirectionRequest,
    onProgress: (data: { current: number; total: number; direction: string; message: string }) => void,
    onDone: (data: QualityPipelineDirectionResponse) => void,
    onError: (msg: string) => void,
  ) => {
    await api.ensureReady();
    const response = await fetch(`${api.baseUrl}/generate/quality-pipeline/directions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    if (!response.ok || !response.body) {
      const text = await response.text().catch(() => '请求失败');
      onError(text);
      return;
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let finalResult: QualityPipelineDirectionResponse | null = null;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const data = JSON.parse(line);
          if (data.type === 'progress') {
            onProgress({ current: data.current, total: data.total, direction: data.direction, message: data.message });
          } else if (data.type === 'done') {
            finalResult = data as QualityPipelineDirectionResponse;
          } else if (data.type === 'error') {
            onError(data.message);
            return;
          }
        } catch {
          // ignore malformed lines
        }
      }
    }
    if (buffer.trim()) {
      try {
        const data = JSON.parse(buffer.trim());
        if (data.type === 'done') finalResult = data as QualityPipelineDirectionResponse;
        else if (data.type === 'error') { onError(data.message); return; }
      } catch { /* ignore */ }
    }
    if (finalResult) onDone(finalResult);
    else onError('未收到生成结果');
  },
};

// --- Assets ---
export const assetApi = {
  list: (params: { project_id: string; asset_type?: string; status?: string; tag?: string; search?: string; page?: number; page_size?: number; sort_by?: string; sort_order?: string }) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined) query.set(k, String(v)); });
    return api.get<AssetListResponse>(`/assets?${query}`);
  },
  get: (id: string) => api.get<Asset>(`/assets/${id}`),
  update: (id: string, data: Partial<Asset>) => api.put<Asset>(`/assets/${id}`, data),
  delete: (id: string) => api.delete(`/assets/${id}`),
  batchDelete: (ids: string[]) => api.post('/assets/batch-delete', { asset_ids: ids }),
  getAnimation: (id: string) => api.get<AnimationResponse>(`/assets/${id}/animation`),
  getTags: (projectId: string) => api.get<TagsResponse>(`/tags?project_id=${projectId}`),
};

// --- Projects ---
export const projectApi = {
  list: () => api.get<Project[]>('/projects'),
  get: (id: string) => api.get<ProjectDetail>(`/projects/${id}`),
  create: (req: CreateProjectRequest) => api.post<Project>('/projects', req),
  update: (id: string, req: Partial<CreateProjectRequest>) => api.put<Project>(`/projects/${id}`, req),
  delete: (id: string) => api.delete(`/projects/${id}`),
};

// --- Styles ---
export const styleApi = {
  list: () => api.get<StyleProfile[]>('/styles'),
  get: (id: string) => api.get<StyleProfile>(`/styles/${id}`),
  create: (req: CreateStyleRequest) => api.post<StyleProfile>('/styles', req),
  update: (id: string, req: Partial<CreateStyleRequest>) => api.put<StyleProfile>(`/styles/${id}`, req),
  delete: (id: string) => api.delete(`/styles/${id}`),
  uploadReference: (id: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.postFormData<ReferenceUploadResponse>(`/styles/${id}/reference`, formData);
  },
  deleteReference: (id: string) => api.delete(`/styles/${id}/reference`),
};

// --- Export ---
export const exportApi = {
  create: (req: ExportRequest) => api.post<ExportResponse>('/export', req),
  getHistory: (projectId: string) => api.get<ExportRecord[]>(`/export/history?project_id=${projectId}`),
  get: (id: string) => api.get<ExportRecord>(`/export/${id}`),
  delete: (id: string) => api.delete(`/export/${id}`),
};

// --- Settings ---
export const settingsApi = {
  get: () => api.get<SettingsResponse>('/settings'),
  update: (req: UpdateSettingsRequest) => api.put<SettingsResponse>('/settings', req),
  testImageApi: (body: Record<string, string>) => api.post<ApiTestResponse>('/settings/test-image-api', body),
  testTextApi: (body: Record<string, string>) => api.post<ApiTestResponse>('/settings/test-text-api', body),
};
