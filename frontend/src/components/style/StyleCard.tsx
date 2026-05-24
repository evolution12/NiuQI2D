import type { StyleProfile } from '../../types';

const artStyleLabels: Record<string, string> = {
  pixel: '像素风',
  hand_drawn: '手绘风',
  cartoon: '卡通风',
  realistic: '写实风',
  custom: '自定义',
};

const perspectiveLabels: Record<string, string> = {
  top_down: '俯视',
  side_scroller: '横版',
  isometric: '等距',
};

interface StyleCardProps {
  style: StyleProfile;
  expanded: boolean;
  onToggleExpand: () => void;
  onDuplicate: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onSelect?: () => void;
}

export function StyleCard({
  style,
  expanded,
  onToggleExpand,
  onDuplicate,
  onEdit,
  onDelete,
  onSelect,
}: StyleCardProps) {
  const params = style.extra_params ?? {};
  const isPreset = style.is_preset;

  return (
    <div
      className="nq-card"
      style={{
        padding: 'var(--sp-3)',
        cursor: 'default',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 'var(--sp-2)',
        }}
      >
        <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-1)' }}>
          {style.name}
        </span>
        <div style={{ display: 'flex', gap: 'var(--sp-1)' }}>
          <span
            className="nq-tag"
            style={{
              background: isPreset ? 'var(--accent-muted)' : 'rgba(255,255,255,0.08)',
              color: isPreset ? 'var(--accent)' : 'var(--text-3)',
            }}
          >
            {isPreset ? '预设' : '自定义'}
          </span>
          {onSelect && (
            <button
              className="nq-btn nq-btn--sm nq-btn--accent"
              onClick={(e) => { e.stopPropagation(); onSelect(); }}
            >
              使用
            </button>
          )}
        </div>
      </div>

      {/* Quick info tags */}
      <div style={{ display: 'flex', gap: 'var(--sp-1)', flexWrap: 'wrap', marginBottom: 'var(--sp-2)' }}>
        <span className="nq-tag" style={{ background: 'rgba(255,255,255,0.04)' }}>
          {artStyleLabels[style.art_style] ?? style.art_style}
        </span>
        <span className="nq-tag" style={{ background: 'rgba(255,255,255,0.04)' }}>
          {perspectiveLabels[style.perspective] ?? style.perspective}
        </span>
      </div>

      {/* Color palette preview */}
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

      {/* Expanded detail */}
      {expanded && (
        <div
          style={{
            marginTop: 'var(--sp-2)',
            marginBottom: 'var(--sp-2)',
            padding: 'var(--sp-2)',
            background: 'rgba(255,255,255,0.03)',
            borderRadius: 'var(--r-md)',
            fontSize: '12px',
            color: 'var(--text-2)',
          }}
        >
          {Object.keys(params).length > 0 && (
            <div style={{ marginBottom: 'var(--sp-2)' }}>
              <div style={{ fontWeight: 500, color: 'var(--text-1)', marginBottom: '2px' }}>风格参数</div>
              {Object.entries(params).map(([k, v]) => (
                <div key={k} style={{ marginLeft: 'var(--sp-2)' }}>
                  {k}: {typeof v === 'boolean' ? (v ? '是' : '否') : String(v)}
                </div>
              ))}
            </div>
          )}
          <div>
            <div style={{ fontWeight: 500, color: 'var(--text-1)', marginBottom: '2px' }}>基本信息</div>
            <div style={{ marginLeft: 'var(--sp-2)' }}>画风: {artStyleLabels[style.art_style]}</div>
            <div style={{ marginLeft: 'var(--sp-2)' }}>视角: {perspectiveLabels[style.perspective]}</div>
            <div style={{ marginLeft: 'var(--sp-2)' }}>尺寸: {style.default_size.w}×{style.default_size.h}</div>
            {style.color_palette && (
              <div style={{ marginLeft: 'var(--sp-2)' }}>色板: {style.color_palette.join(', ')}</div>
            )}
          </div>
        </div>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', gap: 'var(--sp-1)' }}>
        <button className="nq-btn nq-btn--sm" onClick={(e) => { e.stopPropagation(); onToggleExpand(); }}>
          {expanded ? '收起' : '详情'}
        </button>
        <button className="nq-btn nq-btn--sm" onClick={(e) => { e.stopPropagation(); onDuplicate(); }}>
          复制
        </button>
        {!isPreset && (
          <>
            <button className="nq-btn nq-btn--sm" onClick={(e) => { e.stopPropagation(); onEdit(); }}>
              编辑
            </button>
            <button className="nq-btn nq-btn--sm nq-btn--danger" onClick={(e) => { e.stopPropagation(); onDelete(); }}>
              删除
            </button>
          </>
        )}
      </div>
    </div>
  );
}
