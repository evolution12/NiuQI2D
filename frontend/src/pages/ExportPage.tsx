import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAppStore } from '../stores/appStore';
import { exportApi, assetApi } from '../services/api';
import { toast } from '../components/common/Toast';
import { EmptyState } from '../components/common/EmptyState';
import { AssetSelector } from '../components/export/AssetSelector';
import { ExportTypeSelector } from '../components/export/ExportTypeSelector';
import { ExportConfigForm } from '../components/export/ExportConfigForm';
import { PathSelector } from '../components/export/PathSelector';
import { ExportHistory } from '../components/export/ExportHistory';
import type { Asset, ExportFormat, ExportRecord } from '../types';

export function ExportPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const currentProject = useAppStore((s) => s.currentProject);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [format, setFormat] = useState<ExportFormat>('png_single');
  const [config, setConfig] = useState<Record<string, number | string>>({});
  const [exportPath, setExportPath] = useState('');
  const [exporting, setExporting] = useState(false);
  const [history, setHistory] = useState<ExportRecord[]>([]);

  useEffect(() => {
    const s = (location.state as { selectedAssetIds?: string[] } | null);
    if (s?.selectedAssetIds && currentProject) Promise.all(s.selectedAssetIds.map((id) => assetApi.get(id).catch(() => null))).then((r) => setAssets(r.filter((a): a is Asset => a !== null)));
  }, [location.state, currentProject]);

  useEffect(() => { if (currentProject) exportApi.getHistory(currentProject.id).then(setHistory).catch(() => {}); }, [currentProject]);

  const handleExport = async () => {
    if (!assets.length) { toast.warning('请先选择素材'); return; }
    if (!exportPath.trim()) { toast.warning('请设置导出路径'); return; }
    if (!currentProject) return;
    setExporting(true);
    try {
      await exportApi.create({ asset_ids: assets.map((a) => a.id), export_format: format, export_path: exportPath, sheet_layout: config.layout as string, sheet_padding: config.padding as number, sheet_margin: config.margin as number, tileset_columns: config.columns as number, tileset_spacing: config.spacing as number, tileset_margin: config.margin as number });
      toast.success('导出成功');
      setHistory(await exportApi.getHistory(currentProject.id));
    } catch (e: any) { toast.error('导出失败: ' + (e.message ?? '未知错误')); }
    finally { setExporting(false); }
  };

  if (!currentProject) return <div className="page"><EmptyState title="选择一个项目" description="从侧边栏选择一个项目" /></div>;

  return (
    <div className="page">
      <div className="page-header"><h2 className="page-title">导出</h2></div>

      <div className="nq-section">
        <div className="nq-section-title">已选素材 ({assets.length})</div>
        <AssetSelector assets={assets} onRemove={(id) => setAssets((p) => p.filter((a) => a.id !== id))} />
        {!assets.length && <div style={{ textAlign: 'center', marginTop: 'var(--sp-2)' }}><button className="nq-btn nq-btn--sm" onClick={() => navigate('/assets')}>浏览素材</button></div>}
      </div>

      <div className="nq-section">
        <div className="nq-section-title">导出类型</div>
        <ExportTypeSelector value={format} onChange={setFormat} />
      </div>

      <div className="nq-section">
        <div className="nq-section-title">配置</div>
        <ExportConfigForm format={format} config={config} onChange={setConfig} />
      </div>

      <PathSelector value={exportPath} onChange={setExportPath} />

      <button className="nq-btn nq-btn--accent nq-btn--lg" disabled={exporting || !assets.length || !exportPath.trim()} onClick={handleExport}>
        {exporting ? '导出中...' : '导出'}
      </button>

      <ExportHistory records={history} onOpenFolder={(p) => toast.info(`Path: ${p}`)} />
    </div>
  );
}
