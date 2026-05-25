import { useState, useEffect } from 'react';
import { styleApi } from '../../services/api';
import { toast } from '../common/Toast';
import { ConfirmDialog } from '../common/ConfirmDialog';
import { StyleCard } from './StyleCard';
import { StyleEditor } from './StyleEditor';
import type { StyleProfile, CreateStyleRequest } from '../../types';
import { compactStyleOptions } from '../../utils/styleOptions';

interface StyleLibraryProps {
  onClose: () => void;
  onSelect?: (style: StyleProfile) => void;
}

export function StyleLibrary({ onClose, onSelect }: StyleLibraryProps) {
  const [styles, setStyles] = useState<StyleProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [showEditor, setShowEditor] = useState(false);
  const [editingStyle, setEditingStyle] = useState<StyleProfile | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const loadStyles = async () => {
    try {
      const result = await styleApi.list();
      setStyles(result);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStyles();
  }, []);

  const handleCreate = async (data: CreateStyleRequest) => {
    try {
      await styleApi.create(data);
      toast.success('风格创建成功');
      setShowEditor(false);
      loadStyles();
    } catch (e: any) {
      toast.error('创建失败：' + (e.message ?? '未知错误'));
    }
  };

  const handleUpdate = async (data: CreateStyleRequest) => {
    if (!editingStyle) return;
    try {
      await styleApi.update(editingStyle.id, data);
      toast.success('风格更新成功');
      setEditingStyle(null);
      loadStyles();
    } catch (e: any) {
      toast.error('更新失败：' + (e.message ?? '未知错误'));
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await styleApi.delete(deleteTarget);
      toast.success('风格已删除');
      setDeleteTarget(null);
      loadStyles();
    } catch (e: any) {
      toast.error('删除失败：' + (e.message ?? '未知错误'));
    }
  };

  const handleDuplicate = async (style: StyleProfile) => {
    try {
      await styleApi.create({
        name: `${style.name} (副本)`,
        art_style: style.art_style,
        default_size: style.default_size,
        perspective: style.perspective,
        color_palette: style.color_palette,
        extra_params: style.extra_params,
      });
      toast.success('风格已复制');
      loadStyles();
    } catch (e: any) {
      toast.error('复制失败：' + (e.message ?? '未知错误'));
    }
  };

  const handleEditCustom = (style: StyleProfile) => {
    setEditingStyle(style);
  };

  return (
    <div
      className="modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="modal-panel"
        style={{
          width: '720px',
          maxHeight: '80vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div className="modal-header">
          <span className="modal-title">风格库</span>
          <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
            <button className="nq-btn nq-btn--accent nq-btn--sm" onClick={() => { setShowEditor(true); setEditingStyle(null); }}>
              创建风格
            </button>
            <button className="nq-btn nq-btn--sm" onClick={onClose}>
              关闭
            </button>
          </div>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: 'var(--sp-4)' }}>
          {loading ? (
            <div style={{ textAlign: 'center', color: 'var(--text-3)', padding: 'var(--sp-8)' }}>
              加载中...
            </div>
          ) : showEditor || editingStyle ? (
            <StyleEditor
              initial={editingStyle ? {
                id: editingStyle.id,
                name: editingStyle.name,
                art_style: editingStyle.art_style,
                default_size: editingStyle.default_size,
                perspective: editingStyle.perspective,
                color_palette: editingStyle.color_palette,
                extra_params: editingStyle.extra_params,
              } : undefined}
              onSave={editingStyle ? handleUpdate : handleCreate}
              onCancel={() => { setShowEditor(false); setEditingStyle(null); }}
            />
          ) : (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
                gap: 'var(--sp-3)',
              }}
            >
              {compactStyleOptions(styles).map((style) => (
                <StyleCard
                  key={style.id}
                  style={style}
                  expanded={expandedId === style.id}
                  onToggleExpand={() => setExpandedId(expandedId === style.id ? null : style.id)}
                  onDuplicate={() => handleDuplicate(style)}
                  onEdit={() => handleEditCustom(style)}
                  onDelete={() => setDeleteTarget(style.id)}
                  onSelect={onSelect ? () => { onSelect(style); onClose(); } : undefined}
                />
              ))}
              {styles.length === 0 && (
                <div style={{ color: 'var(--text-3)', textAlign: 'center', padding: 'var(--sp-8)' }}>
                  暂无风格，点击"创建风格"开始
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Delete confirm */}
      <ConfirmDialog
        open={deleteTarget !== null}
        title="确认删除该风格？"
        message="删除后无法恢复"
        danger
        confirmLabel="删除"
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
