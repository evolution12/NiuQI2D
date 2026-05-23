interface BatchActionBarProps {
  selectedCount: number;
  totalCount: number;
  onSelectAll: () => void;
  onExport: () => void;
  onDelete: () => void;
  onClearSelection: () => void;
}

export function BatchActionBar({
  selectedCount,
  totalCount,
  onSelectAll,
  onExport,
  onDelete,
  onClearSelection,
}: BatchActionBarProps) {
  if (selectedCount === 0) return null;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--sp-2)',
        padding: 'var(--sp-2) var(--sp-3)',
        backgroundColor: 'var(--bg-2)',
        border: '1px solid var(--accent)',
        borderRadius: 'var(--r-md)',
        fontSize: '13px',
      }}
    >
      <span style={{ color: 'var(--text-2)' }}>
        已选 {selectedCount} / {totalCount}
      </span>
      <button className="nq-btn nq-btn--sm" onClick={onSelectAll}>
        全选
      </button>
      <button className="nq-btn nq-btn--accent nq-btn--sm" onClick={onExport}>
        批量导出
      </button>
      <button className="nq-btn nq-btn--sm nq-btn--danger" onClick={onDelete}>
        批量删除
      </button>
      <button
        className="nq-btn nq-btn--sm"
        onClick={onClearSelection}
        style={{ marginLeft: 'auto' }}
      >
        取消选择
      </button>
    </div>
  );
}
