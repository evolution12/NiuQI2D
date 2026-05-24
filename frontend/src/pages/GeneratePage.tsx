import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../stores/appStore';
import { generationApi } from '../services/api';
import { toast } from '../components/common/Toast';
import { EmptyState } from '../components/common/EmptyState';
import { AssetTypeSelector } from '../components/generate/AssetTypeSelector';
import { PromptInput } from '../components/generate/PromptInput';
import { PromptPreview } from '../components/generate/PromptPreview';
import { ParamPanel } from '../components/generate/ParamPanel';
import { ReferenceUpload } from '../components/generate/ReferenceUpload';
import { CandidateGrid } from '../components/generate/CandidateGrid';
import { ImageModal } from '../components/generate/ImageModal';
import type { AssetType, AssetSubtype, GenerateParams, GenerationRecord } from '../types';

export function GeneratePage() {
  const navigate = useNavigate();
  const currentProject = useAppStore((s) => s.currentProject);

  const [assetType, setAssetType] = useState<AssetType>('character');
  const [assetSubtype, setAssetSubtype] = useState<AssetSubtype | null>('animated_spritesheet');
  const [prompt, setPrompt] = useState('');
  const [params, setParams] = useState<GenerateParams>({
    asset_type: 'character', asset_subtype: 'animated_spritesheet',
    target_size: [32, 32], direction_count: 4, frame_count: 3, actions: ['walk'],
  });
  const [referencePreview, setReferencePreview] = useState<string | null>(null);

  const [generating, setGenerating] = useState(false);
  const [records, setRecords] = useState<GenerationRecord[]>([]);
  const [optimizedPrompt, setOptimizedPrompt] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [imageModalSrc, setImageModalSrc] = useState<string | null>(null);
  const [addDialog, setAddDialog] = useState<{ recordId: string; name: string; tags: string } | null>(null);

  const handleTypeChange = useCallback((type: AssetType, subtype: AssetSubtype | null) => {
    setAssetType(type); setAssetSubtype(subtype);
    setParams((p) => ({ ...p, asset_type: type, asset_subtype: subtype ?? undefined }));
  }, []);

  const handleGenerate = useCallback(async (preview: boolean) => {
    if (!currentProject) { toast.warning('请先选择一个项目'); return; }
    if (!prompt.trim()) { toast.warning('请输入描述'); return; }
    setGenerating(true); setSelectedId(null);
    try {
      const fn = preview ? generationApi.generatePreview : generationApi.generate;
      const r = await fn({ project_id: currentProject.id, user_prompt: prompt, ...params, preview_mode: preview });
      setRecords(r.records); setOptimizedPrompt(r.optimized_prompt);
      toast.success(`已生成 ${r.records.length} 个候选`);
    } catch (e: any) { toast.error('生成失败: ' + (e.message ?? '未知错误')); }
    finally { setGenerating(false); }
  }, [currentProject, prompt, params]);

  const handleAddToLibrary = async () => {
    if (!addDialog) return;
    try {
      const tags = addDialog.tags.split(',').map((t) => t.trim()).filter(Boolean);
      await generationApi.selectRecord(addDialog.recordId, { name: addDialog.name, tags });
      toast.success('已加入素材库'); setAddDialog(null);
    } catch (e: any) { toast.error('操作失败: ' + (e.message ?? '未知错误')); }
  };

  const handleVariant = useCallback(async (id: string) => {
    if (!currentProject) return;
    setGenerating(true);
    try {
      const r = await generationApi.variant(id, { project_id: currentProject.id, ...params });
      setRecords(r.records); setOptimizedPrompt(r.optimized_prompt); toast.success('变体已生成');
    } catch (e: any) { toast.error('变体生成失败: ' + (e.message ?? '未知错误')); }
    finally { setGenerating(false); }
  }, [currentProject, params]);

  if (!currentProject) {
    return (
      <div className="page">
        <EmptyState title="选择一个项目开始" description="从侧边栏创建或选择一个项目" action={{ label: '设置', onClick: () => navigate('/settings') }} />
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <h2 className="page-title">生成</h2>
        <span className="page-subtitle">{currentProject.name}</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 'var(--sp-5)' }}>
        {/* Left column: input */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-4)' }}>
          <AssetTypeSelector value={assetType} subtype={assetSubtype} onChange={handleTypeChange} />
          <PromptInput value={prompt} onChange={setPrompt} onSubmit={() => handleGenerate(false)} disabled={generating} />

          <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
            <button className="nq-btn nq-btn--accent nq-btn--lg" style={{ flex: 1 }} disabled={generating || !prompt.trim()} onClick={() => handleGenerate(true)}>
              {generating ? '生成中...' : '快速预览'}
            </button>
            <button className="nq-btn nq-btn--lg" style={{ flex: 1 }} disabled={generating || !prompt.trim()} onClick={() => handleGenerate(false)}>
              {generating ? '生成中...' : '高质量'}
            </button>
          </div>

          <PromptPreview prompt={optimizedPrompt} />
        </div>

        {/* Right column: params */}
        <div className="nq-section" style={{ alignSelf: 'flex-start' }}>
          <div className="nq-section-title">参数</div>
          <ParamPanel assetType={assetType} assetSubtype={assetSubtype} params={params} onChange={setParams} />
          <div style={{ borderTop: '1px solid var(--border-1)', marginTop: 'var(--sp-3)', paddingTop: 'var(--sp-3)' }}>
            <ReferenceUpload
              onUploadComplete={(path) => { setReferencePreview(path); setParams((p) => ({ ...p, reference_image_path: path })); }}
              onRemove={() => { setReferencePreview(null); setParams((p) => ({ ...p, reference_image_path: undefined })); }}
              previewUrl={referencePreview} disabled={generating}
            />
          </div>
        </div>
      </div>

      {records.length > 0 && (
        <CandidateGrid records={records} optimizedPrompt={optimizedPrompt} selectedId={selectedId}
          onSelect={setSelectedId}
          onAddToLibrary={(id) => setAddDialog({ recordId: id, name: '', tags: '' })}
          onRetry={() => handleGenerate(false)} onVariant={handleVariant}
        />
      )}

      {imageModalSrc && <ImageModal src={imageModalSrc} onClose={() => setImageModalSrc(null)} />}

      {/* Add to library dialog */}
      {addDialog && (
        <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) setAddDialog(null); }}>
          <div className="modal-panel">
            <div className="modal-header"><span className="modal-title">加入素材库</span></div>
            <div className="modal-body">
              <div className="form-row">
                <label className="form-label">素材名称</label>
                <input className="nq-input" value={addDialog.name} onChange={(e) => setAddDialog((p) => p ? { ...p, name: e.target.value } : null)} placeholder="为素材命名" autoFocus style={{ width: '100%' }} />
              </div>
              <div className="form-row">
                <label className="form-label">标签（逗号分隔）</label>
                <input className="nq-input" value={addDialog.tags} onChange={(e) => setAddDialog((p) => p ? { ...p, tags: e.target.value } : null)} placeholder="弓箭手, 角色, 森林" style={{ width: '100%' }} />
              </div>
            </div>
            <div className="modal-footer">
              <button className="nq-btn nq-btn--sm" onClick={() => setAddDialog(null)}>取消</button>
              <button className="nq-btn nq-btn--sm nq-btn--accent" onClick={handleAddToLibrary} disabled={!addDialog.name.trim()}>添加</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
