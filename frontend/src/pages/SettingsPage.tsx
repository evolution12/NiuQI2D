import { useState, useEffect } from 'react';
import { settingsApi } from '../services/api';
import { toast } from '../components/common/Toast';
import { ApiConfigSection } from '../components/settings/ApiConfigSection';
import { ModelSelector } from '../components/settings/ModelSelector';
import { StorageManager } from '../components/settings/StorageManager';
import type { SettingsResponse, UpdateSettingsRequest } from '../types';

export function SettingsPage() {
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [pending, setPending] = useState<UpdateSettingsRequest>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    settingsApi.get().then(setSettings).catch(() =>
      setSettings({ image_api_provider: 'openai', image_api_key_set: false, image_api_model: 'gpt-image-1', text_api_provider: 'openai', text_api_key_set: false, text_api_model: 'gpt-4o-mini', preview_image_model: 'dall-e-3', quality_image_model: 'gpt-image-1', default_style_id: null, default_export_path: '' })
    );
  }, []);

  const handleSave = async () => {
    if (!Object.keys(pending).length) return;
    setSaving(true);
    try { setSettings(await settingsApi.update(pending)); setPending({}); toast.success('Saved'); }
    catch (e: any) { toast.error('Failed: ' + (e.message ?? 'unknown')); }
    finally { setSaving(false); }
  };

  if (!settings) return <div className="page" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', color: 'var(--text-3)' }}>Loading...</div>;

  return (
    <div className="page" style={{ maxWidth: 600 }}>
      <div className="page-header"><h2 className="page-title">Settings</h2></div>

      <ApiConfigSection title="Image API" provider={pending.image_api_provider ?? settings.image_api_provider}
        keySet={settings.image_api_key_set || !!pending.image_api_key} model={pending.image_api_model ?? settings.image_api_model}
        onProviderChange={(v) => setPending((p) => ({ ...p, image_api_provider: v }))} onKeyChange={(v) => setPending((p) => ({ ...p, image_api_key: v }))}
        onModelChange={(v) => setPending((p) => ({ ...p, image_api_model: v }))} testEndpoint="testImageApi" />

      <ApiConfigSection title="Text API" provider={pending.text_api_provider ?? settings.text_api_provider}
        keySet={settings.text_api_key_set || !!pending.text_api_key} model={pending.text_api_model ?? settings.text_api_model}
        onProviderChange={(v) => setPending((p) => ({ ...p, text_api_provider: v }))} onKeyChange={(v) => setPending((p) => ({ ...p, text_api_key: v }))}
        onModelChange={(v) => setPending((p) => ({ ...p, text_api_model: v }))} testEndpoint="testTextApi" />

      <div className="nq-section">
        <div className="nq-section-title">Generation models</div>
        <div style={{ display: 'flex', gap: 'var(--sp-4)' }}>
          <div style={{ flex: 1 }}><ModelSelector label="Quick preview" value={pending.preview_image_model ?? settings.preview_image_model}
            onChange={(v) => setPending((p) => ({ ...p, preview_image_model: v }))} options={[{ value: 'dall-e-3', label: 'DALL-E 3' }, { value: 'gpt-image-1', label: 'GPT Image 1' }]} /></div>
          <div style={{ flex: 1 }}><ModelSelector label="High quality" value={pending.quality_image_model ?? settings.quality_image_model}
            onChange={(v) => setPending((p) => ({ ...p, quality_image_model: v }))} options={[{ value: 'gpt-image-1', label: 'GPT Image 1' }, { value: 'dall-e-3', label: 'DALL-E 3 (HD)' }]} /></div>
        </div>
      </div>

      <div className="nq-section">
        <div className="nq-section-title">Default export path</div>
        <input className="nq-input" value={pending.default_export_path ?? settings.default_export_path}
          onChange={(e) => setPending((p) => ({ ...p, default_export_path: e.target.value }))} placeholder="Choose default export path" style={{ width: '100%' }} />
      </div>

      <StorageManager dataPath={(window as any).electronAPI?.app?.getDataPath?.() ?? '~/.niuqi2d/data'} usageMb={0} onClearCache={async () => {}} />

      <button className="nq-btn nq-btn--accent" onClick={handleSave} disabled={saving || !Object.keys(pending).length}>
        {saving ? 'Saving...' : 'Save settings'}
      </button>
    </div>
  );
}
