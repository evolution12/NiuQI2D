import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../stores/appStore';
import { assetApi, generationApi } from '../services/api';
import { toast } from '../components/common/Toast';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { EmptyState } from '../components/common/EmptyState';
import { AssetFilterBar } from '../components/asset/AssetFilterBar';
import { AssetGrid } from '../components/asset/AssetGrid';
import { BatchActionBar } from '../components/asset/BatchActionBar';
import { AssetDetailPanel } from '../components/asset/AssetDetailPanel';
import type { Asset, AssetType, AssetStatus, GenerationRecord, AnimationResponse } from '../types';

export function AssetLibraryPage() {
  const navigate = useNavigate();
  const currentProject = useAppStore((s) => s.currentProject);
  const [assetType, setAssetType] = useState<AssetType | ''>('');
  const [status, setStatus] = useState<AssetStatus | ''>('');
  const [search, setSearch] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [selectedTag, setSelectedTag] = useState('');
  const timerRef = useRef(0);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [detailId, setDetailId] = useState<string | null>(null);
  const [detailRecords, setDetailRecords] = useState<GenerationRecord[]>([]);
  const [detailAnim, setDetailAnim] = useState<AnimationResponse | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ type: 'single' | 'batch'; ids: string[] } | null>(null);

  const loadAssets = useCallback(async () => {
    if (!currentProject) return;
    setLoading(true);
    try {
      const r = await assetApi.list({ project_id: currentProject.id, asset_type: assetType || undefined, status: status || undefined, tag: selectedTag || undefined, search: search || undefined, page, page_size: 20 });
      setAssets(r.items); setTotal(r.total);
    } catch {} finally { setLoading(false); }
  }, [currentProject, assetType, status, selectedTag, search, page]);

  useEffect(() => { loadAssets(); }, [loadAssets]);
  useEffect(() => { if (currentProject) assetApi.getTags(currentProject.id).then((r) => setTags(r.tags)).catch(() => {}); }, [currentProject]);

  const handleSearch = (v: string) => { setSearch(v); if (timerRef.current) clearTimeout(timerRef.current); timerRef.current = window.setTimeout(() => setPage(1), 300); };
  const handleDetail = async (id: string) => {
    setDetailId(id);
    try {
      const a = await assetApi.get(id);
      const recs = await generationApi.listRecords(a.project_id);
      setDetailRecords(recs.filter((r) => r.id === id));
      if (a.asset_type === 'character') setDetailAnim(await assetApi.getAnimation(id)); else setDetailAnim(null);
    } catch {}
  };
  const handleDelete = async () => {
    if (!deleteTarget) return;
    try { if (deleteTarget.type === 'batch') await assetApi.batchDelete(deleteTarget.ids); else await assetApi.delete(deleteTarget.ids[0]); toast.success('已删除'); setSelectedIds((p) => { const n = new Set(p); deleteTarget.ids.forEach((id) => n.delete(id)); return n; }); setDeleteTarget(null); setDetailId(null); loadAssets(); }
    catch (e: any) { toast.error('操作失败: ' + (e.message ?? '未知错误')); }
  };

  if (!currentProject) return <div className="page"><EmptyState title="选择一个项目" description="从侧边栏选择一个项目查看素材" /></div>;

  return (
    <div className="page">
      <div className="page-header">
        <h2 className="page-title">素材库</h2>
        <span className="page-subtitle">{currentProject.name} &middot; {total}</span>
      </div>

      <AssetFilterBar assetType={assetType} status={status} search={search} tags={tags} selectedTag={selectedTag}
        onAssetTypeChange={(v) => { setAssetType(v); setPage(1); }} onStatusChange={(v) => { setStatus(v); setPage(1); }}
        onSearchChange={handleSearch} onTagChange={(v) => { setSelectedTag(v); setPage(1); }} />

      <BatchActionBar selectedCount={selectedIds.size} totalCount={total}
        onSelectAll={() => setSelectedIds(new Set(assets.map((a) => a.id)))}
        onExport={() => navigate('/export', { state: { selectedAssetIds: Array.from(selectedIds) } })}
        onDelete={() => setDeleteTarget({ type: 'batch', ids: Array.from(selectedIds) })}
        onClearSelection={() => setSelectedIds(new Set())} />

      <div style={{ flex: 1, overflowY: 'auto' }}>
        {loading ? <div style={{ padding: 'var(--sp-8)', textAlign: 'center', color: 'var(--text-3)', font: '400 12px var(--font)' }}>加载中...</div>
          : <AssetGrid assets={assets} selectedIds={selectedIds} onToggleSelect={(id) => setSelectedIds((p) => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; })} onDetail={handleDetail} />}
      </div>

      {total > 20 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: 'var(--sp-2)', padding: 'var(--sp-3) 0' }}>
          <button className="nq-btn nq-btn--sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>上一页</button>
          <span style={{ font: '400 11px var(--mono)', color: 'var(--text-3)', display: 'flex', alignItems: 'center' }}>{page}/{Math.ceil(total/20)}</span>
          <button className="nq-btn nq-btn--sm" disabled={page >= Math.ceil(total/20)} onClick={() => setPage((p) => p + 1)}>下一页</button>
        </div>
      )}

      {detailId && assets.find((a) => a.id === detailId) && (
        <AssetDetailPanel asset={assets.find((a) => a.id === detailId)!} records={detailRecords} animation={detailAnim}
          onClose={() => setDetailId(null)}
          onReproduce={async (id) => { try { await generationApi.reproduce(id); toast.success('重新生成中...'); } catch (e: any) { toast.error(e.message); } }}
          onVariant={async (id) => { try { await generationApi.variant(id, {}); toast.success('生成变体中...'); } catch (e: any) { toast.error(e.message); } }}
          onDelete={(id) => setDeleteTarget({ type: 'single', ids: [id] })} />
      )}

      <ConfirmDialog open={!!deleteTarget} title={deleteTarget?.type === 'batch' ? `确定删除 ${deleteTarget?.ids.length} 个素材？` : '确定删除该素材？'} message="此操作不可撤销。" danger confirmLabel="删除" onConfirm={handleDelete} onCancel={() => setDeleteTarget(null)} />
    </div>
  );
}
