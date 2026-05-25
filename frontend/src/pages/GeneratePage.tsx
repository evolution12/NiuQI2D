import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../stores/appStore';
import { generationApi, backendUrl } from '../services/api';
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

type PipelineStep = 'idle' | 'base_select' | 'generating_directions' | 'done';

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

  const generationSession = useAppStore((s) => s.generationSession);
  const setGenerationSession = useAppStore((s) => s.setGenerationSession);
  const records = generationSession?.records ?? [];
  const optimizedPrompt = generationSession?.optimizedPrompt ?? '';
  const selectedId = generationSession?.selectedId ?? null;
  const setSelectedId = useCallback((id: string | null) => {
    setGenerationSession(generationSession ? { ...generationSession, selectedId: id } : null);
  }, [generationSession, setGenerationSession]);

  const [generating, setGenerating] = useState(false);
  const [imageModalSrc, setImageModalSrc] = useState<string | null>(null);
  const [addDialog, setAddDialog] = useState<{ recordId: string; name: string; tags: string } | null>(null);

  // Quality pipeline state
  const [pipelineStep, setPipelineStep] = useState<PipelineStep>('idle');
  const [, setPipelineId] = useState<string | null>(null);
  const [, setBaseRecordId] = useState<string | null>(null);
  const [directionProgress, setDirectionProgress] = useState<string>('');
  const [composedRecord, setComposedRecord] = useState<GenerationRecord | null>(null);

  const handleTypeChange = useCallback((type: AssetType, subtype: AssetSubtype | null) => {
    setAssetType(type); setAssetSubtype(subtype);
    setParams((p) => ({ ...p, asset_type: type, asset_subtype: subtype ?? undefined }));
  }, []);

  const handleGenerate = useCallback(async (preview: boolean) => {
    if (!currentProject) { toast.warning('请先选择一个项目'); return; }
    if (!prompt.trim()) { toast.warning('请输入描述'); return; }
    setGenerating(true); setSelectedId(null);
    setPipelineStep('idle');

    const usePipeline = !preview && assetSubtype === 'animated_spritesheet';

    try {
      if (usePipeline) {
        // Quality pipeline Step 1: base character candidates
        const r = await generationApi.qualityPipelineBase({
          project_id: currentProject.id, user_prompt: prompt, ...params,
        });
        setPipelineId(r.pipeline_id);
        setGenerationSession({ records: r.records, optimizedPrompt: r.optimized_prompt, selectedId: null });
        setPipelineStep('base_select');
        toast.success(`已生成 ${r.records.length} 个基座图候选，请选择一个`);
      } else {
        const fn = preview ? generationApi.generatePreview : generationApi.generate;
        const r = await fn({ project_id: currentProject.id, user_prompt: prompt, ...params, preview_mode: preview });
        setGenerationSession({ records: r.records, optimizedPrompt: r.optimized_prompt, selectedId: null });
        toast.success(`已生成 ${r.records.length} 个候选`);
      }
    } catch (e: any) { toast.error('生成失败: ' + (e.message ?? '未知错误')); }
    finally { setGenerating(false); }
  }, [currentProject, prompt, params, assetSubtype]);

  const handleSelectBase = useCallback(async () => {
    if (!selectedId || !currentProject) return;
    setBaseRecordId(selectedId);
    setPipelineStep('generating_directions');
    setGenerating(true);
    setDirectionProgress('准备生成方向动画...');

    await generationApi.qualityPipelineDirectionsStream(
      {
        base_record_id: selectedId,
        direction_count: params.direction_count,
        frame_count: params.frame_count,
        actions: params.actions,
        target_size: params.target_size,
      },
      (progress) => {
        setDirectionProgress(`${progress.current}/${progress.total} ${progress.message}`);
      },
      async (result) => {
        const successCount = result.direction_results.filter((d: any) => d.status === 'success').length;
        const totalCount = result.direction_results.length;
        setDirectionProgress(`方向生成完成: ${successCount}/${totalCount} 成功`);
        setPipelineStep('done');

        const record = await generationApi.getRecord(result.composed_record_id);
        setComposedRecord(record);
        setGenerationSession({ records: [record], optimizedPrompt: '', selectedId: record.id });

        toast.success(`方向动画已生成 (${successCount}/${totalCount})`);
        setGenerating(false);
      },
      (errMsg) => {
        toast.error('方向生成失败: ' + errMsg);
        setPipelineStep('base_select');
        setGenerating(false);
      },
    );
  }, [selectedId, currentProject, params]);

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
      setGenerationSession({ records: r.records, optimizedPrompt: r.optimized_prompt, selectedId: null }); toast.success('变体已生成');
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
              {generating ? (
                <>
                  <span className="spinner" />
                  <span>生成中...</span>
                </>
              ) : '快速预览'}
            </button>
            <button className="nq-btn nq-btn--lg" style={{ flex: 1 }} disabled={generating || !prompt.trim()} onClick={() => handleGenerate(false)}>
              {generating ? (
                <>
                  <span className="spinner" />
                  <span>生成中...</span>
                </>
              ) : '高质量'}
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

      {/* Base selection modal — must select before leaving */}
      {pipelineStep === 'base_select' && records.length > 0 && (
        <div className="modal-overlay">
          <div className="modal-panel" style={{ minWidth: '700px', maxWidth: '900px', maxHeight: '85vh', display: 'flex', flexDirection: 'column' }}>
            <div className="modal-header">
              <span className="modal-title">选择基座图</span>
            </div>
            <div className="modal-body" style={{ overflowY: 'auto' }}>
              <div style={{ marginBottom: 'var(--sp-3)', fontSize: '13px', color: 'var(--text-2)' }}>
                请选择一张作为方向动画生成的参考基座，所有方向将基于该角色的外观、颜色和比例生成。
              </div>
              <CandidateGrid records={records} optimizedPrompt={optimizedPrompt} selectedId={selectedId}
                onSelect={setSelectedId}
                onAddToLibrary={() => {}}
                onRetry={() => handleGenerate(false)} onVariant={handleVariant}
              />
            </div>
            <div className="modal-footer">
              <button className="nq-btn nq-btn--sm" onClick={() => { setPipelineStep('idle'); setPipelineId(null); setGenerationSession(null); }}>取消</button>
              <button className="nq-btn nq-btn--sm nq-btn--accent" disabled={!selectedId || generating} onClick={handleSelectBase}>
                {generating ? (
                  <>
                    <span className="spinner spinner--sm" />
                    <span>生成中...</span>
                  </>
                ) : '以此为基础生成方向动画'}
              </button>
            </div>
          </div>
        </div>
      )}

      {pipelineStep === 'generating_directions' && (
        <div style={{ marginTop: 'var(--sp-4)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--sp-3)', padding: 'var(--sp-8)' }}>
          <div className="spinner" />
          <span>{directionProgress}</span>
        </div>
      )}

      {pipelineStep === 'done' && composedRecord && (
        <div style={{ marginTop: 'var(--sp-4)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3)', marginBottom: 'var(--sp-3)' }}>
            <span style={{ fontWeight: 600 }}>方向动画生成完成</span>
            <span style={{ fontSize: '12px', color: 'var(--text-3)' }}>{directionProgress}</span>
          </div>
          {composedRecord.image_url && (
            <div
              style={{ cursor: 'pointer', display: 'inline-block', borderRadius: 'var(--r-md)', overflow: 'hidden', border: '1px solid var(--border-1)' }}
              onClick={() => setImageModalSrc(composedRecord.image_url!)}
            >
              <img
                src={backendUrl(composedRecord.image_url)}
                alt="Composed spritesheet"
                style={{ maxWidth: '100%', maxHeight: '400px', objectFit: 'contain', imageRendering: 'pixelated' }}
              />
            </div>
          )}
          <div style={{ marginTop: 'var(--sp-3)', display: 'flex', gap: 'var(--sp-2)' }}>
            <button className="nq-btn nq-btn--accent nq-btn--lg"
              onClick={() => setAddDialog({ recordId: composedRecord.id, name: '', tags: '' })}>
              加入素材库
            </button>
            <button className="nq-btn nq-btn--lg" onClick={() => { setPipelineStep('idle'); setPipelineId(null); setComposedRecord(null); }}>
              重新开始
            </button>
          </div>
        </div>
      )}

      {records.length > 0 && pipelineStep === 'idle' && (
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
