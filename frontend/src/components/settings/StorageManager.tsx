import { useState } from 'react';
import { toast } from '../common/Toast';
import { ConfirmDialog } from '../common/ConfirmDialog';

interface StorageManagerProps {
  dataPath: string;
  usageMb: number;
  onClearCache: () => Promise<void>;
}

export function StorageManager({ dataPath, usageMb, onClearCache }: StorageManagerProps) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [clearing, setClearing] = useState(false);

  const handleClear = async () => {
    setClearing(true);
    try {
      await onClearCache();
      toast.success('缓存清理完成');
    } catch (e: any) {
      toast.error('清理失败：' + (e.message ?? '未知错误'));
    } finally {
      setClearing(false);
      setShowConfirm(false);
    }
  };

  return (
    <div className="nq-section">
      <div className="nq-section-title">存储管理</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-3)' }}>
        <div className="form-row">
          <label className="form-label">数据目录</label>
          <div style={{ display: 'flex', gap: 'var(--sp-2)', alignItems: 'center' }}>
            <span style={{ fontSize: '13px', color: 'var(--text-2)', flex: 1 }}>
              {dataPath}
            </span>
            <button
              className="nq-btn nq-btn--sm"
              onClick={() => {
                const electronAPI = (window as any).electronAPI;
                if (electronAPI?.fs?.selectDirectory) {
                  toast.info('请在文件管理器中查看');
                }
              }}
            >
              打开目录
            </button>
          </div>
        </div>

        <div className="form-row">
          <label className="form-label">占用空间</label>
          <span style={{ fontSize: '13px', color: 'var(--text-2)' }}>
            {usageMb > 0 ? `${usageMb.toFixed(1)} MB` : '未知'}
          </span>
        </div>

        <button
          className="nq-btn nq-btn--sm"
          onClick={() => setShowConfirm(true)}
          disabled={clearing}
        >
          {clearing ? '清理中...' : '清理缓存'}
        </button>
      </div>

      <ConfirmDialog
        open={showConfirm}
        title="确认清理缓存？"
        message="将删除临时文件和缩略图缓存，不会删除已保存的资产和导出文件。"
        confirmLabel="清理"
        onConfirm={handleClear}
        onCancel={() => setShowConfirm(false)}
      />
    </div>
  );
}
