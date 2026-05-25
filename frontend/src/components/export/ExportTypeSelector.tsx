import type { Asset, ExportFormat } from '../../types';

interface ExportTypeSelectorProps {
  value: ExportFormat;
  onChange: (format: ExportFormat) => void;
  assets: Asset[];
}

const allExportTypes: { format: ExportFormat; label: string; desc: string; allowed: (assets: Asset[]) => boolean }[] = [
  { format: 'png_single', label: '单图 PNG', desc: '每个素材输出独立 PNG 文件', allowed: (assets) => assets.every((a) => a.asset_type !== 'map') },
  { format: 'spritesheet_png_json', label: 'Sprite Sheet + JSON', desc: '多帧动画拼合为 Sprite Sheet，附 JSON 元数据', allowed: (assets) => assets.every((a) => a.asset_type === 'character' && a.asset_subtype === 'animated_spritesheet') },
  { format: 'tileset_png_json', label: 'Tileset + JSON', desc: '地图切分为 Tileset，附 JSON 分块信息', allowed: (assets) => assets.every((a) => a.asset_type === 'map') },
];

export function ExportTypeSelector({ value, onChange, assets }: ExportTypeSelectorProps) {
  return (
    <div style={{ display: 'flex', gap: 'var(--sp-2)' }}>
      {allExportTypes.map(({ format, label, desc, allowed }) => {
        const disabled = !allowed(assets);
        return (
          <button
            key={format}
            className={value === format ? 'nq-btn nq-btn--accent' : 'nq-btn'}
            onClick={() => !disabled && onChange(format)}
            disabled={disabled}
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              padding: 'var(--sp-3)',
              gap: 'var(--sp-1)',
              opacity: disabled ? 0.35 : 1,
            }}
          >
            <span style={{ fontSize: '13px', fontWeight: 500 }}>{label}</span>
            <span style={{ fontSize: '11px', color: 'var(--text-3)', fontWeight: 400 }}>
              {desc}
            </span>
          </button>
        );
      })}
    </div>
  );
}
