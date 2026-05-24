import type { ExportFormat } from '../../types';

interface ExportConfigFormProps {
  format: ExportFormat;
  config: Record<string, number | string>;
  onChange: (config: Record<string, number | string>) => void;
}

export function ExportConfigForm({ format, config, onChange }: ExportConfigFormProps) {
  const update = (key: string, value: number | string) =>
    onChange({ ...config, [key]: value });

  if (format === 'png_single') {
    return (
      <div style={{ color: 'var(--text-3)', fontSize: '13px' }}>
        单图模式无需额外配置
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
            <label className="form-label">Tile 宽度</label>
            <input
              className="nq-input"
              type="number"
              min={1}
              value={config.tileW ?? 64}
              onChange={(e) => update('tileW', Number(e.target.value))}
              style={{ width: '100%' }}
            />
          </div>
          <div className="form-row" style={{ flex: 1 }}>
            <label className="form-label">Tile 高度</label>
            <input
              className="nq-input"
              type="number"
              min={1}
              value={config.tileH ?? 64}
              onChange={(e) => update('tileH', Number(e.target.value))}
              style={{ width: '100%' }}
            />
          </div>
        </div>
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
          </div>
        </div>
      </div>
    );
  }

  return null;
}
