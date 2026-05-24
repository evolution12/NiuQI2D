import type { StyleProfile } from '../../types';

interface StyleCardProps {
  style: StyleProfile;
  isPreset: boolean;
  onEdit?: () => void;
  onDelete?: () => void;
  onDuplicate: () => void;
  onSelect?: () => void;
}

export function StyleCard({
  style,
  isPreset,
  onEdit,
  onDelete,
  onDuplicate,
  onSelect,
}: StyleCardProps) {
  return (
    <div
      className="nq-card"
      onClick={onSelect}
      style={{
        padding: 'var(--sp-3)',
        cursor: onSelect ? 'pointer' : 'default',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 'var(--sp-2)',
        }}
      >
        <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-1)' }}>{style.name}</span>
        {isPreset && (
          <span className="nq-tag" style={{ background: 'var(--accent-muted)', color: 'var(--accent)' }}>
            预设
          </span>
        )}
      </div>

      <div
        style={{
          display: 'flex',
          gap: 'var(--sp-1)',
          flexWrap: 'wrap',
          marginBottom: 'var(--sp-2)',
        }}
      >
        <span className="nq-tag" style={{ background: 'rgba(255,255,255,0.04)' }}>
          {style.art_style}
        </span>
        <span className="nq-tag" style={{ background: 'rgba(255,255,255,0.04)' }}>
          {style.default_size.w}x{style.default_size.h}
        </span>
        <span className="nq-tag" style={{ background: 'rgba(255,255,255,0.04)' }}>
          {style.perspective}
        </span>
      </div>

      {/* 色板预览 */}
      {style.color_palette && style.color_palette.length > 0 && (
        <div style={{ display: 'flex', gap: '2px', marginBottom: 'var(--sp-2)' }}>
          {style.color_palette.slice(0, 8).map((color, i) => (
            <div
              key={i}
              style={{
                width: '16px',
                height: '16px',
                borderRadius: 'var(--r-sm)',
                backgroundColor: color,
              }}
            />
          ))}
        </div>
      )}

      {/* 操作按钮 */}
      <div style={{ display: 'flex', gap: 'var(--sp-1)' }}>
        {!isPreset && onEdit && (
          <button className="nq-btn nq-btn--sm" onClick={(e) => { e.stopPropagation(); onEdit(); }}>
            编辑
          </button>
        )}
        <button className="nq-btn nq-btn--sm" onClick={(e) => { e.stopPropagation(); onDuplicate(); }}>
          复制
        </button>
        {!isPreset && onDelete && (
          <button className="nq-btn nq-btn--sm nq-btn--danger" onClick={(e) => { e.stopPropagation(); onDelete(); }}>
            删除
          </button>
        )}
      </div>
    </div>
  );
}
