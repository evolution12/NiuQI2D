import { useState, useEffect } from 'react';
import { settingsApi } from '../services/api';
import { toast } from '../components/common/Toast';
import { ApiConfigSection } from '../components/settings/ApiConfigSection';
import { ModelSelector } from '../components/settings/ModelSelector';
import { StorageManager } from '../components/settings/StorageManager';
import type { SettingsResponse, UpdateSettingsRequest } from '../types';

const DEFAULT_SETTINGS: SettingsResponse = {
  image_api_provider: 'openai',
  image_api_key_set: false,
  image_api_model: 'gpt-image-1',
  text_api_provider: 'openai',
  text_api_key_set: false,
  text_api_model: 'gpt-4o-mini',
  preview_image_model: 'dall-e-3',
  quality_image_model: 'gpt-image-1',
  volcengine_access_key_set: false,
  volcengine_req_key: 'high_aes_general_v21',
  doubao_api_key_set: false,
  doubao_model: 'doubao-seedream-4-5-251128',
  default_style_id: null,
  default_export_path: '',
};

export function SettingsPage() {
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [pending, setPending] = useState<UpdateSettingsRequest>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    settingsApi.get().then(setSettings).catch(() => setSettings(DEFAULT_SETTINGS));
  }, []);

  const handleSave = async () => {
    if (!Object.keys(pending).length) return;
    setSaving(true);
    try {
      setSettings(await settingsApi.update(pending));
      setPending({});
      toast.success('设置已保存');
    } catch (e: any) {
      toast.error('保存失败: ' + (e.message ?? '未知错误'));
    } finally {
      setSaving(false);
    }
  };

  if (!settings) {
    return (
      <div className="page" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', color: 'var(--text-3)' }}>
        加载中...
      </div>
    );
  }

  const imageProvider = pending.image_api_provider ?? settings.image_api_provider;

  return (
    <div className="page" style={{ maxWidth: 600 }}>
      <div className="page-header">
        <h2 className="page-title">设置</h2>
      </div>

      {/* Image API config — supports OpenAI, Doubao, and Volcengine */}
      <ApiConfigSection
        title="图片 API"
        provider={imageProvider}
        keySet={settings.image_api_key_set || !!pending.image_api_key}
        model={pending.image_api_model ?? settings.image_api_model}
        volcengineKeySet={settings.volcengine_access_key_set || !!pending.volcengine_access_key}
        volcengineReqKey={pending.volcengine_req_key ?? settings.volcengine_req_key}
        doubaoKeySet={settings.doubao_api_key_set || !!pending.doubao_api_key}
        doubaoModel={pending.doubao_model ?? settings.doubao_model}
        showDoubao
        showVolcengine
        onProviderChange={(v) => setPending((p) => ({ ...p, image_api_provider: v }))}
        onKeyChange={(v) => setPending((p) => ({ ...p, image_api_key: v }))}
        onModelChange={(v) => setPending((p) => ({ ...p, image_api_model: v }))}
        onVolcengineAccessKeyChange={(v) => setPending((p) => ({ ...p, volcengine_access_key: v }))}
        onVolcengineSecretKeyChange={(v) => setPending((p) => ({ ...p, volcengine_secret_key: v }))}
        onVolcengineReqKeyChange={(v) => setPending((p) => ({ ...p, volcengine_req_key: v }))}
        onDoubaoKeyChange={(v) => setPending((p) => ({ ...p, doubao_api_key: v }))}
        onDoubaoModelChange={(v) => setPending((p) => ({ ...p, doubao_model: v }))}
        testEndpoint="testImageApi"
      />

      {/* Text API config — OpenAI / DeepSeek */}
      <ApiConfigSection
        title="文本 API"
        provider={pending.text_api_provider ?? settings.text_api_provider}
        keySet={settings.text_api_key_set || !!pending.text_api_key}
        model={pending.text_api_model ?? settings.text_api_model}
        showDoubao
        showDeepSeek
        onProviderChange={(v) => setPending((p) => ({ ...p, text_api_provider: v }))}
        onKeyChange={(v) => setPending((p) => ({ ...p, text_api_key: v }))}
        onModelChange={(v) => setPending((p) => ({ ...p, text_api_model: v }))}
        testEndpoint="testTextApi"
      />

      {/* Generation models — only relevant for OpenAI */}
      {imageProvider === 'openai' && (
        <div className="nq-section">
          <div className="nq-section-title">生成模型</div>
          <div style={{ display: 'flex', gap: 'var(--sp-4)' }}>
            <div style={{ flex: 1 }}>
              <ModelSelector
                label="快速预览"
                value={pending.preview_image_model ?? settings.preview_image_model}
                onChange={(v) => setPending((p) => ({ ...p, preview_image_model: v }))}
                options={[
                  { value: 'dall-e-3', label: 'DALL-E 3' },
                  { value: 'gpt-image-1', label: 'GPT Image 1' },
                ]}
              />
            </div>
            <div style={{ flex: 1 }}>
              <ModelSelector
                label="高质量"
                value={pending.quality_image_model ?? settings.quality_image_model}
                onChange={(v) => setPending((p) => ({ ...p, quality_image_model: v }))}
                options={[
                  { value: 'gpt-image-1', label: 'GPT Image 1' },
                  { value: 'dall-e-3', label: 'DALL-E 3 (HD)' },
                ]}
              />
            </div>
          </div>
        </div>
      )}

      {/* Default export path */}
      <div className="nq-section">
        <div className="nq-section-title">默认导出路径</div>
        <input
          className="nq-input"
          value={pending.default_export_path ?? settings.default_export_path}
          onChange={(e) => setPending((p) => ({ ...p, default_export_path: e.target.value }))}
          placeholder="选择默认导出路径"
          style={{ width: '100%' }}
        />
      </div>

      <StorageManager
        dataPath={(window as any).electronAPI?.app?.getDataPath?.() ?? '~/.niuqi2d/data'}
        usageMb={0}
        onClearCache={async () => {}}
      />

      <button
        className="nq-btn nq-btn--accent"
        onClick={handleSave}
        disabled={saving || !Object.keys(pending).length}
      >
        {saving ? '保存中...' : '保存设置'}
      </button>
    </div>
  );
}
