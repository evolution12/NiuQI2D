import type { ExportFormat } from '../../types';

interface ExportConfigFormProps {
  format: ExportFormat;
  config: Record<string, number | string>;
  onChange: (config: Record<string, number | string>) => void;
}

const hintStyle: React.CSSProperties = {
  color: 'var(--text-3)',
  fontSize: '11px',
  marginTop: '2px',
};

export function ExportConfigForm({ format, config, onChange }: ExportConfigFormProps) {
  const update = (key: string, value: number | string) =>
    onChange({ ...config, [key]: value });

  if (format === 'png_single') {
    return (
      <div style={{ color: 'var(--text-3)', fontSize: '13px' }}>
        每个素材导出为独立的 PNG 文件，无需额外配置
      </div>
    );
  }

  if (format === 'spritesheet_png_json') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-3)' }}>
        <div className="form-row">
          <label className="form-label">排列方式</label>
          <select
            className="nq-select"
            value={config.layout ?? 'by_action'}
            onChange={(e) => update('layout', e.target.value)}
            style={{ width: '100%' }}
          >
            <option value="by_action">按动作分行</option>
            <option value="by_direction">按方向分行</option>
            <option value="linear">线性排列</option>
          </select>
          <div style={hintStyle}>每行对应一个动作或方向，列对应帧序列</div>
        </div>
        <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
          <div className="form-row" style={{ flex: 1 }}>
            <label className="form-label">帧间距</label>
            <input
              className="nq-input"
              type="number"
              min={0}
              value={config.padding ?? 0}
              onChange={(e) => update('padding', Number(e.target.value))}
              style={{ width: '100%' }}
            />
            <div style={hintStyle}>相邻帧之间的像素间隔，0 为无间距</div>
          </div>
          <div className="form-row" style={{ flex: 1 }}>
            <label className="form-label">画布补边</label>
            <input
              className="nq-input"
              type="number"
              min={0}
              value={config.margin ?? 0}
              onChange={(e) => update('margin', Number(e.target.value))}
              style={{ width: '100%' }}
            />
            <div style={hintStyle}>整张 Sprite Sheet 四周的留白像素</div>
          </div>
        </div>
      </div>
    );
  }

  if (format === 'tileset_png_json') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-3)' }}>
        <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
          <div className="form-row" style={{ flex: 1 }}>
            <label className="form-label">列数</label>
            <input
              className="nq-input"
              type="number"
              min={1}
              value={config.columns ?? 8}
              onChange={(e) => update('columns', Number(e.target.value))}
              style={{ width: '100%' }}
            />
            <div style={hintStyle}>每行排列的 Tile 数量</div>
          </div>
          <div className="form-row" style={{ flex: 1 }}>
            <label className="form-label">Tile 间距</label>
            <input
              className="nq-input"
              type="number"
              min={0}
              value={config.spacing ?? 0}
              onChange={(e) => update('spacing', Number(e.target.value))}
              style={{ width: '100%' }}
            />
            <div style={hintStyle}>相邻 Tile 之间的像素间隔</div>
          </div>
          <div className="form-row" style={{ flex: 1 }}>
            <label className="form-label">画布 Margin</label>
            <input
              className="nq-input"
              type="number"
              min={0}
              value={config.margin ?? 0}
              onChange={(e) => update('margin', Number(e.target.value))}
              style={{ width: '100%' }}
            />
            <div style={hintStyle}>Tileset 整体四周的留白像素</div>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
